import re, os, subprocess, logging
from flask import Flask, render_template, request, jsonify, session
from utils.gemini_client import GeminiClient
from utils.groq_client import GroqClient

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_secret_key")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template(
        "index.html",
        user_input=request.form.get("text") if request.method == "POST" else None,
    )


@app.route("/generate_and_execute_manim", methods=["POST"])
def generate_and_execute_manim():
    try:
        desc = request.json.get("manimPrompt")
        if not desc:
            logger.error("No animation description provided in request")
            return jsonify({"error": "No animation description provided"}), 400

        # Update chat history
        if "chat_history" not in session:
            session["chat_history"] = []
        session["chat_history"].append({"role": "user", "content": desc})

        # Generate Manim code using AI
        logger.info("Generating Manim code")
        response, errors = None, []
        for Client in [GeminiClient, GroqClient]:
            try:
                logger.info(f"Attempting to generate code with {Client.__name__}")
                response = Client().generate_code(desc, session["chat_history"])
                logger.info(f"Successfully generated response with {Client.__name__}")
                logger.debug(
                    f"Raw response: {response[:100]}..."
                )  # Log first 100 chars
                break
            except Exception as e:
                error_msg = f"{Client.__name__} error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        if not response:
            logger.error(f"All AI APIs failed: {errors}")
            return jsonify({"error": "All AI APIs failed", "details": errors}), 500

        # Extract code from <manim> tags
        logger.info("Extracting code from <manim> tags")
        code_match = re.search(r"<manim>(.*?)</manim>", response, re.DOTALL)

        if not code_match:
            logger.error(
                f"No <manim> tags found in response. Response preview: {response[:200]}..."
            )
            return (
                jsonify(
                    {
                        "error": "No code found in <manim> tags. The AI response did not follow the required format.",
                        "response_preview": response[:200],
                    }
                ),
                400,
            )

        manim_code = code_match.group(1).strip()
        logger.info(
            f"Successfully extracted code, length: {len(manim_code)} characters"
        )

        # Ensure we have a MainScene class
        if manim_code and "class MainScene" not in manim_code:
            logger.info("Adding MainScene class wrapper to code")
            manim_code = (
                "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        "
                + manim_code
            )

        # Update chat history
        session["chat_history"].append({"role": "assistant", "content": response})
        session.modified = True

        # Now execute the generated code
        logger.info("Executing Manim code")
        if not manim_code:
            return jsonify({"error": "No code generated"}), 400

        scene_path = os.path.join(app.static_folder, "manim_code.py")
        os.makedirs(app.static_folder, exist_ok=True)
        with open(scene_path, "w") as f:
            f.write(manim_code)

        scene_name_match = re.search(r"class\s+(\w+)\((.*?)Scene\):", manim_code)
        if not scene_name_match:
            return jsonify({"error": "Could not find scene class in the code"}), 400
        scene_name = scene_name_match.group(1)

        logger.info(f"Starting Manim: {scene_name}")
        process = subprocess.Popen(
            ["manim", "-ql", scene_path, scene_name],
            cwd=app.static_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        _, stderr = process.communicate()

        if process.returncode != 0:
            logger.error(f"Manim Failed: {stderr}")
            return jsonify(
                {
                    "status": "error",
                    "message": "Animation creation failed. Please try again.",
                    "code": manim_code,
                    "chat_history": session["chat_history"],
                }
            )

        video_dir = os.path.join(
            app.static_folder, "media", "videos", "manim_code", "480p15"
        )
        if not os.path.exists(video_dir):
            return jsonify(
                {
                    "status": "error",
                    "message": "Animation creation failed. Please try again.",
                    "code": manim_code,
                    "chat_history": session["chat_history"],
                }
            )

        videos = [
            f
            for f in os.listdir(video_dir)
            if f.startswith(scene_name) and f.endswith(".mp4")
        ]
        if not videos:
            return jsonify(
                {
                    "status": "error",
                    "message": "No video found for the scene",
                    "code": manim_code,
                    "chat_history": session["chat_history"],
                }
            )

        latest = max(videos, key=lambda f: os.path.getmtime(os.path.join(video_dir, f)))

        # Return success response with all data
        return jsonify(
            {
                "status": "success",
                "video_url": f"/static/media/videos/manim_code/480p15/{latest}",
                "code": manim_code,
                "chat_history": session["chat_history"],
            }
        )

    except Exception as e:
        error_msg = f"Animation processing failed: {str(e)}"
        logger.exception(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500


@app.route("/get_chat_history", methods=["GET"])
def get_chat_history():
    if "chat_history" not in session:
        session["chat_history"] = []
    return jsonify({"chat_history": session["chat_history"]})


@app.route("/clear_chat_history", methods=["POST"])
def clear_chat_history():
    session["chat_history"] = []
    session.modified = True
    return jsonify({"success": True})
