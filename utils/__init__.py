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
        return """You are a Manim code generator that helps users create mathematical animations.
        CRITICAL INSTRUCTIONS - MUST BE FOLLOWED:
        1. You MUST place ALL executable Python code ONLY between <manim> and </manim> tags.
           Example format: 
           <manim>
           from manim import *
           
           class MainScene(Scene):
               def construct(self):
                   # Your code here
           </manim>
           
        2. Include all necessary imports inside the <manim> tags
        3. Create a Scene class named 'MainScene' with proper construct method
        4. You may provide explanations or context outside the <manim> tags
        5. DO NOT use markdown code blocks (```) for code - ONLY use <manim> tags
        6. This requirement is critical - the system can ONLY process code inside <manim> tags
        """
