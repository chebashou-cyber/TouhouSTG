# -*- coding: utf-8 -*-
"""tools/balance_check.py — 符卡可击破性检查

弹幕游戏里有一类隐蔽的设计错误: 某张符卡的 hp_threshold 需要打掉的伤害,
超过了玩家在 duration 秒内能打出的理论最大伤害。这种卡玩家永远只能「超时」,
拿不到 bonus, 但游戏不会报错, 手测也很难发现 (你会以为是自己打得慢)。

本脚本按玩家理论 DPS 逐张卡算「需求伤害 / 可用伤害」:

    需求伤害 = boss.hp * hp_threshold      (注意: 每张符卡开始时 HP 会回满)
    可用伤害 = DPS * duration

DPS 取值来自 config: 满火力时每次射击 3 发, 间隔 PLAYER_FIRE_INTERVAL。
普通敌人不受影响 (它们的 HP 另按难度缩放), 这里只看 Boss。

判定:
    ratio <= 0.85   舒适
    0.85 < ratio <= 1.0  紧张 (能破, 但基本不能有失误)
    ratio > 1.0     打不破 -> 判失败, 退出码 1

用法: python tools/balance_check.py [--verbose]
退出码: 0 全部可击破 / 1 有打不破的符卡
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import config  # noqa: E402
from src.stages.loader import load_stage, build_bosses  # noqa: E402
from src.stages.stage_factory import STAGE_FILE_MAP, STAGE_LABELS, _stage_json_path  # noqa: E402

# 满火力: 中间 1 发 + 左右各 1 发, 每发 1 点伤害
BULLETS_AT_FULL_POWER = 3
DPS = BULLETS_AT_FULL_POWER / config.PLAYER_FIRE_INTERVAL

COMFORT = 0.85


def main() -> int:
    verbose = "--verbose" in sys.argv
    rows = []
    failures = []

    for sid in sorted(STAGE_FILE_MAP):
        path = _stage_json_path(sid)
        if not os.path.isfile(path):
            continue
        data = load_stage(path)
        for t, boss in build_bosses(data):
            for idx, sc in enumerate(boss.spellcards):
                need = boss.hp * sc.hp_threshold
                avail = DPS * sc.duration
                ratio = need / avail if avail > 0 else 99.0
                tag = "OK" if ratio <= COMFORT else ("TIGHT" if ratio <= 1.0 else "IMPOSSIBLE")
                rows.append((sid, boss.label, idx + 1, sc.no, sc.name,
                             boss.hp, sc.duration, need, avail, ratio, tag))
                if tag == "IMPOSSIBLE":
                    failures.append(rows[-1])

    print(f"玩家理论 DPS = {DPS:.1f} (满火力 {BULLETS_AT_FULL_POWER} 发 / "
          f"{config.PLAYER_FIRE_INTERVAL}s)")
    print()
    header = f"{'st':>2} {'boss':<10} {'#':>2} {'no':<7} {'name':<24}" \
             f"{'hp':>5} {'dur':>5} {'need':>6} {'avail':>6} {'ratio':>6}  tag"
    print(header)
    print("-" * len(header))
    for r in rows:
        sid, label, idx, no, name, hp, dur, need, avail, ratio, tag = r
        if not verbose and tag == "OK":
            continue
        print(f"{sid:>2} {label[:10]:<10} {idx:>2} {no[:7]:<7} {name[:24]:<24}"
              f"{hp:>5} {dur:>5.0f} {need:>6.0f} {avail:>6.0f} {ratio:>6.2f}  {tag}")

    ok = sum(1 for r in rows if r[-1] == "OK")
    tight = sum(1 for r in rows if r[-1] == "TIGHT")
    bad = len(failures)
    print()
    print(f"共 {len(rows)} 张符卡: 舒适 {ok} / 紧张 {tight} / 打不破 {bad}")
    if not verbose and ok:
        print("(用 --verbose 看全部)")

    if failures:
        print()
        print("打不破的符卡 (需要下调 hp_threshold 或延长 duration):")
        for r in failures:
            print(f"  stage {r[0]} {r[1]} #{r[2]} {r[4]}: "
                  f"需要 {r[7]:.0f} 伤害, 只有 {r[8]:.0f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
