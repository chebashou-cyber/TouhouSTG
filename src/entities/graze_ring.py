# -*- coding: utf-8 -*-
"""graze_ring.py — 擦弹波纹

玩家擦弹瞬间在自机位置 spawn 一圈波纹, 0.3s 扩散到半径 18px 后消失。
提示玩家"擦到了"。
"""
from __future__ import annotations
import math
import pygame


GRAZE_RING_LIFE = 0.32
GRAZE_RING_MAX_RADIUS = 22.0


class GrazeRing:
    __slots__ = ("x", "y", "age", "life", "max_r", "alive", "color")

    def __init__(self) -> None:
        self.x = 0.0; self.y = 0.0
        self.age = 0.0
        self.life = GRAZE_RING_LIFE
        self.max_r = GRAZE_RING_MAX_RADIUS
        self.alive = False
        self.color = (255, 230, 180)

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        self.age += dt
        if self.age >= self.life:
            self.alive = False

    def draw(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        t = self.age / self.life
        r = self.max_r * t
        alpha = int(220 * (1.0 - t))
        # 用 set_alpha 的 Surface 太重, 改为按 alpha 直接调亮
        col = (alpha, int(alpha * 0.85), int(alpha * 0.6))
        if r >= 1:
            pygame.draw.circle(surf, col, (int(self.x), int(self.y)), int(r), 1)


class GrazeRingPool:
    __slots__ = ("_free", "_active")

    def __init__(self, initial: int = 64) -> None:
        self._free: list[GrazeRing] = [GrazeRing() for _ in range(initial)]
        self._active: list[GrazeRing] = []

    def spawn(self, x: float, y: float) -> GrazeRing:
        if self._free:
            g = self._free.pop()
        else:
            g = GrazeRing()
        g.x = x; g.y = y
        g.age = 0.0; g.alive = True
        self._active.append(g)
        return g

    def update(self, dt: float) -> None:
        keep = []
        for g in self._active:
            g.update(dt)
            if g.alive:
                keep.append(g)
            else:
                self._free.append(g)
        self._active = keep

    def draw(self, surf: pygame.Surface) -> None:
        for g in self._active:
            g.draw(surf)

    def clear(self) -> None:
        for g in self._active:
            g.alive = False
            self._free.append(g)
        self._active.clear()

    def count(self) -> int:
        return len(self._active)