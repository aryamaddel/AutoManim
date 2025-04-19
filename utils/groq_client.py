import os
import requests
from utils import AICodeClient

class GroqClient(AICodeClient):
    """Client for Groq API"""

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

        # Start with system message
        messages = [{"role": "system", "content": system_instruction}]

        # Add chat history if available
        if chat_history:
            # Filter to exclude the current prompt
            past_history = [msg for msg in chat_history if msg["content"] != prompt]
            messages.extend(past_history)

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        payload = {"model": self.model, "messages": messages}

        response = requests.post(self.api_url, headers=headers, json=payload)
        response.raise_for_status()

        response_json = response.json()
        code = response_json["choices"][0]["message"]["content"]

        if not code:
            raise ValueError("Empty response from Groq API")

        return code
