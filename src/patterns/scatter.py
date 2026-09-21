# -*- coding: utf-8 -*-
"""patterns/scatter.py — 随机散射

围绕 base_angle 在 angle_jitter 范围内随机角度发射 count 颗。
需要外部传入 RNG 实例, 保持弹幕可复现。
"""
from __future__ import annotations
import math
from src.patterns.base import Pattern
from config import to_color
from src.core.rng import RNG


class Scatter(Pattern):
    name = "scatter"

    def __init__(self, *, color: str = "red", speed: float = 180.0,
                 radius: float = 4.0, count: int = 8,
                 base_angle: float | str = math.pi / 2,
                 angle_jitter: float = math.pi / 3,
                 speed_jitter: float = 0.0,
                 rng: RNG | None = None) -> None:
        self.color = to_color(color)
        self.speed = speed
        self.radius = radius
        self.count = max(1, count)
        self.base_angle = base_angle
        self.angle_jitter = angle_jitter
        self.speed_jitter = speed_jitter
        self.rng = rng or RNG(0)

    def tick(self, ox, oy, tx, ty, t):
        if self.base_angle == "aimed":
            base = math.atan2(ty - oy, tx - ox)
        else:
            base = float(self.base_angle)
        specs = []
        for _ in range(self.count):
            a = base + self.rng.uniform(-self.angle_jitter, self.angle_jitter)
            sp = self.speed
            if self.speed_jitter:
                sp += self.rng.uniform(-self.speed_jitter, self.speed_jitter)
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
