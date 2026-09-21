#!/usr/bin/env bash
# tools/build.sh - 跨平台打包脚本 (Linux / macOS)
# 用 PyInstaller 把 main.py 打成单文件
# 用法: bash tools/build.sh

set -e
echo "=== Touhou STG 跨平台打包 (PyInstaller) ==="

if ! command -v pyinstaller >/dev/null 2>&1; then
    echo "PyInstaller 未安装, 正在安装..."
    python3 -m pip install pyinstaller
fi

rm -rf build dist
echo "正在打包 (可能需要 1-2 分钟)..."

python3 -m PyInstaller \
    --onefile \
    --name "TouhouSTG" \
    --add-data "assets:assets" \
    main.py

echo ""
echo "=== 打包完成 ==="
echo "dist/TouhouSTG"
ls -la dist/TouhouSTG 2>/dev/null || ls -la dist/