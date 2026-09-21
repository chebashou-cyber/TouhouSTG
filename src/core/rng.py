# -*- coding: utf-8 -*-
"""rng.py — 可复现的随机数源

设计目标: pattern/弹幕发射器使用独立 RNG 实例, 同一关卡在不同运行下表现一致,
便于复现 / 调试弹幕缝隙。
注意: 不要在业务逻辑里使用全局 random.*, 应通过 RNG 实例取数。
"""
from __future__ import annotations
import random


class RNG:
    """轻量封装的随机数生成器, 支持 seed。"""

    __slots__ = ("_r",)

    def __init__(self, seed: int | None = None) -> None:
        self._r = random.Random(seed)

    def seed(self, value: int) -> None:
        self._r.seed(value)

    def rand(self) -> float:
        """[0, 1) 浮点。"""
        return self._r.random()

    def uniform(self, lo: float, hi: float) -> float:
        return self._r.uniform(lo, hi)

    def randint(self, lo: int, hi: int) -> int:
        return self._r.randint(lo, hi)

    def choice(self, seq):
        return self._r.choice(seq)

    def gauss(self, mu: float, sigma: float) -> float:
        return self._r.gauss(mu, sigma)