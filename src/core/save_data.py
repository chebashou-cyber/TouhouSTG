# -*- coding: utf-8 -*-
"""core/save_data.py — 最高分存档 (save/records.json)

为什么单独做一份:
  项目原本分数只在内存里, 一关打完回标题就归零, 没有任何长期目标。
  这里记录每个难度的最高分与全通次数, 标题画面显示 BEST。

失败策略:
  存档目录不可写 / 文件损坏时静默降级为「内存里记一下」, 绝不让存档
  问题把游戏搞崩 (replay/ 目录在只读环境里也有同样风险)。
"""
from __future__ import annotations

import json
import os

from config import SAVE_DIR_NAME, SAVE_FILE_NAME, DIFFICULTY_NAMES


def _root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def save_path() -> str:
    return os.path.join(_root(), SAVE_DIR_NAME, SAVE_FILE_NAME)


class SaveData:
    __slots__ = ("best", "clears", "_path", "_dirty")

    def __init__(self) -> None:
        self.best: dict[str, int] = {}
        self.clears: dict[str, int] = {}
        self._path = save_path()
        self._dirty = False
        self.load()

    # ---------------- 读写 ----------------
    def load(self) -> None:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                best = data.get("best") or {}
                clears = data.get("clears") or {}
                for name in DIFFICULTY_NAMES:
                    self.best[name] = int(best.get(name, 0) or 0)
                    self.clears[name] = int(clears.get(name, 0) or 0)
        except (OSError, ValueError, TypeError):
            # 首次运行 / 文件损坏: 用空存档继续
            self.best = {n: 0 for n in DIFFICULTY_NAMES}
            self.clears = {n: 0 for n in DIFFICULTY_NAMES}

    def save(self) -> bool:
        if not self._dirty:
            return True
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            tmp = self._path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "best": self.best, "clears": self.clears},
                          f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._path)
            self._dirty = False
            return True
        except OSError:
            return False

    # ---------------- 业务 ----------------
    def _key(self, difficulty: int) -> str:
        if 0 <= difficulty < len(DIFFICULTY_NAMES):
            return DIFFICULTY_NAMES[difficulty]
        return DIFFICULTY_NAMES[0]

    def best_score(self, difficulty: int) -> int:
        return self.best.get(self._key(difficulty), 0)

    def submit(self, difficulty: int, score: int) -> bool:
        """提交一局分数; 返回是否刷新了最高分。"""
        name = self._key(difficulty)
        if score > self.best.get(name, 0):
            self.best[name] = int(score)
            self._dirty = True
            self.save()
            return True
        return False

    def add_clear(self, difficulty: int) -> None:
        name = self._key(difficulty)
        self.clears[name] = self.clears.get(name, 0) + 1
        self._dirty = True
        self.save()

    def clear_count(self, difficulty: int) -> int:
        return self.clears.get(self._key(difficulty), 0)
