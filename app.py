from flask import Flask, render_template, request, jsonify
import subprocess
import os

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

        # Use a fixed file path in the static folder
        scene_path = os.path.join(app.static_folder, "manim_code.py")

        # Write the code to the file
        with open(scene_path, "w") as f:
            f.write(manim_code)

        # Execute manim command
        subprocess.run(
            ["manim", "-ql", scene_path],
            cwd=app.static_folder,
            capture_output=True,
            text=True,
        )

        # Look for the generated video in the expected location
        video_dir = os.path.join(
            app.static_folder, "media", "videos", "manim_code", "480p15"
        )

        video_files = [f for f in os.listdir(video_dir) if f.endswith(".mp4")]

        video_filename = video_files[0]

        # Construct the correct URL for the video
        video_url = f"/static/media/videos/manim_code/480p15/{video_filename}"

        # Log the video URL for debugging
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
