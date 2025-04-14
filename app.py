import re
import os
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from utils.gemini_client import GeminiClient
from utils.groq_client import GroqClient

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_secret_key")  # Set a secret key for sessions

@app.route("/", methods=["GET", "POST"])
def index():
    user_input = None
    if request.method == "POST":
        user_input = request.form.get("text")
    return render_template("index.html", user_input=user_input)


@app.route("/execute_manim", methods=["POST"])
def execute_manim():
    try:
        manim_code = request.json.get("code")
        if not manim_code:
            return jsonify({"error": "No code provided"}), 400

        if not os.path.exists(app.static_folder):
            os.makedirs(app.static_folder)

        scene_path = os.path.join(app.static_folder, "manim_code.py")

        with open(scene_path, "w") as f:
            f.write(manim_code)

        scene_name_match = re.search(r"class\s+(\w+)\((.*?)Scene\):", manim_code)
        if not scene_name_match:
            return jsonify({"error": "Could not find scene class in the code"}), 400

        scene_name = scene_name_match.group(1)

        result = subprocess.run(
            ["manim", "-ql", scene_path, scene_name],
            cwd=app.static_folder,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return jsonify({"error": result.stderr}), 500

        video_dir = os.path.join(
            app.static_folder, "media", "videos", "manim_code", "480p15"
        )

        if not os.path.exists(video_dir):
            return jsonify({"error": "Video directory not found"}), 404

        video_files = [
            f
            for f in os.listdir(video_dir)
            if f.startswith(scene_name) and f.endswith(".mp4")
        ]

        if not video_files:
            return jsonify({"error": "No video found for the scene"}), 404

        latest_video = max(
            video_files, key=lambda f: os.path.getmtime(os.path.join(video_dir, f))
        )

        video_url = f"/static/media/videos/manim_code/480p15/{latest_video}"
        return jsonify({"success": True, "video_url": video_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
        session["chat_history"].append({"role": "user", "content": animation_description})
        
        code = None
        error_messages = []
        
        # Try Gemini first, then fall back to Groq
        try:
            client = GeminiClient()
            code = client.generate_code(animation_description, session["chat_history"])
        except Exception as gemini_error:
            error_messages.append(f"Gemini API error: {str(gemini_error)}")
            # Try Groq as fallback
            try:
                client = GroqClient()
                code = client.generate_code(animation_description, session["chat_history"])
            except Exception as groq_error:
                error_messages.append(f"Groq API error: {str(groq_error)}")
                return jsonify({"error": f"Both APIs failed: {', '.join(error_messages)}"}), 500

        if code:
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
                
            # Add assistant response to history
            session["chat_history"].append({"role": "assistant", "content": code})
            # Save the session
            session.modified = True

            return jsonify({
                "success": True, 
                "code": code,
                "chat_history": session["chat_history"]
            })
        else:
            return jsonify({"error": "Failed to generate valid code"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
