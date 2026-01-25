#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from pathlib import Path

def check_ffmpeg():
    """检查ffmpeg是否安装"""
    try:
        subprocess.run(['/home/EduAgent/miniconda3/envs/manim_env/bin/ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def merge_video_audio(video_file, audio_file, output_file):
    """使用ffmpeg合并单个视频和音频文件"""
    cmd = [
        '/home/EduAgent/miniconda3/envs/manim_env/bin/ffmpeg',
        '-i', video_file,
        '-i', audio_file,
        '-map', '0:v',
        '-map', '1:a',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-strict', 'experimental',
        '-y',  # 覆盖输出文件
        output_file
    ]
    
    try:
        print(f"🔧 正在合并: {os.path.basename(video_file)} + {os.path.basename(audio_file)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ 合并成功: {os.path.basename(output_file)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 合并失败: {e}")
        print(f"   错误输出: {e.stderr}")
        return False

def pad_video(input_file, output_file):
    """对视频进行填充处理，使音视频长度匹配"""
    cmd = [
        '/home/EduAgent/miniconda3/envs/manim_env/bin/ffmpeg',
        '-i', input_file,
        '-af', 'apad',
        '-shortest',
        '-y',  # 覆盖输出文件
        output_file
    ]
    
    try:
        print(f"🔧 正在填充: {os.path.basename(input_file)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ 填充成功: {os.path.basename(output_file)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 填充失败: {e}")
        print(f"   错误输出: {e.stderr}")
        return False

def main():
    # 检查参数
    if len(sys.argv) != 4:
        print("❌ 错误: 请提供三个参数")
        print("📝 使用方法: python3 video_audio_merge_single.py <音频文件> <视频文件> <输出文件>")
        print("📝 示例: python3 video_audio_merge_single.py cover.wav cover.mp4 cover-padded.mp4")
        print()
        print("🎯 功能说明:")
        print("   1. 将单个音频文件与单个视频文件进行合并")
        print("   2. 自动进行音视频时长匹配处理")
        print("   3. 输出合并后的视频文件")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    video_file = sys.argv[2]
    output_file = sys.argv[3]
    
    print("🎬 单文件音视频合并工具")
    print("=" * 50)
    print(f"🎵 音频文件: {audio_file}")
    print(f"📁 视频文件: {video_file}")
    print(f"📤 输出文件: {output_file}")
    print()
    
    # 检查ffmpeg
    if not check_ffmpeg():
        print("❌ 错误: 未找到ffmpeg，请先安装ffmpeg")
        print("💡 安装命令: sudo apt-get install ffmpeg")
        sys.exit(1)
    
    # 检查输入文件是否存在
    if not os.path.exists(video_file):
        print(f"❌ 错误: 视频文件不存在: {video_file}")
        sys.exit(1)
    
    if not os.path.exists(audio_file):
        print(f"❌ 错误: 音频文件不存在: {audio_file}")
        sys.exit(1)
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 创建输出目录: {output_dir}")
    
    # 创建临时合并文件
    temp_merged_file = output_file.replace('.mp4', '_temp.mp4')
    
    # Step 1: 合并音视频
    print("🔄 开始处理...")
    print("   Step 1: 合并音频和视频")
    
    if not merge_video_audio(video_file, audio_file, temp_merged_file):
        print("❌ 音视频合并失败")
        sys.exit(1)
    
    # Step 2: 填充处理，确保音视频时长匹配
    print("   Step 2: 音视频时长匹配处理")
    
    if not pad_video(temp_merged_file, output_file):
        print("❌ 音视频填充失败")
        # 清理临时文件
        if os.path.exists(temp_merged_file):
            os.remove(temp_merged_file)
        sys.exit(1)
    
    # 清理临时文件
    if os.path.exists(temp_merged_file):
        os.remove(temp_merged_file)
        print("🧹 清理临时文件")
    
    # 显示最终结果
    print()
    print("🎉 音视频合并完成！")
    print("=" * 50)
    
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
        print(f"✅ 输出文件: {output_file}")
        print(f"📊 文件大小: {file_size:.1f} MB")
        print()
        print("✨ 单文件音视频合并成功！")
    else:
        print("❌ 输出文件生成失败")
        sys.exit(1)

if __name__ == "__main__":
    main()