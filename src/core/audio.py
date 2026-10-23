# -*- coding: utf-8 -*-
"""core/audio.py — 程序化音效

为什么不用音频文件:
  assets/sfx/ 是空的, 项目也没有发布音频资源的打算。用代码合成 PCM
  就能有射击/命中/擦弹/炸弹/死亡/符卡的全部反馈, 不需要任何外部文件,
  也不会撑大仓库。

实现要点:
  - 取样参数跟 pygame.mixer.get_init() 保持一致 (通常是 44100Hz / 16bit / 单声道),
    直接把 array('h') 的裸缓冲塞进 pygame.mixer.Sound(buffer=...)。
  - 音色是「正弦扫频 + 指数包络」, 爆炸类加白噪。全部惰性生成并缓存。
  - 同类音效有最小间隔 (射击每秒最多 12 次), 否则 200 发/秒会把混音器打满。
  - 混音器不可用时 (无声卡 / 服务端环境) 静默降级为 no-op, 绝不影响游戏。
"""
from __future__ import annotations

import array
import math
import random

import pygame

# 允许同时播放的音源数
_CHANNELS = 16
# 主音量 (0~1); 单独音效的音量在下面 _RECIPES 里
MASTER_VOLUME = 0.45


class Audio:
    __slots__ = ("enabled", "muted", "_rate", "_fmt", "_channels",
                 "_sounds", "_last", "_rng", "_num_channels")

    def __init__(self) -> None:
        self.enabled = False
        self.muted = False
        self._rate = 44100
        self._fmt = -16
        self._channels = 1
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._last: dict[str, int] = {}
        self._rng = random.Random(20261023)
        self._num_channels = _CHANNELS
        self._init()

    # ---------------- 初始化 ----------------
    def _init(self) -> None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            info = pygame.mixer.get_init()
            if not info:
                return
            self._rate, self._fmt, self._channels = info
            pygame.mixer.set_num_channels(_CHANNELS)
            self.enabled = True
        except (pygame.error, AttributeError, OSError):
            self.enabled = False

    # ---------------- 对外 ----------------
    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted

    def play(self, name: str) -> None:
        if not self.enabled or self.muted:
            return
        snd = self._sounds.get(name)
        if snd is None:
            snd = self._build(name)
            if snd is None:
                return
            self._sounds[name] = snd
        # 同类音效节流
        gap = _MIN_GAP.get(name, 0.0)
        now = pygame.time.get_ticks()
        if gap > 0.0 and now - self._last.get(name, -10 ** 9) < gap * 1000:
            return
        self._last[name] = now
        try:
            snd.play()
        except pygame.error:
            self.enabled = False

    # ---------------- 合成 ----------------
    def _build(self, name: str) -> pygame.mixer.Sound | None:
        spec = _RECIPES.get(name)
        if spec is None:
            return None
        kind = spec["kind"]
        if kind == "sweep":
            buf = self._sweep(spec["f0"], spec["f1"], spec["dur"],
                              spec["vol"], spec["decay"], spec.get("square", False))
        elif kind == "noise":
            buf = self._noise(spec["dur"], spec["vol"], spec["decay"])
        elif kind == "arp":
            buf = self._arp(spec["notes"], spec["step"], spec["vol"], spec["decay"])
        else:
            return None
        try:
            snd = pygame.mixer.Sound(buffer=buf.tobytes())
        except (pygame.error, TypeError, ValueError):
            return None
        snd.set_volume(spec.get("gain", 1.0) * MASTER_VOLUME)
        return snd

    def _sweep(self, f0: float, f1: float, dur: float, vol: float,
               decay: float, square: bool) -> array.array:
        n = max(1, int(self._rate * dur))
        buf = array.array("h", bytes(2 * n))
        phase = 0.0
        for i in range(n):
            t = i / self._rate
            f = f0 + (f1 - f0) * (i / n)
            phase += 2.0 * math.pi * f / self._rate
            env = math.exp(-decay * t)
            s = math.sin(phase)
            if square:
                s = 1.0 if s >= 0.0 else -1.0
            v = s * vol * env
            buf[i] = int(max(-1.0, min(1.0, v)) * 32767)
        return buf

    def _noise(self, dur: float, vol: float, decay: float) -> array.array:
        n = max(1, int(self._rate * dur))
        buf = array.array("h", bytes(2 * n))
        low = 0.0
        for i in range(n):
            t = i / self._rate
            # 一阶低通, 让噪声偏「闷」而不是刺耳
            low = low * 0.72 + self._rng.uniform(-1.0, 1.0) * 0.28
            env = math.exp(-decay * t)
            buf[i] = int(max(-1.0, min(1.0, low * vol * env)) * 32767)
        return buf

    def _arp(self, notes: list, step: float, vol: float,
             decay: float) -> array.array:
        total = step * len(notes)
        n = max(1, int(self._rate * total))
        buf = array.array("h", bytes(2 * n))
        for idx, f in enumerate(notes):
            start = int(self._rate * step * idx)
            for i in range(start, n):
                t = (i - start) / self._rate
                if t > step * 1.6:
                    break
                env = math.exp(-decay * t)
                v = math.sin(2.0 * math.pi * f * t) * vol * env
                cur = buf[i] / 32767.0 + v
                buf[i] = int(max(-1.0, min(1.0, cur)) * 32767)
        return buf


# 每类音效的配方 (dur 秒, vol 相对值)
_RECIPES = {
    "shoot":    {"kind": "sweep", "f0": 900.0, "f1": 1350.0, "dur": 0.05,
                 "vol": 0.30, "decay": 40.0, "gain": 0.55},
    "hit":      {"kind": "noise", "dur": 0.03, "vol": 0.35, "decay": 90.0,
                 "gain": 0.45},
    "kill":     {"kind": "sweep", "f0": 320.0, "f1": 90.0, "dur": 0.13,
                 "vol": 0.55, "decay": 16.0, "gain": 0.7, "square": True},
    "graze":    {"kind": "sweep", "f0": 1600.0, "f1": 2100.0, "dur": 0.04,
                 "vol": 0.35, "decay": 60.0, "gain": 0.5},
    "bomb":     {"kind": "noise", "dur": 0.55, "vol": 0.75, "decay": 4.5,
                 "gain": 0.9},
    "death":    {"kind": "sweep", "f0": 420.0, "f1": 55.0, "dur": 0.45,
                 "vol": 0.70, "decay": 4.0, "gain": 0.9},
    "spell":    {"kind": "sweep", "f0": 520.0, "f1": 1040.0, "dur": 0.28,
                 "vol": 0.45, "decay": 2.6, "gain": 0.7},
    "select":   {"kind": "sweep", "f0": 660.0, "f1": 990.0, "dur": 0.09,
                 "vol": 0.45, "decay": 22.0, "gain": 0.65},
    "move":     {"kind": "sweep", "f0": 480.0, "f1": 520.0, "dur": 0.03,
                 "vol": 0.28, "decay": 60.0, "gain": 0.4},
    "clear":    {"kind": "arp", "notes": [523.25, 659.25, 783.99, 1046.5],
                 "step": 0.13, "vol": 0.45, "decay": 3.2, "gain": 0.8},
    "warn":     {"kind": "arp", "notes": [392.0, 311.13],
                 "step": 0.16, "vol": 0.40, "decay": 3.0, "gain": 0.6},
}

# 同类音效最小间隔 (秒)
_MIN_GAP = {
    "shoot": 0.075,
    "hit": 0.03,
    "kill": 0.03,
    "graze": 0.05,
    "move": 0.05,
}


# 全局单例: Game 与 UI 都能拿到同一个混音器
_default: Audio | None = None


def default_audio() -> Audio:
    global _default
    if _default is None:
        _default = Audio()
    return _default
