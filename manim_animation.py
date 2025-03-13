

from manim import *

class MainScene(Scene):
    def construct(self):
        square = Square()
        circle = Circle()
        self.add(square)
        self.play(
            MoveAlongPath(square, circle),
            square.animate.rotate(90 * DEGREES)
        )