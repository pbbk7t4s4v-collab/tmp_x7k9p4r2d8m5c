#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频合并工具
功能：将多个视频文件按教学结构分类并合并为一个完整视频
输入：包含多个视频文件的目录
输出：合并后的完整视频文件 (Full.mp4)
"""

import os
import sys
import re
import glob
import subprocess
from pathlib import Path

def check_ffmpeg():
    """检查ffmpeg是否安装"""
    try:
        subprocess.run(['/home/EduAgent/miniconda3/envs/manim_env/bin/ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def categorize_videos(video_files):
    """按照Introduction、Method、Experiment、Conclusion分类视频文件"""
    categories = {
        'Introduction': [],
        'Method': [],
        'Experiment': [],
        'Conclusion': []
    }
    
    for video_file in video_files:
        basename = os.path.splitext(os.path.basename(video_file))[0]
        basename_lower = basename.lower()
        
        # 分类逻辑
        if 'introduction' in basename_lower or 'intro' in basename_lower:
            categories['Introduction'].append(video_file)
        elif 'method' in basename_lower or 'approach' in basename_lower or 'methodology' in basename_lower:
            categories['Method'].append(video_file)
        elif 'experiment' in basename_lower or 'result' in basename_lower or 'evaluation' in basename_lower:
            categories['Experiment'].append(video_file)
        elif 'conclusion' in basename_lower or 'summary' in basename_lower or 'end' in basename_lower:
            categories['Conclusion'].append(video_file)
        else:
            # 默认归类到Method
            categories['Method'].append(video_file)
    
    # 对每个分类内的文件按字母顺序排序
    for category in categories:
        # categories[category].sort(key=lambda x: os.path.basename(x).lower())
        categories[category].sort(key=lambda x: natural_key(os.path.basename(x)))

    
    return categories

def generate_filelist(categories, output_dir):
    """生成file.txt文件"""
    filelist_path = os.path.join(output_dir, "file.txt")
    
    try:
        with open(filelist_path, 'w', encoding='utf-8') as f:
            for category in ['Introduction', 'Method', 'Experiment', 'Conclusion']:
                # 直接添加该分类的视频文件
                if categories[category]:
                    print(f"📝 添加 {category} 内容: {len(categories[category])} 个文件")
                    
                    for video_file in categories[category]:
                        basename = os.path.basename(video_file)
                        # 写入相对路径，避免路径问题
                        f.write(f'file {basename}\n')
                else:
                    print(f"⚠️  {category} 部分无任何文件")
        
        print(f"✅ 文件列表生成成功: {filelist_path}")
        return filelist_path
    except Exception as e:
        print(f"❌ 文件列表生成失败: {e}")
        return None

def generate_simple_filelist(video_files, output_dir):
    """生成简单的文件列表（按文件名顺序）"""
    filelist_path = os.path.join(output_dir, "file.txt")
    
    try:
        # 按文件名排序
        # sorted_videos = sorted(video_files, key=lambda x: os.path.basename(x).lower())
        sorted_videos = sorted(video_files, key=lambda x: natural_key(os.path.basename(x)))

        
        with open(filelist_path, 'w', encoding='utf-8') as f:
            for video_file in sorted_videos:
                basename = os.path.basename(video_file)
                f.write(f'file {basename}\n')
        
        print(f"✅ 简单文件列表生成成功: {filelist_path}")
        print(f"📋 包含 {len(sorted_videos)} 个视频文件")
        return filelist_path
    except Exception as e:
        print(f"❌ 文件列表生成失败: {e}")
        return None

def concat_videos(filelist_path, output_dir):
    """使用ffmpeg串联所有视频"""
    output_file = os.path.join(output_dir, "Full.mp4")
    
    # 使用相对路径，避免路径问题
    cmd = [
        '/home/EduAgent/miniconda3/envs/manim_env/bin/ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', 'file.txt',  # 使用相对路径
        '-c', 'copy',
        '-y',  # 覆盖输出文件
        'Full.mp4'  # 使用相对路径
    ]
    
    try:
        print(f"🔧 正在串联视频...")
        print(f"   使用文件列表: {os.path.basename(filelist_path)}")
        print(f"   输出文件: Full.mp4")
        print(f"   工作目录: {output_dir}")
        
        # 在输出目录下执行命令，避免路径问题
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=output_dir)
        
        # 检查输出文件是否成功生成
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
            print(f"✅ 视频串联成功: Full.mp4 ({file_size:.1f} MB)")
            return output_file
        else:
            print(f"❌ 视频串联失败: 输出文件未生成")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 视频串联失败: {e}")
        print(f"   错误输出: {e.stderr}")
        return None
    
def natural_key(filename: str):
    """生成自然排序键，保证数字按数值排序"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', filename)]

def main():
    # 检查参数
    if len(sys.argv) != 3:
        print("❌ 错误: 请提供两个路径参数")
        print("📝 使用方法: python3 video_concat.py <视频目录> <输出目录>")
        print("📝 示例: python3 video_concat.py merged_videos output")
        print()
        print("🎯 功能说明:")
        print("   1. 扫描指定目录中的所有视频文件")
        print("   2. 按教学结构自动分类 (可选)")
        print("   3. 生成文件列表 file.txt")
        print("   4. 串联所有视频为完整的教学视频 (Full.mp4)")
        print()
        print("📁 支持的视频格式: .mp4")
        print("🏗️ 分类规则:")
        print("   - Introduction: 包含 'introduction' 或 'intro'")
        print("   - Method: 包含 'method', 'approach', 'methodology'")  
        print("   - Experiment: 包含 'experiment', 'result', 'evaluation'")
        print("   - Conclusion: 包含 'conclusion', 'summary', 'end'")
        print("   - 其他文件默认归类为 Method")
        sys.exit(1)
    
    video_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    print("🎬 视频合并工具")
    print("=" * 50)
    print(f"📁 视频目录: {video_dir}")
    print(f"📤 输出目录: {output_dir}")
    print()
    print("🔄 处理流程:")
    print("   Step 1: 扫描视频文件")
    print("   Step 2: 分类视频文件 (可选)")
    print("   Step 3: 生成文件列表 (file.txt)")
    print("   Step 4: 串联视频 (Full.mp4)")
    print()
    
    # 检查ffmpeg
    if not check_ffmpeg():
        print("❌ 错误: 未找到ffmpeg，请先安装ffmpeg")
        sys.exit(1)
    
    # 检查目录是否存在
    if not os.path.exists(video_dir):
        print(f"❌ 错误: 视频目录不存在: {video_dir}")
        sys.exit(1)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 创建输出目录: {output_dir}")
    print()
    
    # Step 1: 扫描视频文件
    print("🔍 Step 1: 扫描视频文件...")
    video_files = glob.glob(os.path.join(video_dir, "*.mp4"))
    
    if not video_files:
        print("❌ 未找到任何视频文件")
        print("💡 请确认目录中包含 .mp4 格式的视频文件")
        sys.exit(1)
    
    print(f"✅ 找到 {len(video_files)} 个视频文件")
    for video_file in sorted(video_files):
        file_size = os.path.getsize(video_file) / (1024 * 1024)  # MB
        print(f"   📄 {os.path.basename(video_file)} ({file_size:.1f} MB)")
    print()
    
    # 询问用户是否使用教学结构分类
    use_categorization = True  # 默认使用分类，可以改为交互式选择
    filelist_path = None
    
    if use_categorization:
        # Step 2: 按教学结构分类
        print("📋 Step 2: 按教学结构分类视频文件...")
        categories = categorize_videos(video_files)
        
        # 显示分类结果
        print()
        print("📊 视频分类结果:")
        total_categorized = 0
        for category, files in categories.items():
            if files:
                print(f"   📂 {category}: {len(files)} 个文件")
                for file in files:
                    print(f"      - {os.path.basename(file)}")
                total_categorized += len(files)
            else:
                print(f"   📂 {category}: 无文件")
        
        print(f"\\n📊 分类统计: {total_categorized}/{len(video_files)} 个文件已分类")
        
        # Step 3: 生成分类文件列表
        print()
        print("📝 Step 3: 生成教学结构文件列表...")
        filelist_path = generate_filelist(categories, output_dir)
        
    else:
        # Step 3: 生成简单文件列表
        print("📝 Step 3: 生成简单文件列表...")
        filelist_path = generate_simple_filelist(video_files, output_dir)
    
    if not filelist_path:
        print("❌ 文件列表生成失败，无法继续")
        sys.exit(1)
    
    # 显示文件列表内容
    print()
    print("📄 即将串联的视频列表:")
    with open(filelist_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines, 1):
            # 正确解析文件名：去掉 'file ' 前缀和换行符
            if line.strip().startswith('file '):
                filename = line.strip()[5:]  # 去掉 'file ' 前缀
            else:
                filename = line.strip()
                
            full_path = os.path.join(video_dir, filename)
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path) / (1024 * 1024)  # MB
                print(f"   {i:2d}. {filename} ({file_size:.1f} MB) ✅")
            else:
                print(f"   {i:2d}. {filename} ❌ 文件不存在")
    print()
    
    # Step 4: 执行视频串联
    print("🎬 Step 4: 视频串联...")
    final_output = concat_videos(filelist_path, output_dir)
    
    if final_output:
        print()
        print("🎉 视频合并完成！")
        print("=" * 50)
        print("📋 最终结果:")
        print(f"   🎬 输入视频: {len(video_files)} 个")
        print(f"   📝 文件列表: file.txt")
        print(f"   🎦 完整视频: Full.mp4")
        print(f"   📁 输出位置: {output_dir}")
        
        # 显示最终视频信息
        final_size = os.path.getsize(final_output) / (1024 * 1024)  # MB
        print()
        print("🎊 成功生成完整教学视频！")
        print(f"   📁 文件路径: {final_output}")
        print(f"   📊 文件大小: {final_size:.1f} MB")
        print()
        print("✨ 视频合并任务完成！")
        
    else:
        print()
        print("⚠️  视频串联失败")
        print("💡 可手动执行串联命令:")
        print(f"   cd {output_dir}")
        print(f"   /home/EduAgent/miniconda3/envs/manim_env/bin/ffmpeg -f concat -safe 0 -i file.txt -c copy Full.mp4")

if __name__ == "__main__":
    main()