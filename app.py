import re, os, subprocess
from flask import Flask, render_template, request, jsonify, session
from utils.gemini_client import GeminiClient
from utils.groq_client import GroqClient

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_secret_key")

# Global state
manim_running, manim_result = False, None


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

        if process.returncode != 0:
            print(f"--- Manim Process Failed: {stderr} ---")
            # Only show a generic error message to the user
            manim_result = {
                "status": "error",
                "message": "Animation creation failed. Please try again.",
            }
        else:
            video_dir = os.path.join(
                app.static_folder, "media", "videos", "manim_code", "480p15"
            )
            if not os.path.exists(video_dir):
                manim_result = {
                    "status": "error",
                    "message": "Animation creation failed. Please try again.",
                }
            else:
                videos = [
                    f
                    for f in os.listdir(video_dir)
                    if f.startswith(scene_name) and f.endswith(".mp4")
                ]
                if not videos:
                    manim_result = {
                        "status": "error",
                        "message": "No video found for the scene",
                    }
                else:
                    latest = max(
                        videos,
                        key=lambda f: os.path.getmtime(os.path.join(video_dir, f)),
                    )
                    video_url = f"/static/media/videos/manim_code/480p15/{latest}"
                    manim_result = {"status": "success", "video_url": video_url}

            print(f"--- Manim Process: {manim_result['status']} ---")

        manim_running = False
        return jsonify({"success": True, "message": "Manim execution started"})

    except Exception as e:
        manim_running = False
        manim_result = {"status": "error", "message": str(e)}
        return jsonify({"error": str(e)}), 500


@app.route("/check_manim_status", methods=["GET"])
def check_manim_status():
    global manim_result, manim_running
    if manim_result:
        result, manim_result = manim_result, None
        return jsonify(result)
    return jsonify({"status": "processing" if manim_running else "idle"})


@app.route("/generate_manim_code", methods=["POST"])
def generate_manim_code():
    try:
        desc = request.json.get("manimPrompt")
        if not desc:
            return jsonify({"error": "No animation description provided"}), 400

        if "chat_history" not in session:
            session["chat_history"] = []
        session["chat_history"].append({"role": "user", "content": desc})

        # Try AI clients
        code, errs = None, []
        for Client in [GeminiClient, GroqClient]:
            try:
                code = Client().generate_code(desc, session["chat_history"])
                break
            except Exception as e:
                errs.append(f"{Client.__name__} error: {str(e)}")

        if not code:
            return jsonify({"error": f"All APIs failed: {', '.join(errs)}"}), 500

        code = re.sub(r"<think>.*?</think>", "", code, flags=re.DOTALL)
        code = re.sub(r"^```python\s*|^```\s*|\s*```$", "", code).strip()
        if "class MainScene" not in code:
            code = (
                "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        "
                + code
            )

        session["chat_history"].append({"role": "assistant", "content": code})
        session.modified = True

        return jsonify(
            {"success": True, "code": code, "chat_history": session["chat_history"]}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
