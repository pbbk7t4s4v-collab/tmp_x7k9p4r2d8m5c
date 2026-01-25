#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单独调用封面/尾页 Scene.render()，并打印：
1) manim_config 的关键配置
2) 渲染是否报错
3) output_dir 实际生成了哪些内容（包括 mp4、partial_movie_files）

用法示例：
    conda activate manim_env
    python debug_cover_ending_render.py \
        --scene cover \
        --lang zh \
        --output_dir /home/TeachMaster/ML/debug_output \
        --quality 1080p60
"""

import argparse
import os
import sys
from pathlib import Path

# 根据你实际项目目录调整
BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.append(str(BACKEND_ROOT))
sys.path.append(str(BACKEND_ROOT.parent))

from manim import config as manim_config

# 导入你的封面/尾页 Scene
from Demo import MergedLayoutScene2
from Demo_cn import MergedLayoutScene2_cn
from EndingDemo import EndingScene
from EndingDemo_cn import EndingScene_cn


def list_videos_under(output_dir: Path):
    """递归列出 output_dir 下所有文件（用于调试）"""
    print("\n==== 扫描输出目录内容 ====")
    if not output_dir.exists():
        print(f"[WARN] 输出目录不存在: {output_dir}")
        return

    for p in sorted(output_dir.rglob("*")):
        rel = p.relative_to(output_dir)
        if p.is_dir():
            print(f"[DIR ] {rel}")
        else:
            print(f"[FILE] {rel}")
    print("==== 扫描结束 ====\n")


def choose_scene(scene_type: str, lang: str):
    """根据 scene_type + lang 返回对应 Scene 类"""
    if lang == "zh":
        return MergedLayoutScene2_cn if scene_type == "cover" else EndingScene_cn
    else:
        return MergedLayoutScene2 if scene_type == "cover" else EndingScene


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", choices=["cover", "ending"], required=True)
    parser.add_argument("--lang", choices=["zh", "en"], default="zh")
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--quality", default="1080p60")
    parser.add_argument("--course_title", default="测试课程标题")
    parser.add_argument("--professor_name", default="Prof. Test")
    parser.add_argument("--avatar_image", default="csh.png")
    parser.add_argument("--background_image", default="SAI.png")
    parser.add_argument("--school", default="测试学校")
    parser.add_argument("--university", default="测试大学")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # 设置 Manim 全局配置（很关键）
    manim_config.media_dir = str(output_dir)
    manim_config.quality = args.quality
    manim_config.preview = False  # 建议关闭 preview

    print("==== Manim 配置 ====")
    print(f"media_dir   = {manim_config.media_dir}")
    print(f"quality     = {manim_config.quality}")
    print(f"preview     = {manim_config.preview}")
    print("====================\n")

    SceneClass = choose_scene(args.scene, args.lang)

    # 处理图片路径
    avatar_image = (BACKEND_ROOT / args.avatar_image).resolve()
    background_image = (BACKEND_ROOT / args.background_image).resolve()

    print(f"[INFO] 使用 Scene: {SceneClass.__name__}")
    print(f"[INFO] avatar_image      = {avatar_image}")
    print(f"[INFO] background_image  = {background_image}")

    # 初始化 scene（按你 Demo 内的构造函数名调整参数）
    scene = SceneClass(
        class_title_text=args.course_title,
        avatar_image=str(avatar_image),
        professor_name=args.professor_name,
        background_image=str(background_image),
        school=args.school,
        university=args.university,
    )

    # 渲染
    try:
        print(f"[INFO] 开始渲染 {SceneClass.__name__} ...")
        scene.render()
        print(f"[INFO] Scene.render() 完成。")
    except Exception as e:
        print(f"[ERROR] 渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 打印输出结果
    list_videos_under(output_dir)


if __name__ == "__main__":
    main()
