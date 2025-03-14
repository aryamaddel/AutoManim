from flask import Flask, render_template, request
from groq import Groq
import subprocess
import os
import re

app = Flask(__name__, template_folder="template")


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


def generate_and_run_manim(
    animation_description: str, max_attempts=6, filename="manim_animation.py"
):
    """Generate Manim code, run it, and fix errors if needed"""
    attempt = 1
    error_message = None
    final_code = None
    success = False

    file_path = os.path.join(os.getcwd(), filename)
    print(f"Using file for all attempts: {file_path}")

    while attempt <= max_attempts:
        print(f"\nAttempt {attempt} of {max_attempts}")

        code = generate_manim_code(animation_description, error_message)
        final_code = code  # Store the latest code

        print("\nGenerated Code Preview:")
        print("----------------------")
        print(code)

        with open(file_path, "w") as f:
            f.write(code)

        print(f"Updated Manim code in: {file_path}")

        cmd = f"manim -pql {file_path} MainScene"
        print(f"Running: {cmd}")

        result = subprocess.run(cmd, shell=True, text=True, capture_output=True)

        print("Output:")
        print(result.stdout)

        success = result.returncode == 0

        if success:
            print(f"Manim animation completed successfully on attempt {attempt}!")
            break
        else:
            if result.stderr:
                print("Errors:")
                print(result.stderr)
                error_message = result.stderr

            attempt += 1
            print(f"Attempt {attempt-1} failed. Sending error to LLM for correction.")

    if not success:
        print(f"Failed to generate working Manim code after {max_attempts} attempts.")

    return success, file_path, final_code



@app.route("/", methods=["GET", "POST"])
def index():
    user_input = None
    if request.method == "POST":
        user_input = request.form.get("text")
        print(f"User input: {user_input}")
        generate_and_run_manim(user_input)

    return render_template("index.html", user_input=user_input)


if __name__ == "__main__":
    app.run()
