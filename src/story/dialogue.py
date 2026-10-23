# -*- coding: utf-8 -*-
"""story/dialogue.py — 对话推进状态机 (纯逻辑, 不碰 pygame)

打字机效果在这里做: 每帧按 CHARS_PER_SEC 增加 reveal 进度,
渲染层只负责把 text_visible() 画出来。

用法:
    ctrl = DialogueController()
    ctrl.start(lines)                 # 进入
    ctrl.update(dt)                   # 每帧
    ctrl.advance()                    # 玩家按确认: 未打完 -> 立刻打完; 打完了 -> 下一句
    ctrl.skip_line()                  # 立刻打完当前句
    ctrl.skip_all()                   # 全部跳过, finished=True
    if ctrl.finished: ...             # 结束回调
"""
from __future__ import annotations

from src.story.model import Line

# 每秒显示字数 (中文 28 字/秒 大约 3.5 秒一句话, 阅读节奏舒适)
CHARS_PER_SEC = 34.0
# 标点额外停顿 (秒) — 只在打字机推进时用, 不影响最终长度
_PAUSE_CHARS = "，。！？、…—"


class DialogueController:
    __slots__ = ("lines", "index", "reveal", "finished", "_t")

    def __init__(self) -> None:
        self.lines: list[Line] = []
        self.index = 0
        self.reveal = 0.0
        self.finished = True
        self._t = 0.0

    # ---------------- 生命周期 ----------------
    def start(self, lines: list[Line]) -> None:
        self.lines = list(lines or [])
        self.index = 0
        self.reveal = 0.0
        self._t = 0.0
        self.finished = not self.lines

    @property
    def active(self) -> bool:
        return not self.finished and bool(self.lines)

    # ---------------- 每帧 ----------------
    def update(self, dt: float) -> None:
        if self.finished:
            return
        self._t += dt
        line = self.current
        if line is None:
            self.finished = True
            return
        if self.reveal < len(line.text):
            self.reveal = min(float(len(line.text)), self.reveal + CHARS_PER_SEC * dt)

    # ---------------- 查询 ----------------
    @property
    def current(self) -> Line | None:
        if 0 <= self.index < len(self.lines):
            return self.lines[self.index]
        return None

    @property
    def current_speaker(self) -> str | None:
        line = self.current
        return line.speaker if line else None

    def text_visible(self) -> str:
        line = self.current
        if line is None:
            return ""
        return line.text[: int(self.reveal)]

    def text_full(self) -> str:
        line = self.current
        return line.text if line else ""

    def line_complete(self) -> bool:
        line = self.current
        return line is not None and self.reveal >= len(line.text)

    @property
    def progress(self) -> tuple[int, int]:
        return (min(self.index + 1, len(self.lines)), len(self.lines))

    # ---------------- 玩家输入 ----------------
    def advance(self) -> bool:
        """确认键。返回 True 表示还有后续 (仍在对话中)。"""
        if self.finished:
            return False
        if not self.line_complete():
            self.reveal = float(len(self.text_full()))
            return True
        if self.index + 1 >= len(self.lines):
            self.finished = True
            return False
        self.index += 1
        self.reveal = 0.0
        return True

    def skip_line(self) -> None:
        if not self.finished:
            self.reveal = float(len(self.text_full()))

    def skip_all(self) -> None:
        self.finished = True
        self.index = len(self.lines)
        self.reveal = 0.0
