# Touhou-style Vertical STG — 星屑异变 (v1.0)

类东方风格的纵版弹幕射击游戏，Python + pygame-ce 实现。

v1.0 在原有弹幕引擎之上补了**剧情模式**：六章连续闯关，章首、Boss 登场、章末都有对话，
残机 / 炸弹 / 火力 / 分数跨章继承，最后有 ALL CLEAR 结算与最高分存档。

![标题](docs/screenshots/01_title.png)

| 剧情对话 | 道中弹幕 |
| --- | --- |
| ![剧情](docs/screenshots/02_story.png) | ![道中](docs/screenshots/03_gameplay.png) |
| **Boss 符卡** | **ALL CLEAR** |
| ![Boss](docs/screenshots/04_boss.png) | ![结算](docs/screenshots/06_allclear.png) |

## 运行

```powershell
pip install -r requirements.txt
python main.py
```

只有 `pygame-ce` 是运行必需依赖（`numpy` 是可选的，当前代码不 import 它）。

## 玩法

标题菜单（↑↓ 选择，←→ 调整，Enter / Z 确认）:

| 行 | 说明 |
| --- | --- |
| START | 剧情模式：六章连续闯关，中途不退出 |
| STAGE | 单关练习：0 教学关 / 1~6 剧情章 / 7~9 EX 关 |
| DIFFICULTY | EASY / NORMAL / HARD / LUNATIC |
| REPLAY | 播放 `replay/` 里最新的一份录像 |
| QUIT | 退出 |

游戏中按键:

- 方向键 / WASD：8 向移动
- Shift：低速（聚焦）— 显示判定点
- Z：射击（按住连续发射）
- X：炸弹（清屏 + 无敌 2s + 计分）
- P：暂停 / 恢复
- Esc：退出
- R：Game Over / Stage Clear 后重来
- F1 调试 overlay / F2 帧步进 / F3 无敌 / F4 清屏

剧情对话中：Z / Enter 继续（未打完则立刻打完），X 跳过整段。

## 剧情：星屑异变

夜空中的星星在以肉眼可见的速度变少。博丽的巫女铃岚和森林妖精露叶一路向上，
最后发现是一台「收集愿望、以星光为燃料」的装置在抽取整片夜空。

| 章 | 关卡 | 对手 | 一句话 |
| --- | --- | --- | --- |
| 一章 | 夜雀之森 | 小夜（夜雀） | 碎星不是掉下来的，是往上飞的 |
| 二章 | 雾湖冰晶 | 冰华（冰之妖精） | 有人在把星星冻进湖里 |
| 三章 | 迷途竹林 | 铃月（守路人） | 竹林后面，是通到天上的路 |
| 四章 | 星之书库 | 紫书（记录者） | 星之器是照着我的书造的 |
| 五章 | 机关天守 | 机织 零（机关人偶） | 三百六十一年，一直在数星星 |
| 终章 | 星之器 | 穹（守护者） | 愿望需要燃料，夜空就是燃料 |

剧情数据全部在 [`assets/story/campaign.json`](assets/story/campaign.json)：
角色名 / 立绘颜色 / 站位、每章的前置对话（prologue）、Boss 登场对话（boss_intro）、
章末对话（clear）、以及结局（ending）。**改台词不需要动代码**。

```json
{
  "rein": { "name": "铃岚", "title": "博丽的巫女",
            "color": [255, 110, 130], "side": "left" },
  "chapters": [
    { "id": 1, "stage_id": 1, "title": "一章", "subtitle": "褪色的夜空",
      "prologue":  [{ "speaker": "rein", "text": "……星星在掉。" },
                    { "text": "（省略 speaker 即为旁白）" }],
      "boss_intro": [ ... ],
      "clear":     [ ... ] }
  ],
  "ending": [ ... ]
}
```

立绘没有美术资源，是 [`src/ui/dialoguebox.py`](src/ui/dialoguebox.py) 里用几何图形
按角色颜色程序化画出来的 Q 版人形——改颜色就能换人设。

## 关卡数据

六个剧情章在 `assets/stages/ch1.json ~ ch6.json`，由
[`tools/gen_stages.py`](tools/gen_stages.py) 生成：

```powershell
python tools/gen_stages.py           # 重新生成 ch1..ch6
python tools/gen_stages.py --check   # 只校验，不写文件
```

因为同构编队（横穿妖精、悬停环弹机、分裂弹机……）很多，用脚本描述比手写 JSON 好维护，
调平衡只改这个文件里的数值。每章的 JSON 仍可直接手改，但下次生成会被覆盖。

关卡支持的弹幕模式：`aimed / fan / ring / spiral / scatter / delayed_aimed /
delayed_fan / delayed_ring`，角度可写成 `"PI"`, `"PI/3"`, `"2*PI"` 这类字符串。
数据结构见 [`src/stages/loader.py`](src/stages/loader.py) 顶部说明。

## 目录结构

```
game/
├── main.py                   入口
├── config.py                 全局数值 / 颜色 / 难度曲线
├── assets/
│   ├── stages/               关卡 JSON (ch1..ch6 = 剧情六章, stage*.json = 教学/EX)
│   └── story/campaign.json   剧情脚本 + 角色定义
├── docs/screenshots/         无头截图 (README 用)
├── replay/                   录像输出 (自动生成, 已 gitignore)
├── save/records.json         最高分 / 通关次数 (自动生成, 已 gitignore)
├── src/
│   ├── core/
│   │   ├── game.py           主循环 + 场景/章节状态机
│   │   ├── input_manager.py  输入 + 缓冲 + Replay 注入
│   │   ├── save_data.py      最高分存档 (读写失败静默降级)
│   │   ├── assets.py / replay.py / rng.py
│   ├── entities/             自机 / 敌机 / Boss / 子弹池 / 激光 / 道具 / 粒子
│   ├── patterns/             8 种弹幕模式 + 符卡数据
│   ├── stages/               JSON loader / stage_factory / stage1(兼容)
│   ├── story/                剧情数据模型 + 对话状态机
│   └── ui/                   hud / menu / dialoguebox / fonts / overlay
└── tools/
    ├── check_ast.py          静态检查 (语法 + import 链 + JSON)
    ├── smoke_test.py         模块级冒烟测试 (真 pygame, dummy 驱动)
    ├── story_smoke.py        剧情模式端到端测试 (六章跑通到 ALL CLEAR)
    ├── capture_shots.py      无头截图
    ├── gen_stages.py         生成六章关卡数据
    └── build.bat / build.sh  PyInstaller 打包
```

## 测试

全部无头运行，不需要显示器：

```powershell
python tools\check_ast.py      # 静态检查：语法 / import 链 / JSON 合法性
python tools\smoke_test.py     # 模块冒烟：对象池、弹幕模式、Replay、UI
python tools\story_smoke.py    # 端到端：六章连续闯关直到 ALL CLEAR
```

`story_smoke.py` 会真的跑完整流程：自动跳过所有对话、秒杀每个 Boss、
检查章节顺序、分数继承、存档写入，最后渲染 ALL CLEAR 画面。
它把存档重定向到临时目录，不会污染 `save/records.json`。

三个脚本的退出码都是 `0` 通过 / `1` 失败，可直接接 CI。

## 打包

```powershell
tools\build.bat        # Windows -> dist/TouhouSTG.exe
bash tools/build.sh    # Linux / macOS
```

依赖 `pip install pyinstaller`。`TouhouSTG.spec` 现在用相对路径打包
`assets/`（原来的绝对路径 `D:/myfirstgame/assets` 换目录就失效）。

## 数值约定 (config.py)

- 屏幕 640×480，y 向下，左上为 (0, 0)
- 角度：弧度，0 = +x
- 速度：px/s；时间：物理秒
- `BULLET_SPEED_GLOBAL_SCALE` 统一压慢敌弹，改一个数即可整体调难度

## 已知限制

- 立绘是程序化几何图形，不是美术资源
- 没有音乐 / 音效资源（`assets/sfx/` 为空时用静音占位）
- Replay 只记录**单关**输入；剧情模式每章单独录一份，不能整局回放
- Replay 依赖 RNG seed 重放：改了关卡 JSON 后旧录像会对不上
- LUNATIC 高密度弹幕的帧率取决于机器

## 版本与回滚

- 本版为 **v1.0**，对应 tag `v0.6-baseline` 的上游版本是改造前的快照
- 回退到改造前：

  ```powershell
  git fetch --tags
  git reset --hard v0.6-baseline
  ```

- 只想看旧版：`git worktree add ../TouhouSTG-v0.6 v0.6-baseline`
- 单次提交出问题：`git revert <commit>`，历史保持线性，没有强推

## 变更点 (v0.6 -> v1.0)

- **剧情模式**：6 章连续闯关，章首 / Boss 登场 / 章末对话，结局与 ALL CLEAR
- **章节继承**：残机 / 炸弹 / 火力 / 分数 / 擦弹跨章保留（原先打完一关就回菜单）
- **关卡**：新增六章主线和 8 种编队模式，Boss 符卡从 2~3 张提升到 3~5 张
- **存档**：`save/records.json` 记录各难度最高分与全通次数，标题画面显示 BEST
- **修 bug**：
  - `pygame.font.SysFont` 在部分 Windows 机器上直接抛 `TypeError`，游戏起不来 —— 改为直接指定字体文件，并接入中文字体
  - pygame-ce 2.6.1 下小半径圆形被光栅化成「十字/齿轮」，弹幕看起来像小星星 —— 改为 4 倍超采样
  - 自机机身颜色恒为白色（`bomb_time=0` 时取错分支）
  - 教学关提示被重复绘制两次；`_tutorial_hints` 每帧重建
  - 菜单关卡上限与 `STAGE_FILE_MAP` 差一位，教学关与 EX 关选不到
  - `check_ast.py` 不认 `from package import submodule`，误报
