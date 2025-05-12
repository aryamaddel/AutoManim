import re
import subprocess
import os
from typing import Dict, Any, Tuple

class ManimService:
    def __init__(self, config):
        self.config = config
        self.quality_presets = {
            'low': {'resolution': '854,480', 'frame_rate': 15},
            'medium': {'resolution': '1280,720', 'frame_rate': 30},
            'high': {'resolution': '1920,1080', 'frame_rate': 60}
        }
        
    def render_animation(self, code: str, settings: Dict[str, Any]) -> Tuple[bool, str]:
        """Render animation with optimized quality settings based on complexity"""
        # Analyze code complexity to determine appropriate quality
        complexity = self._analyze_complexity(code)
        quality_settings = self._get_quality_for_complexity(complexity, settings)
        
        # Save code to temporary file
        file_path = self._save_code_to_file(code)
        
        # Build command with optimized settings
        cmd = self._build_manim_command(file_path, quality_settings)
        
        # Execute manim
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
        finally:
            # Clean up temp file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def _analyze_complexity(self, code: str) -> float:
        """Analyze the complexity of the Manim code"""
        complexity_score = 0
        
        # Count number of objects
        object_count = len(re.findall(r'self\.add\(', code))
        complexity_score += object_count * 0.5
        
        # Count animations
        animation_count = len(re.findall(r'self\.play\(', code))
        complexity_score += animation_count * 1.0
        
        # Count mobjects created
        mobject_count = len(re.findall(r'=\s*\w+\(', code))
        complexity_score += mobject_count * 0.3
        
        # Count transforms which are more expensive
        transform_count = len(re.findall(r'Transform|ReplacementTransform', code))
        complexity_score += transform_count * 1.5
        
        return complexity_score
    
    def _get_quality_for_complexity(self, complexity: float, user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Get appropriate quality settings based on complexity"""
        # If user explicitly set quality, respect that
        if 'quality' in user_settings:
            preset = user_settings['quality']
        else:
            # Otherwise choose based on complexity
            if complexity < 5:
                preset = 'high'
            elif complexity < 15:
                preset = 'medium'
            else:
                preset = 'low'
        
        settings = self.quality_presets[preset].copy()
        
        # Override with any specific user settings
        settings.update({k: v for k, v in user_settings.items() 
                        if k not in ['quality']})
                        
        return settings
    
    def _save_code_to_file(self, code: str) -> str:
        temp_file_path = "temp_manim_code.py"
        with open(temp_file_path, "w") as temp_file:
            temp_file.write(code)
        return temp_file_path
        
    def _build_manim_command(self, file_path: str, settings: Dict[str, Any]) -> list:
        resolution = settings['resolution']
        frame_rate = settings['frame_rate']
        return [
            "manim",
            file_path,
            "-r", resolution,
            "-f", str(frame_rate)
        ]