import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.spinner import Spinner
from rich.live import Live
from rich.columns import Columns
from rich.rule import Rule
from rich import box
from rich.table import Table
from rich.prompt import Prompt
import time


load_dotenv()
console = Console()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

SYSTEM_PROMPT = """You are an expert Manim developer. Write a complete, runnable Manim script for the requested animation.
The script must define a Scene class named 'GenScene'. Use ONLY standard Manim Community Edition (v0.18+) classes and methods.
Output ONLY the python code, no markdown block or explanations. Do not use ```python``` or ``````."""

MODEL = "arcee-ai/trinity-large-preview:free"

# ── Helpers ──────────────────────────────────────────────────────────────────


def print_banner():
    banner = Text()
    banner.append(
        "  ▄▄▄       █    ██ ▄▄▄█████▓ ▒█████      ███▄ ▄███▓ ▄▄▄       ███▄    █  ██▓ ███▄ ▄███▓\n",
        style="bold bright_magenta",
    )
    banner.append(
        "  ▒████▄     ██  ▓██▒▓  ██▒ ▓▒▒██▒  ██▒   ▓██▒▀█▀ ██▒▒████▄     ██ ▀█   █ ▓██▒▓██▒▀█▀ ██▒\n",
        style="bold magenta",
    )
    banner.append(
        "  ▒██  ▀█▄  ▓██  ▒██░▒ ▓██░ ▒░▒██░  ██▒   ▓██    ▓██░▒██  ▀█▄  ▓██  ▀█ ██▒▒██▒▓██    ▓██░\n",
        style="bold bright_blue",
    )
    banner.append(
        "  ░██▄▄▄▄██ ▓▓█  ░██░░ ▓██▓ ░ ▒██   ██░   ▒██    ▒██ ░██▄▄▄▄██ ▓██▒  ▐▌██▒░██░▒██    ▒██ \n",
        style="bold blue",
    )
    banner.append(
        "   ▓█   ▓██▒▒▒█████▓   ▒██▒ ░ ░ ████▓▒░   ▒██▒   ░██▒ ▓█   ▓██▒▒██░   ▓██░░██░▒██▒   ░██▒\n",
        style="bold bright_cyan",
    )
    banner.append(
        "   ▒▒   ▓▒█░░▒▓▒ ▒ ▒   ▒ ░░   ░ ▒░▒░▒░    ░ ▒░   ░  ░ ▒▒   ▓▒█░░ ▒░   ▒ ▒ ░▓  ░ ▒░   ░  ░\n",
        style="bold cyan",
    )

    # Simpler, more reliable banner
    title = Text()
    title.append("Auto", style="bold bright_magenta")
    title.append("Manim", style="bold bright_cyan")

    subtitle = Text("  AI-powered Manim animation generator", style="dim white")

    version = Text("  v0.1.0  •  powered by OpenRouter", style="dim bright_black")

    console.print()
    console.print(
        Panel(
            Text.assemble(
                Text(" ✦ ", style="bold bright_magenta"),
                Text("Auto", style="bold bright_magenta"),
                Text("Manim", style="bold bright_cyan"),
                Text("  ", style=""),
                Text("AI-powered Manim animation generator", style="dim white"),
                Text("\n"),
                Text(
                    "   v0.1.0  •  powered by OpenRouter  •  arcee-ai/trinity",
                    style="dim bright_black",
                ),
            ),
            box=box.ROUNDED,
            border_style="bright_magenta",
            padding=(0, 2),
        )
    )
    console.print()


def print_step(icon: str, label: str, value: str = "", style: str = "bright_cyan"):
    line = Text()
    line.append(f" {icon} ", style=f"bold {style}")
    line.append(label, style="bold white")
    if value:
        line.append(f"  {value}", style="dim white")
    console.print(line)


def print_success(message: str):
    text = Text()
    text.append(" ✓ ", style="bold bright_green")
    text.append(message, style="bold white")
    console.print(text)


def print_error(message: str):
    console.print(
        Panel(
            Text.assemble(
                Text(" ✗  Error\n", style="bold bright_red"),
                Text(f" {message}", style="white"),
            ),
            border_style="bright_red",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def print_code_preview(code: str, filename: str):
    """Print a syntax-highlighted preview of the generated code."""
    lines = code.splitlines()
    preview_lines = lines[:20]
    truncated = len(lines) > 20
    preview = "\n".join(preview_lines)
    if truncated:
        preview += f"\n  … ({len(lines) - 20} more lines)"

    syntax = Syntax(
        preview, "python", theme="monokai", line_numbers=True, word_wrap=False
    )
    console.print(
        Panel(
            syntax,
            title=f"[bold bright_black] {filename} [/bold bright_black]",
            title_align="left",
            border_style="bright_black",
            box=box.ROUNDED,
            padding=(0, 0),
        )
    )


# ── Core Logic ───────────────────────────────────────────────────────────────


def generate_code(prompt: str) -> str:
    """Call the LLM and return the generated Python code."""
    console.print()
    with Live(
        Text.assemble(
            Text(" ⠦ ", style="bold bright_magenta"),
            Text("Thinking", style="bold white"),
            Text("  generating Manim code…", style="dim white"),
        ),
        console=console,
        refresh_per_second=10,
        transient=True,
    ) as live:
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        frame_idx = 0
        start = time.time()

        # Start the actual API call
        import threading

        result = {"code": None, "error": None}

        def api_call():
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                )
                result["code"] = response.choices[0].message.content or ""
            except Exception as e:
                result["error"] = e

        thread = threading.Thread(target=api_call)
        thread.start()

        while thread.is_alive():
            elapsed = time.time() - start
            frame = frames[frame_idx % len(frames)]
            frame_idx += 1
            live.update(
                Text.assemble(
                    Text(f" {frame} ", style="bold bright_magenta"),
                    Text("Thinking", style="bold white"),
                    Text(
                        f"  generating Manim code… ({elapsed:.1f}s)", style="dim white"
                    ),
                )
            )
            time.sleep(0.1)

        thread.join()

    if result["error"]:
        raise result["error"]

    elapsed = time.time() - start
    print_step("✓", "Code generated", f"({elapsed:.1f}s)", style="bright_green")
    return result["code"]


def render_scene(script_path: Path):
    """Run manim to render the scene and stream its output."""
    console.print()
    console.print(Rule(style="bright_black"))
    console.print(
        Text.assemble(
            Text(" ▶ ", style="bold bright_yellow"),
            Text("Rendering scene", style="bold white"),
            Text("  manim -ql GenScene", style="dim bright_black"),
        )
    )
    console.print(Rule(style="bright_black"))
    console.print()

    result = subprocess.run(
        [sys.executable, "-m", "manim", "-ql", str(script_path), "GenScene"],
        check=False,
    )

    console.print()
    console.print(Rule(style="bright_black"))
    if result.returncode == 0:
        print_success("Render complete!")
    else:
        print_error(f"Manim exited with code {result.returncode}")


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    print_banner()

    # Get prompt
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        print_step("◆", "Prompt", prompt, style="bright_cyan")
    else:
        console.print(
            Text.assemble(
                Text(" ◆ ", style="bold bright_cyan"),
                Text("What animation would you like to create?", style="bold white"),
            )
        )
        console.print()
        prompt = Prompt.ask(
            "   [dim]Describe your animation[/dim]",
            console=console,
        ).strip()

    console.print()

    if not prompt:
        print_error("No prompt provided.")
        sys.exit(1)

    # Generate code
    try:
        code = generate_code(prompt)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)

    # Clean up LLM output
    code = (
        code.strip()
        .removeprefix("```python")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )

    if not code:
        print_error("The model returned empty output. Try a different prompt.")
        sys.exit(1)

    # Save file
    output_file = Path("generated_scene.py")
    output_file.write_text(code, encoding="utf-8")
    print_step("◆", "Saved to", str(output_file.absolute()), style="bright_cyan")

    # Show code preview
    console.print()
    print_code_preview(code, output_file.name)
    console.print()

    # Render
    render_scene(output_file)
    console.print()


if __name__ == "__main__":
    main()
