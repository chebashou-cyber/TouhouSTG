# -*- coding: utf-8 -*-
"""assets.py — 资源加载接口 (v0.5)

设计:
  - 优先从 assets/{chars,boss,bg,sfx}/ 加载真实 PNG/Sound
  - 加载失败时, 用程序化方式生成 Surface / silent Sound 占位
  - 统一 API: AssetLoader.image(name, gen_fallback) / sound(name, freq)

占位资源 (无真实文件时使用):
  - 玩家自机: 蓝色三角 + 引擎焰
  - 敌机: 橙色六边形 (按 HP 调亮度)
  - Boss: 紫色十二边形 + 内白点
  - 自机弹: 小绿圆
  - 敌弹: 用 BulletPool 的预渲染, 此处不再额外生成
  - 音效: silent Sound (空 sound buffer)
"""
from __future__ import annotations
import os
import math
import pygame


def _asset_root() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "assets")


class AssetLoader:
    __slots__ = ("root", "_image_cache", "_sound_cache")

    def __init__(self, root: str | None = None) -> None:
        self.root = root or _asset_root()
        self._image_cache: dict[str, pygame.Surface] = {}
        self._sound_cache: dict[str, pygame.mixer.Sound] = {}

    # ---------------- 图片 ----------------
    def image(self, name: str, gen_fallback) -> pygame.Surface:
        if name in self._image_cache:
            return self._image_cache[name]
        # 尝试加载
        for sub in ("chars", "boss", "bg"):
            path = os.path.join(self.root, sub, f"{name}.png")
            if os.path.isfile(path):
                try:
                    surf = pygame.image.load(path).convert_alpha()
                    self._image_cache[name] = surf
                    return surf
                except Exception:
                    break
        # Fallback: 程序化生成
        surf = gen_fallback()
        self._image_cache[name] = surf
        return surf

    # ---------------- 音效 ----------------
    def sound(self, name: str, freq: float = 0.0, duration: float = 0.0) -> pygame.mixer.Sound:
        if name in self._sound_cache:
            return self._sound_cache[name]
        path = os.path.join(self.root, "sfx", f"{name}.ogg")
        if os.path.isfile(path):
            try:
                s = pygame.mixer.Sound(path)
                self._sound_cache[name] = s
                return s
            except Exception:
                pass
        # Fallback: silent sound
        s = pygame.mixer.Sound(buffer=bytearray(8000))
        self._sound_cache[name] = s
        return s


# --------------- 程序化图像生成器 ---------------
def make_player_surf() -> pygame.Surface:
    surf = pygame.Surface((24, 24), pygame.SRCALPHA)
    pygame.draw.polygon(surf, (96, 192, 255), [
        (12, 2), (4, 20), (20, 20),
    ])
    pygame.draw.polygon(surf, (255, 200, 120), [
        (9, 16), (12, 22), (15, 16),
    ])
    return surf


def make_enemy_surf() -> pygame.Surface:
    surf = pygame.Surface((28, 28), pygame.SRCALPHA)
    pts = []
    for i in range(6):
        a = math.pi / 6 + i * math.pi / 3
        pts.append((14 + math.cos(a) * 12, 14 + math.sin(a) * 12))
    pygame.draw.polygon(surf, (255, 180, 120), pts)
    pygame.draw.polygon(surf, (255, 255, 255), pts, 1)
    return surf


def make_boss_surf() -> pygame.Surface:
    surf = pygame.Surface((80, 80), pygame.SRCALPHA)
    pts = []
    for i in range(12):
        a = math.pi / 12 + i * 2 * math.pi / 12
        pts.append((40 + math.cos(a) * 36, 40 + math.sin(a) * 36))
    pygame.draw.polygon(surf, (220, 140, 200), pts)
    pygame.draw.polygon(surf, (255, 255, 255), pts, 1)
    pygame.draw.circle(surf, (255, 255, 255), (40, 40), 14, 0)
    pygame.draw.circle(surf, (40, 40, 60), (40, 40), 6, 0)
    return surf


# 全局单例
_default_loader: AssetLoader | None = None


def default_loader() -> AssetLoader:
    global _default_loader
    if _default_loader is None:
        _default_loader = AssetLoader()
    return _default_loader