# -*- coding: utf-8 -*-
"""enemy.py — 敌机

每个敌机:
  - 路径 (关键帧列表 [(time, x, y)]) 用于移动
  - Emitter 列表, 按各自的 start_t/period 触发 Pattern
  - HP 与碰撞半径 (默认 12px)
  - 死亡掉落 Item (按 ENEMY_DROP_TABLE 概率表 + 难度 drop_bias 修正)
不发射子弹的敌机也可被定义为 emitters=[] 的静态靶。
"""
from __future__ import annotations
import math
import random
import pygame
from dataclasses import dataclass

from config import (
    ENEMY_DEFAULT_HP, ENEMY_DEFAULT_SCORE, ENEMY_HITBOX_RADIUS,
    ENEMY_DROP_TABLE,
    COLOR_ENEMY, COLOR_ENEMY_HITBOX,
    DIFFICULTY_MULTIPLIERS, DIFFICULTY_DEFAULT,
)
from src.entities.bullet import BulletPool
from src.entities.item import ItemPool, TYPE_POWER, TYPE_SCORE, TYPE_BOMB, TYPE_LIFE


# 难度类型 -> 道具 kind 名字映射
_KIND_NAME_TO_TYPE = {
    "power": TYPE_POWER,
    "score": TYPE_SCORE,
    "bomb":  TYPE_BOMB,
    "life":  TYPE_LIFE,
}


def pick_drop_kind(score: int, drop_bias: float, rng: random.Random):
    """根据敌机 score 决定是否掉落道具, 返回 (kind, value) 或 None。"""
    # 取第一个匹配的阈值
    chosen = None
    for (threshold, kind_name, value, prob) in ENEMY_DROP_TABLE:
        if score >= threshold:
            chosen = (kind_name, value, prob)
            break
    if chosen is None or chosen[0] is None:
        return None
    kind_name, value, prob = chosen
    # 难度调整概率 (EASY 多掉, LUNATIC 少掉)
    p = prob * drop_bias
    if rng.random() > p:
        return None
    kind = _KIND_NAME_TO_TYPE.get(kind_name)
    if kind is None:
        return None
    return (kind, value)


# -------------------- Emitter --------------------
class Emitter:
    """绑定到敌机上的发射器: 控制 Pattern 的发射节奏。"""

    __slots__ = ("pattern", "start_t", "period", "duration",
                 "last_emit_t", "elapsed", "active", "label",
                 "_period_scale")

    def __init__(self, pattern, *, start_t: float = 0.0, period: float = 0.5,
                 duration: float = -1.0, label: str = "",
                 period_scale: float = 1.0) -> None:
        self.pattern = pattern
        self.start_t = start_t
        self.period = period * period_scale
        self.duration = duration
        self.last_emit_t = 0.0
        self.elapsed = 0.0
        self.active = True
        self.label = label
        self._period_scale = period_scale

    def update(self, dt: float, owner_x: float, owner_y: float,
               player_x: float, player_y: float, pool: BulletPool) -> None:
        if not self.active:
            return
        self.elapsed += dt
        if self.elapsed < self.start_t:
            return
        if self.duration > 0 and (self.elapsed - self.start_t) > self.duration:
            self.active = False
            return
        while self.last_emit_t + self.period <= self.elapsed:
            self.last_emit_t += self.period
            specs = self.pattern.tick(owner_x, owner_y, player_x, player_y, self.elapsed)
            pool.acquire_many(specs)


# -------------------- Enemy --------------------
class Enemy:
    __slots__ = ("x", "y", "hp", "max_hp", "path", "path_index",
                 "emitters", "score", "age", "alive", "radius",
                 "_hp_scale")

    def __init__(self, x: float, y: float,
                 hp: int = ENEMY_DEFAULT_HP,
                 path: list[tuple[float, float, float]] | None = None,
                 emitters: list[Emitter] | None = None,
                 score: int = ENEMY_DEFAULT_SCORE,
                 radius: int = ENEMY_HITBOX_RADIUS,
                 hp_scale: float = 1.0) -> None:
        self.x = x; self.y = y
        scaled_hp = max(1, int(round(hp * hp_scale)))
        self.hp = scaled_hp; self.max_hp = scaled_hp
        self.path = path or []
        self.path_index = 0
        self.emitters = emitters or []
        self.score = score
        self.age = 0.0
        self.alive = True
        self.radius = radius
        self._hp_scale = hp_scale

    def update(self, dt: float, pool: BulletPool, player_x: float, player_y: float) -> None:
        if not self.alive:
            return
        self.age += dt
        self._follow_path()
        for em in self.emitters:
            em.update(dt, self.x, self.y, player_x, player_y, pool)

    def _follow_path(self) -> None:
        if not self.path:
            return
        path = self.path
        while self.path_index + 1 < len(path) and self.age >= path[self.path_index + 1][0]:
            self.path_index += 1
        if self.path_index + 1 >= len(path):
            _, fx, fy = path[self.path_index]
            self.x, self.y = fx, fy
            return
        t0, x0, y0 = path[self.path_index]
        t1, x1, y1 = path[self.path_index + 1]
        if t1 <= t0:
            return
        u = (self.age - t0) / (t1 - t0)
        self.x = x0 + (x1 - x0) * u
        self.y = y0 + (y1 - y0) * u

    def hit(self, dmg: int) -> int:
        if not self.alive:
            return 0
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False
            return self.score
        return 0

    def on_death_drop(self, item_pool: ItemPool, drop_bias: float,
                      rng: random.Random) -> None:
        """死亡时按概率表决定掉落道具。"""
        result = pick_drop_kind(self.score, drop_bias, rng)
        if result is None:
            return
        kind, value = result
        item_pool.spawn(self.x, self.y, kind, value)

    def draw(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        col = (COLOR_ENEMY[0], max(40, int(255 * self.hp / self.max_hp)), COLOR_ENEMY[2])
        pts = []
        for i in range(6):
            a = math.pi / 6 + i * math.pi / 3
            pts.append((self.x + math.cos(a) * self.radius,
                        self.y + math.sin(a) * self.radius))
        pygame.draw.polygon(surf, col, pts)

    def draw_hitbox(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        pygame.draw.circle(surf, COLOR_ENEMY_HITBOX,
                           (int(self.x), int(self.y)), self.radius, 1)


# -------------------- 工厂 --------------------
@dataclass
class Wave:
    """一波敌机: 在 start_t 时刻按 spec 列表生成敌机。"""
    start_t: float
    enemies: list

    def spawn(self, *, difficulty: int = DIFFICULTY_DEFAULT) -> list["Enemy"]:
        mult = DIFFICULTY_MULTIPLIERS[difficulty]
        hp_scale = mult["hp"]
        period_scale = mult["period"]
        out = []
        for spec in self.enemies:
            spec = dict(spec)
            # 把 difficulty period_scale 应用到每个 emitter
            ems = spec.get("emitters") or []
            new_ems = []
            for em in ems:
                new_em = Emitter(
                    em.pattern,
                    start_t=em.start_t,
                    period=em.period,
                    duration=em.duration,
                    label=em.label,
                    period_scale=period_scale,
                )
                new_ems.append(new_em)
            spec["emitters"] = new_ems
            spec.pop("period_scale", None)
            spec["hp_scale"] = hp_scale
            out.append(make_enemy(**spec))
        return out


def make_enemy(x: float, y: float,
               hp: int = ENEMY_DEFAULT_HP,
               path: list[tuple[float, float, float]] | None = None,
               emitters: list | None = None,
               score: int = ENEMY_DEFAULT_SCORE,
               radius: int = ENEMY_HITBOX_RADIUS,
               hp_scale: float = 1.0) -> Enemy:
    return Enemy(x, y, hp=hp, path=path, emitters=emitters, score=score,
                 radius=radius, hp_scale=hp_scale)