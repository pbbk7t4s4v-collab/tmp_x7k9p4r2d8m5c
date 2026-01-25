#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
讲稿合并工具
"""

import re
import argparse
from pathlib import Path

def natural_key(s: str):
    """自然排序"""
    return [int(text) if text.isdigit() else text
            for text in re.split(r'(\d+)', s)]

def main():
    parser = argparse.ArgumentParser(description="合并指定目录下的文本文件")
    parser.add_argument("indir", help="输入目录（包含 1_1.txt, 1_2.txt 等文件）")
    parser.add_argument("--out", default="merged", help="输出文件名前缀（默认 merged）")
    args = parser.parse_args()

    indir = Path(args.indir)
    if not indir.is_dir():
        raise NotADirectoryError(f"输入路径 {indir} 不是有效目录")
    txt_files = sorted(indir.glob("*.txt"), key=lambda p: natural_key(p.name))

    if not txt_files:
        raise FileNotFoundError(f"目录 {indir} 下没有找到任何 txt 文件")
    merged = []
    for f in txt_files:
        print(f"[INFO] 读取 {f.name}")
        merged.append(f.read_text(encoding="utf-8").rstrip())

    result = "\n\n".join(merged)
    out_txt = Path(f"{args.out}.txt")
    out_md = Path(f"{args.out}.md")
    out_txt.write_text(result, encoding="utf-8")
    out_md.write_text(result, encoding="utf-8")
    print(f"[OK] 已合并 {len(txt_files)} 个文件 -> {out_txt} / {out_md}")

if __name__ == "__main__":
    main()
