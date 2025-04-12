from manim import *

class MainScene(Scene):
    def construct(self):
        vertices = {
            0: [0, 3, 0],
            1: [-2, 1, 0],
            2: [2, 1, 0],
            3: [-3, -1, 0],
            4: [-1, -1, 0],
            5: [1, -1, 0],
            6: [3, -1, 0]
        }
        edges = [
            (0, 1), (0, 2),
            (1, 3), (1, 4),
            (2, 5), (2, 6)
        ]

        vertex_dots = VGroup(*[Dot(vertices[v]) for v in vertices])
        edge_lines = VGroup(*[Line(vertices[u], vertices[v]) for u, v in edges])

        self.play(Create(vertex_dots), run_time=3)
        self.play(Create(edge_lines), run_time=5)
        self.wait(1)