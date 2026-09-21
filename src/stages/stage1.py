# -*- coding: utf-8 -*-
"""stages/stage1.py — 从 JSON 加载的 Stage1

数据在 assets/stages/stage1.json。
Stage1 实例:
  - waves / bosses 通过 src.stages.loader.build_waves / build_bosses 构造
  - update() 接受 dt / enemies_out / boss_out / pool / player / difficulty
"""
from __future__ import annotations
import os
from src.entities.enemy import Wave
from src.entities.boss import Boss
from src.stages.loader import load_stage, build_waves, build_bosses


def _default_json_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "assets", "stages", "stage1.json")


class Stage1:
    def __init__(self, json_path: str | None = None) -> None:
        path = json_path or _default_json_path()
        data = load_stage(path)
        self.name = data.get("name", "Stage 1")
        self._waves: list[Wave] = build_waves(data)
        self._wave_index = 0
        self._elapsed = 0.0
        self.finished = False
        # Boss 出场时间表
        self._pending_boss_spawn: list[tuple[float, Boss]] = build_bosses(data)

    def reset(self) -> None:
        self._wave_index = 0
        self._elapsed = 0.0
        self.finished = False
        # 重新读 JSON 重建 (简单粗暴, 阶段时间不长)
        path = _default_json_path()
        data = load_stage(path)
        self._waves = build_waves(data)
        self._pending_boss_spawn = build_bosses(data)

    def update(self, dt: float, enemies_out: list, boss_out: list,
               pool, player, difficulty: int = 1) -> None:
        self._elapsed += dt
        # 普通波
        while (self._wave_index < len(self._waves)
               and self._elapsed >= self._waves[self._wave_index].start_t):
            w = self._waves[self._wave_index]
            for e in w.spawn(difficulty=difficulty):
                enemies_out.append(e)
            self._wave_index += 1
        if self._wave_index >= len(self._waves):
            self.finished = True
        # Boss
        still_pending = []
        for t, b in self._pending_boss_spawn:
            if self._elapsed >= t:
                boss_out.append(b)
            else:
                still_pending.append((t, b))
        self._pending_boss_spawn = still_pending