from manim import *

class MainScene(Scene):
    def construct(self):
        # Define node content and positions
        node_contents = {
            1: "1", 2: "2", 3: "3", 4: "4", 5: "5"
        }
        node_positions = {
            1: UP * 2,
            2: LEFT * 2,
            3: RIGHT * 2,
            4: LEFT * 3 + DOWN * 1.5,
            5: LEFT * 1 + DOWN * 1.5
        }
        edges_info = [
            (1, 2), (1, 3), (2, 4), (2, 5)
        ]

        # Create nodes (circles + text)
        nodes = VGroup()
        node_mobjects = {}
        for i, pos in node_positions.items():
            circle = Circle(radius=0.5, color=BLUE, fill_opacity=0.8)
            text = Text(node_contents[i], color=WHITE).move_to(circle.get_center())
            node = VGroup(circle, text).move_to(pos)
            node_mobjects[i] = node
            # nodes.add(node) # Add later during animation

        # Create edges (arrows representing pointers)
        edges = VGroup()
        edge_mobjects = {}
        for start_node_idx, end_node_idx in edges_info:
            start_node = node_mobjects[start_node_idx]
            end_node = node_mobjects[end_node_idx]
            # Adjust start and end points to be on the circumference
            direction = end_node.get_center() - start_node.get_center()
            unit_direction = direction / np.linalg.norm(direction)
            start_point = start_node.get_center() + unit_direction * start_node[0].radius # Use circle radius
            end_point = end_node.get_center() - unit_direction * end_node[0].radius

            arrow = Arrow(start_point, end_point, buff=0, stroke_width=4, max_tip_length_to_length_ratio=0.15, color=GRAY)
            edge_mobjects[(start_node_idx, end_node_idx)] = arrow
            # edges.add(arrow) # Add later during animation

        # Title
        title = Text("Tree Structure (Linked Nodes)").to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # Animate creation
        self.play(Create(node_mobjects[1]))
        self.wait(0.5)

        # Animate Root -> Left Child (2)
        edge12 = edge_mobjects[(1, 2)]
        label12 = Text("Left Pointer", font_size=20).next_to(edge12.get_center(), UP, buff=0.1)
        self.play(
            Create(node_mobjects[2]),
            GrowArrow(edge12),
            Write(label12)
        )
        self.wait(1)

        # Animate Root -> Right Child (3)
        edge13 = edge_mobjects[(1, 3)]
        label13 = Text("Right Pointer", font_size=20).next_to(edge13.get_center(), UP, buff=0.1)
        self.play(
            FadeOut(label12),
            Create(node_mobjects[3]),
            GrowArrow(edge13),
            Write(label13)
        )
        self.wait(1)

        # Animate Node 2 -> Left Child (4)
        edge24 = edge_mobjects[(2, 4)]
        label24 = Text("Left Pointer", font_size=20).next_to(edge24.get_center(), DOWN, buff=0.1)
        self.play(
            FadeOut(label13),
            Create(node_mobjects[4]),
            GrowArrow(edge24),
            Write(label24)
        )
        self.wait(1)

        # Animate Node 2 -> Right Child (5)
        edge25 = edge_mobjects[(2, 5)]
        label25 = Text("Right Pointer", font_size=20).next_to(edge25.get_center(), DOWN, buff=0.1)
        self.play(
            FadeOut(label24),
            Create(node_mobjects[5]),
            GrowArrow(edge25),
            Write(label25)
        )
        self.wait(1)

        self.play(FadeOut(label25))
        self.wait(0.5)

        # Indicate all pointers
        all_edges = VGroup(*edge_mobjects.values())
        self.play(Indicate(all_edges, color=YELLOW, scale_factor=1.1), run_time=2)
        self.wait(2)