# -*- coding: utf-8 -*-
"""ui/menu.py — 菜单系统

场景:
  title      标题画面 (START / DIFFICULTY / STAGE 三行选择)
  paused     暂停
  gameover   Game Over (Continue / Restart)
  stageclear Stage Clear (评级 + Restart / Continue)
"""
from __future__ import annotations
import pygame
from config import (
    SCREEN_W, SCREEN_H,
    DIFFICULTY_NAMES, DIFFICULTY_DEFAULT,
    COLOR_MENU_DIM, COLOR_MENU_SEL, COLOR_MENU_TITLE, COLOR_MENU_ACCENT,
    COLOR_TEXT, COLOR_TEXT_DIM,
    CONTINUE_MAX,
    STAGE_CLEAR_RANK_FINAL, STAGE_CLEAR_RANK_A, STAGE_CLEAR_RANK_B, STAGE_CLEAR_RANK_C,
)


# 标题 cursor 行: 0=START, 1=DIFFICULTY, 2=STAGE, 3=REPLAY
TITLE_ROW_START = 0
TITLE_ROW_DIFFICULTY = 1
TITLE_ROW_STAGE = 2
TITLE_ROW_REPLAY = 3


def compute_rank(lives: int, continue_used: int) -> str:
    if continue_used == 0 and lives >= 2:
        return STAGE_CLEAR_RANK_FINAL
    if lives >= 1 and continue_used <= 1:
        return STAGE_CLEAR_RANK_A
    if lives >= 1:
        return STAGE_CLEAR_RANK_B
    return STAGE_CLEAR_RANK_C


class MenuSystem:
    __slots__ = (
        "font_huge", "font_big", "font_med", "font_small",
        "_t",
        "_title_cursor",
        "_title_diff_cursor",
        "_title_stage_cursor",
        "max_stage",
    )

    def __init__(self, max_stage: int = 3) -> None:
        self.font_huge = pygame.font.SysFont("consolas", 44, bold=True)
        self.font_big = pygame.font.SysFont("consolas", 26, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 18)
        self.font_small = pygame.font.SysFont("consolas", 14)
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
            total_rows = 4
            if input.was_pressed("up"):
                self._title_cursor = (self._title_cursor - 1) % total_rows
            if input.was_pressed("down"):
                self._title_cursor = (self._title_cursor + 1) % total_rows
            if self._title_cursor == TITLE_ROW_DIFFICULTY:
                if input.was_pressed("left"):
                    self._title_diff_cursor = (self._title_diff_cursor - 1) % len(DIFFICULTY_NAMES)
                if input.was_pressed("right"):
                    self._title_diff_cursor = (self._title_diff_cursor + 1) % len(DIFFICULTY_NAMES)
            elif self._title_cursor == TITLE_ROW_STAGE:
                if input.was_pressed("left"):
                    self._title_stage_cursor = max(1, self._title_stage_cursor - 1)
                if input.was_pressed("right"):
                    self._title_stage_cursor = min(self.max_stage, self._title_stage_cursor + 1)
            if input.consume_press("enter") or input.consume_press("z") or input.consume_press("space"):
                if self._title_cursor == TITLE_ROW_START:
                    actions.append(("start", self._title_diff_cursor, self._title_stage_cursor))
                elif self._title_cursor == TITLE_ROW_DIFFICULTY:
                    actions.append(("set_difficulty", self._title_diff_cursor))
                elif self._title_cursor == TITLE_ROW_STAGE:
                    actions.append(("set_stage", self._title_stage_cursor))
                else:  # TITLE_ROW_REPLAY
                    actions.append(("list_replays",))
            if input.consume_press("escape"):
                actions.append(("quit",))
        elif scene == "paused":
            if input.consume_press("escape"):
                actions.append(("quit",))
            if input.consume_press("r"):
                actions.append(("restart",))
        elif scene == "gameover":
            if input.consume_press("enter") or input.consume_press("z") or input.consume_press("space"):
                actions.append(("continue_or_restart",))
            if input.consume_press("r"):
                actions.append(("restart",))
            if input.consume_press("escape"):
                actions.append(("quit",))
        elif scene == "stageclear":
            if input.consume_press("enter") or input.consume_press("z") or input.consume_press("space"):
                actions.append(("continue_or_restart",))
            if input.consume_press("r"):
                actions.append(("restart",))
            if input.consume_press("escape"):
                actions.append(("quit",))
        return actions

    # ---------------- 渲染 ----------------
    def draw(self, surf: pygame.Surface, scene: str, *, player=None,
             difficulty: int = DIFFICULTY_DEFAULT,
             continue_left: int = CONTINUE_MAX,
             continue_used: int = 0) -> None:
        if scene == "title":
            self._draw_title(surf)
        elif scene == "paused":
            self._draw_paused(surf)
        elif scene == "gameover":
            self._draw_gameover(surf, player, difficulty, continue_left)
        elif scene == "stageclear":
            self._draw_stageclear(surf, player, difficulty, continue_left, continue_used)

    # ---- title ----
    def _draw_title(self, surf):
        title = self.font_huge.render("TOUHOU-STYLE", True, COLOR_MENU_TITLE)
        surf.blit(title, ((SCREEN_W - title.get_width()) // 2, 50))
        sub = self.font_med.render("v0.5  MVP + Boss + Laser + 3 Stages", True, COLOR_MENU_ACCENT)
        surf.blit(sub, ((SCREEN_W - sub.get_width()) // 2, 105))

        # START
        c0 = COLOR_MENU_SEL if self._title_cursor == TITLE_ROW_START else COLOR_MENU_DIM
        start = self.font_big.render("START", True, c0)
        surf.blit(start, ((SCREEN_W - start.get_width()) // 2, 180))

        # DIFFICULTY
        c1 = COLOR_MENU_SEL if self._title_cursor == TITLE_ROW_DIFFICULTY else COLOR_MENU_DIM
        diff_label = self.font_med.render("DIFFICULTY", True, c1)
        diff_value = self.font_big.render(
            DIFFICULTY_NAMES[self._title_diff_cursor], True, COLOR_MENU_ACCENT
        )
        larrow = self.font_med.render("<", True, COLOR_MENU_ACCENT)
        rarrow = self.font_med.render(">", True, COLOR_MENU_ACCENT)
        yd = 230
        total_w = larrow.get_width() + 12 + diff_value.get_width() + 12 + rarrow.get_width()
        cx = SCREEN_W // 2
        surf.blit(diff_label, ((SCREEN_W - diff_label.get_width()) // 2, yd - 22))
        x = cx - total_w // 2
        surf.blit(larrow, (x, yd + 4))
        x += larrow.get_width() + 12
        surf.blit(diff_value, (x, yd))
        x += diff_value.get_width() + 12
        surf.blit(rarrow, (x, yd + 4))

        # STAGE (0=TUTORIAL)
        c2 = COLOR_MENU_SEL if self._title_cursor == TITLE_ROW_STAGE else COLOR_MENU_DIM
        st_label = self.font_med.render("STAGE", True, c2)
        st_value = self.font_big.render(
            f"{self._title_stage_cursor}", True, COLOR_MENU_ACCENT
        )
        sl = self.font_med.render("<", True, COLOR_MENU_ACCENT)
        sr = self.font_med.render(">", True, COLOR_MENU_ACCENT)
        ys = 280
        tw = sl.get_width() + 12 + st_value.get_width() + 12 + sr.get_width()
        surf.blit(st_label, ((SCREEN_W - st_label.get_width()) // 2, ys - 22))
        x = cx - tw // 2
        surf.blit(sl, (x, ys + 4))
        x += sl.get_width() + 12
        surf.blit(st_value, (x, ys))
        x += st_value.get_width() + 12
        surf.blit(sr, (x, ys + 4))

        # REPLAY
        c3 = COLOR_MENU_SEL if self._title_cursor == TITLE_ROW_REPLAY else COLOR_MENU_DIM
        replay_text = self.font_med.render("REPLAY", True, c3)
        surf.blit(replay_text, ((SCREEN_W - replay_text.get_width()) // 2, 330))

        if int(self._t * 2) % 2 == 0:
            h = self.font_med.render("PRESS  ENTER / Z  TO  START", True, COLOR_TEXT)
            surf.blit(h, ((SCREEN_W - h.get_width()) // 2, 360))

        ops = self.font_small.render(
            "Arrows/WASD Move   Shift Focus   Z Fire   X Bomb",
            True, COLOR_TEXT_DIM,
        )
        surf.blit(ops, ((SCREEN_W - ops.get_width()) // 2, 410))
        ops2 = self.font_small.render(
            "F1 Debug   F2 Step   F3 God   F4 Clear   P Pause",
            True, COLOR_TEXT_DIM,
        )
        surf.blit(ops2, ((SCREEN_W - ops2.get_width()) // 2, 430))
        ver = self.font_small.render("Esc to quit", True, COLOR_TEXT_DIM)
        surf.blit(ver, ((SCREEN_W - ver.get_width()) // 2, 458))

    # ---- paused ----
    def _draw_paused(self, surf):
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 96))
        surf.blit(s, (0, 0))
        t = self.font_huge.render("PAUSED", True, (255, 220, 120))
        surf.blit(t, ((SCREEN_W - t.get_width()) // 2, SCREEN_H // 2 - 80))
        sub = self.font_med.render("Press P to resume", True, COLOR_TEXT)
        surf.blit(sub, ((SCREEN_W - sub.get_width()) // 2, SCREEN_H // 2 - 10))
        sub2 = self.font_med.render("F2 = step frame    R = restart    Esc = quit",
                                    True, COLOR_TEXT_DIM)
        surf.blit(sub2, ((SCREEN_W - sub2.get_width()) // 2, SCREEN_H // 2 + 24))

    # ---- gameover ----
    def _draw_gameover(self, surf, player, difficulty, continue_left):
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        surf.blit(s, (0, 0))
        t = self.font_huge.render("GAME OVER", True, (255, 80, 80))
        surf.blit(t, ((SCREEN_W - t.get_width()) // 2, 110))
        score = self.font_big.render(f"SCORE  {player.score if player else 0}",
                                     True, COLOR_TEXT)
        surf.blit(score, ((SCREEN_W - score.get_width()) // 2, 200))
        diff_label = self.font_med.render(
            f"DIFFICULTY  {DIFFICULTY_NAMES[difficulty]}", True, COLOR_MENU_ACCENT
        )
        surf.blit(diff_label, ((SCREEN_W - diff_label.get_width()) // 2, 250))

        if continue_left > 0:
            cont = self.font_big.render(
                f"CONTINUE  ({continue_left} left)", True, (255, 230, 120)
            )
            surf.blit(cont, ((SCREEN_W - cont.get_width()) // 2, 310))
            hint = self.font_med.render(
                "Press ENTER to continue    R to restart    Esc to quit",
                True, COLOR_TEXT,
            )
            surf.blit(hint, ((SCREEN_W - hint.get_width()) // 2, 360))
        else:
            no_cont = self.font_big.render("NO CONTINUE LEFT", True, COLOR_TEXT_DIM)
            surf.blit(no_cont, ((SCREEN_W - no_cont.get_width()) // 2, 310))
            hint = self.font_med.render(
                "Press ENTER / R to restart    Esc to quit",
                True, COLOR_TEXT,
            )
            surf.blit(hint, ((SCREEN_W - hint.get_width()) // 2, 360))

    # ---- stageclear ----
    def _draw_stageclear(self, surf, player, difficulty, continue_left, continue_used):
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        surf.blit(s, (0, 0))
        t = self.font_huge.render("STAGE CLEAR", True, (180, 255, 200))
        surf.blit(t, ((SCREEN_W - t.get_width()) // 2, 90))
        score = self.font_big.render(
            f"SCORE  {player.score if player else 0}", True, COLOR_TEXT
        )
        surf.blit(score, ((SCREEN_W - score.get_width()) // 2, 170))
        rank = compute_rank(
            player.lives if player else 0, continue_used
        )
        rank_color = {
            STAGE_CLEAR_RANK_FINAL: (255, 240, 120),
            STAGE_CLEAR_RANK_A: (180, 220, 255),
            STAGE_CLEAR_RANK_B: (180, 180, 180),
            STAGE_CLEAR_RANK_C: (180, 180, 180),
        }.get(rank, COLOR_TEXT)
        rank_text = self.font_huge.render(f"RANK {rank}", True, rank_color)
        surf.blit(rank_text, ((SCREEN_W - rank_text.get_width()) // 2, 230))
        diff_label = self.font_med.render(
            f"DIFFICULTY  {DIFFICULTY_NAMES[difficulty]}", True, COLOR_MENU_ACCENT
        )
        surf.blit(diff_label, ((SCREEN_W - diff_label.get_width()) // 2, 310))

        if continue_left > 0:
            cont = self.font_big.render(
                f"CONTINUE  ({continue_left} left)", True, (255, 230, 120)
            )
            surf.blit(cont, ((SCREEN_W - cont.get_width()) // 2, 360))
        hint = self.font_med.render(
            "Press ENTER to continue    R to restart    Esc to quit",
            True, COLOR_TEXT,
        )
        surf.blit(hint, ((SCREEN_W - hint.get_width()) // 2, 410))