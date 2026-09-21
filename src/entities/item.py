# -*- coding: utf-8 -*-
"""item.py — 道具

类型:
  TYPE_POWER  : P 点, 加 Power, 满 Power 时自动转 50000 分
  TYPE_SCORE  : 分数道具, 越靠上分越高
  TYPE_BOMB   : 炸弹道具, +1 炸弹
  TYPE_LIFE   : 1UP, +1 残机
掉落:
  敌机死亡时按 ENEMY_DROP_TABLE 决定 (在 enemy.py 中实现)
吸引:
  自机进入 ITEM_ATTRACT_RADIUS 时向玩家加速 (匀加速曲线, 限制最高速)
收集:
  与自机 hitbox 碰撞时被吸收, 同时清道具
"""
from __future__ import annotations
import math
import pygame
from config import (
    SCREEN_H, SCREEN_W,
    ITEM_FALL_SPEED, ITEM_ATTRACT_SPEED_MIN, ITEM_ATTRACT_SPEED_MAX,
    ITEM_ATTRACT_ACCEL, ITEM_ATTRACT_RADIUS,
    ITEM_COLLECT_RADIUS,
    ITEM_P_VALUE, ITEM_P_FULL_BONUS_SCORE,
    ITEM_SCORE_BASE, ITEM_SCORE_HEIGHT_FACTOR,
    ITEM_BOMB_VALUE, ITEM_LIFE_VALUE,
    ITEM_COLOR_POWER, ITEM_COLOR_POWER_FULL,
    ITEM_COLOR_SCORE, ITEM_COLOR_BOMB, ITEM_COLOR_LIFE,
    ITEM_RADIUS, PLAYER_MAX_POWER,
)

# 类型常量
TYPE_POWER = 0
TYPE_SCORE = 1
TYPE_BOMB = 2
TYPE_LIFE = 3


def item_color(kind: int) -> tuple:
    return {
        TYPE_POWER: ITEM_COLOR_POWER,
        TYPE_SCORE: ITEM_COLOR_SCORE,
        TYPE_BOMB:  ITEM_COLOR_BOMB,
        TYPE_LIFE:  ITEM_COLOR_LIFE,
    }.get(kind, ITEM_COLOR_POWER)


def item_label(kind: int) -> str:
    return {
        TYPE_POWER: "P",
        TYPE_SCORE: "$",
        TYPE_BOMB:  "B",
        TYPE_LIFE:  "1UP",
    }.get(kind, "?")


class Item:
    __slots__ = (
        "x", "y", "vx", "vy",
        "kind", "value", "alive", "age",
    )

    def __init__(self, x: float, y: float, kind: int, value: int = 1) -> None:
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = ITEM_FALL_SPEED
        self.kind = kind
        self.value = value
        self.alive = True
        self.age = 0.0

    def update(self, dt: float, player) -> None:
        if not self.alive:
            return
        self.age += dt

        dx = player.x - self.x
        dy = player.y - self.y
        d = math.hypot(dx, dy)

        if d < ITEM_ATTRACT_RADIUS and d > 1e-3:
            ax = dx / d * ITEM_ATTRACT_ACCEL
            ay = dy / d * ITEM_ATTRACT_ACCEL
            self.vx += ax * dt
            self.vy += ay * dt

        sp = math.hypot(self.vx, self.vy)
        if sp > ITEM_ATTRACT_SPEED_MAX:
            scale = ITEM_ATTRACT_SPEED_MAX / sp
            self.vx *= scale
            self.vy *= scale
        elif sp < ITEM_ATTRACT_SPEED_MIN and d >= ITEM_ATTRACT_RADIUS:
            if sp > 0:
                scale = ITEM_ATTRACT_SPEED_MIN / sp
                self.vx *= scale
                self.vy *= scale
            else:
                self.vy = ITEM_FALL_SPEED

        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.y < -16 or self.y > SCREEN_H + 16 or self.x < -16 or self.x > SCREEN_W + 16:
            self.alive = False

    def try_collect(self, player) -> bool:
        if not self.alive:
            return False
        dx = self.x - player.x
        dy = self.y - player.y
        if dx * dx + dy * dy <= (ITEM_COLLECT_RADIUS) ** 2:
            return self._collect(player)
        return False

    def _collect(self, player) -> bool:
        if self.kind == TYPE_POWER:
            if player.power < PLAYER_MAX_POWER:
                player.power = min(PLAYER_MAX_POWER, player.power + self.value * ITEM_P_VALUE)
            else:
                player.score += ITEM_P_FULL_BONUS_SCORE
        elif self.kind == TYPE_SCORE:
            norm = max(0.0, min(1.0, 1.0 - self.y / SCREEN_H))
            bonus = int(ITEM_SCORE_BASE * (1.0 + norm * ITEM_SCORE_HEIGHT_FACTOR))
            player.score += bonus
        elif self.kind == TYPE_BOMB:
            player.bombs = min(player.bombs + ITEM_BOMB_VALUE, 8)
        elif self.kind == TYPE_LIFE:
            player.lives = min(player.lives + ITEM_LIFE_VALUE, 9)
        self.alive = False
        return True

    def draw(self, surf: pygame.Surface, font=None) -> None:
        if not self.alive:
            return
        color = item_color(self.kind)
        pygame.draw.circle(surf, color, (int(self.x), int(self.y)), ITEM_RADIUS, 0)
        pygame.draw.circle(surf, (255, 255, 255), (int(self.x), int(self.y)), ITEM_RADIUS, 1)
        if font is None:
            font = pygame.font.SysFont("consolas", 10, bold=True)
        s = font.render(item_label(self.kind), True, (20, 20, 20))
        surf.blit(s, (self.x - s.get_width() / 2, self.y - s.get_height() / 2))


class ItemPool:
    """道具对象池, 与 BulletPool 同样的设计: free / active 双列表。"""

    __slots__ = ("_free", "_active", "_font")

    def __init__(self, initial: int = 256) -> None:
        self._free: list[Item] = [Item(0, 0, TYPE_POWER) for _ in range(initial)]
        self._active: list[Item] = []
        self._font = pygame.font.SysFont("consolas", 10, bold=True)

    def spawn(self, x: float, y: float, kind: int, value: int = 1) -> Item:
        item = self._free.pop() if self._free else Item(0, 0, TYPE_POWER)
        item.x = float(x); item.y = float(y)
        item.vx = 0.0; item.vy = ITEM_FALL_SPEED
        item.kind = kind; item.value = value
        item.alive = True; item.age = 0.0
        self._active.append(item)
        return item

    def release(self, item: Item) -> None:
        item.alive = False
        a = self._active
        for i in range(len(a) - 1, -1, -1):
            if a[i] is item:
                last = a.pop()
                if i < len(a):
                    a[i] = last
                break
        self._free.append(item)

    def update(self, dt: float, player) -> None:
        keep: list[Item] = []
        for it in self._active:
            it.update(dt, player)
            if not it.alive:
                self._free.append(it)
            else:
                keep.append(it)
        self._active = keep

    def collect_pass(self, player) -> int:
        if not self._active:
            return 0
        collected = 0
        keep: list[Item] = []
        for it in self._active:
            if it.try_collect(player):
                collected += 1
                self._free.append(it)
            elif it.alive:
                keep.append(it)
        self._active = keep
        return collected

    def clear(self) -> None:
        for it in self._active:
            it.alive = False
            self._free.append(it)
        self._active.clear()

    @property
    def active(self) -> list[Item]:
        return self._active

    def count(self) -> int:
        return len(self._active)

    def draw(self, surf: pygame.Surface) -> None:
        for it in self._active:
            it.draw(surf, self._font)