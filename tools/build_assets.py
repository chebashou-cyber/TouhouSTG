# -*- coding: utf-8 -*-
"""tools/build_assets.py — 程序化生成占位资源

用户本地运行: python tools/build_assets.py
会向 assets/chars|boss|bg|sfx/ 写入 PNG 与 WAV 文件。

依赖: pygame (>= 2.0), numpy (>= 1.20), wave (标准库)。
"""
from __future__ import annotations
import os
import math
import wave
import struct


def _project_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(here)


def _ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def make_player_png(path: str) -> None:
    import pygame
    surf = pygame.Surface((24, 32), pygame.SRCALPHA)
    # 三角
    pygame.draw.polygon(surf, (96, 192, 255), [
        (12, 2), (4, 22), (20, 22),
    ])
    # 内白点 (highlights)
    pygame.draw.polygon(surf, (200, 230, 255), [
        (12, 6), (8, 18), (16, 18),
    ])
    # 引擎焰
    pygame.draw.polygon(surf, (255, 200, 120), [
        (10, 22), (12, 30), (14, 22),
    ])
    pygame.image.save(surf, path)


def make_enemy_png(path: str) -> None:
    import pygame
    surf = pygame.Surface((28, 28), pygame.SRCALPHA)
    pts = []
    for i in range(6):
        a = math.pi / 6 + i * math.pi / 3
        pts.append((14 + math.cos(a) * 12, 14 + math.sin(a) * 12))
    pygame.draw.polygon(surf, (255, 180, 120), pts)
    pygame.draw.polygon(surf, (255, 255, 200), pts, 1)
    pygame.draw.circle(surf, (60, 30, 0), (14, 14), 3, 0)
    pygame.image.save(surf, path)


def make_boss_png(path: str) -> None:
    import pygame
    surf = pygame.Surface((80, 80), pygame.SRCALPHA)
    pts = []
    for i in range(12):
        a = math.pi / 12 + i * 2 * math.pi / 12
        pts.append((40 + math.cos(a) * 36, 40 + math.sin(a) * 36))
    pygame.draw.polygon(surf, (220, 140, 200), pts)
    pygame.draw.polygon(surf, (255, 255, 255), pts, 1)
    pygame.draw.circle(surf, (40, 40, 60), (40, 40), 14, 0)
    pygame.draw.circle(surf, (255, 230, 80), (40, 40), 6, 0)
    pygame.image.save(surf, path)


def make_item_png(path: str) -> None:
    import pygame
    surf = pygame.Surface((14, 14), pygame.SRCALPHA)
    pygame.draw.circle(surf, (96, 192, 255), (7, 7), 6, 0)
    pygame.draw.circle(surf, (255, 255, 255), (7, 7), 6, 1)
    pygame.image.save(surf, path)


def make_bullet_png(path: str) -> None:
    import pygame
    surf = pygame.Surface((10, 10), pygame.SRCALPHA)
    pygame.draw.circle(surf, (120, 255, 140), (5, 5), 4, 0)
    pygame.image.save(surf, path)


def make_laser_warn_png(path: str) -> None:
    import pygame
    surf = pygame.Surface((640, 480), pygame.SRCALPHA)
    pygame.draw.line(surf, (255, 200, 200), (0, 240), (640, 240), 1)
    pygame.image.save(surf, path)


def make_bg_starfield(path: str) -> None:
    import pygame
    surf = pygame.Surface((640, 480), pygame.SRCALPHA)
    # 远景星点
    for i in range(80):
        import random
        random.seed(i + 100)
        x = random.randint(0, 639); y = random.randint(0, 479)
        pygame.draw.circle(surf, (60, 60, 80), (x, y), 1)
    # 近景星点
    for i in range(40):
        import random
        random.seed(i + 200)
        x = random.randint(0, 639); y = random.randint(0, 479)
        pygame.draw.circle(surf, (200, 220, 240), (x, y), 2)
    pygame.image.save(surf, path)


def _write_wav(path: str, samples: list[int], rate: int = 22050) -> None:
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        for s in samples:
            w.writeframes(struct.pack("<h", max(-32767, min(32767, s))))


def make_tone_wav(path: str, freq: float, duration: float,
                  vol: float = 0.3, decay: bool = True,
                  rate: int = 22050) -> None:
    n = int(rate * duration)
    samples = []
    for i in range(n):
        t = i / rate
        env = math.exp(-3 * t / duration) if decay else 1.0
        s = int(vol * env * 32767 * math.sin(2 * math.pi * freq * t))
        samples.append(s)
    _write_wav(path, samples, rate)


def make_shoot_wav(path: str) -> None:
    # 短促高频: 880Hz 下降 0.1s
    make_tone_wav(path, 880.0, 0.08, vol=0.25)


def make_hit_wav(path: str) -> None:
    make_tone_wav(path, 220.0, 0.12, vol=0.4)


def make_graze_wav(path: str) -> None:
    make_tone_wav(path, 1320.0, 0.05, vol=0.18)


def make_bomb_wav(path: str) -> None:
    # 滑音: 200Hz → 80Hz, 0.4s
    n = int(22050 * 0.4)
    samples = []
    for i in range(n):
        t = i / 22050
        u = t / 0.4
        f = 200.0 - 120.0 * u
        env = math.exp(-2 * u)
        s = int(0.5 * env * 32767 * math.sin(2 * math.pi * f * t))
        samples.append(s)
    _write_wav(path, samples)


def make_death_wav(path: str) -> None:
    make_tone_wav(path, 110.0, 0.6, vol=0.5, decay=True)


def make_card_announce_wav(path: str) -> None:
    # 上行音阶: 440 → 880 → 1320, 0.6s
    n = int(22050 * 0.6)
    samples = []
    freqs = [440.0, 660.0, 880.0, 1320.0]
    for i in range(n):
        t = i / 22050
        seg = int(t / 0.15) % 4
        f = freqs[seg]
        env = math.exp(-3 * (t % 0.15) / 0.15)
        s = int(0.4 * env * 32767 * math.sin(2 * math.pi * f * t))
        samples.append(s)
    _write_wav(path, samples)


def make_item_wav(path: str) -> None:
    make_tone_wav(path, 1100.0, 0.06, vol=0.2)


def main() -> None:
    root = _project_root()
    chars = os.path.join(root, "assets", "chars")
    boss = os.path.join(root, "assets", "boss")
    bg = os.path.join(root, "assets", "bg")
    sfx = os.path.join(root, "assets", "sfx")
    for d in (chars, boss, bg, sfx):
        _ensure_dir(d)

    print("Generating PNG images...")
    make_player_png(os.path.join(chars, "player.png"))
    make_enemy_png(os.path.join(chars, "enemy.png"))
    make_item_png(os.path.join(chars, "item.png"))
    make_bullet_png(os.path.join(chars, "bullet.png"))
    make_laser_warn_png(os.path.join(chars, "laser_warn.png"))
    make_boss_png(os.path.join(boss, "boss.png"))
    make_bg_starfield(os.path.join(bg, "starfield.png"))
    print("  OK")

    print("Generating WAV sounds...")
    make_shoot_wav(os.path.join(sfx, "shoot.wav"))
    make_hit_wav(os.path.join(sfx, "hit.wav"))
    make_graze_wav(os.path.join(sfx, "graze.wav"))
    make_bomb_wav(os.path.join(sfx, "bomb.wav"))
    make_death_wav(os.path.join(sfx, "death.wav"))
    make_card_announce_wav(os.path.join(sfx, "card_announce.wav"))
    make_item_wav(os.path.join(sfx, "item.wav"))
    print("  OK")
    print("Done. Assets regenerated.")


if __name__ == "__main__":
    main()