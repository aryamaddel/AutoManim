import asyncio
import functools
import re
import subprocess
import tempfile
import os
from aiocache import cached
from typing import Dict, Any, Optional, Tuple, List

class ProcessingService:
    def __init__(self):
        self._cache = {}
        self.max_retries = 3
        
    @cached(ttl=3600)  # Cache results for 1 hour
    async def process_animation(self, code: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Process animation asynchronously with caching"""
        # Use asyncio for non-blocking operations
        return await self._run_animation_process(code, settings)
        
    async def _run_animation_process(self, code: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Run animation process with automatic error correction"""
        retries = 0
        current_code = code
        errors = []
        
        while retries <= self.max_retries:
            # Run the CPU-intensive tasks in a thread pool
            loop = asyncio.get_event_loop()
            success, result, error = await loop.run_in_executor(
                None,
                functools.partial(self._execute_manim, current_code, settings)
            )
            
            if success:
                return {
                    "success": True, 
                    "result": result,
                    "code": current_code,
                    "errors": errors if errors else None
                }
            
            # Parse the error and get AI to fix it
            error_info = self._parse_error(error)
            errors.append(error_info)
            
            # Get AI to fix the code
            fixed_code = await self._get_ai_fix(current_code, error_info)
            
            if fixed_code:
                current_code = fixed_code
                retries += 1
            else:
                # If AI couldn't fix it, break the loop
                break
        
        # If we get here, all retries failed
        return {
            "success": False,
            "error": errors[-1]["message"] if errors else "Unknown error",
            "code": current_code,
            "errors": errors
        }
    
    def _execute_manim(self, code: str, settings: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        """Execute Manim animation and capture output/errors"""
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as f:
            f.write(code)
            file_path = f.name
        
        try:
            # Build command with settings
            cmd = self._build_manim_command(file_path, settings)
            
            # Execute manim with subprocess
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False  # Don't raise exception on error
            )
            
            if process.returncode == 0:
                return True, process.stdout, None
            else:
                return False, None, process.stderr
        except Exception as e:
            return False, None, str(e)
        finally:
            # Clean up temp file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def _parse_error(self, error_output: str) -> Dict[str, Any]:
        """Parse error output to extract useful information"""
        error_info = {"raw": error_output, "message": error_output}
        
        # Extract error type and message
        error_match = re.search(r'(\w+Error): (.+?)(?:\n|$)', error_output)
        if error_match:
            error_info["type"] = error_match.group(1)
            error_info["message"] = error_match.group(2)
        
        # Extract file and line number
        file_line_match = re.search(r'File "(.+?)", line (\d+)', error_output)
        if file_line_match:
            error_info["file"] = file_line_match.group(1)
            error_info["line"] = int(file_line_match.group(2))
        
        # Extract code context if available
        context_lines = []
        in_context = False
        for line in error_output.split('\n'):
            if re.match(r'^\s+\d+\s+', line):  # Line starts with spaces followed by numbers
                in_context = True
                context_lines.append(line)
            elif in_context and line.strip():
                context_lines.append(line)
            elif in_context:
                break
        
        if context_lines:
            error_info["context"] = '\n'.join(context_lines)
        
        return error_info
    
    async def _get_ai_fix(self, code: str, error_info: Dict[str, Any]) -> Optional[str]:
        """Send code and error to AI service for fixing"""
        try:
            # Get AI service (assuming it's injected or imported elsewhere)
            ai_service = self._get_ai_service()
            
            # Build prompt for the AI
            prompt = self._build_error_fix_prompt(code, error_info)
            
            # Get fixed code from AI
            fixed_code = await ai_service.generate_fixed_code(prompt)
            
            return fixed_code
        except Exception as e:
            print(f"Error getting AI fix: {str(e)}")
            return None
    
    def _build_error_fix_prompt(self, code: str, error_info: Dict[str, Any]) -> str:
        """Build a prompt for the AI to fix the code"""
        prompt = f"""Fix the following Manim Python code that produced this error:

Error Type: {error_info.get('type', 'Unknown')}
Error Message: {error_info.get('message', 'Unknown error')}
"""
        
        if error_info.get('context'):
            prompt += f"\nError Context:\n{error_info['context']}\n"
        
        prompt += f"\nCode to fix:\n```python\n{code}\n```\n"
        prompt += "\nPlease provide only the fixed code without explanations."
        
        return prompt
    
    def _get_ai_service(self):
        """Get or create AI service"""
        # This would be implemented to return your AI service
        # For now it's a placeholder
        from app.services.ai_service import AIService
        return AIService()
    
    def _build_manim_command(self, file_path: str, settings: Dict[str, Any]) -> List[str]:
        """Build manim command with settings"""
        # This is a placeholder - implement with actual Manim CLI options
        cmd = ["python", "-m", "manim", file_path, "-p"]
        
        # Add quality settings
        if settings.get("quality"):
            cmd.append(f"--quality={settings['quality']}")
            
        # Add other settings as needed
        
        return cmd