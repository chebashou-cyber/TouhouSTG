# -*- coding: utf-8 -*-
"""laser.py — 激光弹幕

状态机:
  warning  警告阶段 (LASER_WARNING_TIME 秒), 显示半透明白色虚线
  active   实弹阶段 (LASER_ACTIVE_TIME 秒), 显示实色, 对玩家造成持续伤害
  fade     淡出阶段 (LASER_FADE_TIME 秒), 显示半透明, 不造成伤害
设计:
  - 激光是一段宽度 width 长度 length 的矩形, 从 (x,y) 朝 angle 方向延伸
  - 碰撞判定: 把玩家位置投影到激光方向与垂直方向, 检查长度/宽度范围
  - 一根激光在 active 期间每帧检测一次, 但实际只产生一次 on_hit (玩家有无敌帧避免秒扣)
  - 性能: 激光数量少 (一般 <50), 不用对象池, 直接 list 维护
"""
from __future__ import annotations
import math
import pygame
from config import (
    LASER_POOL_INITIAL, LASER_WARNING_TIME, LASER_ACTIVE_TIME, LASER_FADE_TIME,
    LASER_DEFAULT_WIDTH, LASER_DEFAULT_LENGTH, LASER_HITBOX_HALF_WIDTH,
    PLAYER_HITBOX_RADIUS, PLAYER_GRAZE_RADIUS,
    COLOR_LASER_WARNING, COLOR_LASER_ACTIVE,
)


STATE_WARNING = "warning"
STATE_ACTIVE = "active"
STATE_FADE = "fade"


class Laser:
    """单条激光。alive=False 时可被回收。"""

    __slots__ = (
        "x", "y", "angle",
        "length", "width",
        "warning_time", "active_time", "fade_time",
        "age", "state",
        "alive", "color",
        "hit_already",  # active 期间是否已命中一次 (避免每帧重复扣命)
    )

    def __init__(self, x: float, y: float, angle: float,
                 length: float = LASER_DEFAULT_LENGTH,
                 width: float = LASER_DEFAULT_WIDTH,
                 warning_time: float = LASER_WARNING_TIME,
                 active_time: float = LASER_ACTIVE_TIME,
                 fade_time: float = LASER_FADE_TIME,
                 color: tuple = COLOR_LASER_ACTIVE) -> None:
        self.x = float(x)
        self.y = float(y)
        self.angle = float(angle)
        self.length = float(length)
        self.width = float(width)
        self.warning_time = warning_time
        self.active_time = active_time
        self.fade_time = fade_time
        self.age = 0.0
        self.state = STATE_WARNING
        self.alive = True
        self.color = color
        self.hit_already = False

    def update(self, dt: float, player) -> int:
        """更新状态; 返回命中的次数 (0 或 1, 一根激光只命中一次避免秒杀)。"""
        if not self.alive:
            return 0
        self.age += dt
        hit_count = 0

        if self.state == STATE_WARNING:
            if self.age >= self.warning_time:
                self.state = STATE_ACTIVE
                self.age = 0.0
                self.hit_already = False
        elif self.state == STATE_ACTIVE:
            if not self.hit_already and self._collide_player(player):
                self.hit_already = True
                hit_count = 1
            if self.age >= self.active_time:
                self.state = STATE_FADE
                self.age = 0.0
        elif self.state == STATE_FADE:
            if self.age >= self.fade_time:
                self.alive = False

        return hit_count

    def _collide_player(self, player) -> bool:
        """激光矩形 vs 玩家判定点 (圆形)。"""
        dx = player.x - self.x
        dy = player.y - self.y
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        # 沿激光方向投影
        along = dx * cos_a + dy * sin_a
        if along < 0 or along > self.length + PLAYER_HITBOX_RADIUS:
            return False
        # 垂直方向
        perp = -dx * sin_a + dy * cos_a
        if abs(perp) <= self.width / 2.0 + PLAYER_HITBOX_RADIUS:
            return True
        return False

    def draw(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        # 激光末端
        ex = self.x + cos_a * self.length
        ey = self.y + sin_a * self.length
        # 垂直偏移
        nx, ny = -sin_a, cos_a
        hw = self.width / 2.0
        pts = [
            (self.x + nx * hw, self.y + ny * hw),
            (self.x - nx * hw, self.y - ny * hw),
            (ex - nx * hw, ey - ny * hw),
            (ex + nx * hw, ey + ny * hw),
        ]
        if self.state == STATE_WARNING:
            col = COLOR_LASER_WARNING
            # 画两条线 (虚线效果: 实心 + 中空)
            pygame.draw.polygon(surf, col, pts, 1)
            pygame.draw.line(surf, (255, 255, 255),
                             (self.x, self.y), (ex, ey), 1)
        elif self.state == STATE_ACTIVE:
            col = self.color
            pygame.draw.polygon(surf, col, pts, 0)
            pygame.draw.polygon(surf, (255, 255, 255), pts, 1)
        else:  # fade
            col = COLOR_LASER_WARNING
            pygame.draw.polygon(surf, col, pts, 0)


class LaserEmitter:
    """符卡用的激光发射器: 按 period 周期成组放出 count 条激光。

    和子弹的 Emitter 分开写, 因为激光要往 LaserPool 里塞, 而子弹是往
    BulletPool 里塞; 参数也不一样 (有预警时间、持续时间、宽度)。
    """

    __slots__ = ("period", "start_t", "count", "arc", "angle", "width",
                 "warning", "active", "fade", "length", "color",
                 "elapsed", "last_emit_t", "enabled")

    def __init__(self, *, period: float = 2.0, start_t: float = 0.0,
                 count: int = 1, arc: float = 0.0, angle=math.pi / 2,
                 width: float = LASER_DEFAULT_WIDTH,
                 warning: float = LASER_WARNING_TIME,
                 active: float = LASER_ACTIVE_TIME,
                 fade: float = LASER_FADE_TIME,
                 length: float = LASER_DEFAULT_LENGTH,
                 color: tuple = COLOR_LASER_ACTIVE) -> None:
        self.period = max(0.1, float(period))
        self.start_t = float(start_t)
        self.count = max(1, int(count))
        self.arc = float(arc)
        self.angle = angle            # "aimed" 或弧度值
        self.width = float(width)
        self.warning = float(warning)
        self.active = float(active)
        self.fade = float(fade)
        self.length = float(length)
        self.color = color
        self.elapsed = 0.0
        # 让第一组激光正好落在 start_t 时刻, 而不是 start_t + period
        self.last_emit_t = self.start_t - self.period
        self.enabled = True

    def reset(self) -> None:
        self.elapsed = 0.0
        self.last_emit_t = self.start_t - self.period
        self.enabled = True

    def update(self, dt: float, ox: float, oy: float, tx: float, ty: float,
               laser_pool) -> int:
        """到点就放一组激光; 返回本次放出的条数。"""
        if not self.enabled:
            return 0
        self.elapsed += dt
        if self.elapsed < self.start_t:
            return 0
        spawned = 0
        while self.last_emit_t + self.period <= self.elapsed:
            self.last_emit_t += self.period
            if self.angle == "aimed":
                base = math.atan2(ty - oy, tx - ox)
            else:
                base = float(self.angle)
            if self.count == 1:
                angles = [base]
            else:
                half = self.arc / 2.0
                angles = [base - half + self.arc * i / (self.count - 1)
                          for i in range(self.count)]
            for a in angles:
                laser_pool.spawn(ox, oy, a, length=self.length, width=self.width,
                                 warning_time=self.warning,
                                 active_time=self.active, fade_time=self.fade,
                                 color=self.color)
                spawned += 1
        return spawned


class LaserPool:
    """激光集合。性能不是瓶颈, 简单 list 维护。"""

    __slots__ = ("_active", "_free")

    def __init__(self, initial: int = LASER_POOL_INITIAL) -> None:
        self._active: list[Laser] = []
        self._free: list[Laser] = [Laser(0, 0, 0) for _ in range(initial)]

    def spawn(self, x: float, y: float, angle: float, *,
              length: float = LASER_DEFAULT_LENGTH,
              width: float = LASER_DEFAULT_WIDTH,
              warning_time: float = LASER_WARNING_TIME,
              active_time: float = LASER_ACTIVE_TIME,
              fade_time: float = LASER_FADE_TIME,
              color: tuple = COLOR_LASER_ACTIVE) -> Laser:
        if self._free:
            l = self._free.pop()
        else:
            l = Laser(0, 0, 0)
        l.x = float(x); l.y = float(y); l.angle = float(angle)
        l.length = length; l.width = width
        l.warning_time = warning_time
        l.active_time = active_time
        l.fade_time = fade_time
        l.age = 0.0
        l.state = STATE_WARNING
        l.alive = True
        l.color = color
        l.hit_already = False
        self._active.append(l)
        return l

    def update(self, dt: float, player) -> int:
        hits = 0
        keep = []
        for l in self._active:
            h = l.update(dt, player)
            if h > 0:
                hits += h
            if l.alive:
                keep.append(l)
            else:
                self._free.append(l)
        self._active = keep
        return hits

    def draw(self, surf: pygame.Surface) -> None:
        for l in self._active:
            l.draw(surf)

    def clear(self) -> None:
        for l in self._active:
            l.alive = False
            self._free.append(l)
        self._active.clear()

    def count(self) -> int:
        return len(self._active)