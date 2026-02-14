import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize API client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)


def generate_manim_code(prompt: str) -> str:
    """Generate Manim code using OpenRouter with streaming output."""
    system_prompt = (
        "You are an expert Manim developer. "
        "Write a complete, runnable Manim script for the requested animation. "
        "The script must define a Scene class named 'GenScene'. "
        "Use ONLY standard Manim Community Edition (v0.18+) classes and methods. "
        "Example valid code structure:\n"
        "from manim import *\n"
        "class GenScene(Scene):\n"
        "    def construct(self):\n"
        "        # Your animation code here\n"
        "        c = Circle(color=RED)\n"
        "        c.move_to(RIGHT * 2)\n"
        "        self.play(Create(c))\n"
        "STRICT RULES:\n"
        "1. Use `obj.move_to(point)` NOT `obj.position(point)`\n"
        "2. Use `obj.set_color(color)` NOT `obj.color(color)`\n"
        "3. Do NOT use fake methods like `plot_point`, `shape`, or `note`.\n"
        "4. Always use `self.play()` to animate.\n"
        "5. Use `Text('content')` for text, not `Label`.\n"
        "Output ONLY the python code, no markdown block or explanations. "
        "Do not use ```python``` or ``````."
    )

    try:
        response_stream = client.chat.completions.create(
            model="openrouter/free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            stream=True,
        )

        full_code = ""
        actual_model = "unknown"
        print("\nRequest sent to openrouter/free...")

        first_chunk = True

        for chunk in response_stream:
            if first_chunk:
                actual_model = getattr(chunk, "model", "unknown")
                print(f"Model responding: {actual_model}\n\nGenerating code:\n")
                first_chunk = False

            content = chunk.choices[0].delta.content or ""
            print(content, end="", flush=True)
            full_code += content

        print("\n\nDone.\n")

        # Clean up any potential markdown formatting if model ignored instructions
        clean_code = full_code.strip()
        if clean_code.startswith("```python"):
            clean_code = clean_code.replace("```python", "", 1)
        if clean_code.startswith("```"):
            clean_code = clean_code.replace("```", "", 1)
        if clean_code.endswith("```"):
            clean_code = clean_code[:-3]

        return clean_code.strip()

    except Exception as e:
        print(f"\nError generating code: {e}")
        return None


def main():
    if len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:])
    else:
        print("Welcome to AutoManim CLI (OpenRouter Edition)")
        user_prompt = input("Enter animation description: ")

    if not user_prompt:
        print("No prompt provided. Exiting.")
        return

    code = generate_manim_code(user_prompt)
    if not code:
        print("Failed to generate code.")
        return

    output_file = Path("generated_scene.py")
    output_file.write_text(code, encoding="utf-8")
    print(f"Code saved to {output_file.absolute()}")

    run_now = input("Render animation now? (Y/n): ").strip().lower()
    if run_now in ["", "y", "yes"]:
        print("Rendering...")
        # Render low quality preview (-ql)
        try:
            subprocess.run(
                [sys.executable, "-m", "manim", "-ql", str(output_file), "GenScene"],
                check=True,
            )
            print("\nRender complete!")
        except subprocess.CalledProcessError as e:
            print(f"\nRender failed with exit code {e.returncode}")
            print("Check the generated code for errors.")


if __name__ == "__main__":
    main()
