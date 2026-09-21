# -*- coding: utf-8 -*-
"""patterns/aimed.py — 自机狙

按当前自机位置精确发射 count 颗, 默认 1 颗。可选 spread 让多颗之间张开。
"""
from __future__ import annotations
import math
from src.patterns.base import Pattern
from config import to_color


class Aimed(Pattern):
    name = "aimed"

    def __init__(self, *, color: str = "red", speed: float = 220.0,
                 radius: float = 4.0, count: int = 1, spread: float = 0.0) -> None:
        self.color = to_color(color)
        self.speed = speed
        self.radius = radius
        self.count = max(1, count)
        self.spread = spread  # 多颗时相邻张角 (弧度)

    def tick(self, ox, oy, tx, ty, t):
        dx = tx - ox
        dy = ty - oy
        d = math.hypot(dx, dy) or 1.0
        base_angle = math.atan2(dy, dx)
        specs = []
        if self.count == 1:
            angles = [base_angle]
        else:
            half = self.spread * (self.count - 1) / 2.0
            angles = [base_angle - half + self.spread * i for i in range(self.count)]
        for a in angles:
            specs.append({
                "x": ox, "y": oy,
                "vx": math.cos(a) * self.speed,
                "vy": math.sin(a) * self.speed,
                "radius": self.radius,
                "color": self.color,
                "kind": 0,
            })
        return specs

    def reset(self) -> None:
        pass
