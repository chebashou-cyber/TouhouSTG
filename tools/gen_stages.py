# -*- coding: utf-8 -*-
"""tools/gen_stages.py — 生成剧情模式六章关卡 JSON

为什么用脚本生成而不是手写 JSON:
  六个关卡里有大量同构编队 (横穿妖精、悬停环弹机、分裂弹机……),
  手写 JSON 既啰嗦又容易漏字段。这里用少量辅助函数描述编队,
  数值集中在本文件里, 调整平衡只改一处, 重跑即生成新 JSON。

用法:
    python tools/gen_stages.py            # 写入 assets/stages/ch1..ch6.json
    python tools/gen_stages.py --check    # 只校验生成结果, 不写文件

生成的 JSON 结构见 src/stages/loader.py 顶部说明。
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "stages")

SCREEN_W = 640

# ---------------------------------------------------------------- 基础构件
def enemy(x, y, hp, path, emitters, score):
    return {"x": x, "y": y, "hp": hp, "path": path,
            "emitters": emitters, "score": score}


def aimed(color, speed=200, count=1, spread=0.0, period=0.8, start_t=0.0):
    return {"pattern": "aimed", "color": color, "speed": speed, "count": count,
            "spread": spread, "period": period, "start_t": start_t}


def fan(color, speed=190, count=5, arc="PI/2", base_angle="aimed",
        period=0.7, start_t=0.0, rotate_speed=0.0):
    return {"pattern": "fan", "color": color, "speed": speed, "count": count,
            "arc": arc, "base_angle": base_angle, "rotate_speed": rotate_speed,
            "period": period, "start_t": start_t}


def ring(color, speed=180, count=16, base_angle=0.0, rotate_speed=0.0,
         period=0.6, start_t=0.0, speed_jitter=0.0):
    return {"pattern": "ring", "color": color, "speed": speed, "count": count,
            "base_angle": base_angle, "rotate_speed": rotate_speed,
            "speed_jitter": speed_jitter, "period": period, "start_t": start_t}


def spiral(color, speed=170, count=2, step_angle=0.18, arms=1, period=0.1,
           start_t=0.0):
    return {"pattern": "spiral", "color": color, "speed": speed, "count": count,
            "step_angle": step_angle, "arms": arms, "period": period,
            "start_t": start_t}


def scatter(color, speed=190, count=8, base_angle="PI/2", angle_jitter="PI/3",
            period=0.5, start_t=0.0, rng_seed=7):
    return {"pattern": "scatter", "color": color, "speed": speed, "count": count,
            "base_angle": base_angle, "angle_jitter": angle_jitter,
            "rng_seed": rng_seed, "period": period, "start_t": start_t}


def delayed_aimed(color, speed=240, count=1, split_at=0.7, split_count=4,
                  split_speed=150, period=0.5, start_t=0.0):
    return {"pattern": "delayed_aimed", "color": color, "speed": speed,
            "count": count, "split_at": split_at, "split_count": split_count,
            "split_speed": split_speed, "period": period, "start_t": start_t}


def delayed_fan(color, speed=230, count=9, arc="PI/3", base_angle="aimed",
                split_at=0.6, split_count=4, split_speed=160, period=0.6,
                start_t=0.0):
    return {"pattern": "delayed_fan", "color": color, "speed": speed,
            "count": count, "arc": arc, "base_angle": base_angle,
            "split_at": split_at, "split_count": split_count,
            "split_speed": split_speed, "period": period, "start_t": start_t}


def delayed_ring(color, speed=200, count=4, split_at=0.55, split_count=3,
                 split_speed=140, period=0.09, start_t=0.0):
    return {"pattern": "delayed_ring", "color": color, "speed": speed,
            "count": count, "split_at": split_at, "split_count": split_count,
            "split_speed": split_speed, "period": period, "start_t": start_t}


# ---------------------------------------------------------------- 编队
def sweep(x_from, y, x_to, hold=3.0, cross=1.8, hp=24, score=600,
          emitters=None, out_y=-70):
    """从一侧横穿到另一侧, 在 (x_to, y) 悬停 hold 秒, 然后飞离屏幕。"""
    path = [[0.0, x_from, y], [cross, x_to, y],
            [cross + hold, x_to, y], [cross + hold + 1.6, x_to, out_y]]
    return enemy(x_from, y, hp, path, emitters or [], score)


def drop_in(x, y_to, hp=40, score=900, emitters=None, hold=4.0, enter=1.8):
    """自屏幕上方进入并悬停在 (x, y_to)。"""
    path = [[0.0, x, -40], [enter, x, y_to],
            [enter + hold, x, y_to], [enter + hold + 1.8, x + 60, -70]]
    return enemy(x, -40, hp, path, emitters or [], score)


def vee(cx, y, hp=28, score=700, emitters=None, spread=140):
    """三机 V 字编队, 从上方切入左右两侧。"""
    out = []
    for k, dx in enumerate((0, -spread, spread)):
        x = cx + dx
        t = 1.6 + abs(k - 1) * 0.35
        path = [[0.0, x, -40], [t, x, y], [t + 3.0, x, y],
                [t + 4.4, x + (dx * 0.4), -70]]
        out.append(enemy(x, -40, hp, path, emitters or [], score))
    return out


def stream(n, x0, y0, x1, y1, t0, dt, hp=20, score=500, emitters=None):
    """等间隔放出 n 架直线通过的敌机 (排队机)。"""
    out = []
    for i in range(n):
        t = t0 + i * dt
        path = [[0.0, x0, y0], [1.8, x1, y1], [4.2, x1, y1],
                [5.6, x1 + (x1 - SCREEN_W / 2) * 0.5, -70]]
        out.append(enemy(x0, y0, hp, path, emitters or [], score + i * 10))
    return out


def spells(*items):
    out = []
    for i, sc in enumerate(items):
        out.append(sc)
    return out


def spell(no, name, duration, threshold, bonus, emitters):
    return {"no": no, "name": name, "duration": duration,
            "hp_threshold": threshold, "bonus_score": bonus,
            "emitters": emitters}


def boss(t, x, y, hp, label, radius, path, score, spellcards):
    return {"time": t, "x": x, "y": y, "hp": hp, "radius": radius,
            "label": label, "path": path, "score": score,
            "spellcards": spellcards}


def boss_path(hover_y=130, enter=2.0):
    return [[0.0, SCREEN_W // 2, -50], [enter, SCREEN_W // 2, hover_y],
            [enter + 12.0, SCREEN_W // 2, hover_y]]


# ---------------------------------------------------------------- 第一章
def stage_ch1():
    waves = [
        {"time": 1.5, "enemies": [
            sweep(-30, 90, 140, hold=2.6, emitters=[aimed("red", 200, period=0.9)]),
            sweep(-40, 150, 150, hold=2.6, emitters=[aimed("red", 200, period=0.9)]),
            sweep(-50, 210, 160, hold=2.6, emitters=[aimed("red", 200, period=0.9)]),
        ]},
        {"time": 8.0, "enemies": [
            sweep(670, 100, 500, hold=2.6, emitters=[aimed("blue", 200, period=0.9)]),
            sweep(680, 160, 490, hold=2.6, emitters=[aimed("blue", 200, period=0.9)]),
            sweep(690, 220, 480, hold=2.6, emitters=[aimed("blue", 200, period=0.9)]),
        ]},
        {"time": 15.0, "enemies": vee(320, 120, hp=60, score=1600,
                                      emitters=[fan("purple", 180, 5, "PI/2", "aimed", 0.55)])},
        {"time": 23.0, "enemies": [
            drop_in(320, 130, hp=120, score=3200,
                    emitters=[ring("green", 170, 16, rotate_speed=0.5, period=0.75)],
                    hold=5.0),
        ]},
        {"time": 32.0, "enemies": [
            sweep(160, 100, 260, hold=3.0, hp=40, score=1200,
                  emitters=[scatter("yellow", 180, 6, "PI/2", "PI/3", 0.45, rng_seed=3)]),
            sweep(480, 140, 380, hold=3.0, hp=40, score=1200,
                  emitters=[scatter("yellow", 180, 6, "PI/2", "PI/3", 0.45, rng_seed=5)]),
        ]},
        {"time": 40.0, "enemies": [
            sweep(-30, 120, 90, hold=5.0, hp=90, score=2200,
                  emitters=[spiral("red", 160, 2, 0.2, period=0.12)]),
            sweep(670, 180, 550, hold=5.0, hp=90, score=2200,
                  emitters=[spiral("red", 160, 2, -0.2, period=0.12)]),
        ]},
    ]
    bosses = [
        boss(52, 320, -40, 380, "Mid", 22, boss_path(110, 1.6), 100000, spells(
            spell("Mid", "夜符「小夜啼鸟」", 20, 0.4, 150000, [
                aimed("purple", 230, 3, 0.10, period=0.42),
                ring("blue", 160, 12, rotate_speed=0.35, period=0.9),
            ]),
        )),
        boss(76, 320, -50, 750, "Boss", 30, boss_path(130, 2.0), 200000, spells(
            spell("1", "夜符「暮色三羽」", 24, 0.35, 250000, [
                fan("blue", 200, 7, "PI/2", "aimed", 0.45),
                delayed_aimed("purple", 240, 1, 0.7, 3, 140, period=0.55),
            ]),
            spell("2", "暗符「无月之夜」", 26, 0.45, 450000, [
                ring("red", 190, 22, rotate_speed=0.55, period=0.55),
                ring("yellow", 160, 22, base_angle="PI/22", rotate_speed=-0.4,
                     period=0.55, start_t=0.28),
            ]),
        )),
    ]
    return {"name": "一章 · 夜雀之森", "waves": waves, "bosses": bosses}


# ---------------------------------------------------------------- 第二章
def stage_ch2():
    waves = [
        {"time": 1.5, "enemies": [
            sweep(-30, 110, 180, hold=3.0, emitters=[fan("blue", 190, 5, "PI/3", "aimed", 0.6)]),
            sweep(670, 110, 460, hold=3.0, emitters=[fan("blue", 190, 5, "PI/3", "aimed", 0.6)]),
        ]},
        {"time": 9.0, "enemies": stream(4, 240, -30, 240, 150, 0.0, 0.9, hp=30, score=800,
                                        emitters=[aimed("green", 210, 1, period=0.85)])},
        {"time": 17.0, "enemies": [
            drop_in(200, 120, hp=110, score=3000,
                    emitters=[delayed_aimed("purple", 250, 1, 0.75, 4, 150, period=0.5)],
                    hold=5.0),
            drop_in(440, 120, hp=110, score=3000,
                    emitters=[delayed_aimed("purple", 250, 1, 0.75, 4, 150, period=0.5)],
                    hold=5.0),
        ]},
        {"time": 26.0, "enemies": [
            drop_in(320, 120, hp=150, score=4200, hold=6.0,
                    emitters=[ring("blue", 180, 20, rotate_speed=0.4, period=0.7),
                              ring("blue", 150, 20, base_angle="PI/20",
                                   rotate_speed=-0.35, period=0.7, start_t=0.35)]),
        ]},
        {"time": 36.0, "enemies": [
            sweep(-30, 130, 120, hold=4.0, hp=70, score=1800,
                  emitters=[spiral("green", 170, 3, 0.22, period=0.1)]),
            sweep(670, 170, 520, hold=4.0, hp=70, score=1800,
                  emitters=[spiral("green", 170, 3, -0.22, period=0.1)]),
        ]},
        {"time": 45.0, "enemies": [
            sweep(-30, 100, 160, hold=3.0, hp=80, score=2000,
                  emitters=[delayed_fan("blue", 220, 7, "PI/3", "aimed",
                                        split_at=0.6, split_count=3, split_speed=150, period=0.7)]),
            sweep(670, 200, 480, hold=3.0, hp=80, score=2000,
                  emitters=[delayed_fan("blue", 220, 7, "PI/3", "aimed",
                                        split_at=0.6, split_count=3, split_speed=150, period=0.7)]),
        ]},
    ]
    bosses = [
        boss(56, 320, -40, 450, "Mid", 24, boss_path(115, 1.6), 120000, spells(
            spell("Mid", "冰符「霜之环」", 22, 0.4, 180000, [
                ring("blue", 190, 18, rotate_speed=0.6, period=0.6),
                aimed("purple", 240, 1, period=0.5),
            ]),
        )),
        boss(82, 320, -50, 900, "Boss", 30, boss_path(132, 2.0), 220000, spells(
            spell("1", "冰符「结晶十字」", 24, 0.32, 280000, [
                fan("blue", 210, 9, "PI/2", "aimed", 0.4),
                delayed_ring("purple", 200, 3, 0.55, 3, 140, period=0.11),
            ]),
            spell("2", "冻符「永冬之湖」", 26, 0.4, 480000, [
                ring("blue", 170, 26, rotate_speed=0.3, period=0.65),
                ring("purple", 200, 13, base_angle="PI/13", rotate_speed=-0.5,
                     period=0.65, start_t=0.32),
            ]),
            spell("Final", "冰奥「绝不融化的星空」", 28, 0.5, 750000, [
                delayed_ring("blue", 190, 6, 0.6, 4, 150, period=0.12),
                fan("purple", 230, 11, "PI/3", "aimed", 0.5),
            ]),
        )),
    ]
    return {"name": "二章 · 雾湖冰晶", "waves": waves, "bosses": bosses}


# ---------------------------------------------------------------- 第三章
def stage_ch3():
    waves = [
        {"time": 1.5, "enemies": [
            sweep(-30, 100, 150, hold=2.4, hp=34, score=800,
                  emitters=[aimed("green", 230, 2, 0.08, period=0.8)]),
            sweep(670, 160, 490, hold=2.4, hp=34, score=800,
                  emitters=[aimed("green", 230, 2, 0.08, period=0.8)]),
        ]},
        {"time": 8.0, "enemies": vee(200, 110, hp=70, score=1700,
                                      emitters=[fan("yellow", 200, 7, "PI/2", "aimed", 0.5)])},
        {"time": 15.0, "enemies": vee(440, 110, hp=70, score=1700,
                                      emitters=[fan("yellow", 200, 7, "PI/2", "aimed", 0.5)])},
        {"time": 22.0, "enemies": [
            drop_in(320, 110, hp=170, score=4600, hold=6.5,
                    emitters=[spiral("green", 180, 4, 0.16, arms=2, period=0.09),
                              aimed("red", 240, 1, period=0.6, start_t=0.4)]),
        ]},
        {"time": 32.0, "enemies": stream(5, 520, -30, 200, 160, 0.0, 0.7, hp=28, score=900,
                                         emitters=[scatter("purple", 190, 5, "PI/2",
                                                           "PI/4", 0.5, rng_seed=11)])},
        {"time": 40.0, "enemies": [
            sweep(-30, 120, 140, hold=4.0, hp=95, score=2400,
                  emitters=[delayed_aimed("yellow", 260, 2, 0.8, 4, 160, period=0.55)]),
            sweep(670, 180, 500, hold=4.0, hp=95, score=2400,
                  emitters=[delayed_aimed("yellow", 260, 2, 0.8, 4, 160, period=0.55)]),
        ]},
        {"time": 49.0, "enemies": [
            drop_in(240, 140, hp=130, score=3600, hold=5.0,
                    emitters=[ring("green", 190, 14, rotate_speed=0.7, period=0.5)]),
            drop_in(400, 140, hp=130, score=3600, hold=5.0,
                    emitters=[ring("green", 190, 14, rotate_speed=-0.7, period=0.5)]),
        ]},
    ]
    bosses = [
        boss(58, 320, -40, 520, "Mid", 24, boss_path(118, 1.6), 140000, spells(
            spell("Mid", "弓符「穿林之矢」", 22, 0.4, 200000, [
                aimed("green", 270, 3, 0.07, period=0.38),
                fan("yellow", 200, 5, "PI/4", "aimed", 0.55),
            ]),
        )),
        boss(86, 320, -50, 1050, "Boss", 30, boss_path(134, 2.0), 240000, spells(
            spell("1", "竹符「千本贯月」", 24, 0.3, 300000, [
                aimed("green", 300, 1, period=0.22),
                aimed("green", 300, 1, period=0.22, start_t=0.11),
                fan("yellow", 210, 7, "PI/3", "aimed", 0.55),
            ]),
            spell("2", "迷符「回不去的路」", 26, 0.38, 500000, [
                ring("purple", 180, 24, rotate_speed=0.25, period=0.6),
                spiral("green", 200, 2, 0.3, arms=2, period=0.09),
            ]),
            spell("Final", "守符「不退让的月」", 28, 0.5, 800000, [
                delayed_fan("yellow", 240, 11, "PI/3", "aimed", 0.55, 4, 170, period=0.55),
                aimed("red", 280, 2, 0.06, period=0.3),
            ]),
        )),
    ]
    return {"name": "三章 · 迷途竹林", "waves": waves, "bosses": bosses}


# ---------------------------------------------------------------- 第四章
def stage_ch4():
    waves = [
        {"time": 1.5, "enemies": [
            sweep(-30, 90, 160, hold=2.6, hp=40, score=1000,
                  emitters=[fan("purple", 200, 5, "PI/3", "aimed", 0.55)]),
            sweep(670, 150, 480, hold=2.6, hp=40, score=1000,
                  emitters=[fan("purple", 200, 5, "PI/3", "aimed", 0.55)]),
        ]},
        {"time": 9.0, "enemies": [
            drop_in(240, 120, hp=120, score=3200, hold=5.0,
                    emitters=[delayed_ring("blue", 200, 4, 0.55, 3, 150, period=0.12)]),
            drop_in(400, 120, hp=120, score=3200, hold=5.0,
                    emitters=[delayed_ring("blue", 200, 4, 0.55, 3, 150, period=0.12)]),
        ]},
        {"time": 18.0, "enemies": [
            drop_in(320, 130, hp=190, score=5000, hold=7.0,
                    emitters=[ring("purple", 190, 24, rotate_speed=0.45, period=0.62),
                              fan("blue", 210, 9, "PI/2", "aimed", 0.62, start_t=0.3)]),
        ]},
        {"time": 29.0, "enemies": stream(6, -30, 110, 670, 110, 0.0, 0.55, hp=32, score=900,
                                         emitters=[aimed("yellow", 240, 1, period=0.7)])},
        {"time": 38.0, "enemies": [
            sweep(-30, 130, 130, hold=4.0, hp=100, score=2600,
                  emitters=[spiral("green", 180, 3, 0.24, arms=2, period=0.1)]),
            sweep(670, 190, 510, hold=4.0, hp=100, score=2600,
                  emitters=[spiral("green", 180, 3, -0.24, arms=2, period=0.1)]),
        ]},
        {"time": 47.0, "enemies": vee(200, 120, hp=90, score=2200,
                                      emitters=[delayed_aimed("purple", 250, 2, 0.7, 4, 160,
                                                              period=0.6)]),
         },
        {"time": 47.0, "enemies": vee(440, 120, hp=90, score=2200,
                                      emitters=[delayed_aimed("purple", 250, 2, 0.7, 4, 160,
                                                              period=0.6)])},
    ]
    bosses = [
        boss(60, 320, -40, 600, "Mid", 24, boss_path(120, 1.6), 160000, spells(
            spell("Mid", "书符「读不完的注」", 22, 0.4, 220000, [
                ring("purple", 195, 18, rotate_speed=0.65, period=0.55),
                aimed("blue", 260, 2, 0.07, period=0.45),
            ]),
        )),
        boss(90, 320, -50, 1250, "Boss", 30, boss_path(136, 2.0), 260000, spells(
            spell("1", "记录「一页一世界」", 25, 0.3, 320000, [
                fan("purple", 220, 11, "PI/2", "aimed", 0.45),
                delayed_ring("blue", 190, 5, 0.6, 4, 150, period=0.13),
            ]),
            spell("2", "烧符「焚册之火」", 26, 0.38, 520000, [
                ring("red", 200, 20, rotate_speed=0.35, period=0.5),
                spiral("yellow", 190, 2, -0.28, arms=3, period=0.09),
            ]),
            spell("Final", "星符「借来的那本书」", 30, 0.5, 900000, [
                delayed_fan("purple", 240, 13, "PI/2", "aimed", 0.55, 4, 170, period=0.5),
                ring("blue", 170, 30, rotate_speed=0.2, period=0.6),
            ]),
        )),
    ]
    return {"name": "四章 · 星之书库", "waves": waves, "bosses": bosses}


# ---------------------------------------------------------------- 第五章
def stage_ch5():
    waves = [
        {"time": 1.5, "enemies": [
            sweep(-30, 90, 150, hold=2.6, hp=46, score=1200,
                  emitters=[aimed("blue", 250, 2, 0.06, period=0.7)]),
            sweep(-40, 160, 170, hold=2.6, hp=46, score=1200,
                  emitters=[ring("blue", 170, 12, rotate_speed=0.5, period=0.6)]),
            sweep(670, 230, 470, hold=2.6, hp=46, score=1200,
                  emitters=[aimed("blue", 250, 2, 0.06, period=0.7)]),
        ]},
        {"time": 10.0, "enemies": [
            drop_in(200, 120, hp=140, score=3600, hold=5.5,
                    emitters=[spiral("red", 185, 4, 0.2, arms=2, period=0.09)]),
            drop_in(440, 120, hp=140, score=3600, hold=5.5,
                    emitters=[spiral("red", 185, 4, -0.2, arms=2, period=0.09)]),
        ]},
        {"time": 20.0, "enemies": vee(320, 110, hp=110, score=2600,
                                      emitters=[delayed_fan("yellow", 235, 9, "PI/2", "aimed",
                                                            0.6, 4, 165, period=0.55)])},
        {"time": 29.0, "enemies": [
            drop_in(320, 120, hp=230, score=6000, hold=8.0,
                    emitters=[ring("red", 200, 28, rotate_speed=0.5, period=0.6),
                              ring("blue", 170, 28, base_angle="PI/28",
                                   rotate_speed=-0.42, period=0.6, start_t=0.3)]),
        ]},
        {"time": 40.0, "enemies": stream(6, 670, 90, -30, 150, 0.0, 0.6, hp=36, score=1100,
                                         emitters=[fan("purple", 210, 5, "PI/3", "aimed", 0.5)])},
        {"time": 49.0, "enemies": [
            sweep(-30, 110, 120, hold=4.5, hp=120, score=3000,
                  emitters=[delayed_aimed("red", 270, 3, 0.75, 4, 170, period=0.5)]),
            sweep(670, 200, 520, hold=4.5, hp=120, score=3000,
                  emitters=[delayed_aimed("red", 270, 3, 0.75, 4, 170, period=0.5)]),
        ]},
    ]
    bosses = [
        boss(62, 320, -40, 700, "Mid", 26, boss_path(122, 1.6), 180000, spells(
            spell("Mid", "机符「齿轮计数」", 23, 0.38, 240000, [
                ring("blue", 200, 20, rotate_speed=0.7, period=0.5),
                delayed_ring("purple", 200, 5, 0.55, 3, 150, period=0.12),
            ]),
        )),
        boss(94, 320, -50, 1450, "Boss", 32, boss_path(138, 2.0), 280000, spells(
            spell("1", "机关「三百六十一格」", 25, 0.3, 340000, [
                ring("blue", 210, 24, rotate_speed=0.3, period=0.5),
                aimed("red", 280, 1, period=0.3),
            ]),
            spell("2", "工符「不再计数之夜」", 27, 0.38, 560000, [
                delayed_fan("purple", 250, 11, "PI/3", "aimed", 0.58, 4, 175, period=0.5),
                spiral("yellow", 200, 2, 0.26, arms=3, period=0.09),
            ]),
            spell("Final", "零符「第一次的愿望」", 30, 0.5, 950000, [
                ring("red", 220, 32, rotate_speed=0.4, period=0.45),
                delayed_ring("blue", 190, 6, 0.6, 4, 160, period=0.1),
            ]),
        )),
    ]
    return {"name": "五章 · 机关天守", "waves": waves, "bosses": bosses}


# ---------------------------------------------------------------- 第六章
def stage_ch6():
    waves = [
        {"time": 1.5, "enemies": [
            sweep(-30, 90, 150, hold=2.6, hp=52, score=1400,
                  emitters=[aimed("yellow", 260, 3, 0.05, period=0.6)]),
            sweep(670, 170, 480, hold=2.6, hp=52, score=1400,
                  emitters=[aimed("yellow", 260, 3, 0.05, period=0.6)]),
        ]},
        {"time": 10.0, "enemies": [
            drop_in(200, 110, hp=170, score=4200, hold=6.0,
                    emitters=[delayed_ring("purple", 210, 5, 0.55, 4, 160, period=0.11)]),
            drop_in(440, 110, hp=170, score=4200, hold=6.0,
                    emitters=[delayed_ring("purple", 210, 5, 0.55, 4, 160, period=0.11)]),
        ]},
        {"time": 20.0, "enemies": vee(320, 120, hp=130, score=3000,
                                      emitters=[ring("yellow", 200, 18, rotate_speed=0.6,
                                                     period=0.55)])},
        {"time": 30.0, "enemies": [
            drop_in(320, 120, hp=280, score=7000, hold=8.0,
                    emitters=[spiral("purple", 200, 3, 0.22, arms=4, period=0.08),
                              fan("yellow", 220, 9, "PI/2", "aimed", 0.66, start_t=0.4)]),
        ]},
        {"time": 42.0, "enemies": [
            sweep(-30, 100, 130, hold=4.5, hp=140, score=3400,
                  emitters=[delayed_fan("blue", 250, 9, "PI/3", "aimed", 0.6, 4, 175,
                                        period=0.5)]),
            sweep(670, 200, 510, hold=4.5, hp=140, score=3400,
                  emitters=[delayed_fan("blue", 250, 9, "PI/3", "aimed", 0.6, 4, 175,
                                        period=0.5)]),
        ]},
        {"time": 52.0, "enemies": [
            drop_in(240, 130, hp=160, score=4000, hold=6.0,
                    emitters=[ring("red", 210, 20, rotate_speed=0.8, period=0.5)]),
            drop_in(400, 130, hp=160, score=4000, hold=6.0,
                    emitters=[ring("red", 210, 20, rotate_speed=-0.8, period=0.5)]),
        ]},
    ]
    bosses = [
        boss(64, 320, -40, 800, "Mid", 26, boss_path(124, 1.6), 200000, spells(
            spell("Mid", "星符「落下来的光」", 23, 0.36, 260000, [
                delayed_ring("purple", 210, 6, 0.55, 4, 160, period=0.1),
                aimed("yellow", 280, 2, 0.05, period=0.35),
            ]),
        )),
        boss(96, 320, -50, 1800, "Boss", 34, boss_path(140, 2.0), 300000, spells(
            spell("1", "器符「收集愿望的皿」", 25, 0.28, 380000, [
                ring("purple", 215, 26, rotate_speed=0.35, period=0.48),
                fan("yellow", 230, 11, "PI/2", "aimed", 0.5),
            ]),
            spell("2", "星符「被吃掉的夜空」", 27, 0.35, 600000, [
                delayed_ring("blue", 200, 7, 0.6, 4, 165, period=0.11),
                spiral("purple", 210, 2, 0.3, arms=3, period=0.08),
            ]),
            spell("3", "终符「七个人的愿望」", 28, 0.4, 800000, [
                ring("red", 220, 36, rotate_speed=0.45, period=0.42),
                aimed("yellow", 300, 3, 0.04, period=0.26),
            ]),
            spell("Final", "奥义「把星星还给我」", 32, 0.55, 1200000, [
                delayed_fan("purple", 260, 15, "PI/2", "aimed", 0.55, 5, 180, period=0.46),
                ring("blue", 190, 28, rotate_speed=-0.3, period=0.55),
                aimed("yellow", 300, 1, period=0.3, start_t=0.15),
            ]),
        )),
    ]
    return {"name": "终章 · 星之器", "waves": waves, "bosses": bosses}


GEN = {
    "ch1": stage_ch1,
    "ch2": stage_ch2,
    "ch3": stage_ch3,
    "ch4": stage_ch4,
    "ch5": stage_ch5,
    "ch6": stage_ch6,
}


def validate(name: str, data: dict) -> list[str]:
    errs = []
    if not data.get("name"):
        errs.append(f"{name}: 缺少 name")
    seen_t = []
    for i, w in enumerate(data.get("waves", [])):
        if "time" not in w:
            errs.append(f"{name}.waves[{i}]: 缺少 time")
            continue
        seen_t.append(w["time"])
        for j, e in enumerate(w.get("enemies", [])):
            for k in ("x", "y", "hp", "path"):
                if k not in e:
                    errs.append(f"{name}.waves[{i}].enemies[{j}]: 缺少 {k}")
            if not e.get("path"):
                errs.append(f"{name}.waves[{i}].enemies[{j}]: path 为空")
            for m, em in enumerate(e.get("emitters", [])):
                if "pattern" not in em:
                    errs.append(f"{name}.waves[{i}].enemies[{j}].emitters[{m}]: 缺少 pattern")
    if seen_t != sorted(seen_t):
        errs.append(f"{name}: waves 时间未按升序")
    bt = [b["time"] for b in data.get("bosses", [])]
    if bt != sorted(bt):
        errs.append(f"{name}: bosses 时间未按升序")
    if not data.get("bosses"):
        errs.append(f"{name}: 没有 boss")
    for b in data.get("bosses", []):
        if not b.get("spellcards"):
            errs.append(f"{name}: boss@{b.get('time')} 没有 spellcards")
        for sc in b.get("spellcards", []):
            for k in ("name", "duration", "hp_threshold", "emitters"):
                if k not in sc:
                    errs.append(f"{name}: 符卡 {sc.get('name')} 缺少 {k}")
    return errs


def main() -> int:
    check_only = "--check" in sys.argv
    os.makedirs(OUT_DIR, exist_ok=True)
    all_errs: list[str] = []
    for name, fn in GEN.items():
        data = fn()
        all_errs.extend(validate(name, data))
        if check_only:
            continue
        path = os.path.join(OUT_DIR, f"{name}.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        n_wave = len(data["waves"])
        n_enemy = sum(len(w["enemies"]) for w in data["waves"])
        n_spell = sum(len(b["spellcards"]) for b in data["bosses"])
        print(f"  {name}.json  waves={n_wave:<2} enemies={n_enemy:<3} "
              f"bosses={len(data['bosses'])} spells={n_spell}  {data['name']}")
    if all_errs:
        print("\n校验失败:")
        for e in all_errs:
            print("  - " + e)
        return 1
    print("\n生成/校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
