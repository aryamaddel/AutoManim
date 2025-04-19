# Services initialization
import os
from abc import ABC, abstractmethod

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
        """Common system instruction for code generation"""
        return """You are a Manim code generator that ONLY outputs executable Python code.
        IMPORTANT INSTRUCTIONS:
        1. Return ONLY Python code - no explanations, no thinking, no markdown
        2. Include all necessary imports (from manim import *)
        3. Create a Scene class named 'MainScene' with proper construct method
        4. Follow exact Manim syntax and conventions
        5. Do not include main blocks or code fences (```)
        6. Ensure animations work correctly with proper syntax
        7. Do not output ANY text that isn't part of the final code
        8. Consider the entire conversation history to maintain context"""

# Empty init file to make directory a proper Python package
