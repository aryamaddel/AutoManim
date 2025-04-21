import re, os, subprocess
from flask import Flask, render_template, request, jsonify, session
from utils.gemini_client import GeminiClient
from utils.groq_client import GroqClient

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_secret_key")


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template(
        "index.html",
        user_input=request.form.get("text") if request.method == "POST" else None,
    )


@app.route("/execute_manim", methods=["POST"])
def execute_manim():
    try:
        manim_code = request.json.get("code")
        if not manim_code:
            return jsonify({"error": "No code provided"}), 400

        # Setup and save the scene file
        scene_path = os.path.join(app.static_folder, "manim_code.py")
        os.makedirs(app.static_folder, exist_ok=True)
        with open(scene_path, "w") as f:
            f.write(manim_code)

        # Extract scene name
        scene_name_match = re.search(r"class\s+(\w+)\((.*?)Scene\):", manim_code)
        if not scene_name_match:
            return jsonify({"error": "Could not find scene class in the code"}), 400
        scene_name = scene_name_match.group(1)

        print(f"--- Starting Manim: {scene_name} ---")
        process = subprocess.Popen(
            ["manim", "-ql", scene_path, scene_name],
            cwd=app.static_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        _, stderr = process.communicate()

        # Handle process results directly
        if process.returncode != 0:
            print(f"--- Manim Failed: {stderr} ---")
            return jsonify(
                {
                    "status": "error",
                    "message": "Animation creation failed. Please try again.",
                }
            )

        # Look for the video file
        video_dir = os.path.join(
            app.static_folder, "media", "videos", "manim_code", "480p15"
        )
        if not os.path.exists(video_dir):
            return jsonify(
                {
                    "status": "error",
                    "message": "Animation creation failed. Please try again.",
                }
            )

        videos = [
            f
            for f in os.listdir(video_dir)
            if f.startswith(scene_name) and f.endswith(".mp4")
        ]

        if not videos:
            return jsonify(
                {"status": "error", "message": "No video found for the scene"}
            )

        # Get the latest video
        latest = max(
            videos,
            key=lambda f: os.path.getmtime(os.path.join(video_dir, f)),
        )
        video_url = f"/static/media/videos/manim_code/480p15/{latest}"

        print(f"--- Manim Process: successful ---")
        return jsonify({"status": "success", "video_url": video_url})

    except Exception as e:
        print(f"Exception: {str(e)}")
        return jsonify({"status": "error", "message": "Animation creation failed"}), 500


@app.route("/generate_manim_code", methods=["POST"])
def generate_manim_code():
    try:
        desc = request.json.get("manimPrompt")
        if not desc:
            return jsonify({"error": "No animation description provided"}), 400

        # Update chat history
        if "chat_history" not in session:
            session["chat_history"] = []
        session["chat_history"].append({"role": "user", "content": desc})

        # Try AI clients
        code = None
        errors = []
        for Client in [GeminiClient, GroqClient]:
            try:
                code = Client().generate_code(desc, session["chat_history"])
                break
            except Exception as e:
                errors.append(f"{Client.__name__} error: {str(e)}")

        if not code:
            return jsonify({"error": "All AI APIs failed"}), 500

        # Clean up the code
        code = re.sub(r"<think>.*?</think>", "", code, flags=re.DOTALL)
        code = re.sub(r"^```python\s*|^```\s*|\s*```$", "", code).strip()
        if "class MainScene" not in code:
            code = (
                "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        "
                + code
            )

        # Save to session
        session["chat_history"].append({"role": "assistant", "content": code})
        session.modified = True
        return jsonify(
            {"success": True, "code": code, "chat_history": session["chat_history"]}
        )

    except Exception as e:
        print(f"Code generation failed: {str(e)}")
        return jsonify({"error": "Code generation failed"}), 500


@app.route("/get_chat_history", methods=["GET"])
def get_chat_history():
    if "chat_history" not in session:
        session["chat_history"] = []
    return jsonify({"chat_history": session["chat_history"]})


@app.route("/clear_chat_history", methods=["POST"])
def clear_chat_history():
    session["chat_history"] = []
    session.modified = True
    return jsonify({"success": True})
