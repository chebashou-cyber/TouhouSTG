# -*- coding: utf-8 -*-
"""stages/loader.py — 关卡 JSON 加载器

数据格式 (JSON):
{
  "name": "Stage 1 - ...",
  "waves": [
    {
      "time": 0.5,
      "enemies": [
        {
          "x": -20, "y": 80, "hp": 20,
          "path": [[t0, x0, y0], [t1, x1, y1], ...],
          "emitters": [
            {"pattern": "aimed", "color": "red", "speed": 200, "count": 1,
             "period": 0.7}
          ],
          "score": 500
        }
      ]
    }
  ],
  "bosses": [
    {
      "time": 50,
      "x": 320, "y": -40, "hp": 400, "radius": 22, "label": "Mid Boss",
      "path": [[t0, x0, y0], ...],
      "score": 100000,
      "spellcards": [
        {
          "no": "Mid",
          "name": "...",
          "duration": 22,
          "hp_threshold": 0.4,
          "bonus_score": 200000,
          "emitters": [...]
        }
      ]
    }
  ]
}

支持 angle 字段用字符串: "PI", "PI/2", "PI/3", "PI/4", "PI/6", "2*PI"。
支持 pattern: aimed / fan / ring / spiral / scatter / delayed_aimed / delayed_fan / delayed_ring。
"""
from __future__ import annotations
import json
import math
from src.entities.enemy import Wave, Enemy, Emitter
from src.entities.boss import Boss
from src.patterns.spellcard import SpellCard
from src.patterns.aimed import Aimed
from src.patterns.fan import Fan
from src.patterns.ring import Ring
from src.patterns.spiral import Spiral
from src.patterns.scatter import Scatter
from src.patterns.delayed import DelayedAimed, DelayedFan, DelayedRing
from src.core.rng import RNG
from config import (
    ENEMY_DEFAULT_HP, ENEMY_DEFAULT_SCORE, ENEMY_HITBOX_RADIUS,
    BOSS_HITBOX_RADIUS, BOSS_SCORE,
    parse_angle,
)


def _make_pattern(spec: dict):
    """根据 spec["pattern"] 创建对应 Pattern 实例, 处理 split_* 与 rng_seed 等特殊字段。"""
    pname = spec.pop("pattern")
    rng_seed = spec.pop("rng_seed", None)
    # parse angle string (aimed is reserved for Pattern)
    for angle_key in (
        "base_angle",
        "angle_jitter",
        "arc",
    ):
        if angle_key in spec and isinstance(spec[angle_key], str):
            if angle_key == "base_angle" and spec[angle_key] == "aimed":
                continue
            spec[angle_key] = parse_angle(spec[angle_key])

    # Apply global speed scale to enemy bullets
    from config import BULLET_SPEED_GLOBAL_SCALE, PLAYER_BULLET_SPEED_SCALE
    if "speed" in spec and isinstance(spec["speed"], (int, float)):
        spec["speed"] *= BULLET_SPEED_GLOBAL_SCALE
    if "split_speed" in spec and isinstance(spec["split_speed"], (int, float)):
        spec["split_speed"] *= BULLET_SPEED_GLOBAL_SCALE
    # 处理散射 RNG
    if pname in ("scatter", "delayed_aimed", "delayed_fan", "delayed_ring"):
        if rng_seed is not None and "rng" not in spec:
            spec["rng"] = RNG(rng_seed)

    if pname == "aimed":
        return Aimed(**spec)
    if pname == "fan":
        return Fan(**spec)
    if pname == "ring":
        return Ring(**spec)
    if pname == "spiral":
        return Spiral(**spec)
    if pname == "scatter":
        return Scatter(**spec)
    if pname == "delayed_aimed":
        return DelayedAimed(**spec)
    if pname == "delayed_fan":
        return DelayedFan(**spec)
    if pname == "delayed_ring":
        return DelayedRing(**spec)
    raise ValueError(f"Unknown pattern: {pname}")


def _make_emitter(spec: dict) -> Emitter:
    pname = spec["pattern"]
    period = spec.get("period", 0.5)
    start_t = spec.get("start_t", 0.0)
    duration = spec.get("duration", -1.0)
    # 把非 Emitter 参数剥离, 剩余给 Pattern
    # 注意: pattern 不能从 spec 中剔除 (需要传给 _make_pattern 识别类型)
    pattern_spec = {k: v for k, v in spec.items()
                    if k not in ("period", "start_t", "duration")}
    pattern = _make_pattern(dict(pattern_spec))  # copy 防修改原 dict
    return Emitter(pattern, period=period, start_t=start_t, duration=duration)


def load_stage(path: str) -> dict:
    """读取 JSON 文件, 返回原始 dict (name / waves / bosses)。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_waves(data: dict) -> list[Wave]:
    """从 stage dict 中提取 waves 列表并转换为 Wave 实例。"""
    waves: list[Wave] = []
    for w in data.get("waves", []):
        enemies_specs = []
        for es in w.get("enemies", []):
            spec = dict(es)
            spec["emitters"] = [_make_emitter(dict(em)) for em in es.get("emitters", [])]
            enemies_specs.append(spec)
        waves.append(Wave(start_t=w["time"], enemies=enemies_specs))
    return waves


def build_bosses(data: dict) -> list[tuple[float, Boss]]:
    """从 stage dict 中提取 bosses, 返回 (spawn_time, Boss) 列表。"""
    out = []
    for bs in data.get("bosses", []):
        # path: list[[t, x, y]]
        path = [tuple(p) for p in bs.get("path", [])]
        # spellcards
        spellcards = []
        for sc in bs.get("spellcards", []):
            emitters = [_make_emitter(dict(em)) for em in sc.get("emitters", [])]
            spell = SpellCard(
                name=sc["name"],
                duration=sc.get("duration", 25.0),
                hp_threshold=sc.get("hp_threshold", 0.3),
                emitters=emitters,
                bonus_score=sc.get("bonus_score", 100000),
                no=sc.get("no", "1"),
            )
            spellcards.append(spell)
        boss = Boss(
            x=bs.get("x", 320),
            y=bs.get("y", -50),
            hp=bs.get("hp", 800),
            path=path,
            spellcards=spellcards,
            score=bs.get("score", BOSS_SCORE),
            radius=bs.get("radius", BOSS_HITBOX_RADIUS),
            label=bs.get("label", "Boss"),
        )
        out.append((bs["time"], boss))
    return out
