import os
import requests


class GroqClient:
    """Client for Groq API"""

    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        self.api_url = "https://api.groq.com/v1/chat/completions"
        self.model = "llama3-70b-8192"  # Default model

    def generate_code(self, prompt, chat_history=None):
        system_instruction = """You are a Manim code generator that ONLY outputs executable Python code.
        IMPORTANT INSTRUCTIONS:
        1. Return ONLY Python code - no explanations, no thinking, no markdown
        2. Include all necessary imports (from manim import *)
        3. Create a Scene class named 'MainScene' with proper construct method
        4. Follow exact Manim syntax and conventions
        5. Do not include main blocks or code fences (```)
        6. Ensure animations work correctly with proper syntax
        7. Do not output ANY text that isn't part of the final code
        8. Consider the entire conversation history to maintain context"""

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
