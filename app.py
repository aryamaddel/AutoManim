import re
from flask import Flask, render_template, request, jsonify
import subprocess
import os
import time

app = Flask(__name__)


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

        scene_path = os.path.join(app.static_folder, "manim_code.py")

        with open(scene_path, "w") as f:
            f.write(manim_code)

        scene_name_match = re.search(r"class\s+(\w+)\(Scene\):", manim_code)
        if not scene_name_match:
            return jsonify({"error": "No valid scene class found in the code."}), 400

        scene_name = scene_name_match.group(1)

        subprocess.run(
            ["manim", "-qh", scene_path, scene_name],
            cwd=app.static_folder,
            capture_output=True,
            text=True,
        )

        video_dir = os.path.join(
            app.static_folder, "media", "videos", "manim_code", "1080p60"
        )

        video_files = [
            f
            for f in os.listdir(video_dir)
            if f.startswith(scene_name) and f.endswith(".mp4")
        ]

        if not video_files:
            return jsonify({"error": "No video found for the scene."}), 404

        latest_video = max(
            video_files, key=lambda f: os.path.getmtime(os.path.join(video_dir, f))
        )

        video_url = f"/static/media/videos/manim_code/1080p60/{latest_video}"

        print(f"Video URL: {video_url}")

        return jsonify({"success": True, "video_url": video_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


from groq import Groq


def generate_manim_code(animation_description: str, error_message=None) -> str:
    """Generate runnable Manim code using Groq API"""
    groq = Groq()

    system_content = """You are a Manim code generator that ONLY outputs executable Python code.

    IMPORTANT INSTRUCTIONS:
    1. Return ONLY Python code - no explanations, no thinking, no markdown
    2. Include all necessary imports (from manim import *)
    3. Create a Scene class named 'MainScene' with proper construct method
    4. Follow exact Manim syntax and conventions
    5. Do not include main blocks or code fences (```)
    6. Ensure animations work correctly with proper syntax
    7. Do not output ANY text that isn't part of the final code

    Example correct response format:
    from manim import *

    class MainScene(Scene):
        def construct(self):
            # Your code here
            pass
    """

    if error_message:
        system_content += f"""
        
        The previous code generated had errors. Here's the error message:
        {error_message}
        
        Please fix these errors and provide corrected code.
        """

    user_content = f"Generate Manim code for: {animation_description}"
    if error_message:
        user_content = f"Fix the Manim code for: {animation_description}"

    chat_completion = groq.chat.completions.create(
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        model="deepseek-r1-distill-llama-70b",
        temperature=0.2,
        stream=False,
    )

    code = chat_completion.choices[0].message.content

    code = re.sub(r"<think>.*?</think>", "", code, flags=re.DOTALL)
    code = re.sub(r"^```python\s*", "", code)
    code = re.sub(r"^```\s*", "", code)
    code = re.sub(r"\s*```$", "", code)

    if "class MainScene" not in code:
        code = (
            "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        "
            + code
        )

    return code
