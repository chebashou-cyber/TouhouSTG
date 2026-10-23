# -*- coding: utf-8 -*-
"""input_manager.py — 输入封装 + 一次性按下 + 缓冲 + Replay 注入

提供:
  is_held(name)               当前帧按住
  was_pressed(name)           本帧是否首次按下
  consume_press(name)         取并清除一次性按下
  consume_in_window(name, n)  在最近 n 帧内的缓冲取出
  inject_state(held, pressed) 用于 Replay: 直接灌入按键状态
"""
from __future__ import annotations
import pygame


_PYGAME_KEYMAP = {
    pygame.K_UP: "up", pygame.K_DOWN: "down", pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
    pygame.K_w: "up", pygame.K_s: "down", pygame.K_a: "left", pygame.K_d: "right",
    pygame.K_LSHIFT: "shift", pygame.K_RSHIFT: "shift",
    pygame.K_z: "z", pygame.K_x: "x",
    pygame.K_F1: "f1", pygame.K_F2: "f2", pygame.K_F3: "f3", pygame.K_F4: "f4",
    pygame.K_p: "pause", pygame.K_ESCAPE: "escape",
    pygame.K_RETURN: "enter", pygame.K_SPACE: "space",
    pygame.K_m: "mute",
}


class InputManager:
    __slots__ = (
        "_held",
        "_pressed_this_frame",
        "_released_this_frame",
        "_buffer",
        "_injected",  # bool: 是否处于 replay 注入模式
    )

    def __init__(self) -> None:
        self._held: set[str] = set()
        self._pressed_this_frame: set[str] = set()
        self._released_this_frame: set[str] = set()
        self._buffer: list[tuple[str, int]] = []
        self._injected = False

    def update(self, events: list[pygame.event.Event]) -> None:
        """每帧调用: 把 pygame 事件翻译为语义按键 + 维护缓冲队列。"""
        if self._injected:
            # Replay 注入模式: 不读 pygame 事件, 仅老化缓冲
            return
        self._pressed_this_frame.clear()
        self._released_this_frame.clear()
        new_buf: list = []
        for name, age in self._buffer:
            if age + 1 < 12:
                new_buf.append((name, age + 1))
        self._buffer = new_buf

        for ev in events:
            if ev.type == pygame.KEYDOWN:
                name = _PYGAME_KEYMAP.get(ev.key)
                if name is None:
                    continue
                self._held.add(name)
                self._pressed_this_frame.add(name)
                self._buffer.append((name, 0))
            elif ev.type == pygame.KEYUP:
                name = _PYGAME_KEYMAP.get(ev.key)
                if name is None:
                    continue
                self._held.discard(name)
                self._released_this_frame.add(name)

    def inject_state(self, held: set, pressed: set) -> None:
        """Replay 注入: 直接覆盖按键状态 (绕开 pygame 事件)。"""
        self._held = set(held)
        self._pressed_this_frame = set(pressed)
        self._released_this_frame.clear()
        self._injected = True

    def exit_inject_mode(self) -> None:
        self._injected = False

    def is_held(self, name: str) -> bool:
        return name in self._held

    def was_pressed(self, name: str) -> bool:
        return name in self._pressed_this_frame

    def was_released(self, name: str) -> bool:
        return name in self._released_this_frame

    def consume_press(self, name: str) -> bool:
        if name in self._pressed_this_frame:
            self._pressed_this_frame.discard(name)
            return True
        return False

    def consume_in_window(self, name: str, window_frames: int = 6) -> bool:
        for i, (n, age) in enumerate(self._buffer):
            if n == name and age < window_frames:
                self._buffer.pop(i)
                return True
        return False

    def clear_pressed(self) -> None:
        """丢弃本帧所有「刚按下」状态。

        用于场景切换: 对话里按的 Z 不应漏到游戏里变成开火/放炸弹。
        """
        self._pressed_this_frame.clear()
        self._released_this_frame.clear()

    def buffer_size(self) -> int:
        return len(self._buffer)

    def axis(self) -> tuple[float, float]:
        x = (1 if self.is_held("right") else 0) - (1 if self.is_held("left") else 0)
        y = (1 if self.is_held("down") else 0) - (1 if self.is_held("up") else 0)
        if x == 0 and y == 0:
            return (0.0, 0.0)
        inv = 1.0 / (abs(x) + abs(y)) ** 0.5
        return (x * inv, y * inv)