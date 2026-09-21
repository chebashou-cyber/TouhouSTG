# -*- coding: utf-8 -*-
"""hit_particle.py — 击中粒子

击杀/击退时 spawn 几个短寿命粒子, 让击中反馈更明显。
对象池实现, 性能可控。
"""
from __future__ import annotations
import math
import random
import pygame


HIT_PARTICLE_LIFE = 0.35
HIT_PARTICLE_SPEED = 220.0
HIT_PARTICLE_RADIUS = 2


class HitParticle:
    __slots__ = ("x", "y", "vx", "vy", "color", "age", "life", "alive")

    def __init__(self) -> None:
        self.x = 0.0; self.y = 0.0
        self.vx = 0.0; self.vy = 0.0
        self.color = (255, 255, 255)
        self.age = 0.0
        self.life = HIT_PARTICLE_LIFE
        self.alive = False

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        self.age += dt
        if self.age >= self.life:
            self.alive = False
            return
        # 减速
        damp = 0.92 ** (dt * 60.0)
        self.vx *= damp
        self.vy *= damp
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        t = max(0.0, 1.0 - self.age / self.life)
        r = max(1, int(HIT_PARTICLE_RADIUS * t))
        a = int(255 * t)
        col = (a, a, a)
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), r)


class HitParticlePool:
    __slots__ = ("_free", "_active", "_rng")

    def __init__(self, initial: int = 256) -> None:
        self._free: list[HitParticle] = [HitParticle() for _ in range(initial)]
        self._active: list[HitParticle] = []
        self._rng = random.Random()

    def spawn(self, x: float, y: float, color: tuple, count: int = 6) -> int:
        n = 0
        for _ in range(count):
            p = self._free.pop() if self._free else HitParticle()
            a = self._rng.uniform(0.0, math.tau)
            sp = HIT_PARTICLE_SPEED * self._rng.uniform(0.4, 1.0)
            p.x = x; p.y = y
            p.vx = math.cos(a) * sp; p.vy = math.sin(a) * sp
            p.color = color
            p.age = 0.0
            p.life = HIT_PARTICLE_LIFE
            p.alive = True
            self._active.append(p)
            n += 1
        return n

    def update(self, dt: float) -> None:
        keep = []
        for p in self._active:
            p.update(dt)
            if p.alive:
                keep.append(p)
            else:
                self._free.append(p)
        self._active = keep

    def draw(self, surf: pygame.Surface) -> None:
        for p in self._active:
            p.draw(surf)

    def clear(self) -> None:
        for p in self._active:
            p.alive = False
            self._free.append(p)
        self._active.clear()

    def count(self) -> int:
        return len(self._active)