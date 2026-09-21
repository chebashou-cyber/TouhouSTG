# -*- coding: utf-8 -*-
"""background.py — 视差背景

无贴图情况下用程序化两层星点模拟视差滚动:
  - 远景 (far): 数量多, 亮度低, 滚动慢
  - 近景 (near): 数量少, 亮度高, 滚动快
星点位置在 update 中整体下移, 出屏后回到屏幕顶部随机 x。
"""
from __future__ import annotations
import random
import pygame
from config import (
    SCREEN_W, SCREEN_H,
    BG_FAR_STARS, BG_NEAR_STARS,
    BG_FAR_SPEED, BG_NEAR_SPEED,
    BG_FAR_BRIGHTNESS, BG_NEAR_BRIGHTNESS,
)


class StarLayer:
    """单层星点。所有星点字段都是浮点 (便于精确滚动)。"""

    __slots__ = ("_x", "_y", "_count", "_speed", "_brightness")

    def __init__(self, count: int, speed: float, brightness: int, rng: random.Random) -> None:
        self._count = count
        self._speed = speed
        self._brightness = brightness
        self._x = [rng.uniform(0, SCREEN_W) for _ in range(count)]
        self._y = [rng.uniform(0, SCREEN_H) for _ in range(count)]

    def update(self, dt: float) -> None:
        for i in range(self._count):
            self._y[i] += self._speed * dt
            if self._y[i] > SCREEN_H:
                self._y[i] -= SCREEN_H  # 出屏回顶 (避免随机让原位置看起来跳变)
                # 重新随机水平位置, 制造新星点感
                self._x[i] = (self._x[i] + random.uniform(-50, 50)) % SCREEN_W

    def draw(self, surf: pygame.Surface) -> None:
        col = (self._brightness, self._brightness, self._brightness)
        # 用 set_at + Rect 不快, 但星点数量 ≤120, 性能可接受
        for i in range(self._count):
            surf.set_at((int(self._x[i]), int(self._y[i])), col)


class ParallaxBackground:
    """视差背景, 持有 far + near 两层。"""

    __slots__ = ("far", "near", "_rng")

    def __init__(self, seed: int = 7) -> None:
        self._rng = random.Random(seed)
        self.far = StarLayer(BG_FAR_STARS, BG_FAR_SPEED, BG_FAR_BRIGHTNESS, self._rng)
        self.near = StarLayer(BG_NEAR_STARS, BG_NEAR_SPEED, BG_NEAR_BRIGHTNESS, self._rng)

    def update(self, dt: float) -> None:
        self.far.update(dt)
        self.near.update(dt)

    def draw(self, surf: pygame.Surface) -> None:
        self.far.draw(surf)
        self.near.draw(surf)