# -*- coding: utf-8 -*-
"""config.py — 全局数值常量集中地"""
from __future__ import annotations
import math
import re

# -------------------- 窗口 / 帧率 --------------------
SCREEN_W = 640
SCREEN_H = 480
LOGIC_FPS = 60
LOGIC_DT = 1.0 / LOGIC_FPS
MAX_FRAME_DT = 0.25

# -------------------- 自机 Player --------------------
PLAYER_SPEED = 300.0
PLAYER_FOCUS_SPEED = 140.0
PLAYER_HITBOX_RADIUS = 2
PLAYER_GRAZE_RADIUS = 16
PLAYER_FIRE_INTERVAL = 0.08
PLAYER_FIRE_SPEED = 720.0
PLAYER_INVULN_TIME = 2.5
PLAYER_DEATH_INVULN_FRAMES = 8
PLAYER_START_LIVES = 4
PLAYER_START_BOMBS = 3
PLAYER_START_POWER = 16
PLAYER_MAX_POWER = 128
GRAZE_SCORE = 500
HITBOX_PENALTY_POWER = 8

PLAYER_SPAWN_X = SCREEN_W // 2
PLAYER_SPAWN_Y = SCREEN_H - 80
PLAYER_MOVE_BOUND_TOP = 16
PLAYER_MOVE_BOUND_BOTTOM = SCREEN_H - 8

# -------------------- 炸弹 --------------------
BOMB_INVULN_TIME = 2.0
BOMB_CLEAR_BULLET_SCORE = 100
BOMB_CLEAR_BULLET_SCORE_CAP = 100000
BOMB_MAX_BOMBS = 8

# -------------------- 子弹 --------------------
BULLET_POOL_INITIAL = 4096
BULLET_HITBOX_RADIUS = 4
BULLET_GRAZE_PADDING = 1

# -------------------- 激光 Laser --------------------
LASER_POOL_INITIAL = 64
LASER_WARNING_TIME = 1.0
LASER_ACTIVE_TIME = 1.5
LASER_FADE_TIME = 0.3
LASER_DEFAULT_WIDTH = 18
LASER_DEFAULT_LENGTH = 480
LASER_HITBOX_HALF_WIDTH = 9
COLOR_LASER_WARNING = (255, 200, 200)
COLOR_LASER_ACTIVE = (255, 80, 80)

# -------------------- Delayed 分裂 --------------------
BULLET_SPLIT_COUNT_DEFAULT = 4
BULLET_SPLIT_SPEED_DEFAULT = 180.0
BULLET_SPLIT_ANGLE_SPAN = math.pi

# -------------------- Global scales --------------------
BULLET_SPEED_GLOBAL_SCALE = 0.55    # all enemy bullets: 45% slower (more reaction time)
PLAYER_BULLET_SPEED_SCALE = 0.85   # player bullets: slightly slower (visual clarity)

  # 分裂角跨度 (π = 180°, 即半圈)

# -------------------- 敌机 --------------------
ENEMY_DEFAULT_HP = 50
ENEMY_DEFAULT_SCORE = 1000
ENEMY_HITBOX_RADIUS = 12
ENEMY_DROP_TABLE = (
    (8000,  "bomb",  1, 0.20),
    (3000,  "score", 1, 0.45),
    (1500,  "score", 1, 0.30),
    (500,   "power", 1, 0.25),
    (0,     None,    0, 0.0),
)

# -------------------- 道具 --------------------
ITEM_FALL_SPEED = 120.0
ITEM_ATTRACT_SPEED_MIN = 80.0
ITEM_ATTRACT_SPEED_MAX = 360.0
ITEM_ATTRACT_ACCEL = 540.0
ITEM_ATTRACT_RADIUS = 48.0
ITEM_HITBOX_RADIUS = 6
ITEM_COLLECT_RADIUS = PLAYER_HITBOX_RADIUS + ITEM_HITBOX_RADIUS
ITEM_P_VALUE = 1
ITEM_P_FULL_BONUS_SCORE = 50000
ITEM_SCORE_BASE = 10000
ITEM_SCORE_HEIGHT_FACTOR = 4.0
ITEM_BOMB_VALUE = 1
ITEM_LIFE_VALUE = 1
ITEM_AUTO_COLLECT_BELOW_Y = -16
ITEM_COLOR_POWER = (96, 192, 255)
ITEM_COLOR_POWER_FULL = (255, 215, 0)
ITEM_COLOR_SCORE = (200, 100, 255)
ITEM_COLOR_BOMB = (255, 130, 100)
ITEM_COLOR_LIFE = (120, 255, 160)
ITEM_RADIUS = 6

# -------------------- 死亡动画 --------------------
DEATH_EFFECT_PARTICLES = 24
DEATH_EFFECT_SPEED_MIN = 80.0
DEATH_EFFECT_SPEED_MAX = 200.0
DEATH_EFFECT_LIFE = 0.8
DEATH_EFFECT_RADIUS = 3
DEATH_RESPAWN_DELAY = 1.0

# -------------------- 视差背景 --------------------
BG_FAR_STARS = 80
BG_NEAR_STARS = 40
BG_FAR_SPEED = 10.0
BG_NEAR_SPEED = 40.0
BG_FAR_BRIGHTNESS = 60
BG_NEAR_BRIGHTNESS = 200

# -------------------- 难度 --------------------
DIFFICULTY_NAMES = ("EASY", "NORMAL", "HARD", "LUNATIC")
DIFFICULTY_DEFAULT = 1
# v0.6 平滑曲线: hp 0.5/1.0/1.4/2.0, speed 0.7/1.0/1.15/1.3, period 1.5/1.0/0.9/0.75
# EASY: 玩家轻松, 多掉道具; LUNATIC: 极限但可行, 少掉道具
DIFFICULTY_MULTIPLIERS = (
    {"hp": 0.3, "speed": 0.5, "period": 2.20, "drop_bias": 1.80},
    {"hp": 0.85, "speed": 0.95, "period": 1.10, "drop_bias": 1.10},
    {"hp": 1.5, "speed": 1.20, "period": 0.85, "drop_bias": 0.85},
    {"hp": 2.2, "speed": 1.40, "period": 0.70, "drop_bias": 0.65},
)

# -------------------- Continue --------------------
CONTINUE_MAX = 3
CONTINUE_LIVES = 1
CONTINUE_BOMBS = 1
CONTINUE_POWER = 16

# -------------------- Boss / 符卡 --------------------
BOSS_HITBOX_RADIUS = 28
BOSS_SCORE = 200000
BOSS_PATH_ENTRY_TIME = 2.0
BOSS_BETWEEN_SPELLS_TIME = 1.0
BOSS_TIME_BONUS_RATE = 1000
BOSS_DEFEAT_P_DROP = 32
BOSS_DEFEAT_SCORE_DROP = 10
BOSS_DEFEAT_DROP_JITTER = 32

STAGE_CLEAR_RANK_FINAL = "EX"
STAGE_CLEAR_RANK_A = "A"
STAGE_CLEAR_RANK_B = "B"
STAGE_CLEAR_RANK_C = "C"

COLOR_BOSS_HP_BAR_BG = (60, 30, 30)
COLOR_BOSS_HP_BAR_FG = (255, 90, 140)
COLOR_BOSS_HP_BAR_BORDER = (220, 220, 220)
COLOR_SPELL_CARD_NAME = (255, 220, 140)
COLOR_SPELL_TIMER_WARN = (255, 120, 120)
COLOR_SPELL_TIMER_OK = (180, 220, 255)

# -------------------- 输入 --------------------
INPUT_BUFFER_FRAMES = 6
INPUT_BUFFER_DT = INPUT_BUFFER_FRAMES * LOGIC_DT

# -------------------- 调试键 --------------------
KEY_DEBUG_OVERLAY = "F1"
KEY_DEBUG_STEP = "F2"
KEY_DEBUG_GOD = "F3"
KEY_DEBUG_CLEAR = "F4"
KEY_DEBUG_PAUSE = "P"

# -------------------- HUD / 颜色 --------------------
COLOR_BG = (0, 0, 0)
COLOR_TEXT = (255, 255, 255)
COLOR_TEXT_DIM = (160, 160, 160)
COLOR_PLAYER = (96, 192, 255)
COLOR_PLAYER_HITBOX = (255, 80, 80)
COLOR_GRAZE_RING = (255, 255, 255)
COLOR_BULLET_RED = (255, 90, 90)
COLOR_BULLET_BLUE = (110, 170, 255)
COLOR_BULLET_GREEN = (120, 255, 140)
COLOR_BULLET_PURPLE = (210, 130, 255)
COLOR_BULLET_YELLOW = (255, 230, 110)
COLOR_ENEMY = (255, 180, 120)
COLOR_ENEMY_HITBOX = (255, 255, 0)
COLOR_MENU_DIM = (90, 90, 110)
COLOR_MENU_SEL = (255, 240, 160)
COLOR_MENU_TITLE = (255, 200, 200)
COLOR_MENU_ACCENT = (180, 220, 255)
COLOR_DEATH_PARTICLE = (255, 200, 200)


def to_color(name: str) -> tuple:
    mapping = {
        "red": COLOR_BULLET_RED,
        "blue": COLOR_BULLET_BLUE,
        "green": COLOR_BULLET_GREEN,
        "purple": COLOR_BULLET_PURPLE,
        "yellow": COLOR_BULLET_YELLOW,
    }
    return mapping.get(name, COLOR_BULLET_RED)


def difficulty_multiplier(level: int) -> dict:
    if 0 <= level < len(DIFFICULTY_MULTIPLIERS):
        return DIFFICULTY_MULTIPLIERS[level]
    return DIFFICULTY_MULTIPLIERS[DIFFICULTY_DEFAULT]


def parse_angle(s) -> float:
    """JSON 配置里的角度字符串解析: PI / PI/2 / PI/24 等; 非字符串直接转 float。"""
    if not isinstance(s, str):
        return float(s)
    s = s.replace(" ", "").upper()
    # PI/N 形式: 动态分母 (PI/2, PI/24, PI/48 ...)
    m = re.match(r"^PI/(\d+)$", s)
    if m:
        return math.pi / int(m.group(1))
    m = re.match(r"^(\d+)\*PI/(\d+)$", s)
    if m:
        return int(m.group(1)) * math.pi / int(m.group(2))
    if s == "PI":
        return math.pi
    if s == "2*PI" or s == "TAU":
        return math.tau
    return float(s)