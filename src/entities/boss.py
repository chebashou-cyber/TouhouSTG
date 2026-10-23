# -*- coding: utf-8 -*-
"""boss.py — Boss 实体 + 状态机

状态:
  enter   入场阶段, 沿 path 移动到悬停点
  spell   符卡阶段, 运行当前 SpellCard 的 emitters
  between 符卡间隔 (短暂), 不发射弹幕, 准备进入下一张
  dead    已被击破

符卡击破逻辑:
  - 进入 spell 时记录 spell_start_hp
  - HP <= break_hp() -> 击破, 给奖励, 进入下一张或 die
  - spell_timer >= duration -> 超时 break, 进入下一张或 die (无奖励)
  - 下一张开始时 hp 满血重置 (经典东方规则)
"""
from __future__ import annotations
import math
import pygame
from config import (
    BOSS_HITBOX_RADIUS, BOSS_SCORE, BOSS_BETWEEN_SPELLS_TIME, BOSS_TIME_BONUS_RATE,
    COLOR_ENEMY, COLOR_ENEMY_HITBOX,
)
from src.entities.bullet import BulletPool
from src.patterns.spellcard import SpellCard


STATE_ENTER = "enter"
STATE_SPELL = "spell"
STATE_BETWEEN = "between"
STATE_DEAD = "dead"


class Boss:
    __slots__ = (
        "x", "y",
        "hp", "max_hp",
        "path", "path_index",
        "spellcards",
        "current_spell_index", "current_spell",
        "state", "spell_timer", "between_timer", "age",
        "alive",
        "score", "radius", "bonus_total",
        "label",
    )

    def __init__(self, x: float, y: float, hp: int,
                 path: list[tuple[float, float, float]],
                 spellcards: list[SpellCard],
                 score: int = BOSS_SCORE,
                 radius: int = BOSS_HITBOX_RADIUS,
                 label: str = "Boss") -> None:
        self.x = x; self.y = y
        self.hp = hp; self.max_hp = hp
        self.path = path or []
        self.path_index = 0
        self.spellcards = spellcards
        self.current_spell_index = 0
        self.current_spell = spellcards[0] if spellcards else None
        self.state = STATE_ENTER if path else STATE_SPELL
        self.spell_timer = 0.0
        self.between_timer = 0.0
        self.age = 0.0
        self.alive = True
        self.score = score
        self.radius = radius
        self.bonus_total = 0
        self.label = label

    # ---------------- 主循环 ----------------
    def update(self, dt: float, pool: BulletPool, player, lasers=None) -> None:
        if not self.alive:
            return
        self.age += dt

        if self.state == STATE_ENTER:
            self._follow_path(dt)
            if self._path_done():
                self._start_spell(0)
        elif self.state == STATE_SPELL:
            if self.current_spell is None:
                self._die()
                return
            self.spell_timer += dt
            for em in self.current_spell.emitters:
                em.update(dt, self.x, self.y, player.x, player.y, pool)
            if lasers is not None:
                for le in self.current_spell.lasers:
                    le.update(dt, self.x, self.y, player.x, player.y, lasers)
            # 超时 -> break
            if self.spell_timer >= self.current_spell.duration:
                self._break_timeout()
                return
            # HP 击破
            if self.hp <= self.current_spell.break_hp():
                self._break_killed()
        elif self.state == STATE_BETWEEN:
            self.between_timer += dt
            if self.between_timer >= BOSS_BETWEEN_SPELLS_TIME:
                self._start_spell(self.current_spell_index)

    def hit(self, dmg: int) -> int:
        """被自机弹命中; 返回击破得分 (0 表示仅扣血)。"""
        if not self.alive or self.state != STATE_SPELL:
            return 0
        self.hp -= dmg
        if self.hp <= self.current_spell.break_hp():
            return self._break_killed()
        return 0

    # ---------------- 状态切换 ----------------
    def _start_spell(self, idx: int) -> None:
        if idx >= len(self.spellcards):
            self._die()
            return
        self.current_spell_index = idx
        self.current_spell = self.spellcards[idx]
        self.current_spell.spell_start_hp = self.hp
        self.spell_timer = 0.0
        # 重置每个 emitter / 激光发射器内部计时
        for em in self.current_spell.emitters:
            em.elapsed = 0.0
            em.last_emit_t = 0.0
            em.active = True
        for le in self.current_spell.lasers:
            le.reset()
        self.state = STATE_SPELL

    def _break_killed(self) -> int:
        """HP 击破: 给奖励, 进入下一张或死亡。"""
        score = self.current_spell.bonus_score
        time_left = max(0.0, self.current_spell.duration - self.spell_timer)
        bonus = int(time_left * BOSS_TIME_BONUS_RATE)
        self.bonus_total += score + bonus
        self._next_or_die()
        return score + bonus

    def _break_timeout(self) -> int:
        """超时: 无奖励, 进入下一张或死亡。"""
        self._next_or_die()
        return 0

    def _next_or_die(self) -> None:
        nxt = self.current_spell_index + 1
        if nxt >= len(self.spellcards):
            self._die()
            return
        # 满血进入下一张
        self.hp = self.max_hp
        self.current_spell_index = nxt
        self.between_timer = 0.0
        self.state = STATE_BETWEEN

    def _die(self) -> None:
        self.alive = False
        self.state = STATE_DEAD
        self.bonus_total += self.score

    # ---------------- 路径 ----------------
    def _follow_path(self, dt: float) -> None:
        if not self.path:
            return
        path = self.path
        while (self.path_index + 1 < len(path)
               and self.age >= path[self.path_index + 1][0]):
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

    def _path_done(self) -> bool:
        if not self.path:
            return True
        last_t = self.path[-1][0]
        return self.age >= last_t

    # ---------------- 查询 ----------------
    def is_active(self) -> bool:
        return self.alive and self.state != STATE_DEAD

    def is_dead(self) -> bool:
        return self.state == STATE_DEAD

    def get_hp_progress(self) -> float:
        """当前符卡 HP 进度 (0~1)。"""
        if self.state != STATE_SPELL or self.current_spell is None:
            return 0.0
        return self.current_spell.hp_progress(self.hp)

    def get_time_progress(self) -> float:
        """当前符卡时间进度 (0~1)。"""
        if self.state != STATE_SPELL or self.current_spell is None:
            return 0.0
        return self.current_spell.time_progress(self.spell_timer)

    def get_spell_name(self) -> str:
        if self.current_spell is None:
            return ""
        return f"{self.current_spell.no}. {self.current_spell.name}"

    # ---------------- 渲染 ----------------
    def draw(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        # 大型十二边形 Boss 机身 + 颜色随 HP 进度变化
        ratio = self.get_hp_progress()
        # HP 越低颜色越红
        col = (
            int(200 + 55 * (1 - ratio)),
            int(120 * (1 - ratio) + 80 * ratio),
            int(140 + 80 * ratio),
        )
        pts = []
        sides = 12
        for i in range(sides):
            a = math.pi / 12 + i * 2 * math.pi / sides
            pts.append((self.x + math.cos(a) * self.radius,
                        self.y + math.sin(a) * self.radius))
        pygame.draw.polygon(surf, col, pts)
        # 内圈白点 (眼睛)
        pygame.draw.circle(surf, (255, 255, 255),
                           (int(self.x), int(self.y)), self.radius // 3, 0)

    def draw_hitbox(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        pygame.draw.circle(surf, COLOR_ENEMY_HITBOX,
                           (int(self.x), int(self.y)), self.radius, 1)