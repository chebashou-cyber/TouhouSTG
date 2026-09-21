# -*- coding: utf-8 -*-
"""core/game.py — 主循环 (v0.6)

新增 (v0.6):
  - ReplayRecorder: 每帧记录输入快照到 replay/
  - ReplayPlayer: 读取 replay/*.ndjson 灌入 input_manager
  - 录制在 _start_new_game 时按 stage_id/difficulty/seed 命名文件
  - 回放模式 scene="replay"  菜单选 REPLAY 进入
"""
from __future__ import annotations
import random
import sys
import os
import pygame

from src.core.input_manager import InputManager
from src.core.assets import AssetLoader, default_loader
from src.core.replay import ReplayRecorder, ReplayPlayer
from src.entities.bullet import BulletPool, KIND_ENEMY, KIND_PLAYER
from src.entities.item import ItemPool, TYPE_POWER, TYPE_SCORE
from src.entities.player import Player
from src.entities.enemy import Enemy
from src.entities.boss import Boss
from src.entities.laser import LaserPool
from src.entities.death_effect import DeathEffect
from src.entities.hit_particle import HitParticlePool
from src.entities.graze_ring import GrazeRingPool
from src.entities.background import ParallaxBackground
from src.stages.stage_factory import make_stage, Stage
from src.stages.stage1 import Stage1
from src.ui.hud import HUD
from src.ui.overlay import DebugOverlay
from src.ui.menu import MenuSystem
from config import (
    SCREEN_W, SCREEN_H, LOGIC_DT, MAX_FRAME_DT,
    PLAYER_HITBOX_RADIUS, PLAYER_GRAZE_RADIUS,
    PLAYER_SPAWN_X, PLAYER_INVULN_TIME, PLAYER_DEATH_INVULN_FRAMES,
    COLOR_BG,
    DIFFICULTY_DEFAULT, DIFFICULTY_MULTIPLIERS, DIFFICULTY_NAMES,
    CONTINUE_MAX, CONTINUE_LIVES, CONTINUE_BOMBS, CONTINUE_POWER,
    BOSS_DEFEAT_P_DROP, BOSS_DEFEAT_SCORE_DROP, BOSS_DEFEAT_DROP_JITTER,
)


def difficulty_multiplier(level: int) -> dict:
    if 0 <= level < len(DIFFICULTY_MULTIPLIERS):
        return DIFFICULTY_MULTIPLIERS[level]
    return DIFFICULTY_MULTIPLIERS[DIFFICULTY_DEFAULT]


def _replay_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "replay")


class Game:
    MAX_STAGE = 10

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Touhou-style STG (MVP v0.6 + Replay)")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()

        self.assets: AssetLoader = default_loader()

        self.background = ParallaxBackground(seed=7)
        self.input = InputManager()
        self.pool = BulletPool()
        self.lasers = LaserPool()
        self.items = ItemPool()
        self.hit_particles = HitParticlePool()
        self.graze_rings = GrazeRingPool()
        self.player = Player()
        self.enemies: list[Enemy] = []
        self.boss: Boss | None = None
        self._boss_pending: list[Boss] = []
        self.stage: Stage | Stage1 = make_stage(1)
        self.stage_id = 1
        self.death_effects: list[DeathEffect] = []
        self._drop_rng = random.Random(2026)

        self.hud = HUD()
        self.overlay = DebugOverlay()
        self.menu = MenuSystem(max_stage=self.MAX_STAGE)

        self.scene = "title"
        self.difficulty = DIFFICULTY_DEFAULT
        self.continue_left = CONTINUE_MAX
        self.continue_used = 0
        self._accumulator = 0.0
        self._fps = 0.0
        self._fps_acc = 0.0
        self._fps_frames = 0
        self.stage_elapsed = 0.0
        self._death_effect_pending = False
        self._last_spell_index = -1
        self._tutorial_hints = [
            "Arrows/WASD: MOVE",
            "Shift: FOCUS (slower, shows hitbox)",
            "Z: FIRE   |   X: BOMB (clears bullets)",
            "Graze bullets for +500 score!",
        ]

        self.show_overlay = False
        self.paused = False
        self.frame_step_request = False
        self.god_mode = False

        # Replay
        self.recorder: ReplayRecorder | None = None
        self.replay_player: ReplayPlayer | None = None
        self.is_replaying = False

    # ---------------- 启动 ----------------
    def run(self) -> None:
        running = True
        while running:
            events = pygame.event.get()
            # Replay 模式: 不读事件, 由 _step 内 replay_player 注入
            if not self.is_replaying:
                self.input.update(events)
            for ev in events:
                if ev.type == pygame.QUIT:
                    running = False

            if self.scene in ("title", "gameover", "stageclear") and self.input.consume_press("escape"):
                running = False

            if self.input.consume_press("f1"):
                self.show_overlay = not self.show_overlay
            if self.input.consume_press("f3"):
                self.god_mode = not self.god_mode
            if self.input.consume_press("f4"):
                if self.scene == "play":
                    self.pool.clear_enemy()
            if self.input.consume_press("pause"):
                if self.scene == "play" and not self.is_replaying:
                    self.paused = not self.paused
                    self.frame_step_request = False
            if self.input.consume_press("f2"):
                if self.scene == "play" and self.paused and not self.is_replaying:
                    self.frame_step_request = True

            actions = self.menu.handle(self.input, self.scene)
            for a in actions:
                self._apply_action(a)

            self.menu.update(LOGIC_DT)
            self.hud.update_announce(LOGIC_DT)

            tick_ms = self.clock.tick(0)
            dt = min(tick_ms / 1000.0, MAX_FRAME_DT) if tick_ms > 0 else LOGIC_DT

            self.background.update(dt)

            if tick_ms > 0:
                self._fps_acc += tick_ms / 1000.0
                self._fps_frames += 1
                if self._fps_acc >= 0.5:
                    self._fps = self._fps_frames / self._fps_acc
                    self._fps_acc = 0.0
                    self._fps_frames = 0

            if self.scene == "play":
                self._advance(dt)

            self._render()
            pygame.display.flip()

        # 退出时关闭 recorder
        if self.recorder:
            self.recorder.close()
        pygame.quit()
        sys.exit(0)

    def _advance(self, dt: float) -> None:
        """固定步长推进; Replay 时用 replay_player.inject。"""
        # Replay: 注入输入 (每帧都灌入, 因为一帧可能多个事件)
        if self.is_replaying and self.replay_player:
            end = self.replay_player.apply_until(self.stage_elapsed, self.input)
            if end:
                # 回放结束 -> 切到 stageclear
                self.scene = "stageclear"
                self.input.exit_inject_mode()
                self.is_replaying = False

        if not self.paused or self.frame_step_request:
            self._accumulator += dt
            while self._accumulator >= LOGIC_DT:
                self._step(LOGIC_DT)
                self._accumulator -= LOGIC_DT
            if self.frame_step_request:
                self.frame_step_request = False
                self.paused = True

        # 录制: 每帧写入当前输入快照
        if self.recorder and not self.is_replaying:
            self.recorder.record_frame(
                self.stage_elapsed,
                self.input._held,
                self.input._pressed_this_frame,
            )

    # ---------------- 行动作 ----------------
    def _apply_action(self, action: tuple) -> None:
        kind = action[0]
        if kind == "start":
            self._start_new_game(difficulty=action[1], stage_id=action[2], reset_continue=True)
        elif kind == "restart":
            self._start_new_game(difficulty=self.difficulty, stage_id=self.stage_id, reset_continue=True)
        elif kind == "continue_or_restart":
            if self.continue_left > 0:
                self._do_continue()
            else:
                self._start_new_game(difficulty=self.difficulty, stage_id=self.stage_id, reset_continue=True)
        elif kind == "set_difficulty":
            self.difficulty = action[1]
        elif kind == "set_stage":
            self.stage_id = max(0, min(self.MAX_STAGE, action[1]))
        elif kind == "list_replays":
            # 选最新的一个 replay 自动播放
            files = self.list_replays()
            if files:
                self._start_replay(files[-1])
            else:
                print("[replay] no replay files in", _replay_dir())
        elif kind == "start_replay":
            # action = ("start_replay", replay_filename)
            self._start_replay(action[1])
        elif kind == "quit":
            if self.recorder:
                self.recorder.close()
                self.recorder = None
            pygame.quit()
            sys.exit(0)

    def _start_new_game(self, difficulty: int, stage_id: int = 1,
                        reset_continue: bool = True) -> None:
        self.difficulty = difficulty
        self.stage_id = max(0, min(self.MAX_STAGE, stage_id))
        self.pool.clear_all()
        self.lasers.clear()
        self.items.clear()
        self.hit_particles.clear()
        self.graze_rings.clear()
        self.enemies.clear()
        self.death_effects.clear()
        self.boss = None
        self._boss_pending.clear()
        self.player = Player()
        self.stage = make_stage(self.stage_id)
        self.stage_elapsed = 0.0
        self._accumulator = 0.0
        self._death_effect_pending = False
        self._last_spell_index = -1
        self._tutorial_hints = [
            "Arrows/WASD: MOVE",
            "Shift: FOCUS (slower, shows hitbox)",
            "Z: FIRE   |   X: BOMB (clears bullets)",
            "Graze bullets for +500 score!",
        ]
        self._drop_rng = random.Random(2026 + difficulty * 7 + self.stage_id * 13)
        if reset_continue:
            self.continue_left = CONTINUE_MAX
            self.continue_used = 0
            self.player.score = 0
        self.paused = False
        self.frame_step_request = False
        self.scene = "play"
        self.is_replaying = False

        # 启动 Replay 录制
        if self.recorder:
            self.recorder.close()
        try:
            os.makedirs(_replay_dir(), exist_ok=True)
            fname = f"stage{self.stage_id}_{DIFFICULTY_NAMES[self.difficulty].lower()}_{int(random.random()*1e6)}.ndjson"
            fpath = os.path.join(_replay_dir(), fname)
            self.recorder = ReplayRecorder(fpath, {
                "stage_id": self.stage_id,
                "difficulty": self.difficulty,
                "seed": 2026 + difficulty * 7 + self.stage_id * 13,
            })
        except Exception:
            self.recorder = None

    def _do_continue(self) -> None:
        self.continue_left -= 1
        self.continue_used += 1
        self.pool.clear_all()
        self.lasers.clear()
        self.items.clear()
        self.hit_particles.clear()
        self.graze_rings.clear()
        self.enemies.clear()
        self.death_effects.clear()
        self.player.lives = CONTINUE_LIVES
        self.player.bombs = CONTINUE_BOMBS
        self.player.power = CONTINUE_POWER
        self.player.x = float(PLAYER_SPAWN_X)
        self.player.y = float(SCREEN_H - 80)
        self.player.invuln_time = PLAYER_INVULN_TIME
        self.player.bomb_time = 0.0
        self.player.death_timer = 0.0
        self.player.alive = True
        self.player.fire_cooldown = 0.0
        self.player.death_invuln_left = PLAYER_DEATH_INVULN_FRAMES
        self.stage = make_stage(self.stage_id)
        self.stage_elapsed = 0.0
        self._accumulator = 0.0
        self._death_effect_pending = False
        self._last_spell_index = -1
        self._tutorial_hints = [
            "Arrows/WASD: MOVE",
            "Shift: FOCUS (slower, shows hitbox)",
            "Z: FIRE   |   X: BOMB (clears bullets)",
            "Graze bullets for +500 score!",
        ]
        self.boss = None
        self._boss_pending.clear()
        self.scene = "play"
        self.is_replaying = False

    def _start_replay(self, filename: str) -> None:
        path = os.path.join(_replay_dir(), filename)
        if not os.path.isfile(path):
            return
        self.replay_player = ReplayPlayer(path)
        meta = self.replay_player.meta
        self.difficulty = meta.get("difficulty", DIFFICULTY_DEFAULT)
        self.stage_id = meta.get("stage_id", 1)
        # 清理
        self.pool.clear_all()
        self.lasers.clear()
        self.items.clear()
        self.hit_particles.clear()
        self.graze_rings.clear()
        self.enemies.clear()
        self.death_effects.clear()
        self.boss = None
        self._boss_pending.clear()
        self.player = Player()
        self.stage = make_stage(self.stage_id)
        self.stage_elapsed = 0.0
        self._accumulator = 0.0
        self._death_effect_pending = False
        self._last_spell_index = -1
        self._tutorial_hints = [
            "Arrows/WASD: MOVE",
            "Shift: FOCUS (slower, shows hitbox)",
            "Z: FIRE   |   X: BOMB (clears bullets)",
            "Graze bullets for +500 score!",
        ]
        self._drop_rng = random.Random(meta.get("seed", 2026))
        self.is_replaying = True
        # 不录制回放
        if self.recorder:
            self.recorder.close()
            self.recorder = None
        self.scene = "play"
        self.paused = False
        self.frame_step_request = False

    def list_replays(self) -> list[str]:
        d = _replay_dir()
        if not os.path.isdir(d):
            return []
        return sorted([f for f in os.listdir(d) if f.endswith(".ndjson")])

    def _step(self, dt: float) -> None:
        self.stage_elapsed += dt

        self.stage.update(dt, self.enemies, self._boss_pending, self.pool,
                          self.player, self.difficulty)
        if self._boss_pending:
            self.boss = self._boss_pending.pop(0)
            self._last_spell_index = -1
        self._tutorial_hints = [
            "Arrows/WASD: MOVE",
            "Shift: FOCUS (slower, shows hitbox)",
            "Z: FIRE   |   X: BOMB (clears bullets)",
            "Graze bullets for +500 score!",
        ]

        self.player.update(dt, self.input, self.pool)
        for e in self.enemies:
            e.update(dt, self.pool, self.player.x, self.player.y)
        if self.boss:
            self.boss.update(dt, self.pool, self.player)
            self._check_spell_announce()
            if self.boss.is_dead():
                self._on_boss_defeated()

        self.pool.step(dt)
        laser_hits = self.lasers.update(dt, self.player)
        if laser_hits > 0 and not self.god_mode and self.player.is_vulnerable():
            self.player.on_hit()
        self.items.update(dt, self.player)
        self.items.collect_pass(self.player)
        self.hit_particles.update(dt)
        self.graze_rings.update(dt)
        for fx in self.death_effects:
            fx.update(dt)
        self.death_effects = [fx for fx in self.death_effects if fx.alive]

        self._collisions()

        if any(not e.alive for e in self.enemies):
            self.enemies = [e for e in self.enemies if e.alive]

        if not self.player.alive and not self._death_effect_pending:
            self.death_effects.append(DeathEffect(self.player.x, self.player.y))
            self._death_effect_pending = True
        if self.player.alive:
            self._death_effect_pending = False

        if self.player.is_game_over():
            self.scene = "gameover"
            self.paused = False

    def _check_spell_announce(self) -> None:
        if self.boss is None or self.boss.state != "spell":
            return
        idx = self.boss.current_spell_index
        if idx != self._last_spell_index:
            self._last_spell_index = idx
            name = self.boss.get_spell_name()
            self.hud.set_spell_announce(name, t_remaining=2.5)

    def _on_boss_defeated(self) -> None:
        self.player.score += self.boss.bonus_total
        cx, cy = self.boss.x, self.boss.y
        for _ in range(BOSS_DEFEAT_P_DROP):
            jx = self._drop_rng.uniform(-BOSS_DEFEAT_DROP_JITTER, BOSS_DEFEAT_DROP_JITTER)
            jy = self._drop_rng.uniform(-BOSS_DEFEAT_DROP_JITTER, BOSS_DEFEAT_DROP_JITTER)
            self.items.spawn(cx + jx, cy + jy, TYPE_POWER, 1)
        for _ in range(BOSS_DEFEAT_SCORE_DROP):
            jx = self._drop_rng.uniform(-BOSS_DEFEAT_DROP_JITTER * 1.2,
                                        BOSS_DEFEAT_DROP_JITTER * 1.2)
            jy = self._drop_rng.uniform(-BOSS_DEFEAT_DROP_JITTER * 1.2,
                                        BOSS_DEFEAT_DROP_JITTER * 1.2)
            self.items.spawn(cx + jx, cy + jy, TYPE_SCORE, 1)
        self.death_effects.append(DeathEffect(cx, cy, count=40))
        self.hit_particles.spawn(cx, cy, (255, 200, 200), count=20)
        self.lasers.clear()
        if self.is_replaying:
            self.scene = "stageclear"
            self.input.exit_inject_mode()
        else:
            self.scene = "stageclear"

    def _collisions(self) -> None:
        if self.player.alive:
            px = self.player.x
            py = self.player.y
            hit_r = PLAYER_HITBOX_RADIUS
            graze_r = PLAYER_GRAZE_RADIUS
            for b in self.pool.active:
                if b.kind != KIND_ENEMY:
                    continue
                dx = b.x - px
                dy = b.y - py
                d2 = dx * dx + dy * dy
                br = b.radius
                if d2 <= (br + graze_r) ** 2:
                    if self.player.try_graze(b):
                        self.graze_rings.spawn(px, py)
                if d2 <= (br + hit_r) ** 2:
                    if not self.god_mode and self.player.is_vulnerable():
                        self.player.on_hit()
                        self.pool.release(b)
                        break

        pb_list = [b for b in self.pool.active if b.kind == KIND_PLAYER]
        drop_bias = difficulty_multiplier(self.difficulty)["drop_bias"]
        for e in self.enemies:
            if not e.alive:
                continue
            ex, ey = e.x, e.y
            er = e.radius
            for i in range(len(pb_list) - 1, -1, -1):
                b = pb_list[i]
                if not b.alive:
                    continue
                dx = b.x - ex
                dy = b.y - ey
                d2 = dx * dx + dy * dy
                if d2 <= (b.radius + er) ** 2:
                    score = e.hit(1)
                    if score:
                        self.player.score += score
                        e.on_death_drop(self.items, drop_bias, self._drop_rng)
                        self.hit_particles.spawn(ex, ey, (255, 220, 120), count=8)
                    else:
                        self.hit_particles.spawn(b.x, b.y, (255, 200, 200), count=3)
                    self.pool.release(b)
                    del pb_list[i]

        if self.boss and self.boss.is_active():
            for i in range(len(pb_list) - 1, -1, -1):
                b = pb_list[i]
                if not b.alive:
                    continue
                dx = b.x - self.boss.x
                dy = b.y - self.boss.y
                d2 = dx * dx + dy * dy
                if d2 <= (b.radius + self.boss.radius) ** 2:
                    score = self.boss.hit(1)
                    if score:
                        self.player.score += score
                        if self.boss.is_dead():
                            self._on_boss_defeated()
                            break
                        else:
                            self.hit_particles.spawn(self.boss.x, self.boss.y, (255, 220, 120), count=16)
                    else:
                        self.hit_particles.spawn(b.x, b.y, (200, 220, 255), count=3)
                    self.pool.release(b)
                    del pb_list[i]

    def _render(self) -> None:
        self.screen.fill(COLOR_BG)
        self.background.draw(self.screen)
        if self.stage_id == 0 and self.scene == "play":
            self._draw_tutorial_hints()
        if self.stage_id == 0 and self.scene == "play":
            self._draw_tutorial_hints()

        if self.scene in ("play", "paused", "gameover", "stageclear"):
            self._render_world()

        if self.scene == "title":
            self.menu.draw(self.screen, "title")
        elif self.scene == "paused":
            self.menu.draw(self.screen, "paused")
        elif self.scene == "gameover":
            self.menu.draw(self.screen, "gameover", player=self.player,
                           difficulty=self.difficulty, continue_left=self.continue_left)
        elif self.scene == "stageclear":
            self.menu.draw(self.screen, "stageclear", player=self.player,
                           difficulty=self.difficulty,
                           continue_left=self.continue_left,
                           continue_used=self.continue_used)
        if self.is_replaying:
            t = self.hud._font_small.render("REPLAY", True, (255, 220, 120))
            self.screen.blit(t, (SCREEN_W - t.get_width() - 8, 4))

    def _render_world(self) -> None:
        for e in self.enemies:
            e.draw(self.screen)
        if self.boss and self.boss.is_active():
            self.boss.draw(self.screen)
        if self.show_overlay:
            for e in self.enemies:
                e.draw_hitbox(self.screen)
            if self.boss and self.boss.is_active():
                self.boss.draw_hitbox(self.screen)

        self.lasers.draw(self.screen)
        self.pool.draw(self.screen)
        self.items.draw(self.screen)
        self.hit_particles.draw(self.screen)
        self.graze_rings.draw(self.screen)

        focus_mode = self.input.is_held("shift") and self.player.alive
        self.player.draw(self.screen)
        if self.show_overlay:
            self.player.draw_hitbox(self.screen, focus_mode=True)
            self.player.draw_graze_ring(self.screen, focus_mode=False, debug=True)
        elif focus_mode:
            self.player.draw_hitbox(self.screen, focus_mode=True)
            self.player.draw_graze_ring(self.screen, focus_mode=True, debug=False)

        for fx in self.death_effects:
            fx.draw(self.screen)

        if self.scene in ("play", "paused"):
            self.hud.draw(self.screen, self.player, self._fps,
                          paused=self.paused,
                          frame_step_request=self.frame_step_request,
                          god_mode=self.god_mode,
                          difficulty=self.difficulty,
                          continue_left=self.continue_left,
                          bomb_active=self.player.is_in_bomb(),
                          boss=self.boss)

        if self.show_overlay:
            self.overlay.draw(self.screen, self.player, self.pool, self.enemies,
                              fps=self._fps, paused=self.paused,
                              frame_step_request=self.frame_step_request,
                              god_mode=self.god_mode)
            extra = (f"Items: {self.items.count()}   Lasers: {self.lasers.count()}"
                     f"   Hits: {self.hit_particles.count()}   Grazes: {self.graze_rings.count()}")
            pygame.draw.rect(self.screen, (0, 0, 0),
                             (SCREEN_W - 248, 60 + 10 * 16 + 4, 240, 16), 0)
            t = pygame.font.SysFont("consolas", 11).render(extra, True, (220, 220, 220))
            self.screen.blit(t, (SCREEN_W - 248 + 6, 60 + 10 * 16 + 4))