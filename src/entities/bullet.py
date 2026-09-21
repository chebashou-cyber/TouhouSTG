# -*- coding: utf-8 -*-
"""bullet.py — 子弹统一数据模型 + 对象池

性能要求: 2000 颗敌弹稳定 60 FPS。
新增 (v0.4): split_at_age / split_count / split_speed 等字段支持 delayed 分裂;
  BulletPool.step() 在每颗子弹 age >= split_at_age 时分裂为 split_count 颗,
  原子弹回收。分裂角范围 BULLET_SPLIT_ANGLE_SPAN。
"""
from __future__ import annotations
import math
import pygame
from dataclasses import dataclass

from config import (
    BULLET_POOL_INITIAL, BULLET_HITBOX_RADIUS, BULLET_SPLIT_ANGLE_SPAN,
    SCREEN_W, SCREEN_H,
)


# 子弹种类常量
KIND_ENEMY = 0
KIND_PLAYER = 1


@dataclass(slots=True)
class Bullet:
    """统一子弹数据模型。所有字段每帧就地修改, 不再分配新对象。"""
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    ax: float = 0.0
    ay: float = 0.0
    angle: float = 0.0
    angular_v: float = 0.0
    radius: float = BULLET_HITBOX_RADIUS
    color: tuple = (255, 90, 90)
    kind: int = KIND_ENEMY
    alive: bool = False
    grazed: bool = False
    age: float = 0.0
    # 分裂 (delayed)
    split_at_age: float = -1.0
    split_count: int = 0
    split_speed: float = 0.0
    split_radius: float = BULLET_HITBOX_RADIUS
    split_color: tuple = (255, 90, 90)
    split_kind: int = 0  # KIND_ENEMY=0


def _out_of_bounds(x: float, y: float, r: float) -> bool:
    return x < -r - 8 or x > SCREEN_W + r + 8 or y < -r - 8 or y > SCREEN_H + r + 8


class BulletPool:
    """敌弹 / 自机弹共用池。active 与 free 双列表, swap-and-pop 回收。"""

    __slots__ = ("_free", "_active", "_sprite_cache")

    def __init__(self, initial: int = BULLET_POOL_INITIAL) -> None:
        self._free: list[Bullet] = [Bullet() for _ in range(initial)]
        self._active: list[Bullet] = []
        self._sprite_cache: dict[tuple, pygame.Surface] = {}

    # ------- spawn -------
    def acquire(
        self,
        x: float, y: float,
        vx: float, vy: float,
        *,
        radius: float = BULLET_HITBOX_RADIUS,
        color: tuple = (255, 90, 90),
        kind: int = KIND_ENEMY,
        ax: float = 0.0, ay: float = 0.0,
        angle: float = 0.0, angular_v: float = 0.0,
        split_at_age: float = -1.0,
        split_count: int = 0,
        split_speed: float = 0.0,
        split_radius: float = BULLET_HITBOX_RADIUS,
        split_color: tuple = (255, 90, 90),
        split_kind: int = 0,
    ) -> Bullet:
        b = self._free.pop() if self._free else Bullet()
        b.x = x; b.y = y; b.vx = vx; b.vy = vy
        b.ax = ax; b.ay = ay
        b.angle = angle; b.angular_v = angular_v
        b.radius = radius; b.color = color; b.kind = kind
        b.alive = True; b.grazed = False; b.age = 0.0
        b.split_at_age = split_at_age
        b.split_count = split_count
        b.split_speed = split_speed
        b.split_radius = split_radius
        b.split_color = split_color
        b.split_kind = split_kind
        self._active.append(b)
        return b

    def acquire_many(self, specs) -> int:
        n = 0
        for s in specs:
            self.acquire(**s)
            n += 1
        return n

    # ------- 分裂 -------
    def _split(self, parent: Bullet) -> None:
        """按 parent 的分裂参数生成新子弹, 原子弹由 caller 回收。"""
        count = parent.split_count
        if count <= 0:
            return
        base_angle = math.atan2(parent.vy, parent.vx) if (parent.vx or parent.vy) else 0.0
        span = BULLET_SPLIT_ANGLE_SPAN
        if count == 1:
            angles = [base_angle]
        else:
            angles = [base_angle - span / 2.0 + span * i / (count - 1) for i in range(count)]
        for a in angles:
            self.acquire(
                parent.x, parent.y,
                math.cos(a) * parent.split_speed,
                math.sin(a) * parent.split_speed,
                radius=parent.split_radius,
                color=parent.split_color,
                kind=parent.split_kind,
            )

    # ------- update -------
    def step(self, dt: float) -> None:
        new_active: list[Bullet] = []
        for b in self._active:
            b.age += dt
            b.vx += b.ax * dt
            b.vy += b.ay * dt
            b.x += b.vx * dt
            b.y += b.vy * dt
            b.angle += b.angular_v * dt
            # 分裂
            if b.split_at_age >= 0.0 and b.age >= b.split_at_age:
                self._split(b)
                b.alive = False
                self._free.append(b)
                continue
            if _out_of_bounds(b.x, b.y, b.radius):
                b.alive = False
                self._free.append(b)
            else:
                new_active.append(b)
        self._active = new_active

    def release(self, b: Bullet) -> None:
        b.alive = False
        a = self._active
        for i in range(len(a) - 1, -1, -1):
            if a[i] is b:
                last = a.pop()
                if i < len(a):
                    a[i] = last
                break
        self._free.append(b)

    def clear_enemy(self) -> int:
        keep: list[Bullet] = []
        removed = 0
        for b in self._active:
            if b.kind == KIND_ENEMY:
                b.alive = False
                self._free.append(b)
                removed += 1
            else:
                keep.append(b)
        self._active = keep
        return removed

    def clear_all(self) -> None:
        for b in self._active:
            b.alive = False
            self._free.append(b)
        self._active.clear()

    # ------- 查询 -------
    @property
    def active(self) -> list[Bullet]:
        return self._active

    def enemy_count(self) -> int:
        return sum(1 for b in self._active if b.kind == KIND_ENEMY)

    # ------- render -------
    def _sprite(self, color: tuple, radius: int) -> pygame.Surface:
        key = (color, radius)
        s = self._sprite_cache.get(key)
        if s is None:
            size = radius * 2 + 2
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (size // 2, size // 2), radius)
            self._sprite_cache[key] = s
        return s

    def draw(self, surf: pygame.Surface) -> None:
        groups: dict[tuple, list[Bullet]] = {}
        for b in self._active:
            k = (b.color, int(b.radius))
            lst = groups.get(k)
            if lst is None:
                groups[k] = [b]
            else:
                lst.append(b)
        for (color, radius), bullets in groups.items():
            s = self._sprite(color, radius)
            ox = s.get_width() // 2
            oy = s.get_height() // 2
            payload = [(s, (b.x - ox, b.y - oy)) for b in bullets]
            try:
                surf.blits(payload, dither=False)
            except TypeError:
                # pygame <2.1.3 不支持 dither 参数
                surf.blits(payload)

