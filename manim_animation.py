

from manim import *

class MainScene(Scene):
    def construct(self):
        square = Square()
        self.add(square)
        circle = Circle(radius=3)
        self.play(MoveAlongPath(square, circle), run_time=3)
        self.wait()