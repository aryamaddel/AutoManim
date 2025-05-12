import re
from typing import Optional, List, Dict

class CodeExtractor:
    def __init__(self):
        # Precompile regex patterns for better performance
        self.manim_class_pattern = re.compile(r'class\s+(\w+)\s*\(\s*Scene\s*\)')
        self.python_block_pattern = re.compile(r'```(?:python|py)(.*?)```', re.DOTALL)
        self.import_pattern = re.compile(r'(?:^|\n)(?:from|import)\s+\w+', re.MULTILINE)
    
    def extract_manim_code(self, text: str) -> Optional[str]:
        """Extract Manim code blocks from AI generated text with optimized processing"""
        # First try to extract code blocks
        matches = self.python_block_pattern.findall(text)
        
        if matches:
            # Concatenate all Python code blocks
            code = "\n".join(match.strip() for match in matches)
        else:
            # If no code block found, use the whole text but filter for lines that look like code
            code = self._filter_code_lines(text)
        
        # Verify it's Manim code
        if 'manim' in code and self.manim_class_pattern.search(code):
            return self._cleanup_code(code)
        
        return None
    
    def _filter_code_lines(self, text: str) -> str:
        """Filter lines that appear to be Python code"""
        lines = text.split('\n')
        code_lines = []
        
        in_code_section = False
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            
            # Check for code indicators
            if ('import' in line or 'class' in line or 'def ' in line or 
                stripped.startswith('if ') or stripped.endswith(':') or
                '=' in stripped):
                in_code_section = True
                code_lines.append(line)
                if stripped.endswith(':'):
                    indent_level += 1
            elif in_code_section and (stripped.startswith('#') or 
                                     (indent_level > 0 and line.startswith(' '))):
                code_lines.append(line)
                if indent_level > 0 and not line.strip():
                    indent_level -= 1
            elif not stripped and in_code_section:
                code_lines.append(line)
            else:
                in_code_section = False
        
        return '\n'.join(code_lines)
    
    def _cleanup_code(self, code: str) -> str:
        """Clean up the extracted code"""
        # Add necessary imports if missing
        if 'import manim' not in code and 'from manim import' not in code:
            code = 'from manim import *\n' + code
            
        # Remove any non-code artifacts
        code = code.replace('`', '')
        
        return code.strip()
