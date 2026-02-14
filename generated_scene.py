from manim import *
import numpy as np

class GenScene(ThreeDScene):
    def construct(self):
        # Set initial camera orientation
        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        
        # Create 3D axes
        axes = ThreeDAxes(
            x_range=[-10, 10, 1],
            y_range=[-10, 10, 1],
            z_range=[-4, 4, 1]
        )
        self.add(axes)
        
        # Define colorful spiral helix parametric function
        spiral = ParametricFunction(
            lambda t: np.array([
                t * np.cos(t),
                t * np.sin(t),
                t/3
            ]),
            t_range=np.array([-3*PI, 3*PI]),
            color=WHITE
        )
        spiral.set_color_by_gradient([BLUE, GREEN, YELLOW, RED])
        self.add(spiral)
        
        # Create small red sphere
        sphere = Sphere(radius=0.1, color=RED)
        
        # Animate sphere moving along spiral while rotating camera
        self.play(
            MoveAlongPath(sphere, spiral, run_time=4),
            self.move_camera(phi=2*PI, theta=2*PI, run_time=4)
        )