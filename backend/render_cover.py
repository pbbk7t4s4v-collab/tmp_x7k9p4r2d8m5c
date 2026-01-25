#!/usr/bin/env python3
"""
一键渲染机器学习课程封面和尾页脚本
用法: python render_cover.py "课程标题" [参数]

示例:
    python render_cover.py "Deep Learning"
    python render_cover.py "Neural Networks" --cover-output ./output/cover.mp4 --ending-output ./output/ending.mp4
    python render_cover.py "Computer Vision" -p "Dr. Jane Smith" -a prof.jpg -b campus.jpg --cover-output test/cover.mp4 --ending-output test/ending.mp4 -q medium
"""
import sys
import os
import argparse
from pathlib import Path
from manim import *
from Demo import MergedLayoutScene2
from EndingDemo import EndingScene

def render_videos(title, avatar_image="csh.png", professor_name="Prof. Siheng Chen", background_image="SAI.png", 
                 cover_output=None, ending_output=None, quality="high"):
    """
    渲染课程封面和尾页视频
    
    Args:
        title (str): 课程标题
        avatar_image (str): 头像图片文件名
        professor_name (str): 教授姓名
        background_image (str): 背景图片文件名
        cover_output (str): 封面视频输出文件路径 (包含文件名)
        ending_output (str): 尾页视频输出文件路径 (包含文件名)
        quality (str): 渲染质量 ("low", "medium", "high")
    """
    # 设置质量参数
    quality_map = {
        "low": "low_quality",
        "medium": "medium_quality", 
        "high": "high_quality"
    }
    
    if quality not in quality_map:
        print(f"警告: 质量等级 '{quality}' 无效，使用默认高质量")
        quality = "high"
    
    print(f"开始渲染课程视频...")
    print(f"课程标题: {title}")
    print(f"教授姓名: {professor_name}")
    print(f"头像图片: {avatar_image}")
    print(f"背景图片: {background_image}")
    print(f"渲染质量: {quality}")
    
    # 检查图片文件是否存在
    from pathlib import Path as CheckPath
    current_dir = CheckPath.cwd()
    
    avatar_path = current_dir / avatar_image
    background_path = current_dir / background_image
    logo_path = current_dir / "TeachingMaster.png"
    
    print(f"\n📁 检查文件存在性:")
    print(f"头像文件: {avatar_path} - {'✅存在' if avatar_path.exists() else '❌不存在'}")
    print(f"背景文件: {background_path} - {'✅存在' if background_path.exists() else '❌不存在'}")
    print(f"Logo文件: {logo_path} - {'✅存在' if logo_path.exists() else '❌不存在'}")
    
    # 检查文件大小
    if avatar_path.exists():
        print(f"头像文件大小: {avatar_path.stat().st_size} 字节")
    if background_path.exists():
        print(f"背景文件大小: {background_path.stat().st_size} 字节")
    
    print()
    
    # 渲染封面视频
    cover_file = None
    if cover_output:
        print("🎬 渲染封面视频...")
        cover_file = render_single_video(
            scene_class=MergedLayoutScene2,
            title=title, avatar_image=avatar_image, professor_name=professor_name,
            background_image=background_image, output_path=cover_output, quality=quality
        )
    
    # 渲染尾页视频
    ending_file = None
    if ending_output:
        print("🎬 渲染尾页视频...")
        ending_file = render_single_video(
            scene_class=EndingScene,
            title=title, avatar_image=avatar_image, professor_name=professor_name,
            background_image=background_image, output_path=ending_output, quality=quality
        )
    
    print(f"✅ 渲染完成!")
    results = {}
    if cover_file:
        print(f"📹 封面视频: {cover_file}")
        results['cover'] = cover_file
    if ending_file:
        print(f"📹 尾页视频: {ending_file}")
        results['ending'] = ending_file
    
    return results


def render_single_video(scene_class, title, avatar_image, professor_name, background_image, output_path, quality):
    """渲染单个视频文件"""
    # 设置质量参数
    quality_map = {
        "low": "low_quality",
        "medium": "medium_quality", 
        "high": "high_quality"
    }
    
    # 设置输出路径
    output_dir = None
    output_filename = None
    
    if output_path:
        output_path_obj = Path(output_path).resolve()
        
        # 判断是文件路径还是目录路径
        if output_path.endswith('.mp4') or '.' in output_path_obj.name:
            # 包含文件名
            output_dir = output_path_obj.parent
            output_filename = output_path_obj.stem  # 不含扩展名
            print(f"输出目录: {output_dir}")
            print(f"文件名: {output_filename}.mp4")
        else:
            # 只是目录路径
            output_dir = output_path_obj
            print(f"输出目录: {output_dir}")
        
        # 创建输出目录
        output_dir.mkdir(parents=True, exist_ok=True)
        config.media_dir = str(output_dir)
    
    # 设置渲染参数
    config.quality = quality_map[quality]
    config.preview = True
    
    # 如果指定了文件名，设置场景名称
    if output_filename:
        config.scene_names = [output_filename]
    
    # 创建场景并渲染
    final_output_file = None
    try:
        scene = scene_class(class_title_text=title, avatar_image=avatar_image, professor_name=professor_name, background_image=background_image)
        scene.render()
        
        # 查找并重命名输出文件
        if output_dir:
            # 查找生成的视频文件，优先查找质量目录
            video_dir = output_dir / "videos" / f"{config.quality}"
            if not video_dir.exists():
                # 如果质量目录不存在，查找所有可能的视频目录
                video_dirs = list(output_dir.glob("videos/*/"))
                if video_dirs:
                    for vdir in video_dirs:
                        if vdir.is_dir():
                            video_files = list(vdir.glob("*.mp4"))
                            if video_files:
                                video_dir = vdir
                                break
            
            if video_dir and video_dir.exists():
                video_files = list(video_dir.glob("*.mp4"))
                if video_files and output_filename:
                    # 重命名文件为指定名称
                    original_file = video_files[0]
                    new_file = output_dir / f"{output_filename}.mp4"
                    if original_file != new_file:
                        original_file.rename(new_file)
                        final_output_file = new_file
                    else:
                        final_output_file = original_file
                elif video_files:
                    final_output_file = video_files[0]
                    
            # 生成对应的txt文件
            if output_filename and final_output_file:
                txt_file = output_dir / f"{output_filename}.txt"
                scene_type = "封面" if scene_class == MergedLayoutScene2 else "尾页"
                if scene_class == MergedLayoutScene2:
                    txt_content = f"大家好！欢迎大家聆听本学期的机器学习课程，我是授课老师{professor_name}，今天让我们一起走进{title}吧。"
                else:
                    txt_content = f"感谢大家聆听本次{title}课程，希望大家都有所收获！我是授课老师{professor_name}，期待与大家下次课程再见。"
                with open(txt_file, 'w', encoding='utf-8') as f:
                    f.write(txt_content)
                print(f"📝 {scene_type}文本文件: {txt_file}")
                
    except Exception as e:
        print(f"详细错误信息: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    return final_output_file

def main():
    parser = argparse.ArgumentParser(
        description="一键渲染机器学习课程封面和尾页",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
    python render_cover.py "Deep Learning"
    python render_cover.py "Neural Networks" --cover-output ./output/cover.mp4 --ending-output ./output/ending.mp4
    python render_cover.py "Computer Vision" -p "Dr. Jane Smith" -a prof.jpg -b campus.jpg --cover-output test/cover.mp4 --ending-output test/ending.mp4 -q medium
    python render_cover.py "Machine Learning" --cover-output test/intro.mp4  # 只渲染封面
    python render_cover.py "Deep Learning" --ending-output test/outro.mp4   # 只渲染尾页
        """
    )
    
    parser.add_argument("title", help="课程标题")
    parser.add_argument("-a", "--avatar", default="csh.png", help="头像图片文件名 (默认: csh.png)")
    parser.add_argument("-p", "--professor", default="Prof. Siheng Chen", help="教授姓名 (默认: Prof. Siheng Chen)")
    parser.add_argument("-b", "--background", default="SAI.png", help="背景图片文件名")
    parser.add_argument("--cover-output", help="封面视频输出路径 (包含文件名的完整路径)")
    parser.add_argument("--ending-output", help="尾页视频输出路径 (包含文件名的完整路径)")
    parser.add_argument("-q", "--quality", 
                       choices=["low", "medium", "high"], 
                       default="high",
                       help="渲染质量 (默认: high)")
    
    args = parser.parse_args()
    
    # 检查是否至少指定了一个输出路径
    if not args.cover_output and not args.ending_output:
        print("错误: 请至少指定一个输出路径 (--cover-output 或 --ending-output)")
        print("使用 --help 查看详细用法")
        sys.exit(1)
    
    try:
        render_videos(args.title, args.avatar, args.professor, args.background, 
                     args.cover_output, args.ending_output, args.quality)
    except KeyboardInterrupt:
        print("\n❌ 渲染被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 渲染失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # 如果没有命令行参数，使用默认值或交互式输入
    if len(sys.argv) == 1:
        print("请输入课程标题 (回车使用默认 'Regression'):")
        title = input().strip() or "Regression"
        
        print("请输入教授姓名 (回车使用默认 'Prof. Siheng Chen'):")
        professor = input().strip() or "Prof. Siheng Chen"
        
        print("请输入头像图片文件名 (回车使用默认 'csh.png'):")
        avatar = input().strip() or "csh.png"
        
        print("请输入背景图片文件名 (回车使用默认 'SAI.png'):")
        background = input().strip() or "SAI.png"
        
        print("请输入封面视频输出路径 (可包含文件名，回车跳过):")
        cover_output = input().strip() or None
        
        print("请输入尾页视频输出路径 (可包含文件名，回车跳过):")
        ending_output = input().strip() or None
        
        if not cover_output and not ending_output:
            print("至少需要指定一个输出路径，默认渲染封面到当前目录")
            cover_output = "cover.mp4"
        
        print("请选择渲染质量 [low/medium/high] (回车使用 'high'):")
        quality = input().strip() or "high"
        
        render_videos(title, avatar, professor, background, cover_output, ending_output, quality)
    else:
        main()