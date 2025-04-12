from manim import *

class MainScene(Scene):
    def construct(self):
        # Create initial shape (Circle)
        shape1 = Circle(color=BLUE, fill_opacity=0.5)
        self.play(Create(shape1))
        self.wait(1)

        # Create target shape 1 (Octagon)
        shape2 = RegularPolygon(n=8, color=GREEN, fill_opacity=0.5)
        shape2.scale(shape1.width / shape2.width) # Match size

        # Transform Circle to Octagon
        self.play(Transform(shape1, shape2))
        self.wait(1)

        # Create target shape 2 (Square)
        shape3 = Square(color=RED, fill_opacity=0.5)
        shape3.scale(shape1.width / shape3.width) # Match size

        # Transform Octagon to Square
        self.play(Transform(shape1, shape3))
        self.wait(1)

        # Create target shape 3 (Star)
        shape4 = Star(n=5, outer_radius=shape1.width/2, inner_radius=shape1.width/4, color=YELLOW, fill_opacity=0.5)

        # Transform Square to Star
        self.play(Transform(shape1, shape4))
        self.wait(1)

        # Fade out
        self.play(FadeOut(shape1))
        self.wait(1)