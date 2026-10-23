# -*- coding: utf-8 -*-
"""ui/hud.py — 游戏内 HUD

显示:
  Lives / Bombs / Power / Score / Graze / Difficulty / Continue
  + (有 Boss 时) Boss 血条 / 符卡名 / 倒计时
  + (符卡开始瞬间) 宣言文字淡入淡出
字体: ui/fonts.get_font (直接指定字体文件, 规避 SysFont 的系统字体枚举崩溃)。
"""
from __future__ import annotations
import pygame
from src.ui.fonts import get_font
from config import (
    SCREEN_W, SCREEN_H, PLAYER_MAX_POWER,
    COLOR_TEXT, COLOR_TEXT_DIM,
    DIFFICULTY_NAMES, CONTINUE_MAX,
    COLOR_BOSS_HP_BAR_BG, COLOR_BOSS_HP_BAR_FG, COLOR_BOSS_HP_BAR_BORDER,
    COLOR_SPELL_CARD_NAME, COLOR_SPELL_TIMER_WARN, COLOR_SPELL_TIMER_OK,
)


class HUD:
    __slots__ = ("_font", "_font_big", "_font_small", "_spell_alpha",
               "_spell_name", "_spell_timer", "_spell_total")

    def __init__(self) -> None:
        self._font = get_font(16)
        self._font_big = get_font(20, bold=True, cjk=True)
        self._font_small = get_font(12, cjk=True)
        self._spell_alpha = 0.0  # 符卡宣言淡入淡出 alpha (0~255)

    def set_spell_announce(self, name: str, t_remaining: float = 2.5) -> None:
        """外部调用: 触发符卡宣言文字 alpha=255, t_remaining 秒后淡出。"""
        self._spell_alpha = 255.0
        self._spell_name = name
        self._spell_timer = t_remaining
        self._spell_total = t_remaining

    def update_announce(self, dt: float) -> None:
        if not hasattr(self, "_spell_timer"):
            return
        if self._spell_timer > 0:
            self._spell_timer -= dt
        # 0.7s 内淡入 -> 1.0s 保持 -> 0.8s 淡出
        elapsed = self._spell_total - self._spell_timer
        if elapsed < 0.7:
            self._spell_alpha = 255.0 * (elapsed / 0.7)
        elif self._spell_timer < 0.8:
            self._spell_alpha = 255.0 * (self._spell_timer / 0.8)
        else:
            self._spell_alpha = 255.0
        if self._spell_timer <= 0:
            self._spell_alpha = 0.0

    def draw(self, surf: pygame.Surface, player, fps: float, paused: bool,
             frame_step_request: bool, god_mode: bool,
             difficulty: int = 1, continue_left: int = CONTINUE_MAX,
             bomb_active: bool = False, boss=None, muted: bool = False) -> None:
        # 顶部左
        surf.blit(self._font.render(f"LIVES  {player.lives}", True, COLOR_TEXT), (8, 8))
        surf.blit(self._font.render(f"BOMBS  {player.bombs}", True, COLOR_TEXT), (8, 24))

        # Power 条
        bar_w = 120
        bar_x, bar_y = 8, 44
        pygame.draw.rect(surf, (60, 60, 60), (bar_x, bar_y, bar_w, 8), 0)
        pw = int(player.power / PLAYER_MAX_POWER * bar_w)
        col = (96, 192, 255) if player.power < PLAYER_MAX_POWER else (255, 215, 0)
        pygame.draw.rect(surf, col, (bar_x, bar_y, pw, 8), 0)
        pygame.draw.rect(surf, COLOR_TEXT_DIM, (bar_x, bar_y, bar_w, 8), 1)
        surf.blit(
            self._font_small.render(f"POWER {player.power:>3d} / {PLAYER_MAX_POWER}",
                                    True, COLOR_TEXT),
            (bar_x, bar_y + 10),
        )

        # 顶部右
        score_text = self._font_big.render(f"{player.score:>10d}", True, COLOR_TEXT)
        surf.blit(score_text, (SCREEN_W - score_text.get_width() - 8, 6))
        graze_text = self._font.render(f"GRAZE  {player.graze_count:>5d}",
                                       True, COLOR_TEXT_DIM)
        surf.blit(graze_text, (SCREEN_W - graze_text.get_width() - 8, 32))
        diff_text = self._font_small.render(
            f"DIFFICULTY  {DIFFICULTY_NAMES[difficulty]}", True, (180, 220, 255)
        )
        surf.blit(diff_text, (SCREEN_W - diff_text.get_width() - 8, 50))
        if continue_left < CONTINUE_MAX:
            cont_text = self._font_small.render(
                f"CONTINUE  {continue_left}/{CONTINUE_MAX}", True, (255, 220, 120)
            )
            surf.blit(cont_text, (SCREEN_W - cont_text.get_width() - 8, 66))

        # Boss 区: 顶部居中
        if boss is not None and boss.is_active():
            self._draw_boss_hud(surf, boss)

        # 状态角标 (右下, 提示条上方)
        flags = []
        if paused:
            flags.append("PAUSED")
        if frame_step_request:
            flags.append("STEP")
        if god_mode:
            flags.append("GOD")
        if bomb_active:
            flags.append("BOMB")
        if muted:
            flags.append("MUTE")
        if flags:
            t = self._font_small.render(" ".join(flags), True, (255, 220, 120))
            surf.blit(t, (SCREEN_W - t.get_width() - 8, SCREEN_H - 30))

        # FPS (左下, 提示条上方)
        fps_text = self._font_small.render(f"{fps:>5.1f} FPS", True, COLOR_TEXT_DIM)
        surf.blit(fps_text, (8, SCREEN_H - 30))

        # 底部提示条 (最底一行, 独占, 不再被 FPS/角标覆盖)
        hints = ("Move   Shift Focus   Z Fire   X Bomb   P Pause"
                 "   M Mute   F1 Debug   F3 God   F4 Clear")
        h = self._font_small.render(hints, True, COLOR_TEXT_DIM)
        surf.blit(h, ((SCREEN_W - h.get_width()) // 2, SCREEN_H - h.get_height() - 4))

        # 符卡宣言淡入淡出
        if self._spell_alpha > 0 and hasattr(self, "_spell_name"):
                self._draw_spell_announce(surf, self._spell_name)

    def _draw_boss_hud(self, surf: pygame.Surface, boss) -> None:
        # Boss 血条 (顶部居中)
        bar_w = 360
        bar_h = 10
        bx = (SCREEN_W - bar_w) // 2
        by = 6

        # 血条下方一条黑色半透明底板, 保证符卡名在亮弹幕上也能读
        panel = pygame.Surface((bar_w, 20), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 130))
        surf.blit(panel, (bx, by + bar_h))

        pygame.draw.rect(surf, COLOR_BOSS_HP_BAR_BG, (bx, by, bar_w, bar_h), 0)
        if boss.state == "between":
            fw = bar_w
        else:
            fw = int(bar_w * boss.get_hp_progress())
        pygame.draw.rect(surf, COLOR_BOSS_HP_BAR_FG, (bx, by, fw, bar_h), 0)
        pygame.draw.rect(surf, COLOR_BOSS_HP_BAR_BORDER, (bx, by, bar_w, bar_h), 1)

        # 符卡名 + 倒计时
        name = boss.get_spell_name()
        if name:
            t_name = self._font_small.render(name, True, COLOR_SPELL_CARD_NAME)
            surf.blit(t_name, (bx + 4, by + bar_h + 3))
        time_left = max(0.0, (boss.current_spell.duration - boss.spell_timer)
                        if boss.current_spell else 0.0)
        color = COLOR_SPELL_TIMER_WARN if time_left < 5.0 else COLOR_SPELL_TIMER_OK
        t_time = self._font_small.render(f"{time_left:>4.1f}s", True, color)
        surf.blit(t_time, (bx + bar_w - t_time.get_width() - 4, by + bar_h + 3))

        # 符卡进度 (X/N)
        idx = boss.current_spell_index + 1
        total = len(boss.spellcards)
        t_idx = self._font_small.render(f"[{idx}/{total}]", True, COLOR_TEXT_DIM)
        surf.blit(t_idx, (bx + bar_w - t_idx.get_width() - t_time.get_width() - 12,
                          by + bar_h + 3))

    def _draw_spell_announce(self, surf: pygame.Surface, name: str) -> None:
        alpha = int(max(0.0, min(255.0, self._spell_alpha)))
        big = self._font_big.render(name, True, COLOR_SPELL_CARD_NAME)
        small = self._font_small.render("SIGN", True, COLOR_SPELL_CARD_NAME)
        # 半透明遮罩 (黑)
        layer = pygame.Surface((SCREEN_W, 80), pygame.SRCALPHA)
        layer.fill((0, 0, 0, int(alpha * 0.5)))
        surf.blit(layer, (0, SCREEN_H // 2 - 40))
        # 文字 + alpha (用 set_alpha 不支持抗锯齿, 简化: 直接覆盖)
        t1 = self._font_big.render(name, True, COLOR_SPELL_CARD_NAME)
        t1.set_alpha(alpha)
        surf.blit(t1, ((SCREEN_W - t1.get_width()) // 2, SCREEN_H // 2 - 30))
        t2 = self._font_small.render("SPELL CARD", True, COLOR_SPELL_CARD_NAME)
        t2.set_alpha(alpha)
        surf.blit(t2, ((SCREEN_W - t2.get_width()) // 2, SCREEN_H // 2 + 4))
