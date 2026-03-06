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

FIX_SYSTEM_PROMPT = """You are an expert Manim developer and debugger. You will be given a Manim script that failed to render, along with the error output.
Your job is to fix the code so it runs without errors. Carefully analyze the traceback and error messages.

Common issues to watch for:
- Incorrect Manim API usage (wrong class names, deprecated methods, wrong arguments)
- Syntax errors in Python code
- LaTeX rendering issues (missing escapes, bad TeX syntax)
- Import errors (using classes/functions that don't exist in Manim CE v0.18+)
- Object positioning or animation issues
- Using MathTex vs Tex incorrectly
- Forgetting to import from manim

The fixed script MUST define a Scene class named 'GenScene'.
Output ONLY the corrected Python code, no markdown blocks or explanations. Do not use ```python``` or ``````."""

MODEL = "arcee-ai/trinity-large-preview:free"

MAX_HEAL_ATTEMPTS = 3

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
                Text("\n"),
                Text(
                    f"   self-healing: up to {MAX_HEAL_ATTEMPTS} auto-fix attempts",
                    style="dim bright_yellow",
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


def print_heal_attempt(attempt: int, max_attempts: int):
    """Print a styled healing attempt header."""
    console.print()
    console.print(
        Panel(
            Text.assemble(
                Text(" 🔧 ", style="bold bright_yellow"),
                Text("Self-Healing", style="bold bright_yellow"),
                Text(f"  attempt {attempt}/{max_attempts}", style="bold white"),
                Text("\n"),
                Text(
                    "   Analyzing error and regenerating code…",
                    style="dim white",
                ),
            ),
            border_style="bright_yellow",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def print_heal_success(attempt: int):
    """Print a styled healing success message."""
    console.print()
    console.print(
        Panel(
            Text.assemble(
                Text(" ✦ ", style="bold bright_green"),
                Text("Self-Healed!", style="bold bright_green"),
                Text(f"  fixed on attempt {attempt}", style="bold white"),
                Text("\n"),
                Text(
                    "   The code was automatically repaired and rendered successfully.",
                    style="dim white",
                ),
            ),
            border_style="bright_green",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def print_heal_failure():
    """Print a styled healing failure message."""
    console.print()
    console.print(
        Panel(
            Text.assemble(
                Text(" ✗ ", style="bold bright_red"),
                Text("Self-Healing Failed", style="bold bright_red"),
                Text(
                    f"  exhausted all {MAX_HEAL_ATTEMPTS} attempts",
                    style="bold white",
                ),
                Text("\n"),
                Text(
                    "   Try simplifying your prompt or adjusting the description.",
                    style="dim white",
                ),
            ),
            border_style="bright_red",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def print_error_summary(error_output: str):
    """Print a condensed, readable summary of the manim error."""
    # Extract just the last part of the traceback (most relevant)
    lines = error_output.strip().splitlines()

    # Find the last "Error" or "Exception" line for a concise summary
    error_lines = []
    capture = False
    for line in reversed(lines):
        error_lines.insert(0, line)
        if line.strip().startswith("Traceback") or line.strip().startswith("File"):
            capture = True
        if capture and len(error_lines) >= 15:
            break

    # Limit to last 20 lines max
    summary = "\n".join(error_lines[-20:])

    syntax = Syntax(
        summary,
        "pytb",
        theme="monokai",
        word_wrap=True,
        line_numbers=False,
    )
    console.print(
        Panel(
            syntax,
            title="[bold bright_red] Error Output [/bold bright_red]",
            title_align="left",
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


def _llm_call(messages: list[dict], spinner_label: str = "Thinking") -> str:
    """Internal helper: call the LLM with animated spinner, return content string."""
    with Live(
        Text.assemble(
            Text(" ⠦ ", style="bold bright_magenta"),
            Text(spinner_label, style="bold white"),
            Text("  generating Manim code…", style="dim white"),
        ),
        console=console,
        refresh_per_second=10,
        transient=True,
    ) as live:
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        frame_idx = 0
        start = time.time()

        import threading

        result = {"code": None, "error": None}

        def api_call():
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
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
                    Text(spinner_label, style="bold white"),
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
    return result["code"]


def generate_code(prompt: str) -> str:
    """Call the LLM and return the generated Python code."""
    console.print()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    code = _llm_call(messages, spinner_label="Thinking")
    print_step("✓", "Code generated", style="bright_green")
    return code


def fix_code(original_code: str, error_output: str, original_prompt: str) -> str:
    """Send the broken code and error back to the LLM for a fix."""
    console.print()

    fix_prompt = f"""The following Manim script was generated for this request:
---
{original_prompt}
---

Here is the code that failed:
```python
{original_code}
```

Here is the error output from running it:
```
{error_output}
```

Please fix the code so it runs without errors. Output ONLY the corrected Python code."""

    messages = [
        {"role": "system", "content": FIX_SYSTEM_PROMPT},
        {"role": "user", "content": fix_prompt},
    ]
    code = _llm_call(messages, spinner_label="Healing")
    print_step("✓", "Fix generated", style="bright_green")
    return code


def render_scene(script_path: Path) -> tuple[int, str]:
    """Run manim to render the scene. Returns (returncode, stderr_output)."""
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
        capture_output=True,
        text=True,
    )

    # Always show stdout if present (manim progress info)
    if result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            console.print(Text(f"  {line}", style="dim white"))

    console.print()
    console.print(Rule(style="bright_black"))

    if result.returncode == 0:
        print_success("Render complete!")
    else:
        print_error(f"Manim exited with code {result.returncode}")

    # Combine stdout and stderr for error context
    full_output = ""
    if result.stderr:
        full_output += result.stderr
    if result.returncode != 0 and result.stdout:
        full_output += "\n" + result.stdout

    return result.returncode, full_output.strip()


def clean_code(code: str) -> str:
    """Strip markdown fences and whitespace from LLM output."""
    code = code.strip()
    # Handle ```python ... ``` blocks
    if code.startswith("```python"):
        code = code[len("```python"):]
    elif code.startswith("```"):
        code = code[len("```"):]
    if code.endswith("```"):
        code = code[:-3]
    return code.strip()


def validate_code_syntax(code: str) -> tuple[bool, str]:
    """Check if the code has valid Python syntax before even trying to render."""
    try:
        compile(code, "<generated_scene>", "exec")
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}"


def validate_scene_class(code: str) -> tuple[bool, str]:
    """Check that the code defines a 'GenScene' class."""
    if "class GenScene" not in code:
        return False, "Generated code does not contain a 'class GenScene' definition."
    return True, ""


# ── Self-Healing Loop ────────────────────────────────────────────────────────


def self_healing_loop(
    code: str,
    prompt: str,
    output_file: Path,
) -> bool:
    """
    Attempt to render the scene. If it fails, send the error back to the LLM
    to generate a fix. Repeat up to MAX_HEAL_ATTEMPTS times.

    Returns True if the scene was eventually rendered successfully.
    """
    current_code = code

    for attempt in range(MAX_HEAL_ATTEMPTS + 1):  # 0 = initial, 1..N = fix attempts
        # ── Pre-flight validation ─────────────────────────────────────
        syntax_ok, syntax_err = validate_code_syntax(current_code)
        if not syntax_ok:
            if attempt == 0:
                print_error(f"Generated code has a syntax error: {syntax_err}")
            else:
                print_error(f"Fixed code still has a syntax error: {syntax_err}")
            error_output = syntax_err
        else:
            scene_ok, scene_err = validate_scene_class(current_code)
            if not scene_ok:
                print_error(scene_err)
                error_output = scene_err
            else:
                # ── Save and render ───────────────────────────────
                output_file.write_text(current_code, encoding="utf-8")
                if attempt == 0:
                    print_step(
                        "◆",
                        "Saved to",
                        str(output_file.absolute()),
                        style="bright_cyan",
                    )
                else:
                    print_step(
                        "◆",
                        "Updated",
                        str(output_file.absolute()),
                        style="bright_cyan",
                    )

                # Show code preview
                console.print()
                print_code_preview(current_code, output_file.name)
                console.print()

                # Render
                returncode, error_output = render_scene(output_file)

                if returncode == 0:
                    if attempt > 0:
                        print_heal_success(attempt)
                    return True

        # ── Render failed — attempt healing ───────────────────────────
        if attempt >= MAX_HEAL_ATTEMPTS:
            # No more attempts left
            break

        # Show error details
        if error_output:
            print_error_summary(error_output)

        heal_attempt = attempt + 1
        print_heal_attempt(heal_attempt, MAX_HEAL_ATTEMPTS)

        try:
            fixed_code = fix_code(current_code, error_output, prompt)
        except Exception as e:
            print_error(f"Failed to call LLM for fix: {e}")
            break

        fixed_code = clean_code(fixed_code)

        if not fixed_code:
            print_error("The model returned empty fix output.")
            break

        current_code = fixed_code

    # All attempts exhausted
    print_heal_failure()
    return False


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
    code = clean_code(code)

    if not code:
        print_error("The model returned empty output. Try a different prompt.")
        sys.exit(1)

    # Run self-healing loop: render → fix → re-render → …
    output_file = Path("generated_scene.py")
    success = self_healing_loop(code, prompt, output_file)

    console.print()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
