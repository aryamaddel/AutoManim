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

# Queue for passing results between threads
result_queue = queue.Queue()
# Flag to indicate if the Manim process is running
manim_running = False


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
        while not result_queue.empty():
            result_queue.get()
        manim_running = True

        # Define the manim execution process inline
        def execute_manim_thread():
            global manim_running

            try:
                # Simple print statement for debugging
                print("\n--- Starting Manim Animation Process ---")

                # Start Manim process
                process = subprocess.Popen(
                    ["manim", "-ql", scene_path, scene_name],
                    cwd=app.static_folder,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                # Simple print statement for debugging
                print(f"--- Manim process started for scene: {scene_name} ---")

                # Wait for process to complete
                stdout, stderr = process.communicate()

                # Check for errors
                if process.returncode != 0:
                    print(
                        f"--- Manim Process Failed with code {process.returncode} ---"
                    )
                    print(f"Error output: {stderr}")
                    result_queue.put(
                        {"status": "error", "message": f"Process failed: {stderr}"}
                    )
                    manim_running = False
                    return

                # Find the generated video
                video_url, error = find_video_file(app.static_folder, scene_name)
                if error:
                    print(f"--- Video file error: {error} ---")
                    result_queue.put({"status": "error", "message": error})
                    manim_running = False
                    return

                # Success - video is ready
                print(f"--- Manim Process Completed Successfully: {video_url} ---")
                result_queue.put({"status": "success", "video_url": video_url})

            except Exception as e:
                print(f"System error: [{e.__class__.__name__}] {str(e)}")
                result_queue.put({"status": "error", "message": str(e)})
            finally:
                manim_running = False

        # Start execution in background thread
        threading.Thread(target=execute_manim_thread, daemon=True).start()

        return jsonify({"success": True, "message": "Manim execution started"})

    except Exception as e:
        manim_running = False
        return jsonify({"error": str(e)}), 500


@app.route("/check_manim_status", methods=["GET"])
def check_manim_status():
    """Simple endpoint to check if animation is ready"""
    try:
        if not result_queue.empty():
            result = result_queue.get()
            return jsonify(result)

        if manim_running:
            return jsonify({"status": "processing"})
        else:
            return jsonify({"status": "idle"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/generate_manim_code", methods=["POST"])
def generate_manim_code():
    try:
        animation_description = request.json.get("manimPrompt")

        if not animation_description:
            return jsonify({"error": "No animation description provided"}), 400

        if "chat_history" not in session:
            session["chat_history"] = []

        session["chat_history"].append(
            {"role": "user", "content": animation_description}
        )

        code = None
        error_messages = []

        clients = [GeminiClient, GroqClient]
        code = None
        error_messages = []

        for ClientClass in clients:
            try:
                client = ClientClass()
                code = client.generate_code(
                    animation_description, session["chat_history"]
                )
                break
            except Exception as e:
                error_messages.append(f"{ClientClass.__name__} error: {str(e)}")
                continue

        if not code:
            return (
                jsonify({"error": f"All APIs failed: {', '.join(error_messages)}"}),
                500,
            )

        # Clean up code
        code = clean_generated_code(code)

        # Add assistant response to history
        session["chat_history"].append({"role": "assistant", "content": code})
        session.modified = True

        return jsonify(
            {"success": True, "code": code, "chat_history": session["chat_history"]}
        )

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
        code = (
            "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        "
            + code
        )

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
