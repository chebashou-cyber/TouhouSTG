# -*- coding: utf-8 -*-
"""patterns/ring.py — 环形发射

count 颗在 360 度内均匀发射, base_angle 起始偏移, rotate_speed 整体旋转 (弧度/秒)。
常与 Spiral 配合出多层环。
"""
from __future__ import annotations
import math
from src.patterns.base import Pattern
from config import to_color


class Ring(Pattern):
    name = "ring"

    def __init__(self, *, color: str = "red", speed: float = 200.0,
                 radius: float = 4.0, count: int = 16,
                 base_angle: float = 0.0, rotate_speed: float = 0.0,
                 speed_jitter: float = 0.0) -> None:
        self.color = to_color(color)
        self.speed = speed
        self.radius = radius
        self.count = max(1, count)
        self.base_angle = base_angle
        self.rotate_speed = rotate_speed
        self.speed_jitter = speed_jitter

    def tick(self, ox, oy, tx, ty, t):
        a0 = self.base_angle + self.rotate_speed * t
        step = 2 * math.pi / self.count
        specs = []
        for i in range(self.count):
            a = a0 + step * i
            sp = self.speed
            if self.speed_jitter:
                sp += (math.sin(a * 7 + t * 3) * 0.5) * self.speed_jitter
            specs.append({
                "x": ox, "y": oy,
                "vx": math.cos(a) * sp,
                "vy": math.sin(a) * sp,
                "radius": self.radius,
                "color": self.color,
                "kind": 0,
            })
        return specs

    def reset(self) -> None:
        pass
