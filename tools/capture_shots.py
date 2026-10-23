# -*- coding: utf-8 -*-
"""tools/capture_shots.py — 无头截图 (给 README / 人工检查排版用)

用 SDL dummy 驱动把真实渲染结果存成 PNG, 不需要显示器:
    python tools/capture_shots.py [输出目录]

默认输出到 docs/screenshots/。
"""
from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame  # noqa: E402

from config import LOGIC_DT  # noqa: E402
from src.core.game import Game  # noqa: E402


def save(game: Game, out_dir: str, name: str) -> None:
    game._render()
    path = os.path.join(out_dir, name)
    pygame.image.save(game.screen, path)
    print("  " + os.path.relpath(path, ROOT))


def main() -> int:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "screenshots")
    out_dir = out_dir if os.path.isabs(out_dir) else os.path.join(ROOT, out_dir)
    os.makedirs(out_dir, exist_ok=True)

    game = Game()
    game.god_mode = True
    game._title_card_t = 0.0

    # 1) 标题
    game.scene = "title"
    save(game, out_dir, "01_title.png")

    # 2) 剧情: 第一章开场, 推进到有人说话的台词
    game._start_story(difficulty=1)
    for _ in range(4):
        game.dialogue.advance()
    for _ in range(90):          # 1.5s 打字机
        game.dialogue.update(LOGIC_DT)
        game.dialogue_box.update(LOGIC_DT)
    save(game, out_dir, "02_story.png")

    # 3) 道中战斗 (第三章, 有环弹 + 分裂弹, 要能看到敌机)
    game._start_practice(difficulty=1, stage_id=3)
    game._title_card_t = 0.0
    game.player.x, game.player.y = 320.0, 380.0
    frames = 0
    while game.stage_elapsed < 12.4 and frames < 60 * 40:
        game._step(LOGIC_DT)
        frames += 1
    save(game, out_dir, "03_gameplay.png")

    # 4) Boss 战 (第三章 Boss, 符卡进行中)
    game = Game()
    game.god_mode = True
    game._start_practice(difficulty=1, stage_id=3)
    game._title_card_t = 0.0
    game.player.x, game.player.y = 320.0, 390.0
    frames = 0
    while frames < 60 * 120:
        game._step(LOGIC_DT)
        frames += 1
        if game.boss is not None and game.boss.state == "spell":
            for _ in range(150):
                game._step(LOGIC_DT)
            break
    save(game, out_dir, "04_boss.png")

    # 5) 章节标题卡 (等淡入完成再截)
    game = Game()
    game._start_practice(difficulty=1, stage_id=2)
    for _ in range(30):
        game._step(LOGIC_DT)
    save(game, out_dir, "05_titlecard.png")

    # 6) ALL CLEAR 结算
    game = Game()
    game._start_practice(difficulty=1, stage_id=6)
    game.player.score = 12345678
    game.player.lives = 3
    game.player.bombs = 2
    game.player.power = 96
    game.player.graze_count = 1234
    game.chapters_cleared = 6
    game.continue_used = 0
    game.scene = "allclear"
    game._best_score = 12345678
    save(game, out_dir, "06_allclear.png")

    # 7) EX 章剧情 (残响)
    game = Game()
    game.save._path = os.path.join(tempfile.mkdtemp(prefix="touhou-shot-"), "records.json")
    game.save.add_clear(1)
    game._start_ex(difficulty=1)
    for _ in range(4):
        game.dialogue.advance()
    for _ in range(90):
        game.dialogue.update(LOGIC_DT)
        game.dialogue_box.update(LOGIC_DT)
    save(game, out_dir, "07_ex_story.png")

    # 8) 符卡激光 (跳到本关 Boss 的激光符卡)
    game = Game()
    game.god_mode = True
    game._start_practice(difficulty=1, stage_id=7)
    game._title_card_t = 0.0
    game.player.x, game.player.y = 320.0, 400.0
    frames = 0
    while frames < 60 * 130:
        game._step(LOGIC_DT)
        frames += 1
        if game.boss is not None and game.boss.label == "Boss":
            break
    if game.boss is not None:
        # 跳过入场动画: 直接摆到悬停点, 否则激光会从屏幕外打下来
        game.boss.age = 999.0
        game.boss.x, game.boss.y = 320.0, 140.0
        for idx, sc in enumerate(game.boss.spellcards):
            if sc.lasers:
                game.boss._start_spell(idx)
                break
        for _ in range(140):
            game._step(LOGIC_DT)
        save(game, out_dir, "08_lasers.png")

    game._close_recorder()
    pygame.quit()
    print("\n截图完成")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
