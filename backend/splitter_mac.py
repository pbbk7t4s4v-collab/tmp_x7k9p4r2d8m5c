#!/usr/bin/env python3
"""\
Split a single Markdown file into multiple files by page-break markers.

Input:  a Markdown file that contains page breaks:  <!-- PAGE_BREAK -->
Output: <input_filename>_1.md, <input_filename>_2.md, ... written into the given output directory.

Usage:
  python splitter_mac.py <input.md> <output_dir>

Notes:
- Page break marker matching is case-insensitive and ignores surrounding whitespace.
- Each output page gets an appended context block (parent headings) similar to backend/splitter.py.
"""

import argparse
import os
import re
from typing import List, Tuple


PAGE_BREAK_PATTERN = re.compile(r"<!--\s*PAGE_BREAK\s*-->", re.IGNORECASE)
HEADING_LINE_PATTERN = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", re.UNICODE)


def _extract_headings(text: str) -> List[Tuple[int, str]]:
    headings: List[Tuple[int, str]] = []
    for line in text.splitlines():
        match = HEADING_LINE_PATTERN.match(line)
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        headings.append((level, title))
    return headings


def _update_heading_stack(stack: List[str | None], headings: List[Tuple[int, str]]) -> List[str | None]:
    current = list(stack)
    for level, title in headings:
        if level - 1 >= len(current):
            current.extend([None] * (level - 1 - len(current) + 1))
        current[level - 1] = title
        del current[level:]
    return current


def _format_context_block(stack: List[str | None]) -> str:
    lines = [f"{'#' * (i + 1)} {t}" for i, t in enumerate(stack) if t]
    if not lines:
        return ""
    header = "该部分所处的上下文位置（从最高级到当前）："
    body = "\n".join(lines)
    return f"\n\n<!-- CONTEXT:BEGIN -->\n{header}\n{body}\n<!-- CONTEXT:END -->\n"


def _derive_prefix(input_path: str) -> str:
    base = os.path.basename(input_path)
    stem, _ext = os.path.splitext(base)
    return stem or "split"


def split_markdown_file(input_path: str, output_dir: str) -> List[str]:
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    pages = [p.strip() for p in PAGE_BREAK_PATTERN.split(content) if p.strip()]
    os.makedirs(output_dir, exist_ok=True)

    prefix = _derive_prefix(input_path)
    written: List[str] = []

    heading_stack: List[str | None] = []
    for idx, page_content in enumerate(pages, start=1):
        page_headings = _extract_headings(page_content)

        if page_headings:
            first_level = page_headings[0][0]
            context_stack = heading_stack[: max(0, first_level - 1)]
        else:
            context_stack = heading_stack[:-1] if len(heading_stack) > 1 else []

        page_with_context = page_content + _format_context_block(context_stack)

        out_name = f"{prefix}_{idx}.md"
        out_path = os.path.join(output_dir, out_name)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page_with_context)

        written.append(out_path)
        heading_stack = _update_heading_stack(heading_stack, page_headings)

    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split a single Markdown file by <!-- PAGE_BREAK --> into multiple files.",
    )
    parser.add_argument("input_md", help="Path to input .md file")
    parser.add_argument("output_dir", help="Directory to write output files")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input_md)
    output_dir = os.path.abspath(args.output_dir)

    if not os.path.isfile(input_path):
        raise SystemExit(f"Input file not found: {input_path}")

    written = split_markdown_file(input_path, output_dir)
    print(f"Input: {input_path}")
    print(f"Output dir: {output_dir}")
    print(f"Pages: {len(written)}")
    for p in written:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
