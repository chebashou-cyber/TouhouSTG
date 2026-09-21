@echo off
REM tools/build.bat - 跨平台打包脚本 (Windows)
REM 用 PyInstaller 把 main.py 打成单 exe
REM 用法: tools\build.bat
REM 依赖: pip install pyinstaller pygame-ce

setlocal enabledelayedexpansion

echo === Touhou STG 跨平台打包 (PyInstaller) ===

where pyinstaller >nul 2>nul
if errorlevel 1 (
    echo PyInstaller 未安装, 正在安装...
    python -m pip install pyinstaller || goto :error
)

REM 清理旧构建
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

REM 打包参数:
REM   --onefile: 单文件
REM   --noconsole: 不要控制台窗口
REM   --add-data: 资源目录 (assets/)
REM   --name: 输出文件名
echo 正在打包 (可能需要 1-2 分钟)...
python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name "TouhouSTG" ^
    --add-data "assets;assets" ^
    main.py
if errorlevel 1 goto :error

echo.
echo === 打包完成 ===
echo dist\TouhouSTG.exe
echo 文件大小:
for %%F in (dist\TouhouSTG.exe) do @echo   %%~zF bytes
echo.
echo 运行 dist\TouhouSTG.exe 即可启动游戏。
exit /b 0

:error
echo 打包失败, 请检查 PyInstaller 输出。
exit /b 1