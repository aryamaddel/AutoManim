import os
import requests
from abc import ABC, abstractmethod
from google import genai
from google.genai import types


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
