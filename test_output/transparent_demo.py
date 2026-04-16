"""Simple Manim scene to demonstrate transparent-background video output."""
from manim import *


class TransparentCircleWave(Scene):
    def construct(self):
        # No background — Manim's -t flag makes it transparent
        title = Text("AirClip", font_size=48, color=WHITE, weight=BOLD)
        subtitle = Text("transparent bg demo", font_size=24, color=GRAY_B)
        subtitle.next_to(title, DOWN, buff=0.3)

        circle = Circle(radius=1.5, color=BLUE, stroke_width=4)
        dot = Dot(color=YELLOW).move_to(circle.point_from_proportion(0))

        self.play(Write(title), FadeIn(subtitle), run_time=1)
        self.wait(0.5)
        self.play(FadeOut(title), FadeOut(subtitle), run_time=0.5)

        self.play(Create(circle), run_time=1)
        self.play(FadeIn(dot), run_time=0.3)

        # Dot orbits the circle
        self.play(MoveAlongPath(dot, circle), run_time=2, rate_func=linear)

        # Morphing
        square = Square(side_length=2.5, color=GREEN, stroke_width=4)
        self.play(Transform(circle, square), run_time=1)
        self.play(MoveAlongPath(dot, square), run_time=2, rate_func=linear)

        self.play(FadeOut(circle), FadeOut(dot), run_time=0.5)
        self.wait(0.3)
