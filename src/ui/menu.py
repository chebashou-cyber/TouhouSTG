# -*- coding: utf-8 -*-
"""ui/menu.py — 菜单系统

场景:
  title      标题画面
               START        剧情模式 (全 6 章, 带对话)
               STAGE SELECT 单关练习 (含教学关 / EX 关, 不带剧情)
               DIFFICULTY   ←→ 切换难度
               REPLAY       播放最近一份录像
  paused     暂停
  gameover   Game Over (Continue / Restart)
  stageclear 单关 Stage Clear (评级)
  allclear   剧情模式通关 (总评)

键盘约定 (全场景一致):
  ↑↓ / W S   移动光标
  ←→ / A D   调整当前行数值
  Enter / Z / Space  确认
  Esc        退出 / 返回
"""
from __future__ import annotations
import pygame

from src.ui.fonts import get_font
from src.stages.stage_factory import STAGE_LABELS, MAX_STAGE as MAX_STAGE_ID
from config import (
    SCREEN_W, SCREEN_H,
    DIFFICULTY_NAMES, DIFFICULTY_DEFAULT,
    COLOR_MENU_DIM, COLOR_MENU_SEL, COLOR_MENU_TITLE, COLOR_MENU_ACCENT,
    COLOR_TEXT, COLOR_TEXT_DIM,
    CONTINUE_MAX,
    STAGE_CLEAR_RANK_FINAL, STAGE_CLEAR_RANK_A, STAGE_CLEAR_RANK_B, STAGE_CLEAR_RANK_C,
)

# 标题光标行
TITLE_ROW_START = 0
TITLE_ROW_STAGE = 1
TITLE_ROW_DIFFICULTY = 2
TITLE_ROW_REPLAY = 3
TITLE_ROW_QUIT = 4
TITLE_ROWS = 5

_TITLE_ROW_KEYS = (
    TITLE_ROW_START,
    TITLE_ROW_STAGE,
    TITLE_ROW_DIFFICULTY,
    TITLE_ROW_REPLAY,
    TITLE_ROW_QUIT,
)


def compute_rank(lives: int, continue_used: int) -> str:
    if continue_used == 0 and lives >= 2:
        return STAGE_CLEAR_RANK_FINAL
    if lives >= 1 and continue_used <= 1:
        return STAGE_CLEAR_RANK_A
    if lives >= 1:
        return STAGE_CLEAR_RANK_B
    return STAGE_CLEAR_RANK_C


_RANK_COLORS = {
    STAGE_CLEAR_RANK_FINAL: (255, 240, 120),
    STAGE_CLEAR_RANK_A: (180, 220, 255),
    STAGE_CLEAR_RANK_B: (180, 180, 180),
    STAGE_CLEAR_RANK_C: (180, 180, 180),
}


def _fmt_score(v: int) -> str:
    return f"{v:010d}"


class MenuSystem:
    __slots__ = (
        "font_huge", "font_big", "font_med", "font_small", "font_cjk", "font_cjk_small",
        "_t",
        "_title_cursor",
        "_title_diff_cursor",
        "_title_stage_cursor",
        "max_stage",
    )

    def __init__(self, max_stage: int = MAX_STAGE_ID) -> None:
        self.font_huge = get_font(42, bold=True, cjk=True)
        self.font_big = get_font(24, bold=True, cjk=True)
        self.font_med = get_font(17, cjk=True)
        self.font_small = get_font(13)
        self.font_cjk = get_font(16, cjk=True)
        self.font_cjk_small = get_font(12, cjk=True)
        self._t = 0.0
        self._title_cursor = TITLE_ROW_START
        self._title_diff_cursor = DIFFICULTY_DEFAULT
        self._title_stage_cursor = 1
        self.max_stage = max_stage

    def reset_for_title(self) -> None:
        self._t = 0.0
        self._title_cursor = TITLE_ROW_START

    def update(self, dt: float) -> None:
        self._t += dt

    # ---------------- 输入处理 ----------------
    def handle(self, input, scene: str) -> list:
        actions: list = []
        if scene == "title":
            if input.was_pressed("up"):
                self._title_cursor = (self._title_cursor - 1) % TITLE_ROWS
            if input.was_pressed("down"):
                self._title_cursor = (self._title_cursor + 1) % TITLE_ROWS
            if self._title_cursor == TITLE_ROW_DIFFICULTY:
                if input.was_pressed("left"):
                    self._title_diff_cursor = (self._title_diff_cursor - 1) % len(DIFFICULTY_NAMES)
                if input.was_pressed("right"):
                    self._title_diff_cursor = (self._title_diff_cursor + 1) % len(DIFFICULTY_NAMES)
            elif self._title_cursor == TITLE_ROW_STAGE:
                if input.was_pressed("left"):
                    self._title_stage_cursor = max(0, self._title_stage_cursor - 1)
                if input.was_pressed("right"):
                    self._title_stage_cursor = min(self.max_stage, self._title_stage_cursor + 1)
            confirmed = (input.consume_press("enter") or input.consume_press("z")
                         or input.consume_press("space"))
            if confirmed:
                if self._title_cursor == TITLE_ROW_START:
                    actions.append(("start_story", self._title_diff_cursor))
                elif self._title_cursor == TITLE_ROW_STAGE:
                    actions.append(("start_practice", self._title_diff_cursor,
                                    self._title_stage_cursor))
                elif self._title_cursor == TITLE_ROW_DIFFICULTY:
                    actions.append(("set_difficulty", self._title_diff_cursor))
                elif self._title_cursor == TITLE_ROW_REPLAY:
                    actions.append(("list_replays",))
                else:
                    actions.append(("quit",))
            if input.consume_press("escape"):
                actions.append(("quit",))
        elif scene == "paused":
            if input.consume_press("escape"):
                actions.append(("quit",))
            if input.consume_press("r"):
                actions.append(("restart",))
            if input.consume_press("enter") or input.consume_press("z"):
                actions.append(("resume",))
        elif scene == "gameover":
            if input.consume_press("enter") or input.consume_press("z") or input.consume_press("space"):
                actions.append(("continue_or_restart",))
            if input.consume_press("r"):
                actions.append(("restart",))
            if input.consume_press("escape"):
                actions.append(("to_title",))
        elif scene in ("stageclear", "allclear"):
            if input.consume_press("enter") or input.consume_press("z") or input.consume_press("space"):
                actions.append(("to_title",))
            if input.consume_press("r"):
                actions.append(("restart",))
            if input.consume_press("escape"):
                actions.append(("to_title",))
        return actions

    # ---------------- 渲染 ----------------
    def draw(self, surf: pygame.Surface, scene: str, *, player=None,
             difficulty: int = DIFFICULTY_DEFAULT,
             continue_left: int = CONTINUE_MAX,
             continue_used: int = 0,
             stage_id: int = 1,
             best_score: int = 0,
             chapters_cleared: int = 0,
             total_chapters: int = 0) -> None:
        if scene == "title":
            self._draw_title(surf, best_score)
        elif scene == "paused":
            self._draw_paused(surf)
        elif scene == "gameover":
            self._draw_gameover(surf, player, difficulty, continue_left, stage_id)
        elif scene == "stageclear":
            self._draw_stageclear(surf, player, difficulty, continue_left,
                                  continue_used, stage_id)
        elif scene == "allclear":
            self._draw_allclear(surf, player, difficulty, continue_used,
                                chapters_cleared, total_chapters, best_score)

    # ---- 小工具 ----
    def _center(self, surf, text_surface, y):
        surf.blit(text_surface, ((SCREEN_W - text_surface.get_width()) // 2, y))

    def _row(self, surf, y, label, value_text, color, focused, *, value_color=None,
             left_arrow=False, right_arrow=False):
        """画一行: [>] LABEL   < value >"""
        x_cursor = 0
        text = self.font_big.render(label, True, color)
        surf.blit(text, (SCREEN_W // 2 - 150, y))
        if focused:
            pygame.draw.polygon(surf, COLOR_MENU_SEL, [
                (SCREEN_W // 2 - 175, y + 8),
                (SCREEN_W // 2 - 163, y + 14),
                (SCREEN_W // 2 - 175, y + 20),
            ])
        if value_text:
            vcol = value_color or COLOR_MENU_ACCENT
            v = self.font_big.render(value_text, True, vcol)
            vx = SCREEN_W // 2 + 70
            surf.blit(v, (vx, y))
            if left_arrow:
                a = self.font_med.render("<", True, COLOR_MENU_ACCENT)
                surf.blit(a, (vx - 20, y + 3))
            if right_arrow:
                a = self.font_med.render(">", True, COLOR_MENU_ACCENT)
                surf.blit(a, (vx + v.get_width() + 8, y + 3))
        return x_cursor

    # ---- title ----
    def _draw_title(self, surf, best_score: int = 0):
        title = self.font_huge.render("TOUHOU-STYLE", True, COLOR_MENU_TITLE)
        self._center(surf, title, 34)
        sub = self.font_cjk.render("～ 星 屑 异 变 ～", True, COLOR_MENU_ACCENT)
        self._center(surf, sub, 84)
        ver = self.font_small.render("v1.0  story campaign  /  6 chapters", True, COLOR_TEXT_DIM)
        self._center(surf, ver, 108)

        y0 = 146
        dy = 42

        # START
        c0 = COLOR_MENU_SEL if self._title_cursor == TITLE_ROW_START else COLOR_MENU_DIM
        start = self.font_big.render("START", True, c0)
        surf.blit(start, (SCREEN_W // 2 - 150, y0))
        if self._title_cursor == TITLE_ROW_START:
            pygame.draw.polygon(surf, COLOR_MENU_SEL, [
                (SCREEN_W // 2 - 175, y0 + 8),
                (SCREEN_W // 2 - 163, y0 + 14),
                (SCREEN_W // 2 - 175, y0 + 20),
            ])
        desc = self.font_cjk_small.render("剧情模式 · 6 章连续闯关", True,
                                         COLOR_TEXT if self._title_cursor == TITLE_ROW_START
                                         else COLOR_TEXT_DIM)
        surf.blit(desc, (SCREEN_W // 2 + 26, y0 + 8))

        # STAGE SELECT
        y = y0 + dy
        c1 = COLOR_MENU_SEL if self._title_cursor == TITLE_ROW_STAGE else COLOR_MENU_DIM
        lbl = self.font_big.render("STAGE", True, c1)
        surf.blit(lbl, (SCREEN_W // 2 - 150, y))
        if self._title_cursor == TITLE_ROW_STAGE:
            pygame.draw.polygon(surf, COLOR_MENU_SEL, [
                (SCREEN_W // 2 - 175, y + 8),
                (SCREEN_W // 2 - 163, y + 14),
                (SCREEN_W // 2 - 175, y + 20),
            ])
        sid = self._title_stage_cursor
        val = self.font_big.render(f"{sid:>2d}", True, COLOR_MENU_ACCENT)
        surf.blit(val, (SCREEN_W // 2 + 48, y))
        la = self.font_med.render("<", True, COLOR_MENU_ACCENT)
        ra = self.font_med.render(">", True, COLOR_MENU_ACCENT)
        surf.blit(la, (SCREEN_W // 2 + 28, y + 6))
        surf.blit(ra, (SCREEN_W // 2 + 84, y + 6))
        label = STAGE_LABELS.get(sid, "?")
        st = self.font_cjk_small.render(label, True,
                                       COLOR_TEXT if self._title_cursor == TITLE_ROW_STAGE
                                       else COLOR_TEXT_DIM)
        surf.blit(st, (SCREEN_W // 2 + 104, y + 8))

        # DIFFICULTY
        y = y0 + dy * 2
        c2 = COLOR_MENU_SEL if self._title_cursor == TITLE_ROW_DIFFICULTY else COLOR_MENU_DIM
        lbl = self.font_big.render("DIFFICULTY", True, c2)
        surf.blit(lbl, (SCREEN_W // 2 - 150, y))
        if self._title_cursor == TITLE_ROW_DIFFICULTY:
            pygame.draw.polygon(surf, COLOR_MENU_SEL, [
                (SCREEN_W // 2 - 175, y + 8),
                (SCREEN_W // 2 - 163, y + 14),
                (SCREEN_W // 2 - 175, y + 20),
            ])
        dval = self.font_big.render(DIFFICULTY_NAMES[self._title_diff_cursor], True,
                                    COLOR_MENU_ACCENT)
        surf.blit(dval, (SCREEN_W // 2 + 48, y))
        surf.blit(la, (SCREEN_W // 2 + 28, y + 6))
        surf.blit(ra, (SCREEN_W // 2 + 54 + dval.get_width(), y + 6))

        # REPLAY
        y = y0 + dy * 3
        c3 = COLOR_MENU_SEL if self._title_cursor == TITLE_ROW_REPLAY else COLOR_MENU_DIM
        rp = self.font_big.render("REPLAY", True, c3)
        surf.blit(rp, (SCREEN_W // 2 - 150, y))
        if self._title_cursor == TITLE_ROW_REPLAY:
            pygame.draw.polygon(surf, COLOR_MENU_SEL, [
                (SCREEN_W // 2 - 175, y + 8),
                (SCREEN_W // 2 - 163, y + 14),
                (SCREEN_W // 2 - 175, y + 20),
            ])
        rd = self.font_cjk_small.render("播放最新录像", True,
                                       COLOR_TEXT if self._title_cursor == TITLE_ROW_REPLAY
                                       else COLOR_TEXT_DIM)
        surf.blit(rd, (SCREEN_W // 2 + 26, y + 8))

        # QUIT
        y = y0 + dy * 4
        c4 = COLOR_MENU_SEL if self._title_cursor == TITLE_ROW_QUIT else COLOR_MENU_DIM
        q = self.font_big.render("QUIT", True, c4)
        surf.blit(q, (SCREEN_W // 2 - 150, y))
        if self._title_cursor == TITLE_ROW_QUIT:
            pygame.draw.polygon(surf, COLOR_MENU_SEL, [
                (SCREEN_W // 2 - 175, y + 8),
                (SCREEN_W // 2 - 163, y + 14),
                (SCREEN_W // 2 - 175, y + 20),
            ])

        # 最高分
        best = self.font_cjk_small.render(
            f"BEST  {_fmt_score(best_score)}   ({DIFFICULTY_NAMES[self._title_diff_cursor]})",
            True, (255, 230, 150))
        self._center(surf, best, 358)

        if int(self._t * 2) % 2 == 0:
            h = self.font_cjk_small.render("Enter / Z : 确认      ↑↓ 选择      ←→ 调整", True, COLOR_TEXT)
            self._center(surf, h, 384)

        ops = self.font_small.render(
            "Arrows/WASD Move   Shift Focus   Z Fire   X Bomb   P Pause",
            True, COLOR_TEXT_DIM,
        )
        self._center(surf, ops, 410)
        ops2 = self.font_small.render(
            "F1 Debug   F2 Step   F3 God   F4 Clear   Esc Quit",
            True, COLOR_TEXT_DIM,
        )
        self._center(surf, ops2, 430)

    # ---- paused ----
    def _draw_paused(self, surf):
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 120))
        surf.blit(s, (0, 0))
        t = self.font_huge.render("PAUSED", True, (255, 220, 120))
        self._center(surf, t, SCREEN_H // 2 - 80)
        sub = self.font_cjk.render("暂停中", True, COLOR_TEXT)
        self._center(surf, sub, SCREEN_H // 2 - 20)
        sub2 = self.font_cjk_small.render(
            "P 继续    F2 单帧    R 重开本关    Esc 退出", True, COLOR_TEXT_DIM
        )
        self._center(surf, sub2, SCREEN_H // 2 + 20)

    # ---- gameover ----
    def _draw_gameover(self, surf, player, difficulty, continue_left, stage_id=1):
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 190))
        surf.blit(s, (0, 0))
        t = self.font_huge.render("GAME OVER", True, (255, 80, 80))
        self._center(surf, t, 96)
        score = self.font_big.render(f"SCORE  {_fmt_score(player.score if player else 0)}",
                                     True, COLOR_TEXT)
        self._center(surf, score, 186)
        info = self.font_cjk_small.render(
            f"{STAGE_LABELS.get(stage_id, '')}    难度 {DIFFICULTY_NAMES[difficulty]}",
            True, COLOR_MENU_ACCENT)
        self._center(surf, info, 226)

        if continue_left > 0:
            cont = self.font_big.render(f"CONTINUE   (剩 {continue_left})", True, (255, 230, 120))
            self._center(surf, cont, 286)
            hint = self.font_cjk_small.render(
                "Enter 续关    R 从头再来    Esc 回标题", True, COLOR_TEXT)
            self._center(surf, hint, 330)
        else:
            nc = self.font_big.render("NO CONTINUE LEFT", True, COLOR_TEXT_DIM)
            self._center(surf, nc, 286)
            hint = self.font_cjk_small.render(
                "Enter / R 重新开始    Esc 回标题", True, COLOR_TEXT)
            self._center(surf, hint, 330)

    # ---- stageclear ----
    def _draw_stageclear(self, surf, player, difficulty, continue_left,
                         continue_used, stage_id=1):
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 190))
        surf.blit(s, (0, 0))
        t = self.font_huge.render("STAGE CLEAR", True, (180, 255, 200))
        self._center(surf, t, 82)
        name = self.font_cjk.render(STAGE_LABELS.get(stage_id, f"STAGE {stage_id}"),
                                    True, COLOR_MENU_ACCENT)
        self._center(surf, name, 140)
        score = self.font_big.render(f"SCORE  {_fmt_score(player.score if player else 0)}",
                                     True, COLOR_TEXT)
        self._center(surf, score, 180)
        rank = compute_rank(player.lives if player else 0, continue_used)
        rank_color = _RANK_COLORS.get(rank, COLOR_TEXT)
        rk = self.font_huge.render(f"RANK {rank}", True, rank_color)
        self._center(surf, rk, 226)
        diff_label = self.font_cjk_small.render(
            f"难度 {DIFFICULTY_NAMES[difficulty]}    残机 {player.lives if player else 0}",
            True, COLOR_MENU_ACCENT)
        self._center(surf, diff_label, 300)
        hint = self.font_cjk_small.render(
            "Enter 回标题    R 再打一次    Esc 回标题", True, COLOR_TEXT)
        self._center(surf, hint, 380)

    # ---- allclear ----
    def _draw_allclear(self, surf, player, difficulty, continue_used,
                       chapters_cleared, total_chapters, best_score):
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        s.fill((0, 0, 12, 205))
        surf.blit(s, (0, 0))
        t = self.font_huge.render("ALL CLEAR", True, (255, 240, 130))
        self._center(surf, t, 56)
        sub = self.font_cjk.render("星屑异变 · 解决", True, (180, 220, 255))
        self._center(surf, sub, 112)

        score = self.font_big.render(f"SCORE  {_fmt_score(player.score if player else 0)}",
                                     True, COLOR_TEXT)
        self._center(surf, score, 158)
        lives = self.font_cjk_small.render(
            f"残机 {player.lives if player else 0}    炸弹 {player.bombs if player else 0}"
            f"    火力 {player.power if player else 0}"
            f"    擦弹 {player.graze_count if player else 0}",
            True, COLOR_MENU_ACCENT)
        self._center(surf, lives, 190)

        rank = compute_rank(player.lives if player else 0, continue_used)
        rk = self.font_huge.render(f"RANK {rank}", True, _RANK_COLORS.get(rank, COLOR_TEXT))
        self._center(surf, rk, 224)

        ch = self.font_cjk_small.render(
            f"通关 {chapters_cleared}/{total_chapters} 章    难度 {DIFFICULTY_NAMES[difficulty]}"
            f"    最高分 {_fmt_score(best_score)}",
            True, COLOR_TEXT)
        self._center(surf, ch, 296)

        if int(self._t * 2) % 2 == 0:
            hint = self.font_cjk_small.render("Enter 回标题    感谢游玩", True, COLOR_TEXT_DIM)
            self._center(surf, hint, 348)
