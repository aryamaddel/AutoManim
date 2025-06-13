import re
import os
import subprocess
import logging
import requests
from abc import ABC, abstractmethod
from flask import Flask, render_template, request, jsonify, session
from google import genai
from google.genai import types

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_secret_key")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AICodeClient(ABC):
    """Base abstract class for AI Code Generation clients"""

    def __init__(self, api_key_name):
        self.api_key = os.environ.get(api_key_name)
        if not self.api_key:
            raise ValueError(f"{api_key_name} environment variable not set")

    @abstractmethod
    def generate_code(self, prompt, chat_history=None):
        """Generate code from prompt with optional chat history"""
        pass

    def get_system_instruction(self):
        return """You are a Manim code generator that helps users create mathematical animations.
        You MUST place ALL executable Python code ONLY between <manim> and </manim> tags NOT in ```.
        """


class GroqClient(AICodeClient):
    def __init__(self):
        super().__init__("GROQ_API_KEY")
        self.api_url = "https://api.groq.com/v1/chat/completions"
        self.model = "llama3-70b-8192"  # Default model

    def generate_code(self, prompt, chat_history=None):
        system_instruction = self.get_system_instruction()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = [{"role": "system", "content": system_instruction}]

        if chat_history:
            past_history = [msg for msg in chat_history if msg["content"] != prompt]
            messages.extend(past_history)

        messages.append({"role": "user", "content": prompt})

        payload = {"model": self.model, "messages": messages}

        response = requests.post(self.api_url, headers=headers, json=payload)
        response.raise_for_status()

        response_json = response.json()
        code = response_json["choices"][0]["message"]["content"]

        if not code:
            raise ValueError("Empty response from Groq API")

        return code


class GeminiClient(AICodeClient):
    def __init__(self):
        super().__init__("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.0-flash"

    def generate_code(self, prompt, chat_history=None):
        system_instruction = self.get_system_instruction()

        generate_content_config = types.GenerateContentConfig(
            system_instruction=system_instruction, temperature=0
        )

        contents = []

        if chat_history:
            past_history = [msg for msg in chat_history if msg["content"] != prompt]

            for message in past_history:
                role = "user" if message["role"] == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=message["content"])],
                    )
                )

        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=generate_content_config,
        )

        if not hasattr(response, "text") or response.text is None:
            raise ValueError("Empty response from Gemini API")

        return response.text


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

        session.setdefault("chat_history", []).append({"role": "user", "content": desc})

        logger.info("Generating Manim code")
        response, errors = None, []

        for Client in [GeminiClient, GroqClient]:
            try:
                response = Client().generate_code(desc, session["chat_history"])
                logger.info(f"Generated code with {Client.__name__}")
                break
            except Exception as e:
                errors.append(f"{Client.__name__}: {str(e)}")
                logger.error(f"{Client.__name__} error: {str(e)}")

        if not response:
            logger.error(f"All AI APIs failed: {errors}")
            return jsonify({"error": "All AI APIs failed", "details": errors}), 500

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

        session["chat_history"].append({"role": "assistant", "content": response})
        session.modified = True

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

        latest = max(videos, key=lambda f: os.path.getmtime(os.path.join(video_dir, f)))

        return jsonify(
            {
                "status": "success",
                "video_url": f"/static/media/videos/manim_code/480p15/{latest}",
                "code": manim_code,
                "chat_history": session["chat_history"],
            }
        )

    except Exception as e:
        logger.exception(f"Animation processing failed: {str(e)}")
        return (
            jsonify(
                {"status": "error", "message": f"Animation processing failed: {str(e)}"}
            ),
            500,
        )


@app.route("/get_chat_history", methods=["GET"])
def get_chat_history():
    return jsonify({"chat_history": session.setdefault("chat_history", [])})


@app.route("/clear_chat_history", methods=["POST"])
def clear_chat_history():
    session["chat_history"] = []
    session.modified = True
    return jsonify({"success": True})
