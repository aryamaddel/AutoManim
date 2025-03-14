

from manim import *

class MainScene(Scene):
    def construct(self):
        box = Square(color=BLUE)
        self.add(box)
        
        circular_path = CircularPath(radius=2)
        self.play(box.move_along_path(circular_path), run_time=3)
        
        reverse_circular_path = CircularPath(radius=2, direction=-1)
        self.play(box.move_along_path(reverse_circular_path), run_time=5)