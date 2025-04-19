import re
import os
import subprocess
import threading
import queue
import time
from flask import Flask, render_template, request, jsonify, session, Response
from utils.gemini_client import GeminiClient
from utils.groq_client import GroqClient

app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY", "dev_secret_key"
)  # Set a secret key for sessions

# Queue for passing logs between threads
log_queue = queue.Queue()
# Flag to indicate if the Manim process is running
manim_running = False

# Patterns to include in general logs
LOG_PATTERNS = [
    "Latex", "Played", "Scene", 
    "Writing", "Written", "Rendered", "Animation"
]

# Collect traceback for proper error display
class ErrorTracker:
    def __init__(self):
        self.in_traceback = False
        self.traceback_lines = []
        self.error_type = None
        self.error_message = None
    
    def process_line(self, line):
        """Process a line and determine if it's part of a traceback"""
        # Start of a new traceback
        if "Traceback (most recent call last):" in line:
            self.in_traceback = True
            self.traceback_lines = [line]
            return None  # Don't output yet, collect the entire traceback
        
        # We're in a traceback, collect lines
        if self.in_traceback:
            self.traceback_lines.append(line)
            
            # If this line contains the error type and message (last line of traceback)
            if ": " in line and not line.startswith(" ") and not line.startswith("File "):
                parts = line.split(": ", 1)
                if len(parts) == 2:
                    self.error_type = parts[0].strip()
                    self.error_message = parts[1].strip()
                    self.in_traceback = False
                    
                    # Format the entire traceback nicely and return it
                    return self.format_traceback()
                    
            return None  # Still collecting traceback
            
        # Normal line, not in traceback
        return line

    def format_traceback(self):
        """Format the collected traceback into a readable format"""
        if not self.traceback_lines:
            return None
        
        formatted = ["ERROR: ⚠️ Manim Execution Failed ⚠️"]
        formatted.append(f"ERROR: {self.error_type}: {self.error_message}")
        
        # Extract file and line info from traceback
        file_lines = []
        for line in self.traceback_lines:
            if line.strip().startswith("File "):
                # Extract filename, line number and context
                match = re.search(r'File "([^"]+)", line (\d+), in (.+)', line)
                if match:
                    filename = os.path.basename(match.group(1))
                    line_num = match.group(2)
                    context = match.group(3)
                    file_lines.append(f"ERROR: 📄 {filename}:{line_num} in {context}")
        
        # Add file info if we found any
        if file_lines:
            formatted.append("ERROR: Stack trace:")
            formatted.extend(file_lines)
        
        return formatted

def process_log_line(line, error_tracker):
    """Process a log line with error tracking"""
    line = line.strip()
    if not line:
        return None
        
    # First check if this is part of a traceback
    result = error_tracker.process_line(line)
    if result is not None:
        if isinstance(result, list):
            return result  # Return list of formatted traceback lines
        return result  # Regular processed line
    
    # Check if this is an error line
    if "error" in line.lower() or "exception" in line.lower():
        return f"ERROR: {line}"
    
    # Check if this is a warning
    if "warning" in line.lower():
        return f"WARNING: {line}"
        
    # Check for other important logs
    if any(pattern.lower() in line.lower() for pattern in LOG_PATTERNS):
        return line
        
    # By default, include the line as is for better visibility into the process
    return line

def find_video_file(static_folder, scene_name):
    """Find the generated video file"""
    video_dir = os.path.join(static_folder, "media", "videos", "manim_code", "480p15")

    if not os.path.exists(video_dir):
        return None, "Video directory not found"

    video_files = [
        f
        for f in os.listdir(video_dir)
        if f.startswith(scene_name) and f.endswith(".mp4")
    ]

    if not video_files:
        return None, "No video found for the scene"

    latest_video = max(
        video_files, key=lambda f: os.path.getmtime(os.path.join(video_dir, f))
    )

    return f"/static/media/videos/manim_code/480p15/{latest_video}", None


@app.route("/", methods=["GET", "POST"])
def index():
    user_input = None
    if request.method == "POST":
        user_input = request.form.get("text")
    return render_template("index.html", user_input=user_input)


@app.route("/execute_manim", methods=["POST"])
def execute_manim():
    global manim_running
    try:
        manim_code = request.json.get("code")
        if not manim_code:
            return jsonify({"error": "No code provided"}), 400

        scene_path = os.path.join(app.static_folder, "manim_code.py")
        os.makedirs(app.static_folder, exist_ok=True)

        with open(scene_path, "w") as f:
            f.write(manim_code)

        scene_name_match = re.search(r"class\s+(\w+)\((.*?)Scene\):", manim_code)
        if not scene_name_match:
            return jsonify({"error": "Could not find scene class in the code"}), 400

        scene_name = scene_name_match.group(1)

        # Clear the queue and set running flag
        while not log_queue.empty():
            log_queue.get()
        manim_running = True

        # Define the manim execution process inline
        def execute_manim_thread():
            global manim_running
            error_detected = False
            error_tracker = ErrorTracker()
            
            try:
                # Start Manim process
                process = subprocess.Popen(
                    ["manim", "-ql", scene_path, scene_name],
                    cwd=app.static_folder,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Stream logs with better error tracking
                for line in process.stdout:
                    processed = process_log_line(line, error_tracker)
                    
                    # Skip lines that don't need to be displayed
                    if processed is None:
                        continue
                    
                    # Handle list of lines (formatted traceback)
                    if isinstance(processed, list):
                        for trace_line in processed:
                            log_queue.put(trace_line)
                            if trace_line.startswith("ERROR:"):
                                error_detected = True
                    else:
                        log_queue.put(processed)
                        if processed.startswith("ERROR:"):
                            error_detected = True
                
                # Handle process completion
                process.wait()
                if process.returncode != 0:
                    if not error_detected:
                        log_queue.put(f"ERROR: Manim execution failed with code {process.returncode}")
                    
                    manim_running = False
                    return
                    
                # Find the generated video only if no errors were detected
                if not error_detected:
                    video_url, error = find_video_file(app.static_folder, scene_name)
                    if error:
                        log_queue.put(f"ERROR: {error}")
                        manim_running = False
                        return
                        
                    # Success - video is ready
                    log_queue.put(f"VIDEO_READY:{video_url}")
                    log_queue.put("SUCCESS: Animation rendered successfully! ✨")
                else:
                    log_queue.put("ERROR: Animation could not be rendered due to errors")
                    manim_running = False
                
            except Exception as e:
                log_queue.put(f"ERROR: System error: [{e.__class__.__name__}] {str(e)}")
            finally:
                manim_running = False
        
        # Start execution in background thread
        threading.Thread(target=execute_manim_thread, daemon=True).start()
        
        return jsonify({"success": True, "message": "Manim execution started"})

    except Exception as e:
        manim_running = False
        return jsonify({"error": str(e)}), 500


@app.route("/stream_logs", methods=["GET"])
def stream_logs():
    def generate():
        last_log = None
        while True:
            try:
                # Get new log or timeout after 0.5s
                log = log_queue.get(timeout=0.5)
                yield f"data: {log}\n\n"
            except queue.Empty:
                # Process completed check
                if not manim_running and last_log != "STREAM_END":
                    yield "data: STREAM_END\n\n"
                    last_log = "STREAM_END"
                    break
                # Keep alive
                yield "data: HEARTBEAT\n\n"
            time.sleep(0.1)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/generate_manim_code", methods=["POST"])
def generate_manim_code():
    try:
        animation_description = request.json.get("manimPrompt")

        if not animation_description:
            return jsonify({"error": "No animation description provided"}), 400

        # Initialize chat history if it doesn't exist
        if "chat_history" not in session:
            session["chat_history"] = []

        # Add user message to history
        session["chat_history"].append(
            {"role": "user", "content": animation_description}
        )

        code = None
        error_messages = []

        # Try clients in sequence until one succeeds
        clients = [GeminiClient, GroqClient]
        code = None
        error_messages = []

        for ClientClass in clients:
            try:
                client = ClientClass()
                code = client.generate_code(animation_description, session["chat_history"])
                break  # Stop if successful
            except Exception as e:
                error_messages.append(f"{ClientClass.__name__} error: {str(e)}")
                continue
        
        if not code:
            return jsonify({"error": f"All APIs failed: {', '.join(error_messages)}"}), 500

        # Clean up code
        code = clean_generated_code(code)

        # Add assistant response to history
        session["chat_history"].append({"role": "assistant", "content": code})
        session.modified = True

        return jsonify({"success": True, "code": code, "chat_history": session["chat_history"]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def clean_generated_code(code):
    """Clean generated code by removing markdown and ensuring MainScene class exists"""
    code = re.sub(r"<think>.*?</think>", "", code, flags=re.DOTALL)
    code = re.sub(r"^```python\s*", "", code)
    code = re.sub(r"^```\s*", "", code)
    code = re.sub(r"\s*```$", "", code)
    code = code.strip()

    if "class MainScene" not in code:
        code = "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        " + code

    return code

@app.route("/get_chat_history", methods=["GET"])
def get_chat_history():
    """Endpoint to retrieve the current chat history"""
    if "chat_history" not in session:
        session["chat_history"] = []
    return jsonify({"chat_history": session["chat_history"]})


@app.route("/clear_chat_history", methods=["POST"])
def clear_chat_history():
    """Endpoint to clear the chat history"""
    session["chat_history"] = []
    session.modified = True
    return jsonify({"success": True})
