# -*- coding: utf-8 -*-
"""death_effect.py — 死亡动画

自机被弹/触发 bomb 时播放的粒子爆散效果。粒子用简单的 list 维护,
无需对象池 (一次性短寿命事件, 量很少)。
"""
from __future__ import annotations
import math
import random
import pygame
from config import (
    COLOR_DEATH_PARTICLE,
    DEATH_EFFECT_PARTICLES, DEATH_EFFECT_SPEED_MIN, DEATH_EFFECT_SPEED_MAX,
    DEATH_EFFECT_LIFE, DEATH_EFFECT_RADIUS,
)


class DeathEffect:
    """单次爆散粒子效果。alive=False 时可释放。"""

    __slots__ = ("particles", "alive")

    def __init__(self, x: float, y: float, count: int = DEATH_EFFECT_PARTICLES) -> None:
        self.particles: list[tuple[float, float, float, float, float]] = []
        # (x, y, vx, vy, age)
        for _ in range(count):
            a = random.uniform(0.0, math.tau)
            sp = random.uniform(DEATH_EFFECT_SPEED_MIN, DEATH_EFFECT_SPEED_MAX)
            self.particles.append((x, y, math.cos(a) * sp, math.sin(a) * sp, 0.0))
        self.alive = True

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        new_particles = []
        for (x, y, vx, vy, age) in self.particles:
            age += dt
            if age >= DEATH_EFFECT_LIFE:
                continue  # 自然消亡
            # 简单减速 + 重力效果 (可选)
            damp = 0.985
            vx *= damp
            vy *= damp
            x += vx * dt
            y += vy * dt
            new_particles.append((x, y, vx, vy, age))
        self.particles = new_particles
        if not self.particles:
            self.alive = False

    def draw(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        for (x, y, vx, vy, age) in self.particles:
            # 寿命衰减 alpha (简单按 life 比例调亮)
            t = max(0.0, 1.0 - age / DEATH_EFFECT_LIFE)
            r = max(1, int(DEATH_EFFECT_RADIUS * t))
            alpha = int(255 * t)
            # 简化: 直接用调亮颜色代替 alpha (避免每粒子 SRCALPHA Surface)
            col = (alpha, alpha // 2, alpha // 3)
            pygame.draw.circle(surf, col, (int(x), int(y)), r)