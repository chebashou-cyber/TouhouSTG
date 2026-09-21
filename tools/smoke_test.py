# -*- coding: utf-8 -*-
"""smoke_test.py - real pygame runtime smoke test (SDL_VIDEODRIVER=dummy)

Run full project code paths with real pygame. Discovers real
compatibility/type errors that stub-based tests miss.

Usage: python tools/smoke_test.py
Exit code: 0 pass / 1 fail
"""
from __future__ import annotations
import os
import sys
import traceback

# MUST set dummy driver BEFORE import pygame
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

import pygame
pygame.init()
try:
    pygame.mixer.init()
except Exception:
    pass

failures: list[str] = []


def check(name: str, fn) -> None:
    try:
        fn()
        print("OK  " + name)
    except Exception as e:
        tb = traceback.format_exc().strip().splitlines()[-1]
        failures.append(name + ": " + type(e).__name__ + ": " + tb)
        print("FAIL " + name + ": " + type(e).__name__ + ": " + tb)


print("=" * 60)
print(" smoke_test.py - real pygame (SDL_VIDEODRIVER=dummy)")
print("=" * 60)


def import_all():
    import config
    import core.input_manager  # noqa
    import core.rng  # noqa
    import core.assets  # noqa
    import core.replay  # noqa
    import entities.bullet  # noqa
    import entities.player  # noqa
    import entities.enemy  # noqa
    import entities.item  # noqa
    import entities.death_effect  # noqa
    import entities.background  # noqa
    import entities.boss  # noqa
    import entities.laser  # noqa
    import entities.hit_particle  # noqa
    import entities.graze_ring  # noqa
    import patterns.aimed  # noqa
    import patterns.fan  # noqa
    import patterns.ring  # noqa
    import patterns.spiral  # noqa
    import patterns.scatter  # noqa
    import patterns.spellcard  # noqa
    import patterns.delayed  # noqa
    import stages.loader  # noqa
    import stages.stage_factory  # noqa
    import ui.hud  # noqa
    import ui.menu  # noqa
    import ui.overlay  # noqa


check("import 26 modules", import_all)


import config
import core.input_manager
import core.rng
import core.assets
import core.replay
import entities.bullet
import entities.player
import entities.enemy
import entities.item
import entities.death_effect
import entities.background
import entities.boss
import entities.laser
import entities.hit_particle
import entities.graze_ring
import patterns.aimed
import patterns.fan
import patterns.ring
import patterns.spiral
import patterns.scatter
import patterns.spellcard
import patterns.delayed
import stages.loader
import stages.stage_factory
import ui.hud
import ui.menu
import ui.overlay


def init_assets():
    core.assets.default_loader()


check("AssetLoader.default_loader", init_assets)


def make_player():
    p = entities.player.Player()
    assert p.lives == 4 and p.bombs == 3 and p.power == 16  # updated defaults


check("Player init (lives/bombs/power)", make_player)


def bulletpool_basic():
    pool = entities.bullet.BulletPool(initial=64)
    pool.acquire(100, 100, 50, 50, radius=4)
    pool.step(0.0)
    assert len(pool.active) == 1


check("BulletPool acquire+step", bulletpool_basic)


def bulletpool_split():
    # Spawn at screen center so split bullets stay in bounds
    pool = entities.bullet.BulletPool(initial=64)
    pool.acquire(320, 240, 100, 0, split_at_age=0.5, split_count=4, split_speed=80)
    pool.step(0.3)
    n1 = len(pool.active)
    pool.step(0.3)
    n2 = len(pool.active)
    assert n2 == 4, "expected 4 after split, got " + str(n2)


check("BulletPool split (1->4)", bulletpool_split)


def itempool_basic():
    pool = entities.item.ItemPool(initial=8)
    pool.spawn(200, 100, 0, 1)  # power
    pool.spawn(200, 150, 1, 1)  # score
    assert pool.count() == 2


check("ItemPool spawn 2 items", itempool_basic)


def laserpool_basic():
    pool = entities.laser.LaserPool()
    pool.spawn(100, 100, 0.5)
    assert pool.count() == 1


check("LaserPool spawn", laserpool_basic)


def particle_pools():
    hp = entities.hit_particle.HitParticlePool(initial=8)
    hp.spawn(0, 0, (255, 0, 0), count=4)
    gr = entities.graze_ring.GrazeRingPool(initial=8)
    gr.spawn(0, 0)
    assert hp.count() == 4 and gr.count() == 1


check("HitParticle + GrazeRing pools", particle_pools)


def pattern_ticks():
    # Test patterns via loader (handles PI/N string conversion)
    pat_specs = [
        ("Aimed", {"pattern": "aimed", "color": "red", "speed": 200, "count": 3, "spread": 0.1}),
        ("Fan", {"pattern": "fan", "color": "blue", "speed": 180, "count": 5,
                  "arc": "PI/2", "base_angle": "aimed"}),
        ("Ring", {"pattern": "ring", "color": "green", "speed": 150, "count": 12}),
        ("Spiral", {"pattern": "spiral", "color": "purple", "speed": 160, "count": 2, "step_angle": 0.18}),
        ("Scatter", {"pattern": "scatter", "color": "yellow", "speed": 180, "count": 8,
                      "base_angle": "PI/2", "angle_jitter": "PI/4", "rng_seed": 7}),
        ("DelayedAimed", {"pattern": "delayed_aimed", "color": "purple", "speed": 200,
                           "split_at": 0.5, "split_count": 4}),
        ("DelayedFan", {"pattern": "delayed_fan", "color": "blue", "speed": 180, "count": 5,
                         "arc": "PI/2", "base_angle": "aimed",
                         "split_at": 0.6, "split_count": 3}),
        ("DelayedRing", {"pattern": "delayed_ring", "color": "red", "speed": 200, "count": 12,
                          "split_at": 0.6, "split_count": 3}),
    ]
    for name, spec in pat_specs:
        # Use loader to convert PI/N strings, then tick
        pat = stages.loader._make_pattern(dict(spec))
        specs = pat.tick(100, 100, 200, 300, 0.0)
        assert specs, name + " returned empty specs"


check("8 patterns tick (incl string arc/angle_jitter)", pattern_ticks)


def json_stages():
    import json
    for sid in [1, 2, 3]:
        path = os.path.join(ROOT, "assets", "stages", "stage" + str(sid) + ".json")
        data = stages.loader.load_stage(path)
        waves = stages.loader.build_waves(data)
        bosses = stages.loader.build_bosses(data)
        n_enemy = 0
        for w in waves:
            for e in w.spawn(difficulty=1):
                n_enemy += 1
        for t, b in bosses:
            assert len(b.spellcards) > 0
        print("    stage" + str(sid) + ": " + str(len(waves)) + "w + " + str(len(bosses)) + "b (" + str(n_enemy) + " enemies)")


check("JSON stage1/2/3 load + spawn", json_stages)


def boss_update():
    sc = patterns.spellcard.SpellCard(
        name="test", duration=10, hp_threshold=0.3,
        emitters=[entities.enemy.Emitter(patterns.aimed.Aimed(speed=200, count=1), period=1.0)],
    )
    boss = entities.boss.Boss(x=320, y=140, hp=100, path=[(0, 320, 140), (2, 320, 140)],
                              spellcards=[sc], score=1000)

    class FakePool:
        def acquire_many(self, specs):
            return len(specs)
    boss.update(0.1, FakePool(), entities.player.Player())


check("Boss enter -> spell transition", boss_update)


def replay_roundtrip():
    replay_dir = os.path.join(ROOT, "replay")
    os.makedirs(replay_dir, exist_ok=True)
    path = os.path.join(replay_dir, "_test.ndjson")
    rec = core.replay.ReplayRecorder(path, {"stage_id": 1, "difficulty": 1, "seed": 42})
    rec.record_frame(0.0, {"up", "z"}, {"z"})
    rec.record_frame(0.016, {"up", "z"}, set())
    rec.close()
    rp = core.replay.ReplayPlayer(path)
    assert rp.frame_count == 2
    assert rp.meta.get("stage_id") == 1
    os.remove(path)


check("Replay record + replay round-trip", replay_roundtrip)


def input_keys():
    inp = core.input_manager.InputManager()
    e = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_z})
    inp.update([e])
    assert inp.is_held("z"), "z should be held"
    assert inp.was_pressed("z"), "z should be pressed"


check("InputManager KEYDOWN capture", input_keys)


def ui_init():
    hud = ui.hud.HUD()
    menu = ui.menu.MenuSystem(max_stage=3)
    assert menu.max_stage == 3


check("HUD + MenuSystem init", ui_init)


def spell_announce():
    """Regression test: set_spell_announce must not raise (slots fix)."""
    hud = ui.hud.HUD()
    hud.set_spell_announce("Test Sign 1", t_remaining=2.0)
    hud.update_announce(0.05)
    # Force alpha to fade out
    hud._spell_timer = 0.0
    hud.update_announce(0.05)


check("HUD.set_spell_announce + update_announce", spell_announce)


def config_parse_angle():
    PI = 3.141592653589793
    assert abs(config.parse_angle("PI") - PI) < 1e-9
    assert abs(config.parse_angle("PI/24") - PI / 24) < 1e-9
    assert abs(config.parse_angle("2*PI") - 2 * PI) < 1e-9
    assert config.parse_angle(1.5) == 1.5  # non-string passthrough


check("config.parse_angle 4 forms", config_parse_angle)


def stages_full_run():
    stage = stages.stage_factory.make_stage(1)
    assert stage.name


check("stage_factory.make_stage(1)", stages_full_run)


# Real render test: blits with dither=False should work on real pygame
def blits_render_test():
    surf = pygame.display.set_mode((640, 480))
    b = entities.bullet.BulletPool(initial=32)
    b.acquire(100, 100, 50, 50, radius=4, color=(255, 0, 0))
    # This is the call that crashed with 'dither' kwarg
    b.draw(surf)


check("BulletPool.draw (blits with dither)", blits_render_test)


print()
print("=" * 60)
if failures:
    print(" " + str(len(failures)) + " FAILURES:")
    for f in failures:
        print("  - " + f)
    print("=" * 60)
    sys.exit(1)
else:
    print(" ALL SMOKE TESTS PASSED")
    print("=" * 60)
    sys.exit(0)