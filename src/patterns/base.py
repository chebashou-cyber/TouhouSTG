# -*- coding: utf-8 -*-
"""patterns/base.py — 弹幕 Pattern 抽象基类

约定:
  - tick(ox, oy, tx, ty, t) 返回 dict 列表, 每项是 BulletPool.acquire 的关键字参数
  - 0 弧度 = +x 方向, 逆时针为正
  - Pattern 自身可以维护内部状态 (例如螺旋累计角度)
"""
from __future__ import annotations


class Pattern:
    """所有弹幕模式的基类。子类实现 tick()。"""

    name: str = "base"

    def tick(self, ox: float, oy: float, tx: float, ty: float, t: float) -> list[dict]:
        raise NotImplementedError

    def reset(self) -> None:
        """用于 Boss 重置符卡时把 pattern 状态归零。"""
        pass