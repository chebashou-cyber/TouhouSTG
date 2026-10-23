# -*- coding: utf-8 -*-
"""story/model.py — 剧情数据模型 + JSON 加载

数据结构 (assets/story/campaign.json):
{
  "characters": {
    "rein": {"name": "铃岚", "title": "博丽的巫女",
             "color": [255, 110, 130], "side": "left"}
  },
  "chapters": [
    {"id": 1, "stage_id": 1,
     "title": "一章", "subtitle": "褪色的夜空",
     "prologue":  [{"speaker": "rein", "text": "..."},
                   {"text": "（旁白示例：speaker 省略即旁白）"}],
     "boss_intro": [...],
     "clear": [...],
     "bg_tint": [16, 10, 30]}
  ],
  "ending": [...]
}

设计取舍:
  - 说话人只存 key, 名字/颜色/站位集中定义, 改一处全剧本生效;
  - 旁白用 speaker 缺省表示, 渲染时不画立绘;
  - 章节与 stage_id 绑定, 剧情模式按 chapters 顺序推进。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Character:
    key: str
    name: str
    title: str = ""
    color: tuple = (255, 255, 255)
    side: str = "left"          # left / right: 立绘站位


@dataclass(frozen=True)
class Line:
    speaker: str | None
    text: str
    emotion: str = "normal"     # normal / angry / sad / smile (影响立绘表情)


@dataclass
class Chapter:
    id: int
    stage_id: int
    title: str                  # 一章
    subtitle: str               # 褪色的夜空
    prologue: list[Line] = field(default_factory=list)
    boss_intro: list[Line] = field(default_factory=list)
    clear: list[Line] = field(default_factory=list)
    bg_tint: tuple = (10, 10, 24)

    @property
    def display_title(self) -> str:
        return f"{self.title} · {self.subtitle}" if self.title else self.subtitle


@dataclass
class Campaign:
    characters: dict[str, Character]
    chapters: list[Chapter]
    ending: list[Line] = field(default_factory=list)

    def chapter_for_stage(self, stage_id: int) -> Chapter | None:
        for ch in self.chapters:
            if ch.stage_id == stage_id:
                return ch
        return None

    def chapter(self, chapter_id: int) -> Chapter | None:
        for ch in self.chapters:
            if ch.id == chapter_id:
                return ch
        return None


def _as_color(raw, default=(255, 255, 255)) -> tuple:
    if isinstance(raw, (list, tuple)) and len(raw) >= 3:
        return (int(raw[0]), int(raw[1]), int(raw[2]))
    return default


def _parse_lines(raw, where: str) -> list[Line]:
    out: list[Line] = []
    if raw is None:
        return out
    if not isinstance(raw, list):
        raise ValueError(f"{where}: 应为台词数组")
    for i, item in enumerate(raw):
        if isinstance(item, str):
            out.append(Line(None, item))
            continue
        if not isinstance(item, dict):
            raise ValueError(f"{where}[{i}]: 台词项应为对象或字符串")
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{where}[{i}]: 缺少非空 text")
        out.append(Line(item.get("speaker") or None, text,
                        item.get("emotion", "normal")))
    return out


def default_campaign_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "assets", "story", "campaign.json")


def load_campaign(path: str | None = None) -> Campaign:
    """读剧情 JSON; 任何结构错误都抛 ValueError (带位置信息)。"""
    path = path or default_campaign_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("campaign.json: 顶层应为对象")

    characters: dict[str, Character] = {}
    for key, raw in (data.get("characters") or {}).items():
        if not isinstance(raw, dict):
            raise ValueError(f"characters.{key}: 应为对象")
        characters[key] = Character(
            key=key,
            name=raw.get("name", key),
            title=raw.get("title", ""),
            color=_as_color(raw.get("color")),
            side=raw.get("side", "left"),
        )

    chapters: list[Chapter] = []
    for i, raw in enumerate(data.get("chapters") or []):
        where = f"chapters[{i}]"
        if not isinstance(raw, dict):
            raise ValueError(f"{where}: 应为对象")
        if "stage_id" not in raw:
            raise ValueError(f"{where}: 缺少 stage_id")
        ch = Chapter(
            id=int(raw.get("id", i + 1)),
            stage_id=int(raw["stage_id"]),
            title=raw.get("title", ""),
            subtitle=raw.get("subtitle", ""),
            prologue=_parse_lines(raw.get("prologue"), f"{where}.prologue"),
            boss_intro=_parse_lines(raw.get("boss_intro"), f"{where}.boss_intro"),
            clear=_parse_lines(raw.get("clear"), f"{where}.clear"),
            bg_tint=_as_color(raw.get("bg_tint"), (10, 10, 24)),
        )
        chapters.append(ch)

    # 台词里引用的说话人必须存在, 否则渲染时没有名字/颜色
    known = set(characters)
    for ch in chapters:
        for group in (ch.prologue, ch.boss_intro, ch.clear):
            for line in group:
                if line.speaker is not None and line.speaker not in known:
                    raise ValueError(
                        f"章节 {ch.id}: 未定义的说话人 '{line.speaker}' "
                        f"(characters 里有: {sorted(known)})")

    ending = _parse_lines(data.get("ending"), "ending")
    for line in ending:
        if line.speaker is not None and line.speaker not in known:
            raise ValueError(f"ending: 未定义的说话人 '{line.speaker}'")

    if not chapters:
        raise ValueError("campaign.json: chapters 为空")

    return Campaign(characters=characters, chapters=chapters, ending=ending)
