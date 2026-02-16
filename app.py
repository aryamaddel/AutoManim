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

SYSTEM_PROMPT = """You are an expert Manim developer. Write a complete, runnable Manim script for the requested animation.
The script must define a Scene class named 'GenScene'. Use ONLY standard Manim Community Edition (v0.18+) classes and methods.
Output ONLY the python code, no markdown block or explanations. Do not use ```python``` or ``````.
Example valid code structure:
from manim import *
class GenScene(Scene):
    def construct(self):
        c = Circle(color=RED)
        c.move_to(RIGHT * 2)
        self.play(Create(c))
"""


def main():
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = input("Enter animation description: ").strip()

    if not prompt:
        print("No prompt provided. Exiting.")
        return

    print("Generating code...")
    try:
        response = client.chat.completions.create(
            model="openrouter/free",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        code = response.choices[0].message.content or ""

        # Clean up code
        code = (
            code.strip()
            .removeprefix("```python")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )

        if not code:
            print("Failed to generate code.")
            return

        output_file = Path("generated_scene.py")
        output_file.write_text(code, encoding="utf-8")
        print(f"Code saved to {output_file.absolute()}")

        print("Rendering...")
        subprocess.run(
            [sys.executable, "-m", "manim", "-ql", str(output_file), "GenScene"],
            check=False,  # Don't throw exception on failure, just print error
        )
        print("\nRender complete!")

    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
