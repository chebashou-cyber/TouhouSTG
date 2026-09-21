# Touhou-style Vertical STG — 完整交付 (v0.6)

类东方红魔乡风格的纵版弹幕射击游戏, Python + pygame-ce 实现。

## 当前进度

| 阶段 | 交付 |
| --- | --- |
| 1 | 自机 / 敌机 / BulletPool / 5 pattern / Stage1 / HUD / F1~F4 调试 |
| 2 | 道具系统 / 视差背景 / 死亡动画 / 炸弹 / 4 档菜单 / Continue |
| 3 | Boss 状态机 / 符卡系统 / Stage Clear 评级 |
| 4 | 激光 / Delayed 分裂 / JSON 关卡数据 / Loader |
| 5 | 资源接口 / 击中&擦弹视效 / 输入缓冲 / 多关卡选择 |
| 6 | 难度平衡 / 资源生成脚本 / Replay 录制回放 / 打包工具 |

## 运行

```powershell
pip install -r requirements.txt
python main.py
```

启动后默认进入 TITLE 菜单, 用 ↑↓ 切焦点行:
- START: 开始当前选择的 (STAGE, DIFFICULTY)
- DIFFICULTY: ←→ 切换 EASY / NORMAL / HARD / LUNATIC
- STAGE: ←→ 切换 1 / 2 / 3
- REPLAY: 播放最新一份录制

游戏中按键:
- 方向键 / WASD: 8 向移动
- Shift: 低速 (聚焦) — 显示判定点
- Z: 射击 (按住连续发射)
- X: 炸弹 (清屏 + 无敌 2s + 计分)
- Esc: 退出
- P: 暂停 / 取消暂停 (回放模式不可暂停)
- R: Game Over 后重开
- F1: 调试 overlay
- F2: 帧步进
- F3: 无敌切换
- F4: 清屏 (移除全部敌弹)

## 生成资源

第一运行默认使用程序化 fallback。生成完整资源 (PNG/WAV):

```powershell
python tools/build_assets.py
```

会向 `assets/chars/`、`assets/boss/`、`assets/bg/`、`assets/sfx/` 写入文件。
之后引擎会优先加载真实文件。

## 静态检查 (推荐 CI 入口)

```powershell
python tools\check_ast.py
```

输出示例:
```
=== Scanning 39 .py files ===
=== 39 files, 39 modules, 0 errors ===
ALL CHECKS PASSED
```

工具基于 Python 标准库 `ast` 与 `json`:
- 语法检查 (`ast.parse` 每个 .py 文件)
- import 链验证 (每个 `from X import Y` 的 X 与 Y 真实存在)
- JSON 关卡数据合法性 (`json.load` + 字段完整性)
- 退出码: `0` 通过 / `1` 有错 (CI 可直接用)

选项: `--quiet` (只输出错误) / `--json` (机器可读) / `--files path1 path2` (只检查指定文件)。

依赖: Python 3.10+ 标准库, 无第三方包。

## 跨平台打包 (PyInstaller)

Windows:
```powershell
tools\build.bat
```

Linux / macOS:
```bash
bash tools/build.sh
```

输出 `dist/TouhouSTG.exe` (或 `dist/TouhouSTG` on Linux)。单文件运行, 无需 Python。

依赖: `pip install pyinstaller`

## Replay 系统

每次正常游戏 (非回放) 自动录制到 `replay/stage{N}_{difficulty}_{rand}.ndjson`。
回放时菜单选 REPLAY → 自动加载最新一份。
Replay 文件每行一条 JSON 帧: `{"t": float, "h": [...], "p": [...]}`。

## 目录结构

```
myfirstgame/
├── main.py
├── config.py                 全局数值
├── README.md
├── replay/                    录制输出 (自动生成)
├── assets/
│   ├── bg/  boss/  chars/  sfx/        (程序化生成或手动放置)
│   └── stages/
│       ├── stage1.json
│       ├── stage2.json
│       └── stage3.json
├── tools/
│   ├── build_assets.py      生成 PNG / WAV 占位资源
│   ├── build.bat            Windows 打包
│   ├── build.sh             Linux / macOS 打包
│   ├── check_imports.ps1    静态检查
│   ├── check_methods.ps1    静态检查
│   ├── dump_names.ps1
│   ├── json_verify2.ps1
│   └── append_config.ps1
└── src/
    ├── core/
    │   ├── game.py          主循环
    │   ├── input_manager.py 输入 + 缓冲 + Replay 注入
    │   ├── assets.py        资源接口
    │   ├── replay.py        录制/回放
    │   └── rng.py
    ├── entities/
    │   ├── background.py
    │   ├── boss.py          Boss 状态机
    │   ├── bullet.py        Bullet 数据 + Pool + split
    │   ├── death_effect.py
    │   ├── enemy.py         Enemy + Emitter + Wave
    │   ├── graze_ring.py
    │   ├── hit_particle.py
    │   ├── item.py          Item 道具 + 吸引
    │   ├── laser.py         Laser + LaserPool
    │   └── player.py
    ├── patterns/
    │   ├── aimed.py  fan.py  ring.py  spiral.py  scatter.py
    │   ├── delayed.py        DelayedAimed/Fan/Ring
    │   └── spellcard.py
    ├── stages/
    │   ├── loader.py        JSON loader
    │   ├── stage1.py        兼容老接口
    │   └── stage_factory.py make_stage(id)
    └── ui/
        ├── hud.py           HUD + Boss 血条 + 符卡
        ├── menu.py          标题 / 暂停 / Game Over / Stage Clear
        └── overlay.py       F1 调试
```

## 数值约定 (config.py)

- 屏幕: y 向下, 左上 (0, 0)
- 角度: 弧度 (rad), 0 弧度 = +x
- 速度: px/s
- 时间: 物理秒, 帧 (frame) 仅用于极短常量

## ⚠️ 未在本环境验证

沙箱无 Python 解释器, 所有验证为静态:
- import 链 ✓
- 方法引用 ✓
- JSON 关卡数据合法 ✓
- 关键符号定位 ✓

运行时验证需在本地 Python 3.11 + pygame-ce 2.6+ 环境执行 `python main.py`。

## 已知边界

- 第一帧渲染延迟 (pygame.time.Clock 不限 FPS)
- LUNATIC 难度下有些组合的弹幕密度仍可能压垮 60 FPS, 视机器而定
- 程序化 fallback 资源 (无 PNG 时) 是基础形状, 不如真实贴图
- Replay 仅录制输入, 依赖 RNG seed 重放; 若 stage 数据 (JSON) 被修改, 旧 replay 可能与新数据不一致