# -*- coding: utf-8 -*-
"""patterns/fan.py — 扇形散射

在 base_angle 周围 arc 弧度内均匀发射 count 颗。
base_angle 为 "aimed" 时按当前玩家方向; 否则为固定角度 (弧度)。
"""
from __future__ import annotations
import math
from src.patterns.base import Pattern
from config import to_color


class Fan(Pattern):
    name = "fan"

    def __init__(self, *, color: str = "red", speed: float = 200.0,
                 radius: float = 4.0, count: int = 5, arc: float = math.pi / 2,
                 base_angle: float | str = math.pi / 2, rotate_speed: float = 0.0) -> None:
        """base_angle:
            - "aimed" 表示对玩家
            - 数值表示固定角度 (弧度, 0=+x, pi/2=+y 即屏幕向下)
        """
        self.color = to_color(color)
        self.speed = speed
        self.radius = radius
        self.count = max(1, count)
        self.arc = arc
        self.base_angle = base_angle
        self.rotate_speed = rotate_speed  # 弧度/秒

    def tick(self, ox, oy, tx, ty, t):
        if self.base_angle == "aimed":
            base = math.atan2(ty - oy, tx - ox)
        else:
            base = float(self.base_angle) + self.rotate_speed * t
        half = self.arc / 2.0
        specs = []
        if self.count == 1:
            angles = [base]
        else:
            angles = [base - half + self.arc * i / (self.count - 1) for i in range(self.count)]
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
