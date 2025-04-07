import re
import os
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__)

gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


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

        scene_name_match = re.search(r"class\s+(\w+)\(Scene\):", manim_code)
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
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "API key not configured"}), 500
        system_instruction = """You are a Manim code generator that ONLY outputs executable Python code.
        IMPORTANT INSTRUCTIONS:
        1. Return ONLY Python code - no explanations, no thinking, no markdown
        2. Include all necessary imports (from manim import *)
        3. Create a Scene class named 'MainScene' with proper construct method
        4. Follow exact Manim syntax and conventions
        5. Do not include main blocks or code fences (```)
        6. Ensure animations work correctly with proper syntax
        7. Do not output ANY text that isn't part of the final code"""

        model = "gemini-2.5-pro-exp-03-25"

        generate_content_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
        )

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=animation_description)],
            ),
        ]

        try:
            response = gemini_client.models.generate_content(
                model=model,
                contents=contents,
                config=generate_content_config,
            )

            if not hasattr(response, "text") or response.text is None:

                return (
                    jsonify(
                        {"error": "Failed to generate code: Empty response from API"}
                    ),
                    500,
                )

            code = response.text

        except Exception as api_error:

            return jsonify({"error": f"Failed to generate code: {str(api_error)}"}), 500

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

            return jsonify({"success": True, "code": code})
        else:
            return jsonify({"error": "Failed to generate valid code"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500
