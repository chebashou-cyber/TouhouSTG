# -*- coding: utf-8 -*-
"""tools/story_smoke.py — 剧情模式端到端无头测试

跑真 pygame (SDL dummy 驱动), 不弹窗口, 但走完整渲染与游戏逻辑:
  1. 剧情数据 / 关卡数据引用的完整性
  2. 六章连续闯关直到 ALL CLEAR (自动跳过对话 + 秒杀 Boss)
  3. 章节衔接时残机/分数是否正确继承
  4. 单关练习模式 0..9 全部能开局并渲染
  5. 对话状态机 (打字机 / 翻页 / 跳过) 行为

用法:
    python tools/story_smoke.py
退出码: 0 通过 / 1 失败
"""
from __future__ import annotations

import os
import sys
import tempfile
import traceback

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame  # noqa: E402

from config import LOGIC_DT  # noqa: E402
from src.core import game as game_mod  # noqa: E402
from src.story.model import load_campaign  # noqa: E402
from src.story.dialogue import DialogueController  # noqa: E402
from src.story.model import Line  # noqa: E402
from src.stages import stage_factory  # noqa: E402
from src.stages.loader import load_stage, build_waves, build_bosses  # noqa: E402

failures: list[str] = []


def check(name: str, fn) -> None:
    try:
        fn()
        print("OK   " + name)
    except Exception as e:
        detail = traceback.format_exc().strip().splitlines()[-1]
        failures.append(f"{name}: {type(e).__name__}: {detail}")
        print("FAIL " + name + ": " + type(e).__name__ + ": " + detail)


def _press(game, *keys: str) -> None:
    for k in keys:
        game.input._pressed_this_frame.add(k)


# ---------------------------------------------------------------- 1. 数据
def story_data():
    c = load_campaign()
    assert len(c.chapters) == 6, f"应为 6 章, 实际 {len(c.chapters)}"
    assert c.ending, "缺少结局台词"
    for ch in c.chapters:
        assert ch.prologue or ch.clear, f"章 {ch.id} 没有任何台词"
        path = stage_factory._stage_json_path(ch.stage_id)
        assert os.path.isfile(path), f"章 {ch.id} 的关卡文件不存在: {path}"
    assert c.ex_chapter is not None, "缺少 EX 章 (ex_chapter)"
    assert c.ex_chapter.prologue and c.ex_chapter.clear, "EX 章台词不完整"
    ex_path = stage_factory._stage_json_path(c.ex_chapter.stage_id)
    assert os.path.isfile(ex_path), f"EX 章关卡文件不存在: {ex_path}"


check("剧情数据: 6 章 + EX 章 + 结局 + 关卡文件齐全", story_data)


def stage_data():
    for sid in sorted(stage_factory.STAGE_FILE_MAP):
        path = stage_factory._stage_json_path(sid)
        assert os.path.isfile(path), f"stage {sid} 缺文件 {path}"
        data = load_stage(path)
        assert data.get("name"), f"stage {sid} 缺 name"
        waves = build_waves(data)
        bosses = build_bosses(data)
        assert waves, f"stage {sid} 没有 waves"
        assert bosses, f"stage {sid} 没有 boss"
        for _, b in bosses:
            assert len(b.spellcards) > 0, f"stage {sid} 有 Boss 没符卡"
        # 至少生成一次敌机, 确认 emitter 组装没问题
        n = 0
        for w in waves:
            n += len(w.spawn(difficulty=1))
        assert n > 0, f"stage {sid} 生成敌机数为 0"
        print(f"     stage {sid:<2} {stage_factory.stage_label(sid):<16}"
              f" waves={len(waves):<2} bosses={len(bosses)} enemies={n}")


check("关卡数据: stage 0..10 全部可加载/生成", stage_data)


# ---------------------------------------------------------------- 2. 对话状态机
def dialogue_logic():
    c = DialogueController()
    lines = [Line("rein", "一二三四五六七八九十"), Line(None, "旁白"), Line("ruye", "完")]
    c.start(lines)
    assert c.active and c.current is c.lines[0]
    assert c.text_visible() == ""
    c.update(0.1)                      # 34 字/秒 -> 约 3 字
    assert 0 < len(c.text_visible()) < 10
    c.advance()                        # 未打完 -> 立刻打完
    assert c.line_complete() and len(c.text_visible()) == 10
    c.advance()                        # 打到下一句
    assert c.index == 1 and not c.line_complete()
    c.skip_all()
    assert c.finished, "skip_all 后应结束"


check("对话状态机: 打字机/翻页/跳过", dialogue_logic)


# ---------------------------------------------------------------- 3. 全流程
def full_campaign():
    game = game_mod.Game()
    # 存档写到临时目录, 不污染 save/records.json
    tmp = tempfile.mkdtemp(prefix="touhou-save-")
    game.save._path = os.path.join(tmp, "records.json")
    game.god_mode = True
    game._start_story(difficulty=1)
    assert game.scene == "story", f"开场应进入剧情, 实际 {game.scene}"
    assert len(game.campaign.chapters) == 6

    chapters_entered: list[int] = []
    scenes_seen: set[str] = set()
    score_in_chapter: dict[int, int] = {}
    frames = 0
    limit = 400000
    while game.scene != "allclear" and frames < limit:
        frames += 1
        scenes_seen.add(game.scene)
        if game.scene == "story":
            _press(game, "z")
            game._update_story(LOGIC_DT)
        elif game.scene == "play":
            if not chapters_entered or chapters_entered[-1] != game.chapter_index:
                chapters_entered.append(game.chapter_index)
                score_in_chapter[game.chapter_index] = game.player.score
            game._step(LOGIC_DT)
            b = game.boss
            if b is not None and b.state == "spell":
                b.hit(10 ** 7)          # 秒掉当前符卡
        elif game.scene in ("gameover", "stageclear", "title"):
            raise AssertionError(f"剧情模式不该进入 {game.scene}")
        if frames % 25 == 0:
            game._render()

    print(f"     模拟帧数={frames}  场景={sorted(scenes_seen)}  进入章节={chapters_entered}")
    assert game.scene == "allclear", f"未通关, 停在 {game.scene} (帧数 {frames})"
    assert frames < limit, "超过帧数上限"
    assert game.chapters_cleared == 6, f"通章节数应为 6, 实际 {game.chapters_cleared}"
    assert chapters_entered == [0, 1, 2, 3, 4, 5], f"章节顺序异常: {chapters_entered}"
    assert game.player.score > 0, "通关分数应大于 0"
    assert game.save.best_score(1) > 0, "最高分未写入存档"
    # 章节衔接: 第 2 章开局分数应大于 0 (第一章的分数被带过来了)
    assert score_in_chapter.get(1, 0) > 0, "第二章没有继承第一章的分数"
    assert game.save.clear_count(1) == 1, "全通次数未记录"
    game._render()                     # ALL CLEAR 画面渲染
    game._close_recorder()
    print(f"     最终分数={game.player.score} 残机={game.player.lives}"
          f" 火力={game.player.power} 擦弹={game.player.graze_count}")


check("剧情模式: 六章连续闯关直到 ALL CLEAR", full_campaign)


# ---------------------------------------------------------------- 4. 练习模式
def practice_all_stages():
    game = game_mod.Game()
    tmp = tempfile.mkdtemp(prefix="touhou-save-")
    game.save._path = os.path.join(tmp, "records.json")
    game.god_mode = True
    for sid in range(game_mod.MAX_STAGE_ID + 1):
        game._start_practice(difficulty=1, stage_id=sid)
        assert game.scene == "play", f"stage {sid} 未进入 play"
        assert game.stage_id == sid, f"stage {sid} id 不符: {game.stage_id}"
        for _ in range(10):
            game._step(LOGIC_DT)
        game._render()
        assert game.stage.name, f"stage {sid} 无关卡名"
    game._close_recorder()
    print(f"     练习模式 0..{game_mod.MAX_STAGE_ID} 全部可开局")


check(f"练习模式: 0..{game_mod.MAX_STAGE_ID} 全部可开局并渲染", practice_all_stages)


# ---------------------------------------------------------------- 5. 菜单/标题渲染
def title_and_menus():
    game = game_mod.Game()
    game.scene = "title"
    game._render()
    for scene in ("paused", "gameover", "stageclear"):
        game.scene = scene
        game._render()
        game.scene = "title"
    game._render()


check("标题/暂停/GameOver/StageClear 画面渲染", title_and_menus)


# ---------------------------------------------------------------- 6. 暂停重开本章
def pause_restart_chapter():
    """暂停里的 R 只能重开当前章, 不能把整局重来。"""
    game = game_mod.Game()
    tmp = tempfile.mkdtemp(prefix="touhou-save-")
    game.save._path = os.path.join(tmp, "records.json")
    game.god_mode = True
    game._start_story(difficulty=1)
    game._finish_story()                     # 第一章开场对话结束 -> play
    game.player.score = 100000               # 假装打完第一章
    game._carry = {"score": 100000, "lives": 4, "bombs": 3, "power": 40, "graze": 12}
    game.chapter_index = 1
    game._begin_chapter()                    # 进入第二章
    game._finish_story()                     # 第二章开场对话结束 -> play
    assert game.chapter_index == 1, f"应在第二章, 实际 {game.chapter_index}"
    game.player.score = 555555               # 第二章中途得分
    game.player.lives = 1

    game._apply_action(("restart_stage",))

    assert game.chapter_index == 1, f"重开本章后章节变了: {game.chapter_index}"
    assert game.scene == "play", f"重开本章后场景: {game.scene}"
    assert game.player.score == 100000, f"分数应回到本章开局值, 实际 {game.player.score}"
    assert game.player.lives == 4, f"残机应回到本章开局值, 实际 {game.player.lives}"
    assert game.player.power == 40, f"火力应回到本章开局值, 实际 {game.player.power}"
    game._close_recorder()
    print(f"     重开本章: 章节={game.chapter_index} 分数={game.player.score}"
          f" 残机={game.player.lives} 火力={game.player.power}")


check("暂停重开本章: 回到本章开局状态, 不重开整局", pause_restart_chapter)


# ---------------------------------------------------------------- 7. EX 章
def ex_chapter_run():
    game = game_mod.Game()
    tmp = tempfile.mkdtemp(prefix="touhou-save-")
    game.save._path = os.path.join(tmp, "records.json")
    game.god_mode = True

    # 未通关时不可进
    game._start_ex(difficulty=1)
    assert game.scene == "title", "未解锁时不该进入 EX 章"
    assert not game._ex_unlocked(), "初次启动时 EX 不应解锁"

    # 伪造一次全通 -> 解锁
    game.save.add_clear(1)
    assert game._ex_unlocked(), "通关后 EX 未解锁"

    game._start_ex(difficulty=1)
    assert game.scene == "story", f"EX 开场应进入剧情, 实际 {game.scene}"
    assert game._is_ex, "EX 标志未置位"
    assert game._total_chapters() == 1, f"EX 应只有 1 章, 实际 {game._total_chapters()}"

    frames = 0
    limit = 200000
    while game.scene != "allclear" and frames < limit:
        frames += 1
        if game.scene == "story":
            _press(game, "z")
            game._update_story(LOGIC_DT)
        elif game.scene == "play":
            game._step(LOGIC_DT)
            b = game.boss
            if b is not None and b.state == "spell":
                b.hit(10 ** 7)
        else:
            raise AssertionError(f"EX 章不该进入 {game.scene}")
        if frames % 25 == 0:
            game._render()

    assert game.scene == "allclear", f"EX 未通关, 停在 {game.scene}"
    assert game.chapters_cleared == 1, f"EX 章计数应为 1, 实际 {game.chapters_cleared}"
    assert game.stage_id == 7, f"EX 关卡 id 应为 7, 实际 {game.stage_id}"
    game._render()                     # EX CLEAR 画面
    game._close_recorder()
    print(f"     EX 章通关: 帧数={frames} 分数={game.player.score}")


check("EX 章: 解锁条件 + 单章通关到 EX CLEAR", ex_chapter_run)


# ---------------------------------------------------------------- 8. LUNATIC 压力
def lunatic_stress():
    """LUNATIC 满密度跑 100 秒, 确认不崩、弹幕数量不会失控。"""
    game = game_mod.Game()
    tmp = tempfile.mkdtemp(prefix="touhou-save-")
    game.save._path = os.path.join(tmp, "records.json")
    game.god_mode = True
    game._start_practice(difficulty=3, stage_id=7)
    game._title_card_t = 0.0
    peak = 0
    for _ in range(60 * 100):
        game._step(LOGIC_DT)
        n = game.pool.enemy_count()
        if n > peak:
            peak = n
    assert peak < 12000, f"LUNATIC 弹幕数量失控: {peak}"
    game._close_recorder()
    print(f"     LUNATIC EX 关 100s: 峰值敌弹={peak}")


check("LUNATIC 压力: EX 关满密度 100s", lunatic_stress)


print()
print("=" * 60)
pygame.quit()
if failures:
    print(f" {len(failures)} FAILURES:")
    for f in failures:
        print("  - " + f)
    print("=" * 60)
    raise SystemExit(1)
print(" ALL STORY SMOKE TESTS PASSED")
print("=" * 60)
raise SystemExit(0)
