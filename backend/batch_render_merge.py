#!/usr/bin/env python3
"""\
先渲染，再按文件名顺序合并视频。

- 渲染：调用 backend/batch_render_manim_for_effi_test.py（并行渲染 Manim 代码目录）
- 合并：按“自然序”对输出视频排序后用 ffmpeg concat 合并
  例如：*_2 在 *_11 前（而不是字符串排序的 *_11 在 *_2 前）

用法：
  python bacth_render_merge.py <input_dir> <render_output_dir>

可选参数：
  --quality {l,m,h,p,k}   默认 h
  --workers N             默认 12
  --merged_output PATH    默认 <render_output_dir>/Full.mp4
  --skip_render           只做合并，不重新渲染
  --allow_partial         即使渲染有失败也尝试合并已有视频

说明：
- render_output_dir 内默认应生成与 .py 同名的 .mp4/.mov
- 合并使用 -c copy（不重编码），要求片段编码参数一致；否则请自行改成重编码。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

sys.dont_write_bytecode = True


def _natural_key(text: str) -> List[Tuple[int, object]]:
    parts = re.split(r"(\d+)", text)
    key: List[Tuple[int, object]] = []
    for part in parts:
        if part.isdigit():
            key.append((0, int(part)))
        elif part:
            key.append((1, part.casefold()))
    return key


def _pick_videos(render_output_dir: Path, *, exclude_names: set[str]) -> List[Path]:
    candidates = list(render_output_dir.glob("*.mp4")) + list(render_output_dir.glob("*.mov"))
    by_stem: dict[str, Path] = {}

    # 如果同 stem 同时存在 .mp4 和 .mov，优先 .mp4
    for p in candidates:
        if p.name in exclude_names:
            continue
        if p.name.startswith("."):
            continue
        stem = p.stem
        prev = by_stem.get(stem)
        if prev is None:
            by_stem[stem] = p
            continue
        if prev.suffix.lower() != ".mp4" and p.suffix.lower() == ".mp4":
            by_stem[stem] = p

    return sorted(by_stem.values(), key=lambda p: _natural_key(p.stem))


def _write_ffmpeg_filelist(video_files: List[Path], filelist_path: Path) -> None:
    lines: List[str] = []
    for p in video_files:
        abs_path = str(p.resolve())
        # ffmpeg concat demuxer: file '...'
        abs_path_escaped = abs_path.replace("'", "'\\''")
        lines.append(f"file '{abs_path_escaped}'")
    filelist_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ffmpeg_concat(filelist_path: Path, merged_output: Path) -> None:
    merged_output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(filelist_path),
        "-c",
        "copy",
        str(merged_output),
    ]
    subprocess.run(cmd, check=True)


def _run_render(input_dir: Path, render_output_dir: Path, quality: str, workers: int) -> int:
    # 同目录脚本，直接 import 调用（避免再起一层 python 进程时环境不一致）
    try:
        from batch_render_manim_for_effi_test import main as render_main  # type: ignore
    except Exception:
        # 允许从项目根目录运行：backend/ 不在 sys.path 时补一下
        backend_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(backend_dir))
        from batch_render_manim_for_effi_test import main as render_main  # type: ignore

    return int(render_main(str(input_dir), str(render_output_dir), quality, workers))


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Manim folder then concat videos in natural filename order")
    parser.add_argument("input_dir", help="包含 Manim .py 的目录")
    parser.add_argument("render_output_dir", help="渲染输出目录（生成的 .mp4/.mov 存放处）")
    parser.add_argument("--quality", "-q", choices=["l", "m", "h", "p", "k"], default="h")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--merged_output", default=None, help="合并后输出视频路径，默认 <render_output_dir>/Full.mp4")
    parser.add_argument("--skip_render", action="store_true", help="跳过渲染，仅合并 render_output_dir 中现有视频")
    parser.add_argument("--allow_partial", action="store_true", help="渲染失败也尝试合并已有视频")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    render_output_dir = Path(args.render_output_dir).resolve()
    render_output_dir.mkdir(parents=True, exist_ok=True)

    merged_output = Path(args.merged_output).resolve() if args.merged_output else (render_output_dir / "Full.mp4")

    if not args.skip_render:
        if not input_dir.exists():
            raise SystemExit(f"输入目录不存在: {input_dir}")
        exit_code = _run_render(input_dir, render_output_dir, args.quality, args.workers)
        if exit_code != 0 and not args.allow_partial:
            raise SystemExit(exit_code)

    video_files = _pick_videos(render_output_dir, exclude_names={merged_output.name})
    if not video_files:
        raise SystemExit(f"未在输出目录找到可合并的视频: {render_output_dir}")

    # 写临时 filelist 并 concat
    with tempfile.NamedTemporaryFile(prefix="ffconcat_", suffix=".txt", dir=str(render_output_dir), delete=False) as tf:
        filelist_path = Path(tf.name)

    try:
        _write_ffmpeg_filelist(video_files, filelist_path)
        _ffmpeg_concat(filelist_path, merged_output)
    finally:
        try:
            if filelist_path.exists():
                filelist_path.unlink()
        except Exception:
            pass

    print(f"Rendered videos dir: {render_output_dir}")
    print(f"Merged output: {merged_output}")
    print(f"Segments: {len(video_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
