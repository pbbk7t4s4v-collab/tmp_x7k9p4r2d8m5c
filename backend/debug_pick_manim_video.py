#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试 _render_single_video 中“查找 mp4”这部分。
会详细打印：
1) videos/<quality>/ 是否存在 mp4
2) fallback videos/*/ 下有哪些 mp4
3) 最终会选哪个

用法示例：
    python debug_pick_manim_video.py \
        --output_dir /home/TeachMaster/ML/debug_output \
        --quality 1080p60
"""

import argparse
from pathlib import Path
from manim import config as manim_config


def debug_pick_video(output_dir: Path):
    print(f"\n[DEBUG] output_dir = {output_dir}")
    print(f"[DEBUG] manim_config.quality = {manim_config.quality}")

    videos_root = output_dir / "videos"
    if not videos_root.exists():
        print(f"[WARN] {videos_root} 不存在，说明渲染可能未写入任何内容。")
        return None

    # Step 1: 尝试精准匹配 videos/<quality>/
    video_dir = videos_root / f"{manim_config.quality}"
    print(f"[DEBUG] 首选 video_dir = {video_dir}")
    if video_dir.exists():
        mp4_files = list(video_dir.glob("*.mp4"))
        print(f"[DEBUG] 在 {video_dir} 下找到 mp4: {[f.name for f in mp4_files]}")
        if mp4_files:
            print(f"[OK] 命中 mp4: {mp4_files[0]}")
            return mp4_files[0]
    else:
        print(f"[DEBUG] {video_dir} 不存在，进入 fallback...")

    # Step 2: fallback: 遍历 videos/*/
    candidates = []
    for vdir in sorted(videos_root.glob("*/")):
        if not vdir.is_dir():
            continue
        mp4_files = list(vdir.glob("*.mp4"))
        print(f"[DEBUG] 目录 {vdir} 内的 mp4: {[f.name for f in mp4_files]}")
        for f in mp4_files:
            candidates.append(f)

    if not candidates:
        print("[ERROR] 没有任何 mp4，可能只有 partial_movie_files。")
        return None

    chosen = candidates[0]
    print(f"[OK] 最终选择 mp4: {chosen}")
    return chosen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--quality", default="1080p60")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    manim_config.quality = args.quality

    picked = debug_pick_video(output_dir)
    if picked:
        print(f"\n结论：成功找到 mp4：{picked}")
    else:
        print("\n结论：未找到 mp4，Scene.render() 可能没有生成影片。")


if __name__ == "__main__":
    main()
