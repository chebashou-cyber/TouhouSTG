# -*- coding: utf-8 -*-
"""patterns/spellcard.py — 符卡数据

SpellCard 是 Boss 的一段攻击期:
  - name            : 符卡名 (用于 HUD 宣言)
  - duration        : 持续时间 (s), 超时未击破算 break
  - hp_threshold    : 进入此符卡时需要打掉的 HP 比例 (0~1)
                       击破 = 进入时 HP * (1 - hp_threshold) = break_hp
                       例: hp_threshold=0.4, 进入 HP=1000 -> 需打 400 -> break_hp=600
  - emitters        : 此符卡期间激活的 emitter 列表
  - bonus_score     : 击破基础得分
  - no              : 符卡编号字符串 (例如 "1", "Non", "Final" 等)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from src.entities.enemy import Emitter


@dataclass
class SpellCard:
    name: str
    duration: float
    hp_threshold: float
    emitters: list  # list[Emitter]
    bonus_score: int = 100000
    no: str = "1"
    lasers: list = field(default_factory=list)  # list[LaserEmitter]

    def __post_init__(self) -> None:
        # 运行时状态: 进入此符卡时的 HP 与累计击中
        self.spell_start_hp: float = 0.0

    def break_hp(self) -> float:
        """击破阈值 HP: HP <= 此值算击破。"""
        return self.spell_start_hp * (1.0 - self.hp_threshold)

    def hp_progress(self, current_hp: float) -> float:
        """当前符卡进度 (0=刚进入, 1=击破)。HP 越低越高。"""
        if self.spell_start_hp <= 0:
            return 0.0
        bh = self.break_hp()
        if self.spell_start_hp <= bh:
            return 1.0
        p = (self.spell_start_hp - current_hp) / (self.spell_start_hp - bh)
        return max(0.0, min(1.0, p))

    def time_progress(self, elapsed: float) -> float:
        if self.duration <= 0:
            return 1.0
        return max(0.0, min(1.0, elapsed / self.duration))