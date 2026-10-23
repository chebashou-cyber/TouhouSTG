# -*- coding: utf-8 -*-
"""tools/check_ast.py — Python AST 静态检查 (替代 PowerShell 检查)

功能:
  1. 语法检查: ast.parse 每个 .py 文件
  2. 顶层定义收集: 类 / 函数 / 全大写常量
  3. import 链验证: 每个 `from X import Y` 的 X 模块存在 + Y 名字被定义
  4. JSON 合法性: assets/stages/*.json 都能被 json.loads 解析

用法:
  python tools/check_ast.py                # 人类输出
  python tools/check_ast.py --quiet        # 只输出错误
  python tools/check_ast.py --json         # 机器可读 JSON 输出
  python tools/check_ast.py --files path1 path2 ...   # 只检查指定文件
退出码: 0 全过 / 1 有错
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from typing import Iterable


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUDE_DIRS = {".git", "_tools", "replay", "__pycache__", "build", "dist"}
EXCLUDE_FILES = set()


def collect_py_files(roots: Iterable[str]) -> list[str]:
    out: list[str] = []
    for r in roots:
        if os.path.isfile(r) and r.endswith(".py"):
            out.append(r)
            continue
        for dp, dirs, files in os.walk(r):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                if f.endswith(".py") and f not in EXCLUDE_FILES:
                    out.append(os.path.join(dp, f))
    return sorted(set(out))


def collect_top_level(tree: ast.AST) -> set[str]:
    """收集一个 AST 中所有顶层 (类 / 函数 / 全大写常量) 名字。"""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    # 全大写视为模块常量 (如 SCREEN_W / KIND_ENEMY)
                    if t.id.isupper() or "_" in t.id:
                        names.add(t.id)
                    else:
                        # 也包含小写常量 (如 to_color)
                        names.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.ImportFrom) and node.module == "__future__":
            # __future__ 导入忽略
            pass
    return names


def module_key(path: str) -> str:
    """从文件路径得到模块键 (与 import 一致)。"""
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    if rel.endswith("/__init__.py"):
        return rel[:-len("/__init__.py")]
    if rel == "__init__.py":
        return ""
    return rel[:-3]  # strip .py


def parse_modules(files: list[str]) -> tuple[dict, list[str]]:
    """返回 {module_key: {'names': set, 'err': str|None}} 与 错误列表。"""
    modules: dict = {}
    errors: list[str] = []
    for f in files:
        key = module_key(f)
        try:
            src = open(f, "r", encoding="utf-8").read()
        except Exception as e:
            modules[key] = {"names": set(), "err": f"read error: {e}"}
            errors.append(f"{f}: read error {e}")
            continue
        try:
            tree = ast.parse(src, filename=f)
        except SyntaxError as e:
            modules[key] = {"names": set(), "err": f"syntax error line {e.lineno}: {e.msg}"}
            errors.append(f"{f}: SyntaxError line {e.lineno}: {e.msg}")
            continue
        modules[key] = {"names": collect_top_level(tree), "err": None}
    return modules, errors


def resolve_import_target(src_module: str, target: str) -> str:
    """把 `from src.foo.bar import X` 翻译为模块键 `src/foo/bar`。"""
    if target == "config":
        return "config"
    if src_module.startswith("src."):
        return src_module.replace(".", "/")
    return src_module


def check_imports(files: list[str], modules: dict) -> list[str]:
    """验证每个 from-import 的模块与名字。返回错误列表。"""
    errors: list[str] = []
    for f in files:
        try:
            src = open(f, "r", encoding="utf-8").read()
        except Exception:
            continue
        try:
            tree = ast.parse(src, filename=f)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            mod = node.module
            target_key = resolve_import_target(mod, mod)
            if target_key not in modules:
                # 第三方库 (pygame 等) 跳过
                if not mod.startswith("src.") and mod != "config":
                    continue
                rel = os.path.relpath(f, ROOT).replace(os.sep, "/")
                errors.append(f"{rel}: from {mod} import ...  -> module '{target_key}' not found")
                continue
            tgt = modules[target_key]
            if tgt["err"]:
                continue
            for n in node.names:
                if n.name == "*":
                    continue
                if n.name in tgt["names"]:
                    continue
                # `from package import submodule` 是合法写法:
                # 名字本身可能就是 package 下的一个模块 (src/core/game.py)
                if target_key != "config" and f"{target_key}/{n.name}" in modules:
                    continue
                rel = os.path.relpath(f, ROOT).replace(os.sep, "/")
                errors.append(
                    f"{rel}: from {mod} import {n.name}  -> name not defined in '{target_key}'"
                )
    return errors


def check_json_files() -> list[str]:
    """验证 assets/stages/*.json 合法。"""
    errors: list[str] = []
    stages_dir = os.path.join(ROOT, "assets", "stages")
    if not os.path.isdir(stages_dir):
        return errors
    for f in sorted(os.listdir(stages_dir)):
        if not f.endswith(".json"):
            continue
        path = os.path.join(stages_dir, f)
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            # 字段完整性最低校验
            assert "name" in data, "missing 'name'"
            assert "waves" in data, "missing 'waves'"
            assert "bosses" in data, "missing 'bosses'"
        except Exception as e:
            errors.append(f"{path}: {type(e).__name__}: {e}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Python AST 静态检查器")
    ap.add_argument("--quiet", action="store_true", help="只输出错误")
    ap.add_argument("--json", action="store_true", help="输出 JSON 格式")
    ap.add_argument("--files", nargs="*", default=None, help="只检查这些路径")
    ap.add_argument("--no-imports", action="store_true", help="跳过 import 检查")
    ap.add_argument("--no-json", action="store_true", help="跳过 JSON 检查")
    args = ap.parse_args()

    roots = args.files if args.files else [ROOT]
    files = collect_py_files(roots)

    if not args.quiet and not args.json:
        print(f"=== Scanning {len(files)} .py files ===")

    modules, parse_errors = parse_modules(files)
    import_errors: list[str] = []
    if not args.no_imports:
        import_errors = check_imports(files, modules)
    json_errors: list[str] = []
    if not args.no_json:
        json_errors = check_json_files()

    total_errors = len(parse_errors) + len(import_errors) + len(json_errors)

    if args.json:
        out = {
            "files_scanned": len(files),
            "modules_loaded": sum(1 for m in modules.values() if not m["err"]),
            "parse_errors": parse_errors,
            "import_errors": import_errors,
            "json_errors": json_errors,
            "total_errors": total_errors,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        if parse_errors:
            print("\n--- SYNTAX ERRORS ---")
            for e in parse_errors:
                print(f"  {e}")
        if import_errors:
            print("\n--- IMPORT ERRORS ---")
            for e in import_errors:
                print(f"  {e}")
        if json_errors:
            print("\n--- JSON ERRORS ---")
            for e in json_errors:
                print(f"  {e}")
        if not args.quiet:
            print(f"\n=== {len(files)} files, {len(modules) - len(parse_errors)} modules, "
                  f"{total_errors} errors ===")
            if total_errors == 0:
                print("ALL CHECKS PASSED")

    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
