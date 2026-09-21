# -*- coding: utf-8 -*-
"""patterns/delayed.py — Delayed 分裂模式

继承 Aimed/Fan/Ring 等基础模式, 但给返回的子弹添加 split_at_age / split_count / split_speed 字段,
让子弹在飞行 N 秒后自动分裂为 M 颗。
"""
from __future__ import annotations
import math
from src.patterns.base import Pattern
from src.patterns.aimed import Aimed
from src.patterns.fan import Fan
from src.patterns.ring import Ring
from src.patterns.scatter import Scatter
from config import to_color, BULLET_SPLIT_COUNT_DEFAULT, BULLET_SPLIT_SPEED_DEFAULT


def _wrap_split(specs: list[dict], *, split_at: float, split_count: int,
                split_speed: float, split_radius: float = 4.0,
                split_color: tuple = (255, 90, 90)) -> list[dict]:
    """在每个 spec 上注入分裂参数。"""
    for spec in specs:
        spec["split_at_age"] = split_at
        spec["split_count"] = split_count
        spec["split_speed"] = split_speed
        spec["split_radius"] = split_radius
        spec["split_color"] = split_color
    return specs


class DelayedAimed(Pattern):
    """自机狙 + 飞行后分裂。"""

    def __init__(self, *, color: str = "red", speed: float = 220.0,
                 radius: float = 4.0, count: int = 1, spread: float = 0.0,
                 split_at: float = 0.5,
                 split_count: int = BULLET_SPLIT_COUNT_DEFAULT,
                 split_speed: float = BULLET_SPLIT_SPEED_DEFAULT) -> None:
        self.inner = Aimed(color=color, speed=speed, radius=radius, count=count, spread=spread)
        self.color = to_color(color)
        self.radius = radius
        self.split_at = split_at
        self.split_count = split_count
        self.split_speed = split_speed
        self.split_radius = radius

    def tick(self, ox, oy, tx, ty, t):
        specs = self.inner.tick(ox, oy, tx, ty, t)
        return _wrap_split(specs, split_at=self.split_at,
                           split_count=self.split_count,
                           split_speed=self.split_speed,
                           split_radius=self.split_radius,
                           split_color=self.color)

    def reset(self) -> None:
        self.inner.reset()


class DelayedFan(Pattern):
    """扇形 + 飞行后分裂。"""

    def __init__(self, *, color: str = "red", speed: float = 200.0,
                 radius: float = 4.0, count: int = 5, arc: float = math.pi / 2,
                 base_angle: float | str = math.pi / 2,
                 rotate_speed: float = 0.0,
                 split_at: float = 0.6,
                 split_count: int = BULLET_SPLIT_COUNT_DEFAULT,
                 split_speed: float = BULLET_SPLIT_SPEED_DEFAULT) -> None:
        self.inner = Fan(color=color, speed=speed, radius=radius, count=count,
                          arc=arc, base_angle=base_angle, rotate_speed=rotate_speed)
        self.color = to_color(color)
        self.radius = radius
        self.split_at = split_at
        self.split_count = split_count
        self.split_speed = split_speed
        self.split_radius = radius

    def tick(self, ox, oy, tx, ty, t):
        specs = self.inner.tick(ox, oy, tx, ty, t)
        return _wrap_split(specs, split_at=self.split_at,
                           split_count=self.split_count,
                           split_speed=self.split_speed,
                           split_radius=self.split_radius,
                           split_color=self.color)

    def reset(self) -> None:
        self.inner.reset()


class DelayedRing(Pattern):
    """环形 + 飞行后分裂。"""

    def __init__(self, *, color: str = "red", speed: float = 200.0,
                 radius: float = 4.0, count: int = 16,
                 base_angle: float = 0.0, rotate_speed: float = 0.0,
                 speed_jitter: float = 0.0,
                 split_at: float = 0.6,
                 split_count: int = BULLET_SPLIT_COUNT_DEFAULT,
                 split_speed: float = BULLET_SPLIT_SPEED_DEFAULT) -> None:
        self.inner = Ring(color=color, speed=speed, radius=radius, count=count,
                          base_angle=base_angle, rotate_speed=rotate_speed,
                          speed_jitter=speed_jitter)
        self.color = to_color(color)
        self.radius = radius
        self.split_at = split_at
        self.split_count = split_count
        self.split_speed = split_speed
        self.split_radius = radius

    def tick(self, ox, oy, tx, ty, t):
        specs = self.inner.tick(ox, oy, tx, ty, t)
        return _wrap_split(specs, split_at=self.split_at,
                           split_count=self.split_count,
                           split_speed=self.split_speed,
                           split_radius=self.split_radius,
                           split_color=self.color)

    def reset(self) -> None:
        self.inner.reset()