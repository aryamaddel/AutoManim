from flask import Flask, render_template, request
from groq_manim import *

app = Flask(__name__, template_folder="template")


@app.route("/", methods=["GET", "POST"])
def index():
    user_input = None
    if request.method == "POST":
        user_input = request.form.get("text")
        print(f"User input: {user_input}")

    return render_template("index.html", user_input=user_input)


if __name__ == "__main__":
    app.run(debug=True)
