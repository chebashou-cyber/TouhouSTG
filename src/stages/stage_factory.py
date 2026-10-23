# -*- coding: utf-8 -*-
"""stage_factory.py — 关卡工厂

关卡表 (stage_id -> JSON 文件):
  0        教学关
  1..6     剧情模式六章 (ch1..ch6), 也可以单关练习
  7        EX 章「星之残响」, 通关本篇后解锁
  8..10    EX 追加关 (旧版的 stage2 / stage4 / stage5)

make_stage(stage_id) -> Stage
"""
from __future__ import annotations
import os

from src.stages.stage1 import Stage1
from src.stages.loader import load_stage, build_waves, build_bosses

# stage_id -> 文件名 (不含 .json)
STAGE_FILE_MAP = {
    0: "stage0",   # 教学
    1: "ch1",      # 一章 夜雀之森
    2: "ch2",      # 二章 雾湖冰晶
    3: "ch3",      # 三章 迷途竹林
    4: "ch4",      # 四章 星之书库
    5: "ch5",      # 五章 机关天守
    6: "ch6",      # 终章 星之器
    7: "ch7",      # EX 章 星之残响
    8: "stage2",   # EX 弹幕风暴
    9: "stage4",   # EX 中阶
    10: "stage5",  # EX 高难
}

# 关卡显示名 (菜单 / Stage Clear / 结算用)
STAGE_LABELS = {
    0: "序 · 教程",
    1: "一章 · 夜雀之森",
    2: "二章 · 雾湖冰晶",
    3: "三章 · 迷途竹林",
    4: "四章 · 星之书库",
    5: "五章 · 机关天守",
    6: "终章 · 星之器",
    7: "EX · 星之残响",
    8: "EX1 · 弹幕风暴",
    9: "EX2 · 中阶",
    10: "EX3 · 高难",
}

MAX_STAGE = max(STAGE_FILE_MAP)

# 剧情模式章节 (stage_id 顺序即章节顺序)
CAMPAIGN_STAGES = (1, 2, 3, 4, 5, 6)

# EX 章 (通关本篇后解锁) 的 stage_id
EX_STAGE_ID = 7


def _stage_json_path(stage_id: int) -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    name = STAGE_FILE_MAP.get(stage_id, f"stage{stage_id}")
    return os.path.join(base, "assets", "stages", f"{name}.json")


def stage_label(stage_id: int) -> str:
    return STAGE_LABELS.get(stage_id, f"STAGE {stage_id}")


class Stage:
    """通用 Stage: 持有 waves / boss spawn 时间表。"""

    __slots__ = ("name", "_waves", "_wave_index", "_elapsed", "finished",
                 "_pending_boss_spawn", "_data_path")

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
        data = load_stage(self._data_path) if self._data_path else None
        if data is None:
            return
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
        # fallback: 用第一教学关
        path = _stage_json_path(1)
    data = load_stage(path)
    return Stage(
        name=data.get("name", f"Stage {stage_id}"),
        waves=build_waves(data),
        pending_boss_spawn=build_bosses(data),
        data_path=path,
    )


# 保留 Stage1 作为向后兼容
__all__ = ["Stage", "make_stage", "Stage1", "STAGE_FILE_MAP", "STAGE_LABELS",
           "MAX_STAGE", "CAMPAIGN_STAGES", "stage_label"]
