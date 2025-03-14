from flask import Flask, render_template, request
from groq_manim import *

app = Flask(__name__, template_folder="template", static_folder="static")

@app.route("/", methods=["GET", "POST"])
def index():
    output_code = []  # Ensure it's a list
    error_message = ""

    if request.method == "POST":
        user_input = request.form.get("text", "").strip()

        if not user_input:
            error_message = "No input provided!"
        else:
            try:
                output_code = generate_and_run_manim(user_input)  # Assume it returns a list
                print("Generated Output Code:", output_code)  # Debugging
            except Exception as e:
                error_message = f"Error: {str(e)}"

    return render_template("index.html", output_code=output_code[2] if len(output_code) > 2 else "", error_message=error_message)

if __name__ == "__main__":
    app.run()
