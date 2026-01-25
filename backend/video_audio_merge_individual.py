#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频音频合并与填充工具
功能：将音频文件与对应的视频文件合并，并进行填充处理
输入：音频目录、视频目录、输出目录
输出：合并并填充后的视频文件
"""

import os
import sys
import glob
import subprocess
import shutil
from pathlib import Path

def check_ffmpeg():
    """检查ffmpeg是否安装"""
    try:
        subprocess.run(['/home/EduAgent/miniconda3/envs/manim_env/bin/ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def find_matching_files(video_dir, audio_dir):
    """查找匹配的视频和音频文件"""
    matches = []
    
    # 获取所有mp4文件
    video_files = glob.glob(os.path.join(video_dir, "*.mp4"))
    
    for video_file in video_files:
        # 提取视频文件的基础名称（不含扩展名）
        video_basename = os.path.splitext(os.path.basename(video_file))[0]
        
        # 构建对应的音频文件名：相同的基础名称.wav
        audio_filename = f"{video_basename}.wav"
        audio_file = os.path.join(audio_dir, audio_filename)
        
        # 检查音频文件是否存在
        if os.path.exists(audio_file):
            matches.append((video_file, audio_file, video_basename))
            print(f"✅ 找到匹配: {video_basename}.mp4 <-> {audio_filename}")
        else:
            print(f"⚠️  未找到匹配的音频文件: {audio_filename}")
    
    return matches

def merge_video_audio(video_file, audio_file, output_file):
    """使用ffmpeg合并视频和音频"""
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
    """对视频进行填充处理"""
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
        print("❌ 错误: 请提供三个路径参数")
        print("📝 使用方法: python3 video_audio_merge_individual.py <音频目录> <视频目录> <输出目录>")
        print("📝 示例: python3 video_audio_merge_individual.py speech_audio video_wo_audio output")
        print()
        print("🎯 功能说明:")
        print("   1. 合并指定视频目录和音频目录中的匹配文件")
        print("   2. 对合并后的视频进行填充处理 (apad)")
        print("   3. 输出合并且填充后的视频文件")
        print()
        print("📁 文件匹配规则:")
        print("   视频文件: <名称>.mp4")
        print("   音频文件: <名称>.wav")
        print("   例如: 1_1.mp4 对应 1_1.wav")
        sys.exit(1)
    
    audio_dir = sys.argv[1]
    video_dir = sys.argv[2] 
    output_dir = sys.argv[3]
    
    print("🎬 视频音频合并填充工具")
    print("=" * 50)
    print(f"🎵 音频目录: {audio_dir}")
    print(f"📁 视频目录: {video_dir}")
    print(f"📤 输出目录: {output_dir}")
    print()
    print("🔄 处理流程:")
    print("   Step 1: 查找匹配的视频和音频文件")
    print("   Step 2: 逐个合并视频和音频")
    print("   Step 3: 对合并后的视频进行填充处理")
    print()
    
    # 检查ffmpeg
    if not check_ffmpeg():
        print("❌ 错误: 未找到ffmpeg，请先安装ffmpeg")
        sys.exit(1)
    
    # 检查目录是否存在
    if not os.path.exists(video_dir):
        print(f"❌ 错误: 视频目录不存在: {video_dir}")
        sys.exit(1)
    
    if not os.path.exists(audio_dir):
        print(f"❌ 错误: 音频目录不存在: {audio_dir}")
        sys.exit(1)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 创建输出目录: {output_dir}")
    print()
    
    # Step 1: 查找匹配的文件
    print("🔍 Step 1: 正在查找匹配的视频和音频文件...")
    matches = find_matching_files(video_dir, audio_dir)
    
    if not matches:
        print("❌ 未找到任何匹配的文件对")
        print()
        print("💡 请检查文件命名是否正确:")
        print("   视频文件: <名称>.mp4")
        print("   音频文件: <名称>.wav")
        print("   例如: 1_1.mp4 对应 1_1.wav")
        sys.exit(1)
    
    print(f"✅ 找到 {len(matches)} 对匹配文件")
    print()
    
    # Step 2: 逐个合并文件
    success_count = 0
    total_count = len(matches)
    merged_files = []
    
    print("🎬 Step 2: 开始合并视频和音频...")
    for i, (video_file, audio_file, basename) in enumerate(matches, 1):
        print(f"\n[{i}/{total_count}] 处理文件: {basename}")
        
        # 构建输出文件路径（临时合并文件）
        temp_merged_file = os.path.join(output_dir, f"{basename}_temp.mp4")
        
        # 合并文件
        if merge_video_audio(video_file, audio_file, temp_merged_file):
            merged_files.append((temp_merged_file, basename))
            success_count += 1
        else:
            print(f"⚠️  跳过文件: {basename}")
    
    # 显示合并结果
    print()
    print("🎉 视频音频合并完成！")
    print(f"📊 合并结果:")
    print(f"   ✅ 成功: {success_count} 个文件")
    print(f"   ❌ 失败: {total_count - success_count} 个文件")
    
    if success_count == 0:
        print("❌ 没有成功合并的文件，处理结束")
        return
    
    # Step 3: 视频填充处理
    print()
    print("🔧 Step 3: 视频填充处理...")
    
    pad_success_count = 0
    final_files = []
    
    for i, (temp_file, basename) in enumerate(merged_files, 1):
        print(f"\n[{i}/{len(merged_files)}] 填充处理: {basename}")
        
        # 最终输出文件路径
        final_output_file = os.path.join(output_dir, f"{basename}.mp4")
        
        if pad_video(temp_file, final_output_file):
            final_files.append(final_output_file)
            pad_success_count += 1
            
            # 删除临时文件
            try:
                os.remove(temp_file)
            except Exception as e:
                print(f"⚠️  删除临时文件失败: {e}")
        else:
            print(f"⚠️  跳过填充: {basename}")
    
    print()
    print("🎉 所有处理完成！")
    print("=" * 50)
    print(f"📊 最终结果:")
    print(f"   🎬 合并成功: {success_count} 个文件")
    print(f"   🔧 填充成功: {pad_success_count} 个文件")
    print(f"   📁 输出位置: {output_dir}")
    print()
    print("📋 生成的文件:")
    for final_file in final_files:
        file_size = os.path.getsize(final_file) / (1024 * 1024)  # MB
        print(f"   📄 {os.path.basename(final_file)} ({file_size:.1f} MB)")
    
    print()
    if pad_success_count == len(merged_files):
        print("✨ 视频音频合并填充全部完成！")
    else:
        print(f"⚠️  部分文件处理失败，成功率: {pad_success_count}/{len(merged_files)}")

if __name__ == "__main__":
    main()