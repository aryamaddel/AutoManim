import os
from google import genai
from google.genai import types
from utils import AICodeClient

class GeminiClient(AICodeClient):
    """Client for Google's Gemini API"""

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

        # Add chat history if available
        if chat_history:
            # Filter to exclude the current prompt
            past_history = [msg for msg in chat_history if msg["content"] != prompt]

            for message in past_history:
                role = "user" if message["role"] == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=message["content"])],
                    )
                )

        # Add the current prompt
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
