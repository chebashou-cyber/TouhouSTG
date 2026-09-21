# -*- coding: utf-8 -*-
"""patterns/spiral.py — 螺旋

每次 tick 整体旋转 step_angle, 在 base_angle 周围发射 count 颗 (相邻 2pi/count)。
可以传入 arms=2 等产生多臂螺旋。
"""
from __future__ import annotations
import math
from src.patterns.base import Pattern
from config import to_color


class Spiral(Pattern):
    name = "spiral"

    def __init__(self, *, color: str = "red", speed: float = 200.0,
                 radius: float = 4.0, count: int = 2, arms: int = 1,
                 step_angle: float = 0.15, base_angle: float = 0.0) -> None:
        self.color = to_color(color)
        self.speed = speed
        self.radius = radius
        self.count = max(1, count)
        self.arms = max(1, arms)
        self.step_angle = step_angle
        self.base_angle = base_angle
        self._angle = 0.0

    def tick(self, ox, oy, tx, ty, t):
        # 在 tick 内推进一次
        specs = []
        arm_step = 2 * math.pi / self.arms
        a0 = self.base_angle + self._angle
        for ai in range(self.arms):
            base_a = a0 + ai * arm_step
            for i in range(self.count):
                a = base_a + 2 * math.pi * i / self.count
                specs.append({
                    "x": ox, "y": oy,
                    "vx": math.cos(a) * self.speed,
                    "vy": math.sin(a) * self.speed,
                    "radius": self.radius,
                    "color": self.color,
                    "kind": 0,
                })
        self._angle += self.step_angle
        return specs

    def reset(self) -> None:
        self._angle = 0.0
