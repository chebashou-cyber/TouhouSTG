# -*- coding: utf-8 -*-
"""stage_factory.py — 关卡工厂

make_stage(stage_id, json_path=None) -> Stage1 (或其他 stage 类)
"""
from __future__ import annotations
import os
from src.stages.stage1 import Stage1
from src.stages.loader import load_stage, build_waves, build_bosses


# stage_id -> file name mapping (intro stages use letter suffix to keep order)
STAGE_FILE_MAP = {
    0: "stage0",    # tutorial
    1: "stage_a",  # warm-up (easy)
    2: "stage_b",  # easy ring
    3: "stage_c",  # slow spiral
    4: "stage1",   # original 1 (medium)
    5: "stage2",
    6: "stage3",
    7: "stage4",
    8: "stage5",
    9: "stage6",
}


def _stage_json_path(stage_id: int) -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    name = STAGE_FILE_MAP.get(stage_id, f"stage{stage_id}")
    return os.path.join(base, "assets", "stages", f"{name}.json")


class Stage:
    """通用 Stage: 持有 waves / boss spawn 时间表。"""

    def __init__(self, name: str, waves, pending_boss_spawn, data_path: str = ""):
        self.name = name
        self._waves = waves
        self._wave_index = 0
        self._elapsed = 0.0
        self.finished = False
        self._pending_boss_spawn = pending_boss_spawn
        self._data_path = data_path

    def reset(self) -> None:
        self._wave_index = 0
        self._elapsed = 0.0
        self.finished = False
        # 重建
        data = load_stage(self._data_path) if self._data_path else None
        if data is None: return
        self._waves = build_waves(data)
        self._pending_boss_spawn = build_bosses(data)

    def update(self, dt: float, enemies_out: list, boss_out: list,
               pool, player, difficulty: int = 1) -> None:
        self._elapsed += dt
        while (self._wave_index < len(self._waves)
               and self._elapsed >= self._waves[self._wave_index].start_t):
            w = self._waves[self._wave_index]
            for e in w.spawn(difficulty=difficulty):
                enemies_out.append(e)
            self._wave_index += 1
        if self._wave_index >= len(self._waves):
            self.finished = True
        still_pending = []
        for t, b in self._pending_boss_spawn:
            if self._elapsed >= t:
                boss_out.append(b)
            else:
                still_pending.append((t, b))
        self._pending_boss_spawn = still_pending


def make_stage(stage_id: int) -> Stage:
    """按 stage_id 加载 JSON 并构造 Stage。"""
    path = _stage_json_path(stage_id)
    if not os.path.isfile(path):
        # fallback: 用 stage1
        path = _stage_json_path(1)
    data = load_stage(path)
    return Stage(
        name=data.get("name", f"Stage {stage_id}"),
        waves=build_waves(data),
        pending_boss_spawn=build_bosses(data),
    )


# 保留 Stage1 作为向后兼容
__all__ = ["Stage", "make_stage", "Stage1"]