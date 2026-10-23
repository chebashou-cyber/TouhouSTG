# -*- coding: utf-8 -*-
"""ui/overlay.py — F1 调试 overlay

绘制:
  - 自机判定点 (2px 红) + 擦弹环 (16px 白)
  - 每颗敌弹碰撞圆 (黄)
  - 每个活敌机碰撞盒 (青)
  - 顶部信息: FPS / 子弹数 / 敌机数 / 玩家坐标 / 无敌剩余 / 调试开关
"""
from __future__ import annotations
import pygame
from src.ui.fonts import get_font
from config import (
    SCREEN_W, SCREEN_H,
    PLAYER_HITBOX_RADIUS, PLAYER_GRAZE_RADIUS,
    COLOR_PLAYER_HITBOX, COLOR_GRAZE_RING, COLOR_TEXT, COLOR_TEXT_DIM,
)


class DebugOverlay:
    __slots__ = ("_font", "_font_small")

    def __init__(self) -> None:
        self._font = get_font(14)
        self._font_small = get_font(12)

    def draw(self, surf: pygame.Surface, player, pool, enemies, fps: float,
             paused: bool, frame_step_request: bool, god_mode: bool) -> None:
        # 自机判定 + 擦弹
        px, py = int(player.x), int(player.y)
        pygame.draw.circle(surf, COLOR_PLAYER_HITBOX, (px, py), PLAYER_HITBOX_RADIUS, 1)
        pygame.draw.circle(surf, COLOR_GRAZE_RING, (px, py), PLAYER_GRAZE_RADIUS, 1)

        # 敌弹碰撞圆 (按 kind 区分颜色)
        for b in pool.active:
            if b.kind == 0:  # enemy
                pygame.draw.circle(surf, (255, 230, 80),
                                   (int(b.x), int(b.y)), int(b.radius), 1)

        # 敌机碰撞盒
        for e in enemies:
            if e.alive:
                pygame.draw.circle(surf, (80, 220, 255),
                                   (int(e.x), int(e.y)), int(e.radius), 1)

        # 信息面板
        info_lines = [
            f"FPS         : {fps:6.1f}",
            f"Bullets     : {len(pool.active):4d}   (enemy {pool.enemy_count():4d})",
            f"Enemies     : {sum(1 for e in enemies if e.alive):4d}",
            f"Player Pos  : ({player.x:6.1f}, {player.y:6.1f})",
            f"Power       : {player.power:3d}",
            f"Invuln      : {player.invuln_time:.2f}s",
            f"DeathInvuln : {player.death_invuln_left} fr",
            f"Paused      : {paused}",
            f"Step queued : {frame_step_request}",
            f"God Mode    : {god_mode}",
        ]
        # 背景半透明黑框
        panel_w = 240
        panel_h = len(info_lines) * 16 + 12
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 160))
        surf.blit(panel, (SCREEN_W - panel_w - 8, 60))
        for i, line in enumerate(info_lines):
            t = self._font.render(line, True, COLOR_TEXT)
            surf.blit(t, (SCREEN_W - panel_w - 8 + 8, 60 + 6 + i * 16))