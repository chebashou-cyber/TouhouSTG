# -*- coding: utf-8 -*-
"""ui/dialoguebox.py — 剧情对话渲染

包含三样东西:
  1. DialogueBox  : 底部对话框 + 说话人名牌 + 打字机文字
  2. 立绘         : 程序化绘制的 Q 版角色 (无美术资源也能有角色感)
  3. draw_chapter_title : 关卡开场标题卡 (章节名淡入淡出)

立绘说明:
  项目没有角色贴图, 所以用几何图形拼一个「发色 + 肤色 + 衣服色」的
  简化人形。颜色全部来自 campaign.json 的角色定义, 改颜色即可换人设。
"""
from __future__ import annotations

import math
import pygame

from src.ui.fonts import get_font, wrap_text
from config import SCREEN_W, SCREEN_H, COLOR_TEXT, COLOR_TEXT_DIM

BOX_X = 20
BOX_H = 112
BOX_Y = SCREEN_H - BOX_H - 16
BOX_W = SCREEN_W - BOX_X * 2

_SKIN = (255, 226, 206)
_SKIN_SHADOW = (232, 196, 178)
_DARK = (26, 22, 34)

# 侧写出对话时立绘的站位 (左/右)
_SIDE_X = {"left": 118, "right": SCREEN_W - 118}
_BASE_Y = BOX_Y - 6


def _shade(color: tuple, k: float) -> tuple:
    return (max(0, min(255, int(color[0] * k))),
            max(0, min(255, int(color[1] * k))),
            max(0, min(255, int(color[2] * k))))


def _mix(a: tuple, b: tuple, t: float) -> tuple:
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


class DialogueBox:
    __slots__ = ("_f_name", "_f_text", "_f_small", "_blink")

    def __init__(self) -> None:
        self._f_name = get_font(17, bold=True, cjk=True)
        self._f_text = get_font(18, cjk=True)
        self._f_small = get_font(12, cjk=True)
        self._blink = 0.0

    def update(self, dt: float) -> None:
        self._blink = (self._blink + dt) % 1.0

    # ---------------- 主入口 ----------------
    def draw(self, surf: pygame.Surface, ctrl, characters: dict) -> None:
        # 压暗游戏画面, 突出对话
        dim = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 110))
        surf.blit(dim, (0, 0))

        speakers = self._side_speakers(ctrl, characters)
        current = ctrl.current_speaker
        line = ctrl.current
        emotion = line.emotion if line is not None else "normal"
        for side, key in speakers.items():
            if key is None:
                continue
            ch = characters.get(key)
            if ch is None:
                continue
            speaking = (key == current)
            self._draw_portrait(surf, _SIDE_X[side], _BASE_Y, ch, speaking,
                                emotion if speaking else "normal")

        if line is None:
            return
        ch = characters.get(line.speaker) if line.speaker else None
        self._draw_box(surf, ctrl, ch, line, characters)

    # ---------------- 立绘 ----------------
    @staticmethod
    def _side_speakers(ctrl, characters: dict) -> dict:
        """左右两侧各显示谁: 取对话进行到当前为止最近一次在该侧出场的人。"""
        out = {"left": None, "right": None}
        for i in range(0, min(ctrl.index + 1, len(ctrl.lines))):
            key = ctrl.lines[i].speaker
            if not key:
                continue
            ch = characters.get(key)
            if ch is None:
                continue
            side = ch.side if ch.side in out else "left"
            out[side] = key
        return out

    def _draw_portrait(self, surf: pygame.Surface, cx: int, base_y: int,
                       ch, speaking: bool, emotion: str = "normal") -> None:
        """画一个 Q 版立绘。speaking=False 时整体变暗 (临时面 + set_alpha)。

        图层顺序很关键: 后发 -> 脸 -> 刘海 -> 侧发 -> 五官。
        刘海必须是「额前的一撮」而不是整个圆, 否则会盖住眼睛。
        """
        layer = pygame.Surface((200, 210), pygame.SRCALPHA)
        ox, oy = 100, 196          # 局部坐标: 脚底在 (100, 196)
        head_x, head_y = ox, oy - 118

        hair = _shade(ch.color, 0.92)
        hair_dark = _shade(ch.color, 0.66)
        hair_hi = _shade(ch.color, 1.22)
        cloth = _shade(ch.color, 0.58)

        # 地面阴影
        pygame.draw.ellipse(layer, (0, 0, 0, 80), (ox - 48, oy - 8, 96, 20))

        # 身体 (梯形) + 衣领
        pygame.draw.polygon(layer, cloth, [
            (ox - 42, oy), (ox + 42, oy), (ox + 26, oy - 86), (ox - 26, oy - 86),
        ])
        pygame.draw.polygon(layer, _shade(ch.color, 1.1), [
            (ox - 13, oy - 86), (ox + 13, oy - 86), (ox, oy - 62),
        ])
        # 双臂
        pygame.draw.line(layer, _shade(ch.color, 0.48), (ox - 38, oy - 74),
                         (ox - 47, oy - 16), 9)
        pygame.draw.line(layer, _shade(ch.color, 0.48), (ox + 38, oy - 74),
                         (ox + 47, oy - 16), 9)

        # 后发
        pygame.draw.circle(layer, hair_dark, (head_x, head_y - 4), 40)
        # 脖子
        pygame.draw.rect(layer, _SKIN_SHADOW, (head_x - 7, head_y + 18, 14, 16))
        # 脸
        pygame.draw.circle(layer, _SKIN, (head_x, head_y), 28)

        # 刘海: 额前的一撮 (顶弧 + 下缘锯齿), 不遮眼睛
        pygame.draw.polygon(layer, hair, [
            (head_x - 30, head_y - 2), (head_x - 27, head_y - 18),
            (head_x - 18, head_y - 28), (head_x, head_y - 31),
            (head_x + 18, head_y - 28), (head_x + 27, head_y - 18),
            (head_x + 30, head_y - 2),
            (head_x + 22, head_y - 12), (head_x + 12, head_y - 16),
            (head_x, head_y - 13), (head_x - 12, head_y - 16),
            (head_x - 22, head_y - 12),
        ])
        # 侧发
        pygame.draw.polygon(layer, hair, [
            (head_x - 30, head_y - 6), (head_x - 33, head_y + 30),
            (head_x - 20, head_y + 26), (head_x - 22, head_y + 2),
        ])
        pygame.draw.polygon(layer, hair, [
            (head_x + 30, head_y - 6), (head_x + 33, head_y + 30),
            (head_x + 20, head_y + 26), (head_x + 22, head_y + 2),
        ])
        # 呆毛 + 高光
        pygame.draw.line(layer, hair_hi, (head_x + 4, head_y - 38),
                         (head_x + 13, head_y - 50), 3)
        pygame.draw.arc(layer, hair_hi, (head_x - 22, head_y - 32, 44, 26),
                        0.6, 2.0, 2)

        # 五官
        eye_y = head_y + 2
        for ex in (head_x - 10, head_x + 10):
            pygame.draw.ellipse(layer, _DARK, (ex - 3, eye_y - 4, 6, 9))
            pygame.draw.circle(layer, (255, 255, 255), (ex, eye_y - 1), 1)
        # 眉毛 (按情绪)
        if emotion == "angry":
            pygame.draw.line(layer, _DARK, (head_x - 15, eye_y - 10),
                             (head_x - 6, eye_y - 7), 2)
            pygame.draw.line(layer, _DARK, (head_x + 15, eye_y - 10),
                             (head_x + 6, eye_y - 7), 2)
        elif emotion == "sad":
            pygame.draw.line(layer, _DARK, (head_x - 15, eye_y - 7),
                             (head_x - 6, eye_y - 10), 2)
            pygame.draw.line(layer, _DARK, (head_x + 15, eye_y - 7),
                             (head_x + 6, eye_y - 10), 2)
        # 腮红
        pygame.draw.circle(layer, (255, 166, 166), (head_x - 19, eye_y + 9), 4)
        pygame.draw.circle(layer, (255, 166, 166), (head_x + 19, eye_y + 9), 4)
        # 嘴
        if emotion == "smile":
            pygame.draw.arc(layer, (168, 80, 90), (head_x - 7, eye_y + 8, 14, 10),
                            0.2, 2.9, 2)
        elif emotion == "angry":
            pygame.draw.line(layer, (168, 80, 90), (head_x - 6, eye_y + 14),
                             (head_x + 6, eye_y + 14), 2)
        else:
            pygame.draw.line(layer, (168, 80, 90), (head_x - 5, eye_y + 13),
                             (head_x + 5, eye_y + 13), 2)

        if not speaking:
            layer.set_alpha(145)

        surf.blit(layer, (cx - ox, base_y - oy))

    # ---------------- 对话框 ----------------
    def _draw_box(self, surf: pygame.Surface, ctrl, ch, line, characters: dict) -> None:
        accent = ch.color if ch is not None else (140, 160, 200)

        panel = pygame.Surface((BOX_W, BOX_H), pygame.SRCALPHA)
        panel.fill((6, 8, 20, 218))
        surf.blit(panel, (BOX_X, BOX_Y))
        pygame.draw.rect(surf, accent, (BOX_X, BOX_Y, BOX_W, BOX_H), 1)
        pygame.draw.line(surf, accent, (BOX_X + 1, BOX_Y + 1),
                         (BOX_X + BOX_W - 1, BOX_Y + 1), 2)

        # 名牌
        if ch is not None:
            label = ch.name
            if ch.title:
                label = f"{ch.name}  ({ch.title})"
            name_surf = self._f_name.render(label, True, (14, 12, 20))
            plate_w = name_surf.get_width() + 20
            plate_h = name_surf.get_height() + 6
            plate = pygame.Surface((plate_w, plate_h), pygame.SRCALPHA)
            plate.fill(accent)
            pygame.draw.rect(plate, (255, 255, 255, 120), (0, 0, plate_w, 1))
            surf.blit(plate, (BOX_X + 12, BOX_Y - plate_h + 2))
            surf.blit(name_surf, (BOX_X + 22, BOX_Y - plate_h + 5))

        # 正文 (打字机)
        text = ctrl.text_visible()
        lines = wrap_text(text, self._f_text, BOX_W - 36)
        lh = self._f_text.get_linesize() + 4
        ty = BOX_Y + 16
        for i, ln in enumerate(lines[:3]):
            t = self._f_text.render(ln, True, COLOR_TEXT)
            surf.blit(t, (BOX_X + 18, ty + i * lh))

        # 进度 (右上角, 避开右下角的翻页三角)
        cur, total = ctrl.progress
        prog = self._f_small.render(f"{cur}/{total}", True, COLOR_TEXT_DIM)
        surf.blit(prog, (BOX_X + BOX_W - prog.get_width() - 12, BOX_Y + 6))

        if ctrl.line_complete():
            if self._blink < 0.55:
                tri = [(BOX_X + BOX_W - 34, BOX_Y + BOX_H - 20),
                       (BOX_X + BOX_W - 20, BOX_Y + BOX_H - 20),
                       (BOX_X + BOX_W - 27, BOX_Y + BOX_H - 9)]
                pygame.draw.polygon(surf, accent, tri)

        hint = self._f_small.render("Z / Enter 继续    X 跳过整段", True, COLOR_TEXT_DIM)
        surf.blit(hint, (BOX_X + 18, SCREEN_H - 14))


def draw_chapter_title(surf: pygame.Surface, title: str, subtitle: str,
                       t: float, duration: float = 3.4) -> None:
    """开场标题卡: 0.4s 淡入, 保持, 0.7s 淡出。t 为已过时间。"""
    if t < 0 or t >= duration:
        return
    fade_in, fade_out = 0.4, 0.7
    if t < fade_in:
        a = t / fade_in
    elif t > duration - fade_out:
        a = max(0.0, (duration - t) / fade_out)
    else:
        a = 1.0
    a = max(0.0, min(1.0, a))

    f_title = get_font(30, bold=True, cjk=True)
    f_sub = get_font(16, cjk=True)

    layer = pygame.Surface((SCREEN_W, 110), pygame.SRCALPHA)
    layer.fill((0, 0, 0, int(120 * a)))
    surf.blit(layer, (0, 150))

    for dy, text, font, color in (
        (0, title, f_title, (255, 238, 200)),
        (44, subtitle, f_sub, (180, 220, 255)),
    ):
        s = font.render(text, True, color)
        s.set_alpha(int(255 * a))
        surf.blit(s, ((SCREEN_W - s.get_width()) // 2, 158 + dy))

    # 装饰横线
    line_col = (int(220 * a), int(200 * a), int(160 * a))
    if a > 0.05:
        pygame.draw.line(surf, line_col, (SCREEN_W // 2 - 120, 148),
                         (SCREEN_W // 2 + 120, 148), 1)
        pygame.draw.line(surf, line_col, (SCREEN_W // 2 - 120, 262),
                         (SCREEN_W // 2 + 120, 262), 1)
