import re
import os
import subprocess
from flask import Flask, render_template, request, jsonify, session

from utils.gemini_client import GeminiClient
from utils.groq_client import GroqClient

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_secret_key")

# Global state
manim_running = False
manim_result = None


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
    return render_template(
        "index.html",
        user_input=request.form.get("text") if request.method == "POST" else None,
    )


@app.route("/execute_manim", methods=["POST"])
def execute_manim():
    global manim_running, manim_result
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

        # Reset state and run manim
        manim_running, manim_result = True, None
        print(f"--- Starting Manim Animation Process for scene: {scene_name} ---")

        process = subprocess.Popen(
            ["manim", "-ql", scene_path, scene_name],
            cwd=app.static_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout, stderr = process.communicate()

        # Process result
        if process.returncode != 0:
            print(f"--- Manim Process Failed: {stderr} ---")
            manim_result = {"status": "error", "message": f"Process failed: {stderr}"}
        else:
            video_url, error = find_video_file(app.static_folder, scene_name)
            manim_result = (
                {"status": "error", "message": error}
                if error
                else {"status": "success", "video_url": video_url}
            )
            print(f"--- Manim Process: {manim_result['status']} ---")

        manim_running = False
        return jsonify({"success": True, "message": "Manim execution started"})

    except Exception as e:
        manim_running = False
        manim_result = {"status": "error", "message": str(e)}
        return jsonify({"error": str(e)}), 500


@app.route("/check_manim_status", methods=["GET"])
def check_manim_status():
    """Check if animation is ready"""
    global manim_result, manim_running

    if manim_result is not None:
        result = manim_result
        manim_result = None
        return jsonify(result)

    return jsonify({"status": "processing" if manim_running else "idle"})


@app.route("/generate_manim_code", methods=["POST"])
def generate_manim_code():
    try:
        animation_description = request.json.get("manimPrompt")
        if not animation_description:
            return jsonify({"error": "No animation description provided"}), 400

        # Initialize and update chat history
        if "chat_history" not in session:
            session["chat_history"] = []
        session["chat_history"].append(
            {"role": "user", "content": animation_description}
        )

        # Try available AI clients
        clients = [GeminiClient, GroqClient]
        code, error_messages = None, []

        for ClientClass in clients:
            try:
                client = ClientClass()
                code = client.generate_code(
                    animation_description, session["chat_history"]
                )
                break
            except Exception as e:
                error_messages.append(f"{ClientClass.__name__} error: {str(e)}")

        if not code:
            return (
                jsonify({"error": f"All APIs failed: {', '.join(error_messages)}"}),
                500,
            )

        # Clean up code and update history
        code = clean_generated_code(code)
        session["chat_history"].append({"role": "assistant", "content": code})
        session.modified = True

        return jsonify(
            {"success": True, "code": code, "chat_history": session["chat_history"]}
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def clean_generated_code(code):
    """Clean generated code"""
    code = re.sub(r"<think>.*?</think>", "", code, flags=re.DOTALL)
    code = re.sub(r"^```python\s*|^```\s*|\s*```$", "", code).strip()

    if "class MainScene" not in code:
        code = (
            "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        "
            + code
        )

    return code


@app.route("/get_chat_history", methods=["GET"])
def get_chat_history():
    """Get current chat history"""
    if "chat_history" not in session:
        session["chat_history"] = []
    return jsonify({"chat_history": session["chat_history"]})


@app.route("/clear_chat_history", methods=["POST"])
def clear_chat_history():
    """Clear chat history"""
    session["chat_history"] = []
    session.modified = True
    return jsonify({"success": True})
