# -*- coding: utf-8 -*-
"""replay.py — 录像/回放系统

设计:
  录制:
    - 每帧记录 (t, held_set, pressed_set)
    - meta: {stage_id, difficulty, seed}
    - 输出格式: JSON 行 (NDJSON), 易于追加
  回放:
    - 按帧读取 events, 调用 input_manager.inject_state
    - Game 检测 is_replaying 时把输入改为注入
    - 重放期间所有随机行为用相同 seed
"""
from __future__ import annotations
import json
import os
from typing import IO


class ReplayRecorder:
    __slots__ = ("_fp", "_meta_written", "_t0", "_frame_count")

    def __init__(self, path: str, meta: dict) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._fp: IO[str] = open(path, "w", encoding="utf-8")
        self._meta_written = False
        self._t0 = 0.0
        self._frame_count = 0
        # meta 作为第一行
        self._fp.write(json.dumps({"_meta": True, **meta}, ensure_ascii=False) + "\n")
        self._meta_written = True

    def record_frame(self, t: float, held: set, pressed: set) -> None:
        """记录一帧输入快照。"""
        ev = {
            "t": round(t, 4),
            "h": sorted(list(held)),
            "p": sorted(list(pressed)),
        }
        self._fp.write(json.dumps(ev, ensure_ascii=False) + "\n")
        self._frame_count += 1

    def close(self) -> None:
        if self._fp and not self._fp.closed:
            self._fp.close()

    @property
    def frame_count(self) -> int:
        return self._frame_count


class ReplayPlayer:
    __slots__ = ("path", "meta", "events", "index")

    def __init__(self, path: str) -> None:
        self.path = path
        self.meta: dict = {}
        self.events: list[dict] = []
        self.index = 0
        self._load()

    def _load(self) -> None:
        with open(self.path, "r", encoding="utf-8") as f:
            first = json.loads(f.readline())
            if first.get("_meta"):
                self.meta = first
            else:
                self.meta = {}
                # 第一行是事件, 推入队列
                self.events.append(first)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                self.events.append(json.loads(line))

    def reset(self) -> None:
        self.index = 0

    def apply_until(self, t: float, input) -> bool:
        """把所有 t_event <= t 的事件灌入 input. 返回是否已到末尾。"""
        while self.index < len(self.events):
            ev = self.events[self.index]
            if ev["t"] > t:
                break
            input.inject_state(set(ev["h"]), set(ev["p"]))
            self.index += 1
        return self.index >= len(self.events)

    @property
    def duration(self) -> float:
        if not self.events:
            return 0.0
        return self.events[-1]["t"]

    @property
    def frame_count(self) -> int:
        return len(self.events)