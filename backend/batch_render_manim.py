#!/usr/bin/env python3
"""
Manim 批量渲染工具

功能：
1. 扫描指定文件夹中的所有 Python 文件
2. 自动提取每个文件中的 Manim Scene 类名
3. 使用 manim 命令渲染每个场景
4. 将生成的视频移动到指定输出文件夹

作者：EduAgent ML Assistant
"""

import os
import re
import sys
import glob
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


class ManimBatchRenderer:
    """Manim 批量渲染器"""
    
    def __init__(self, input_dir: str, output_dir: str, quality: str = "h"):
        """
        初始化渲染器
        
        Args:
            input_dir: 包含 Manim 代码的输入文件夹
            output_dir: 视频输出文件夹
            quality: 渲染质量 (l, m, h, p, k)
        """
        self.input_dir = Path(input_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.quality = quality
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 验证输入目录存在
        if not self.input_dir.exists():
            raise FileNotFoundError(f"输入目录不存在: {self.input_dir}")
    
    def extract_scene_classes(self, python_file: Path) -> List[str]:
        """
        从 Python 文件中提取 Manim Scene 类名
        
        Args:
            python_file: Python 文件路径
            
        Returns:
            Scene 类名列表
        """
        try:
            with open(python_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 匹配继承自 Scene 的类
            # 匹配模式：class ClassName(Scene): 或 class ClassName(MovingCameraScene): 等
            pattern = r'class\s+(\w+)\s*\([^)]*Scene[^)]*\)\s*:'
            matches = re.findall(pattern, content)
            
            if not matches:
                # 如果没找到 Scene 类，尝试匹配所有类（作为备选）
                pattern_backup = r'class\s+(\w+)\s*\([^)]*\)\s*:'
                matches = re.findall(pattern_backup, content)
                
                if matches:
                    print(f"警告 {python_file.name}: 未找到明确的Scene类，尝试使用: {matches}")
            
            return matches
            
        except Exception as e:
            print(f"错误: 解析文件 {python_file.name} 时出错: {e}")
            return []
    
    def render_scene(self, python_file: Path, scene_class: str) -> Optional[Path]:
        """
        渲染单个 Manim 场景
        
        Args:
            python_file: Python 文件路径
            scene_class: Scene 类名
            
        Returns:
            生成的视频文件路径，如果失败则返回 None
        """
        try:
            # 查找生成的视频文件
            video_file = self.find_generated_video(python_file, scene_class)
            if video_file:
                return video_file
            # 构建 manim 命令 (新版本格式)
            cmd = [
                "manim",
                "render",  # 新版本需要 render 子命令
                "-q", self.quality,  # 质量设置
                str(python_file),
                scene_class
            ]
            
            # 执行渲染命令
            result = subprocess.run(
                cmd,
                cwd=python_file.parent,  # 在文件所在目录执行
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode != 0:
                print(f"渲染失败: {python_file.name}")
                if result.stderr:
                    print(f"错误: {result.stderr}")
                return None
            
            # 查找生成的视频文件
            video_file = self.find_generated_video(python_file, scene_class)
            if video_file:
                return video_file
            else:
                print(f"错误: 找不到生成的视频文件: {scene_class}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"错误: 渲染超时: {python_file.name} -> {scene_class}")
            return None
        except Exception as e:
            print(f"错误: 渲染过程出错: {python_file.name} -> {scene_class}: {e}")
            return None
    
    def find_generated_video(self, python_file: Path, scene_class: str) -> Optional[Path]:
        """
        查找 Manim 生成的视频文件
        
        Args:
            python_file: 源 Python 文件
            scene_class: Scene 类名
            
        Returns:
            视频文件路径，如果找不到则返回 None
        """
        # Manim 默认输出路径模式
        quality_folder_map = {
            'l': '480p15',
            'm': '720p30', 
            'h': '1080p60',
            'p': '1440p60',
            'k': '2160p60'
        }
        quality_folder = quality_folder_map.get(self.quality, '1080p60')
        
        possible_paths = [
            # 新版 Manim Community 输出路径
            python_file.parent / "media" / "videos" / python_file.stem / quality_folder / f"{scene_class}.mp4",
            python_file.parent / "media" / "videos" / python_file.stem / quality_folder / f"{scene_class}.mov",
            
            # 其他可能的路径
            python_file.parent / "media" / "videos" / f"{scene_class}.mp4",
            python_file.parent / "media" / "videos" / f"{scene_class}.mov",
            
            # 查找任何包含 scene_class 名称的视频文件
        ]
        
        # 检查预定义路径
        for path in possible_paths:
            if path.exists():
                return path
        
        # 如果预定义路径都不存在，在 media 目录下递归查找
        media_dir = python_file.parent / "media"
        if media_dir.exists():
            for video_file in media_dir.rglob("*.mp4"):
                if scene_class in video_file.stem:
                    return video_file
            for video_file in media_dir.rglob("*.mov"):
                if scene_class in video_file.stem:
                    return video_file
        
        return None
    
    def copy_video_to_output(self, video_file: Path, python_file: Path) -> bool:
        """
        将视频文件复制到输出目录
        
        Args:
            video_file: 源视频文件路径
            python_file: 原 Python 文件路径
            
        Returns:
            是否成功复制
        """
        try:
            # 使用原 Python 文件名作为视频文件名
            output_filename = f"{python_file.stem}{video_file.suffix}"
            output_path = self.output_dir / output_filename
            
            # 复制文件
            shutil.copy2(video_file, output_path)
            return True
            
        except Exception as e:
            print(f"错误: 复制视频文件失败: {e}")
            return False
    
    def render_all(self) -> dict:
        """
        批量渲染所有 Manim 文件
        
        Returns:
            渲染结果统计
        """
        # 查找所有 Python 文件并按字母顺序排序
        python_files = sorted(list(self.input_dir.glob("*.py")), key=lambda x: x.name)
        
        if not python_files:
            print(f"错误: 在 {self.input_dir} 中没有找到 Python 文件")
            return {"total": 0, "success": 0, "failed": 0}
        
        print(f"找到 {len(python_files)} 个 Python 文件")
        
        success_count = 0
        failed_count = 0
        
        # 使用进度条
        if HAS_TQDM:
            pbar = tqdm(python_files, desc="渲染进度", unit="文件")
        else:
            pbar = python_files
            print("开始渲染...")
        
        for python_file in pbar:
            if HAS_TQDM:
                pbar.set_description(f"处理: {python_file.name}")
            else:
                print(f"处理文件: {python_file.name}")
            
            # 提取 Scene 类
            scene_classes = self.extract_scene_classes(python_file)
            
            if not scene_classes:
                print(f"未找到 Scene 类: {python_file.name}")
                failed_count += 1
                continue
            
            # 渲染每个 Scene 类（通常只有一个）
            file_success = False
            for scene_class in scene_classes:
                video_file = self.render_scene(python_file, scene_class)
                
                if video_file:
                    if self.copy_video_to_output(video_file, python_file):
                        file_success = True
                        if HAS_TQDM:
                            pbar.set_postfix(status="成功")
                        break  # 成功渲染一个就够了
            
            if file_success:
                success_count += 1
            else:
                failed_count += 1
                if HAS_TQDM:
                    pbar.set_postfix(status="失败")
        
        if HAS_TQDM:
            pbar.close()
        
        # 输出统计结果
        total = len(python_files)
        print(f"\n渲染完成")
        print(f"总文件数: {total}")
        print(f"成功: {success_count}")
        print(f"失败: {failed_count}")
        print(f"输出目录: {self.output_dir}")
        
        return {
            "total": total,
            "success": success_count,
            "failed": failed_count
        }
    
    def pipeline(self) -> dict:
        """简化的流水线接口"""
        result = self.render_all()
        return not result["failed"] == 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Manim 批量渲染工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python batch_render_manim.py Code/KNN_9757_sections/ Video/KNN_9757_sections/
  python batch_render_manim.py Code/KNN_9757_sections/ Video/KNN_9757_sections/ --quality m
        """
    )
    
    parser.add_argument(
        "input_dir",
        help="包含 Manim Python 代码的输入文件夹"
    )
    
    parser.add_argument(
        "output_dir", 
        help="视频输出文件夹"
    )
    
    parser.add_argument(
        "--quality", "-q",
        choices=["l", "m", "h", "p", "k"],
        default="h",
        help="渲染质量 (l=低质量, m=中质量, h=高质量, p=1440p, k=4K质量，默认: h)"
    )
    
    args = parser.parse_args()
    
    try:
        # 创建渲染器并执行批量渲染
        renderer = ManimBatchRenderer(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            quality=args.quality
        )
        
        results = renderer.render_all()
        
        # 根据结果设置退出码
        if results["failed"] == 0:
            print("所有文件渲染成功")
            sys.exit(0)
        else:
            print(f"有 {results['failed']} 个文件渲染失败")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"程序执行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()