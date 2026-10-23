# -*- coding: utf-8 -*-
"""ui/fonts.py — 全项目统一字体入口

为什么不用 pygame.font.SysFont():
  pygame-ce 2.6.x 在部分 Windows 机器上, initsysfonts_win32() 会把字体
  注册表里的非字符串值 (REG_DWORD) 当成文件名传给 os.path.splitext(),
  抛出 `TypeError: expected str, bytes or os.PathLike object, not int`。
  只要机器上装过某些字体就会触发, 结果是 HUD/菜单/ItemPool 一创建就崩,
  游戏根本起不来。这里全部走 pygame.font.Font(具体路径), 不枚举系统字体。

中文支持:
  SysFont("consolas") 本身不含中文字形, 剧情文本会显示成方块。
  因此提供 cjk=True 档位, 依次尝试 微软雅黑 / 黑体 / 宋体 / 苹方 / Noto,
  任何平台都找不到时退回 pygame 内置字体 (英文可用, 中文为方块但不崩)。
"""
from __future__ import annotations

import os
import pygame

# (路径, 是否本身就是粗体)
_MONO_CANDIDATES = (
    (r"C:\Windows\Fonts\consola.ttf", False),
    (r"C:\Windows\Fonts\consolab.ttf", True),
    (r"C:\Windows\Fonts\lucon.ttf", False),
    ("/System/Library/Fonts/Menlo.ttc", False),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", False),
    ("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf", False),
)

_CJK_CANDIDATES = (
    (r"C:\Windows\Fonts\msyhbd.ttc", True),
    (r"C:\Windows\Fonts\msyh.ttc", False),
    (r"C:\Windows\Fonts\simhei.ttf", False),
    (r"C:\Windows\Fonts\msyhl.ttc", False),
    (r"C:\Windows\Fonts\simsun.ttc", False),
    (r"C:\Windows\Fonts\deng.ttf", False),
    ("/System/Library/Fonts/PingFang.ttc", False),
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", False),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", False),
    ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", False),
    ("/usr/share/fonts/truetype/arphic/uming.ttc", False),
)

_cache: dict[tuple, pygame.font.Font] = {}
_resolved: dict[bool, str | None] = {}


def _pick_path(cjk: bool) -> tuple[str | None, bool]:
    """挑一个可用字体文件; 返回 (路径, 是否已含粗体字形)。"""
    if cjk in _resolved:
        p = _resolved[cjk]
        return (p, any(p == f and b for f, b in _CJK_CANDIDATES)) if p else (None, False)
    cands = _CJK_CANDIDATES if cjk else _MONO_CANDIDATES
    for path, is_bold in cands:
        if os.path.isfile(path):
            _resolved[cjk] = path
            return (path, is_bold)
    _resolved[cjk] = None
    return (None, False)


def get_font(size: int, *, cjk: bool = False, bold: bool = False) -> pygame.font.Font:
    """取一个字体对象 (带缓存)。cjk=True 时优先返回支持中文的字体。"""
    key = ("cjk" if cjk else "mono", int(size), bool(bold))
    cached = _cache.get(key)
    if cached is not None:
        return cached

    path, native_bold = _pick_path(cjk)
    font: pygame.font.Font | None = None
    if path:
        try:
            font = pygame.font.Font(path, int(size))
        except Exception:
            font = None
    if font is None:
        # pygame 内置字体: 没有中文, 但至少不会崩
        font = pygame.font.Font(None, int(size))
        native_bold = False
    if bold and not native_bold:
        try:
            font.set_bold(True)
        except Exception:
            pass
    _cache[key] = font
    return font


def font_info() -> dict:
    """给 F1 调试面板/自检用: 当前实际选中的字体文件。"""
    mono, _ = _pick_path(False)
    cjkp, _ = _pick_path(True)
    return {"mono": mono or "<pygame default>", "cjk": cjkp or "<pygame default>"}


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """按像素宽度折行, 逐字符判定 (CJK 没有空格可断, 必须按字断)。"""
    if not text:
        return [""]
    lines: list[str] = []
    cur = ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        trial = cur + ch
        if cur and font.size(trial)[0] > max_width:
            lines.append(cur)
            cur = "" if ch == " " else ch
        else:
            cur = trial
    lines.append(cur) if cur or not lines else None
    return lines
