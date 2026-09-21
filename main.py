# -*- coding: utf-8 -*-
"""main.py — 程序入口

运行: python main.py
阶段: 第一阶段 (MVP)
"""
from __future__ import annotations
from src.core.game import Game


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
