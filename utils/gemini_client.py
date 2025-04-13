import os
from google import genai
from google.genai import types

class GeminiClient:
    """Client for Google's Gemini API"""
    
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.0-flash"
    
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
        
        generate_content_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
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
