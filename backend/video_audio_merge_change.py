#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
与 video_audio_merge_single.py 基本一致，但在第二步根据时长决定处理方式：
- 如果视频更长或时长相近：为音频做 apad，并用 -shortest 截断，保持原逻辑。
- 如果音频更长：克隆视频最后一帧延长视频，直到匹配音频时长。
"""

import os
import sys
import subprocess


FFMPEG_BIN = "/home/EduAgent/miniconda3/envs/manim_env/bin/ffmpeg"
FFPROBE_BIN = "/home/EduAgent/miniconda3/envs/manim_env/bin/ffprobe"


def check_ffmpeg() -> bool:
    """检查 ffmpeg 是否可用。"""
    try:
        subprocess.run([FFMPEG_BIN, "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_duration(path: str) -> float:
    """使用 ffprobe 获取媒体时长（秒）。返回 0 表示失败。"""
    try:
        result = subprocess.run(
            [
                FFPROBE_BIN,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def merge_video_audio(video_file: str, audio_file: str, output_file: str) -> bool:
    """第一步：直接复用视频流 + AAC 音频，生成临时合并文件。"""
    cmd = [
        FFMPEG_BIN,
        "-i",
        video_file,
        "-i",
        audio_file,
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-strict",
        "experimental",
        "-y",
        output_file,
    ]

    try:
        print(f"🔧 正在合并: {os.path.basename(video_file)} + {os.path.basename(audio_file)}")
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ 合并成功: {os.path.basename(output_file)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 合并失败: {e}")
        print(f"   错误输出: {e.stderr}")
        return False


def pad_or_extend(temp_file: str, output_file: str, video_duration: float, audio_duration: float) -> bool:
    """
    第二步：根据时长分支处理。
    - 视频更长（或相差极小）：apad + shortest，填充音频静音并截断到视频长度。
    - 音频更长：优先克隆“倒数第二秒”的首帧延长，再接回最后一秒；若视频不足 1 秒则退化为克隆最后一帧。
    """
    epsilon = 0.05  # 50ms 以内视为相同长度
    if video_duration >= audio_duration - epsilon:
        # 视频更长或几乎相同：保持原逻辑
        cmd = [
            FFMPEG_BIN,
            "-i",
            temp_file,
            "-af",
            "apad",
            "-shortest",
            "-y",
            output_file,
        ]
        try:
            print("   Step 2: 视频更长/相同，给音频补静音并截到最短流")
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ 输出完成: {os.path.basename(output_file)}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 音视频填充失败: {e}")
            print(f"   错误输出: {e.stderr}")
            return False
    else:
        # 音频更长：尽量延长倒数第二秒的一帧，再接回最后一秒；视频过短时退化为延长最后一帧
        extra = audio_duration - video_duration
        if video_duration < 1.0:
            # 退化处理：视频太短，仍用克隆最后一帧
            cmd = [
                FFMPEG_BIN,
                "-i",
                temp_file,
                "-filter_complex",
                f"tpad=stop_mode=clone:stop_duration={extra}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
                "-y",
                output_file,
            ]
            desc = "视频<1s，克隆最后一帧延长"
        else:
            pen_start = max(video_duration - 2.5, 0)
            pen_end = max(video_duration - 1.5, 0)
            filter_complex = (
                f"[0:v]split=3[v0][v1][v2];"
                f"[v0]trim=end={pen_start},setpts=PTS-STARTPTS[head];"
                f"[v1]trim=start={pen_start}:end={pen_end},setpts=PTS-STARTPTS,"
                f"fps=1,select=eq(n\\,0),tpad=stop_mode=clone:stop_duration={extra}[hold];"
                f"[v2]trim=start={pen_end},setpts=PTS-STARTPTS[tail];"
                f"[head][hold][tail]concat=n=3:v=1:a=0[vout]"
            )
            cmd = [
                FFMPEG_BIN,
                "-i",
                temp_file,
                "-filter_complex",
                filter_complex,
                "-map",
                "[vout]",
                "-map",
                "0:a?",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
                "-y",
                output_file,
            ]
            desc = f"音频更长，延长倒数第二秒的首帧 {extra:.2f}s，再接回最后一秒"

        try:
            print(f"   Step 2: {desc}")
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ 输出完成: {os.path.basename(output_file)}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 视频延长失败: {e}")
            print(f"   错误输出: {e.stderr}")
            return False


def main():
    # 参数检查
    if len(sys.argv) != 4:
        print("❌ 错误: 请提供三个参数")
        print("📝 使用方法: python3 video_audio_merge_change.py <音频文件> <视频文件> <输出文件>")
        print("📝 示例: python3 video_audio_merge_change.py cover.wav cover.mp4 cover-merged.mp4")
        print()
        print("🎯 功能说明:")
        print("   1. 将单个音频文件与单个视频文件进行合并")
        print("   2. 根据时长选择：补静音或延长最后一帧")
        print("   3. 输出合并后的视频文件")
        sys.exit(1)

    audio_file = sys.argv[1]
    video_file = sys.argv[2]
    output_file = sys.argv[3]

    print("🎬 单文件音视频合并工具（可延长视频）")
    print("=" * 50)
    print(f"🎵 音频文件: {audio_file}")
    print(f"📁 视频文件: {video_file}")
    print(f"📤 输出文件: {output_file}")
    print()

    if not check_ffmpeg():
        print("❌ 错误: 未找到 ffmpeg，请先安装")
        sys.exit(1)

    if not os.path.exists(video_file):
        print(f"❌ 错误: 视频文件不存在: {video_file}")
        sys.exit(1)

    if not os.path.exists(audio_file):
        print(f"❌ 错误: 音频文件不存在: {audio_file}")
        sys.exit(1)

    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 创建输出目录: {output_dir}")

    # 临时合并文件
    temp_merged_file = output_file.replace(".mp4", "_temp.mp4")

    # Step 1
    print("🔄 开始处理...")
    print("   Step 1: 合并音频和视频")
    if not merge_video_audio(video_file, audio_file, temp_merged_file):
        print("❌ 音视频合并失败")
        sys.exit(1)

    # 计算时长，决定 Step 2 策略
    video_duration = get_duration(video_file)
    audio_duration = get_duration(audio_file)

    print(f"   时长检测: video={video_duration:.2f}s, audio={audio_duration:.2f}s")

    print("   Step 2: 时长匹配处理")
    if not pad_or_extend(temp_merged_file, output_file, video_duration, audio_duration):
        # 清理临时文件
        if os.path.exists(temp_merged_file):
            os.remove(temp_merged_file)
        sys.exit(1)

    # 清理临时文件
    if os.path.exists(temp_merged_file):
        os.remove(temp_merged_file)
        print("🧹 清理临时文件")

    # 展示结果
    print()
    print("🎉 音视频合并完成！")
    print("=" * 50)
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file) / (1024 * 1024)
        print(f"✅ 输出文件: {output_file}")
        print(f"📊 文件大小: {file_size:.1f} MB")
        print()
        print("✨ 合并成功（含时长自适应）！")
    else:
        print("❌ 输出文件生成失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
