# -*- coding: utf-8 -*-
"""core/game.py — 主循环 (v1.0 剧情版)

v1.0 变化:
  - 剧情模式: 六章连续闯关。章首(prologue) / Boss 登场(boss_intro) / 章末(clear)
    都会插入对话, 对话期间游戏世界冻结。
  - 章节衔接: 残机 / 炸弹 / 火力 / 分数 / 擦弹数跨章保留。
  - 单关练习模式: 任意章 / 教学关 / EX 关单独打, 保留原有 Stage Clear 评级。
  - ALL CLEAR 结算 + save/records.json 最高分存档。
  - 开场标题卡 (章节名淡入淡出)。

场景 (self.scene):
  title       标题菜单
  story       剧情对话 (世界冻结)
  play        游戏中
  paused      暂停
  gameover    Game Over
  stageclear  单关通过 (练习模式)
  allclear    剧情模式全通
"""
from __future__ import annotations

import os
import random
import sys

import pygame

from src.core.input_manager import InputManager
from src.core.assets import AssetLoader, default_loader
from src.core.replay import ReplayRecorder, ReplayPlayer
from src.core.save_data import SaveData
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
from src.stages.stage_factory import make_stage, Stage, stage_label, MAX_STAGE as MAX_STAGE_ID
from src.stages.stage1 import Stage1
from src.story.dialogue import DialogueController
from src.story.model import Campaign, Chapter, load_campaign
from src.ui.fonts import get_font
from src.ui.hud import HUD
from src.ui.dialoguebox import DialogueBox, draw_chapter_title
from src.ui.overlay import DebugOverlay
from src.ui.menu import MenuSystem
from config import (
    SCREEN_W, SCREEN_H, LOGIC_DT, MAX_FRAME_DT,
    PLAYER_HITBOX_RADIUS, PLAYER_GRAZE_RADIUS,
    PLAYER_SPAWN_X, PLAYER_INVULN_TIME, PLAYER_DEATH_INVULN_FRAMES,
    PLAYER_START_LIVES, PLAYER_START_BOMBS, PLAYER_START_POWER,
    COLOR_BG, COLOR_TEXT_DIM,
    DIFFICULTY_DEFAULT, DIFFICULTY_MULTIPLIERS, DIFFICULTY_NAMES,
    CONTINUE_MAX, CONTINUE_LIVES, CONTINUE_BOMBS, CONTINUE_POWER,
    BOSS_DEFEAT_P_DROP, BOSS_DEFEAT_SCORE_DROP, BOSS_DEFEAT_DROP_JITTER,
    STAGE_TITLE_CARD_TIME, CHAPTER_CLEAR_BONUS, ALL_CLEAR_BONUS, EX_CLEAR_BONUS,
)

# ---------------- 模式 ----------------
MODE_STORY = "story"
MODE_PRACTICE = "practice"

# ---------------- 对话结束后的去向 ----------------
AFTER_PLAY = "play"
AFTER_NEXT_CHAPTER = "next_chapter"
AFTER_FINISH_RUN = "finish_run"
AFTER_ALL_CLEAR = "all_clear"


def difficulty_multiplier(level: int) -> dict:
    if 0 <= level < len(DIFFICULTY_MULTIPLIERS):
        return DIFFICULTY_MULTIPLIERS[level]
    return DIFFICULTY_MULTIPLIERS[DIFFICULTY_DEFAULT]


def _replay_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "replay")


class Game:
    MAX_STAGE = MAX_STAGE_ID

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Touhou-style STG  —  星屑异变 (v1.0)")
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

        # ---- 剧情 ----
        self.campaign: Campaign | None = None
        try:
            self.campaign = load_campaign()
        except (OSError, ValueError) as e:
            print(f"[story] 剧情数据加载失败, 剧情模式不可用: {e}")
        self.dialogue = DialogueController()
        self.dialogue_box = DialogueBox()
        self._story_after = AFTER_PLAY
        self._title_card_t = 0.0
        self._title_card_pending: tuple[str, str] | None = None
        self._title_card_title = ""
        self._title_card_sub = ""
        self._boss_intro_played = False
        self._chapter_font = get_font(12, cjk=True)

        # ---- 存档 / 进度 ----
        self.save = SaveData()
        self.mode = MODE_PRACTICE
        self.chapter_index = 0
        self.chapters_cleared = 0
        self._chapters: list[Chapter] = []       # 本局要打的章节序列
        self._is_ex = False                      # 当前是否在打 EX 章
        self._carry: dict | None = None
        self._chapter_carry: dict | None = None  # 进入本章时的资源快照 (重开本章用)
        self._best_score = self.save.best_score(DIFFICULTY_DEFAULT)

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

    # ================= 启动 / 主循环 =================
    def run(self) -> None:
        running = True
        while running:
            events = pygame.event.get()
            # Replay 模式: 不读事件, 由 _advance 内 replay_player 注入
            if not self.is_replaying:
                self.input.update(events)
            for ev in events:
                if ev.type == pygame.QUIT:
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

            if self.scene == "story":
                self._update_story(dt)
            elif self.scene == "play":
                self._advance(dt)

            self._render()
            pygame.display.flip()

        self._close_recorder()
        self.save.save()
        pygame.quit()
        sys.exit(0)

    # ================= 剧情 =================
    def _update_story(self, dt: float) -> None:
        self.dialogue.update(dt)
        self.dialogue_box.update(dt)
        if self.input.consume_press("x"):
            self.dialogue.skip_all()
        elif (self.input.consume_press("z") or self.input.consume_press("enter")
              or self.input.consume_press("space")):
            self.dialogue.advance()
        if self.dialogue.finished:
            self._finish_story()

    def _play_story(self, lines: list, after: str) -> None:
        """进入剧情场景; 没有台词就直接执行后续动作。"""
        if not lines:
            self._story_after = after
            self._finish_story()
            return
        self.dialogue.start(lines)
        self._story_after = after
        self.scene = "story"
        self.paused = False

    def _finish_story(self) -> None:
        after = self._story_after
        self._story_after = AFTER_PLAY
        # 防止对话里的 Z 漏到游戏里变成射击
        self.input.clear_pressed()
        if after == AFTER_NEXT_CHAPTER:
            self._advance_chapter()
        elif after == AFTER_FINISH_RUN:
            self._finish_run()
        elif after == AFTER_ALL_CLEAR:
            self._all_clear()
        else:
            self._begin_play()

    def _begin_play(self) -> None:
        self.scene = "play"
        self.paused = False
        self.frame_step_request = False
        if self._title_card_pending is not None:
            self._title_card_title, self._title_card_sub = self._title_card_pending
            self._title_card_pending = None
            self._title_card_t = STAGE_TITLE_CARD_TIME
        self._start_recording()

    # ================= 章节流程 =================
    def _total_chapters(self) -> int:
        return len(self._chapters)

    def _current_chapter(self) -> Chapter | None:
        if not (0 <= self.chapter_index < len(self._chapters)):
            return None
        return self._chapters[self.chapter_index]

    def _start_story(self, difficulty: int) -> None:
        if not self.campaign:
            self._start_practice(difficulty, 1)
            return
        self.mode = MODE_STORY
        self.difficulty = difficulty
        self._is_ex = False
        self._chapters = list(self.campaign.chapters)
        self.chapter_index = 0
        self.chapters_cleared = 0
        self.continue_left = CONTINUE_MAX
        self.continue_used = 0
        self._carry = {
            "score": 0,
            "lives": PLAYER_START_LIVES,
            "bombs": PLAYER_START_BOMBS,
            "power": PLAYER_START_POWER,
            "graze": 0,
        }
        self._begin_chapter()

    def _ex_unlocked(self) -> bool:
        """EX 章解锁条件: 本篇至少全通一次 (任意难度)。"""
        return (self.campaign is not None
                and self.campaign.ex_chapter is not None
                and self.save.total_clears() > 0)

    def _start_ex(self, difficulty: int) -> None:
        """EX 章: 单章剧情, 打完直接 EX CLEAR, 不播本篇结局。"""
        if not self._ex_unlocked():
            print("[story] EX 章未解锁: 需要先通关本篇一次")
            return
        ex = self.campaign.ex_chapter
        assert ex is not None
        self.mode = MODE_STORY
        self.difficulty = difficulty
        self._is_ex = True
        self._chapters = [ex]
        self.chapter_index = 0
        self.chapters_cleared = 0
        self.continue_left = CONTINUE_MAX
        self.continue_used = 0
        self._carry = {
            "score": 0,
            "lives": PLAYER_START_LIVES,
            "bombs": PLAYER_START_BOMBS,
            "power": PLAYER_START_POWER,
            "graze": 0,
        }
        self._begin_chapter()

    def _begin_chapter(self) -> None:
        ch = self._current_chapter()
        if ch is None:
            self._finish_run()
            return
        # 记下进入本章时的资源, 暂停里「重开本章」回到这个状态
        self._chapter_carry = dict(self._carry) if self._carry else None
        self._reset_stage_objects(ch.stage_id)
        self._reset_player(self._carry)
        self._title_card_pending = (ch.display_title, self.stage.name)
        self._boss_intro_played = False
        self._play_story(ch.prologue, AFTER_PLAY)

    def _restart_chapter(self) -> None:
        """暂停菜单的「重开本章」: 回到本章开局状态, 不再播开场对话。"""
        ch = self._current_chapter()
        if ch is None:
            return
        self._close_recorder()
        self._reset_stage_objects(ch.stage_id)
        self._reset_player(self._chapter_carry)
        self._title_card_pending = (ch.display_title, self.stage.name)
        self._boss_intro_played = True
        self._begin_play()

    def _advance_chapter(self) -> None:
        """一章打完: 结算分数, 存下 carry, 进入下一章。"""
        self._close_recorder()
        self.chapters_cleared += 1
        self.player.score += CHAPTER_CLEAR_BONUS
        self._carry = {
            "score": self.player.score,
            "lives": self.player.lives,
            "bombs": self.player.bombs,
            "power": self.player.power,
            "graze": self.player.graze_count,
        }
        self.chapter_index += 1
        if self.chapter_index >= self._total_chapters():
            self._finish_run()
        else:
            self._begin_chapter()

    def _finish_run(self) -> None:
        """最后一章打完: 本篇播结局, EX 章直接结算。"""
        self._close_recorder()
        if (not self._is_ex and self.campaign and self.campaign.ending
                and self.scene != "allclear"):
            self._play_story(self.campaign.ending, AFTER_ALL_CLEAR)
        else:
            self._all_clear()

    def _all_clear(self) -> None:
        self.player.score += EX_CLEAR_BONUS if self._is_ex else ALL_CLEAR_BONUS
        self.save.submit(self.difficulty, self.player.score)
        self.save.add_clear(self.difficulty)
        self._refresh_best()
        self.scene = "allclear"
        self.paused = False
        self._close_recorder()

    def _start_practice(self, difficulty: int, stage_id: int) -> None:
        self.mode = MODE_PRACTICE
        self.difficulty = difficulty
        self.stage_id = max(0, min(self.MAX_STAGE, stage_id))
        self.continue_left = CONTINUE_MAX
        self.continue_used = 0
        self._carry = None
        self._chapter_carry = None
        self.chapter_index = 0
        self.chapters_cleared = 0
        self._is_ex = False
        self._chapters = []
        self._reset_stage_objects(self.stage_id)
        self._reset_player(None)
        self.player.score = 0
        self._title_card_pending = (self.stage.name, "单关练习")
        self._boss_intro_played = True  # 练习模式不插 Boss 对话
        self._begin_play()

    # ================= 世界重置 =================
    def _reset_stage_objects(self, stage_id: int) -> None:
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
        self.stage = make_stage(self.stage_id)
        self.stage_elapsed = 0.0
        self._accumulator = 0.0
        self._death_effect_pending = False
        self._last_spell_index = -1
        self._drop_rng = random.Random(2026 + self.difficulty * 7 + self.stage_id * 13)
        self.paused = False
        self.frame_step_request = False
        self.is_replaying = False

    def _reset_player(self, carry: dict | None) -> None:
        self.player = Player()
        if carry:
            self.player.score = int(carry.get("score", 0))
            self.player.lives = int(carry.get("lives", PLAYER_START_LIVES))
            self.player.bombs = int(carry.get("bombs", PLAYER_START_BOMBS))
            self.player.power = int(carry.get("power", PLAYER_START_POWER))
            self.player.graze_count = int(carry.get("graze", 0))

    # ================= 行动作 =================
    def _apply_action(self, action: tuple) -> None:
        kind = action[0]
        if kind == "start_story":
            self._start_story(difficulty=action[1])
        elif kind == "start_practice":
            self._start_practice(difficulty=action[1], stage_id=action[2])
        elif kind == "start_ex":
            self._start_ex(difficulty=action[1])
        elif kind == "restart_stage":
            # 暂停里按 R: 只重开当前这一关/一章
            if self.mode == MODE_STORY:
                self._restart_chapter()
            else:
                self._start_practice(self.difficulty, self.stage_id)
        elif kind == "restart":
            # Game Over / 结算画面按 R: 整局重来
            if self.mode == MODE_STORY:
                if self._is_ex:
                    self._start_ex(self.difficulty)
                else:
                    self._start_story(self.difficulty)
            else:
                self._start_practice(self.difficulty, self.stage_id)
        elif kind == "continue_or_restart":
            if self.continue_left > 0:
                self._do_continue()
            else:
                self._apply_action(("restart",))
        elif kind == "resume":
            self.paused = False
        elif kind == "to_title":
            self._close_recorder()
            self.is_replaying = False
            self.paused = False
            self.scene = "title"
            self.menu.reset_for_title()
            self._refresh_best()
        elif kind == "set_difficulty":
            self.difficulty = action[1]
        elif kind == "set_stage":
            self.stage_id = max(0, min(self.MAX_STAGE, action[1]))
        elif kind == "list_replays":
            files = self.list_replays()
            if files:
                self._start_replay(files[-1])
            else:
                print("[replay] no replay files in", _replay_dir())
        elif kind == "start_replay":
            self._start_replay(action[1])
        elif kind == "quit":
            self._close_recorder()
            self.save.save()
            pygame.quit()
            sys.exit(0)

    def _refresh_best(self) -> None:
        diff = self.difficulty if self.scene != "title" else self.menu._title_diff_cursor
        self._best_score = self.save.best_score(diff)

    def _do_continue(self) -> None:
        self.continue_left -= 1
        self.continue_used += 1
        prev_score = self.player.score
        stage_id = self.stage_id
        self._reset_stage_objects(stage_id)
        self._reset_player(None)
        self.player.score = prev_score if self.mode == MODE_STORY else 0
        self.player.lives = CONTINUE_LIVES
        self.player.bombs = CONTINUE_BOMBS
        self.player.power = CONTINUE_POWER
        self.player.invuln_time = PLAYER_INVULN_TIME
        self.player.death_invuln_left = PLAYER_DEATH_INVULN_FRAMES
        self._boss_intro_played = True  # 续关不重复播 Boss 登场
        self._begin_play()

    def _start_replay(self, filename: str) -> None:
        path = os.path.join(_replay_dir(), filename)
        if not os.path.isfile(path):
            return
        self.replay_player = ReplayPlayer(path)
        meta = self.replay_player.meta
        self.difficulty = meta.get("difficulty", DIFFICULTY_DEFAULT)
        self.stage_id = meta.get("stage_id", 1)
        self.mode = MODE_PRACTICE
        self._reset_stage_objects(self.stage_id)
        self._reset_player(None)
        self._drop_rng = random.Random(meta.get("seed", 2026))
        self.is_replaying = True
        self._close_recorder()
        self._title_card_t = 0.0
        self._title_card_pending = None
        self.scene = "play"
        self.paused = False
        self.frame_step_request = False

    # ================= Replay 录制 =================
    def _close_recorder(self) -> None:
        if self.recorder:
            self.recorder.close()
            self.recorder = None

    def _start_recording(self) -> None:
        if self.is_replaying:
            return
        self._close_recorder()
        try:
            os.makedirs(_replay_dir(), exist_ok=True)
            tag = (f"ch{self.chapter_index + 1}" if self.mode == MODE_STORY
                   else f"s{self.stage_id}")
            fname = (f"{tag}_{DIFFICULTY_NAMES[self.difficulty].lower()}_"
                     f"{int(random.random() * 1e6)}.ndjson")
            self.recorder = ReplayRecorder(os.path.join(_replay_dir(), fname), {
                "stage_id": self.stage_id,
                "difficulty": self.difficulty,
                "seed": 2026 + self.difficulty * 7 + self.stage_id * 13,
                "mode": self.mode,
            })
        except OSError:
            self.recorder = None

    def list_replays(self) -> list[str]:
        d = _replay_dir()
        if not os.path.isdir(d):
            return []
        return sorted([f for f in os.listdir(d) if f.endswith(".ndjson")])

    # ================= 推进 =================
    def _advance(self, dt: float) -> None:
        """固定步长推进; Replay 时用 replay_player.inject。"""
        if self.is_replaying and self.replay_player:
            end = self.replay_player.apply_until(self.stage_elapsed, self.input)
            if end:
                self.scene = "stageclear"
                self.input.exit_inject_mode()
                self.is_replaying = False

        if not self.paused or self.frame_step_request:
            self._accumulator += dt
            while self._accumulator >= LOGIC_DT:
                self._step(LOGIC_DT)
                self._accumulator -= LOGIC_DT
                if self.scene != "play":
                    # 本帧内发生了场景切换 (Boss 击破 / 剧情插入), 丢掉余量
                    self._accumulator = 0.0
                    break
            if self.frame_step_request:
                self.frame_step_request = False
                self.paused = True

        if self.recorder and not self.is_replaying:
            self.recorder.record_frame(
                self.stage_elapsed,
                self.input._held,
                self.input._pressed_this_frame,
            )

    def _step(self, dt: float) -> None:
        self.stage_elapsed += dt
        if self._title_card_t > 0:
            self._title_card_t = max(0.0, self._title_card_t - dt)

        self.stage.update(dt, self.enemies, self._boss_pending, self.pool,
                          self.player, self.difficulty)
        if self._boss_pending:
            self.boss = self._boss_pending.pop(0)
            self._last_spell_index = -1
            # 最后一个 pending boss = 本关 Boss, 首次登场插一段对话
            if (self.mode == MODE_STORY and not self._boss_intro_played
                    and not self._boss_pending):
                ch = self._current_chapter()
                self._boss_intro_played = True
                if ch is not None and ch.boss_intro:
                    self._play_story(ch.boss_intro, AFTER_PLAY)
                    return

        self.player.update(dt, self.input, self.pool)
        for e in self.enemies:
            e.update(dt, self.pool, self.player.x, self.player.y)
        if self.boss:
            self.boss.update(dt, self.pool, self.player)
            self._check_spell_announce()
            if self.boss.is_dead():
                self._on_boss_defeated()
                if self.scene != "play":
                    return

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
            self.save.submit(self.difficulty, self.player.score)
            self._refresh_best()
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

        if self.mode == MODE_STORY:
            ch = self._current_chapter()
            self._carry = {
                "score": self.player.score,
                "lives": self.player.lives,
                "bombs": self.player.bombs,
                "power": self.player.power,
                "graze": self.player.graze_count,
            }
            if ch is not None and ch.clear:
                self._play_story(ch.clear, AFTER_NEXT_CHAPTER)
            else:
                self._advance_chapter()
        else:
            self.save.submit(self.difficulty, self.player.score)
            self._refresh_best()
            self.scene = "stageclear"
            self._close_recorder()
            if self.is_replaying:
                self.input.exit_inject_mode()
                self.is_replaying = False

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
                            self.hit_particles.spawn(self.boss.x, self.boss.y,
                                                     (255, 220, 120), count=16)
                    else:
                        self.hit_particles.spawn(b.x, b.y, (200, 220, 255), count=3)
                    self.pool.release(b)
                    del pb_list[i]

    # ================= 渲染 =================
    def _render(self) -> None:
        self.screen.fill(COLOR_BG)
        self.background.draw(self.screen)

        if self.scene in ("play", "paused", "story", "gameover", "stageclear", "allclear"):
            self._render_world()

        if self.scene == "title":
            self.menu.draw(self.screen, "title", best_score=self._best_score,
                           ex_unlocked=self._ex_unlocked())
        elif self.scene == "paused":
            self.menu.draw(self.screen, "paused")
        elif self.scene == "gameover":
            self.menu.draw(self.screen, "gameover", player=self.player,
                           difficulty=self.difficulty, continue_left=self.continue_left,
                           stage_id=self.stage_id)
        elif self.scene == "stageclear":
            self.menu.draw(self.screen, "stageclear", player=self.player,
                           difficulty=self.difficulty,
                           continue_left=self.continue_left,
                           continue_used=self.continue_used,
                           stage_id=self.stage_id)
        elif self.scene == "allclear":
            self.menu.draw(self.screen, "allclear", player=self.player,
                           difficulty=self.difficulty,
                           continue_used=self.continue_used,
                           chapters_cleared=self.chapters_cleared,
                           total_chapters=self._total_chapters(),
                           best_score=self._best_score,
                           is_ex=self._is_ex)
        elif self.scene == "story" and self.campaign:
            self.dialogue_box.draw(self.screen, self.dialogue, self.campaign.characters)

        if self._title_card_t > 0 and self.scene == "play":
            draw_chapter_title(self.screen, self._title_card_title,
                               self._title_card_sub,
                               STAGE_TITLE_CARD_TIME - self._title_card_t)

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
            self._draw_chapter_tag()
            if self.stage_id == 0:
                self._draw_tutorial_hints()

        if self.show_overlay:
            self.overlay.draw(self.screen, self.player, self.pool, self.enemies,
                              fps=self._fps, paused=self.paused,
                              frame_step_request=self.frame_step_request,
                              god_mode=self.god_mode)
            extra = (f"Items: {self.items.count()}   Lasers: {self.lasers.count()}"
                     f"   Hits: {self.hit_particles.count()}   Grazes: {self.graze_rings.count()}")
            pygame.draw.rect(self.screen, (0, 0, 0),
                             (SCREEN_W - 248, 60 + 10 * 16 + 4, 240, 16), 0)
            t = get_font(11).render(extra, True, (220, 220, 220))
            self.screen.blit(t, (SCREEN_W - 248 + 6, 60 + 10 * 16 + 4))

    def _draw_chapter_tag(self) -> None:
        if self.mode != MODE_STORY or not self.campaign:
            return
        txt = (f"CH {self.chapter_index + 1}/{self._total_chapters()}"
               f"   {stage_label(self.stage_id)}")
        t = self._chapter_font.render(txt, True, COLOR_TEXT_DIM)
        self.screen.blit(t, (8, 70))

    def _draw_tutorial_hints(self) -> None:
        lines = self._tutorial_hints
        if not lines:
            return
        f = get_font(14, cjk=True)
        total_h = len(lines) * 20 + 12
        top = 140
        panel = pygame.Surface((SCREEN_W - 80, total_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        self.screen.blit(panel, (40, top))
        for i, line in enumerate(lines):
            t = f.render(line, True, (210, 225, 255))
            self.screen.blit(t, (56, top + 6 + i * 20))
