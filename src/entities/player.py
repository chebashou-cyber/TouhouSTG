# -*- coding: utf-8 -*-
"""player.py — 自机

职责:
  - 8 向移动 / 低速 (聚焦)
  - 持续射击 (按住 Z)
  - 炸弹 (X): 清屏 + 无敌 + 加分
  - 判定点 (2px) / 擦弹环 (16px), 与贴图分离
  - 被弹 → 扣命 + 减 Power + 无敌 3s; 死亡 → 重生 8 帧无敌窗
  - 擦弹 +300 分 / 颗 (去重)
"""
from __future__ import annotations
import math
import pygame

from config import (
    SCREEN_W, SCREEN_H,
    PLAYER_SPEED, PLAYER_FOCUS_SPEED,
    PLAYER_HITBOX_RADIUS, PLAYER_GRAZE_RADIUS,
    PLAYER_FIRE_INTERVAL, PLAYER_FIRE_SPEED, PLAYER_BULLET_SPEED_SCALE,
    PLAYER_INVULN_TIME, PLAYER_DEATH_INVULN_FRAMES,
    PLAYER_START_LIVES, PLAYER_START_BOMBS, PLAYER_START_POWER, PLAYER_MAX_POWER,
    PLAYER_SPAWN_X, PLAYER_SPAWN_Y,
    PLAYER_MOVE_BOUND_TOP, PLAYER_MOVE_BOUND_BOTTOM,
    GRAZE_SCORE, HITBOX_PENALTY_POWER,
    BOMB_INVULN_TIME, BOMB_CLEAR_BULLET_SCORE, BOMB_CLEAR_BULLET_SCORE_CAP, BOMB_MAX_BOMBS,
    DEATH_RESPAWN_DELAY,
    COLOR_PLAYER, COLOR_PLAYER_HITBOX, COLOR_GRAZE_RING,
)
from src.entities.bullet import BulletPool, KIND_PLAYER
from src.core.input_manager import InputManager


class Player:
    __slots__ = (
        "x", "y",
        "lives", "bombs", "power",
        "score", "graze_count",
        "invuln_time", "death_invuln_left",
        "bomb_time",
        "fire_cooldown",
        "alive", "death_timer",
        "draw_flicker_on",
    )

    def __init__(self) -> None:
        self.x = float(PLAYER_SPAWN_X)
        self.y = float(PLAYER_SPAWN_Y)
        self.lives = PLAYER_START_LIVES
        self.bombs = PLAYER_START_BOMBS
        self.power = PLAYER_START_POWER
        self.score = 0
        self.graze_count = 0
        self.invuln_time = 0.0
        self.death_invuln_left = 0
        self.bomb_time = 0.0
        self.fire_cooldown = 0.0
        self.alive = True
        self.death_timer = 0.0
        self.draw_flicker_on = True

    # ---------- 主循环 ----------
    def update(self, dt: float, input: InputManager, pool: BulletPool,
               audio=None) -> None:
        if not self.alive:
            self.death_timer += dt
            if self.death_timer >= DEATH_RESPAWN_DELAY:
                self._respawn()
            return

        # 移动
        ax, ay = input.axis()
        speed = PLAYER_FOCUS_SPEED if input.is_held("shift") else PLAYER_SPEED
        self.x += ax * speed * dt
        self.y += ay * speed * dt
        if self.x < PLAYER_HITBOX_RADIUS:
            self.x = PLAYER_HITBOX_RADIUS
        elif self.x > SCREEN_W - PLAYER_HITBOX_RADIUS:
            self.x = SCREEN_W - PLAYER_HITBOX_RADIUS
        if self.y < PLAYER_MOVE_BOUND_TOP:
            self.y = PLAYER_MOVE_BOUND_TOP
        elif self.y > PLAYER_MOVE_BOUND_BOTTOM:
            self.y = PLAYER_MOVE_BOUND_BOTTOM

        # 无敌 / 炸弹计时衰减
        if self.invuln_time > 0.0:
            self.invuln_time -= dt
            self.draw_flicker_on = (int(self.invuln_time * 12) % 2 == 0)
        elif self.bomb_time > 0.0:
            self.bomb_time -= dt
            # 炸弹期间闪烁 (3 Hz 红蓝交替)
            self.draw_flicker_on = (int(self.bomb_time * 6) % 2 == 0)
        else:
            self.draw_flicker_on = True

        if self.death_invuln_left > 0:
            self.death_invuln_left -= 1

        # 射击 (按住 Z)
        if input.is_held("z"):
            self.fire_cooldown -= dt
            if self.fire_cooldown <= 0.0:
                self._fire(pool, audio)
                self.fire_cooldown = PLAYER_FIRE_INTERVAL

        # 炸弹 (X 触发一次性按下)
        if input.was_pressed("x"):
            self.use_bomb(pool, audio)

    def _fire(self, pool: BulletPool, audio=None) -> None:
        if audio is not None:
            audio.play("shoot")
        pool.acquire(self.x, self.y - 10,
                     0.0, -PLAYER_FIRE_SPEED * PLAYER_BULLET_SPEED_SCALE,
                     radius=4, color=(120, 255, 140), kind=KIND_PLAYER)
        if self.power >= 32:
            offset_x = 8.0
            pool.acquire(self.x - offset_x, self.y - 6,
                         -50.0 * PLAYER_BULLET_SPEED_SCALE, -PLAYER_FIRE_SPEED * PLAYER_BULLET_SPEED_SCALE,
                         radius=3, color=(120, 255, 140), kind=KIND_PLAYER)
            pool.acquire(self.x + offset_x, self.y - 6,
                         50.0, -PLAYER_FIRE_SPEED,
                         radius=3, color=(120, 255, 140), kind=KIND_PLAYER)

    # ---------- 判定 ----------
    def is_vulnerable(self) -> bool:
        return (self.alive and self.invuln_time <= 0.0 and self.bomb_time <= 0.0
                and self.death_invuln_left <= 0)

    def on_hit(self) -> int:
        if not self.is_vulnerable():
            return 0
        self.lives -= 1
        self.power = max(0, self.power - HITBOX_PENALTY_POWER)
        self.invuln_time = PLAYER_INVULN_TIME
        if self.lives < 0:
            self.alive = False
        return 1

    def try_graze(self, bullet) -> bool:
        if bullet.grazed:
            return False
        bullet.grazed = True
        self.graze_count += 1
        self.score += GRAZE_SCORE
        return True

    # ---------- 炸弹 ----------
    def use_bomb(self, pool: BulletPool, audio=None) -> int:
        """使用炸弹: 清屏 + 无敌 + 加分。返回清掉的敌弹数量。"""
        if self.bombs <= 0 or not self.alive:
            return 0
        self.bombs -= 1
        self.bomb_time = BOMB_INVULN_TIME
        if audio is not None:
            audio.play("bomb")
        removed = pool.clear_enemy()
        bonus = min(removed * BOMB_CLEAR_BULLET_SCORE, BOMB_CLEAR_BULLET_SCORE_CAP)
        self.score += bonus
        return removed

    # ---------- 死亡 / 重生 ----------
    def _respawn(self) -> None:
        if self.lives < 0:
            return
        self.x = float(PLAYER_SPAWN_X)
        self.y = float(PLAYER_SPAWN_Y)
        self.invuln_time = PLAYER_INVULN_TIME
        self.death_invuln_left = PLAYER_DEATH_INVULN_FRAMES
        self.death_timer = 0.0
        self.alive = True
        self.fire_cooldown = 0.0

    def is_game_over(self) -> bool:
        return (not self.alive) and self.lives < 0 and self.death_timer >= DEATH_RESPAWN_DELAY

    def is_in_bomb(self) -> bool:
        return self.bomb_time > 0.0

    # ---------- 渲染 ----------
    def draw(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        if not self.draw_flicker_on:
            return
        # 炸弹时改机身颜色 (蓝/白交替); 平时保持蓝色机身
        # 注意: bomb_time 常量为 0 时 int(0*12)%2 == 0, 旧写法会让机身一直是白色
        if self.bomb_time > 0.0 and int(self.bomb_time * 12) % 2 == 0:
            body_color = (220, 240, 255)
        else:
            body_color = COLOR_PLAYER
        # 机身: 带机翼的箭形 (纯三角看起来像光标, 加两翼更像自机)
        pygame.draw.polygon(surf, body_color, [
            (self.x, self.y - 11),
            (self.x - 4, self.y - 1),
            (self.x - 11, self.y + 7),
            (self.x - 4, self.y + 6),
            (self.x, self.y + 9),
            (self.x + 4, self.y + 6),
            (self.x + 11, self.y + 7),
            (self.x + 4, self.y - 1),
        ])
        # 座舱
        pygame.draw.circle(surf, (235, 250, 255),
                           (int(self.x), int(self.y - 2)), 2)
        flame_h = 6 + (3 if (int(pygame.time.get_ticks() / 60) % 2 == 0) else 0)
        pygame.draw.polygon(surf, (255, 200, 120), [
            (self.x - 3, self.y + 6),
            (self.x, self.y + 6 + flame_h),
            (self.x + 3, self.y + 6),
        ])

    def draw_hitbox(self, surf: pygame.Surface, focus_mode: bool) -> None:
        if not self.alive:
            return
        if not focus_mode:
            return
        pygame.draw.circle(surf, COLOR_PLAYER_HITBOX,
                           (int(self.x), int(self.y)),
                           PLAYER_HITBOX_RADIUS, 1)

    def draw_graze_ring(self, surf: pygame.Surface, focus_mode: bool, debug: bool) -> None:
        if not self.alive:
            return
        if not (focus_mode or debug):
            return
        pygame.draw.circle(surf, COLOR_GRAZE_RING,
                           (int(self.x), int(self.y)),
                           PLAYER_GRAZE_RADIUS, 1)