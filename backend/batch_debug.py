#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, pathlib
import auto_debug_manim as adm  # 和auto_debug_manim.py 放在同一目录

def main(folder: str, render_dir: str = None):
    folder = pathlib.Path(folder)
    files = sorted(folder.glob("*.py"))
    for f in files:
        if f.name in ("auto_debug_manim.py", "batch_debug.py"):
            continue
        if f.suffix != ".py":
            continue
        print(f"\n=== debug 处理 {f.name} ===")
        try:
            adm.main(str(f), render_dir=render_dir)
        except Exception as e:
            print(f"[ERROR] {f}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("参数不合法，正确用法: python batch_debug.py <文件夹路径>，<可选参数：渲染目录>")
        sys.exit(1)
    if len(sys.argv) == 2:
        main(sys.argv[1])
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    if len(sys.argv) > 3:
        print("参数不合法，正确用法: python batch_debug.py <文件夹路径>，<可选参数：渲染目录>")
        sys.exit(1)
