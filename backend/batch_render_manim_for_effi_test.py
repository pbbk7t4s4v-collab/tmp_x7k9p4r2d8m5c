#!/usr/bin/env python3
"""并行渲染 Manim 代码脚本"""
import argparse
import concurrent.futures
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional
import base64

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


class ParallelManimRenderer:
    def __init__(self, input_dir: str, output_dir: str, quality: str, workers: int):
        self.input_dir = Path(input_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.quality = quality
        self.workers = max(1, workers)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if not self.input_dir.exists():
            raise FileNotFoundError(f"输入目录不存在: {self.input_dir}")

    def _extract_scene_classes(self, python_file: Path) -> List[str]:
        try:
            content = python_file.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"读取 {python_file.name} 失败: {exc}")
            return []

        pattern = r'class\s+(\w+)\s*\([^)]*Scene[^)]*\)\s*:'
        matches = re.findall(pattern, content)
        if matches:
            return matches

        fallback = r'class\s+(\w+)\s*\([^)]*\)\s*:'
        alt_matches = re.findall(fallback, content)
        if alt_matches:
            print(f"警告 {python_file.name}: 未找到 Scene 继承关系，退回到所有类: {alt_matches}")
        return alt_matches

    def _find_generated_video(self, python_file: Path, scene_class: str) -> Optional[Path]:
        quality_map = {
            "l": "480p15",
            "m": "720p30",
            "h": "1080p60",
            "p": "1440p60",
            "k": "2160p60",
        }
        quality_folder = quality_map.get(self.quality, "1080p60")
        candidates = [
            python_file.parent / "media" / "videos" / python_file.stem / quality_folder / f"{scene_class}.mp4",
            python_file.parent / "media" / "videos" / python_file.stem / quality_folder / f"{scene_class}.mov",
            python_file.parent / "media" / "videos" / f"{scene_class}.mp4",
            python_file.parent / "media" / "videos" / f"{scene_class}.mov",
        ]
        for path in candidates:
            if path.exists():
                return path

        media_dir = python_file.parent / "media"
        if media_dir.exists():
            for video_file in media_dir.rglob("*.mp4"):
                if scene_class in video_file.stem:
                    return video_file
            for video_file in media_dir.rglob("*.mov"):
                if scene_class in video_file.stem:
                    return video_file
        return None

    def _copy_video_to_output(self, video_file: Path, python_file: Path) -> bool:
        tmp_out = None
        try:
            final_path = self.output_dir / f"{python_file.stem}{video_file.suffix}"
            # 先拷贝到一个临时文件，再使用原子替换以避免并发写入导致的损坏/部分写入
            tmp_out = self.output_dir / f".{python_file.stem}.{uuid.uuid4().hex}{video_file.suffix}.tmp"
            shutil.copy2(video_file, tmp_out)
            os.replace(tmp_out, final_path)
            return True
        except Exception as exc:
            print(f"复制视频失败 {python_file.name}: {exc}")
            # 清理临时文件（若存在）
            try:
                if tmp_out and tmp_out.exists():
                    tmp_out.unlink()
            except Exception:
                pass
            return False

    def _render_scene(self, python_file: Path, scene_class: str) -> Optional[Path]:
        # 如果已存在生成的视频，直接返回
        existing = self._find_generated_video(python_file, scene_class)
        if existing:
            copied = self._copy_video_to_output(existing, python_file)
            return existing if copied else None

        # 为避免多个并发 manim 进程在同一 media/Tex 等中间文件上冲突，
        # 使用每个渲染任务独立的临时工作目录：
        # 1) 将源 .py 文件（及同目录下的其他 .py）复制到临时目录
        # 2) 在临时目录运行 manim
        # 3) 从临时目录的 media 中查找生成的视频并复制回输出
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                # 复制当前文件和同目录下的 .py（以支持相对导入）
                try:
                    shutil.copy2(python_file, tmpdir_path / python_file.name)
                except Exception:
                    # 如果单文件复制失败，仍继续以免整体失败
                    pass

                for p in python_file.parent.glob("*.py"):
                    try:
                        shutil.copy2(p, tmpdir_path / p.name)
                    except Exception:
                        # 忽略复制失败的非关键文件
                        pass

                # 扫描代码中对图片资源的引用（例如 ImageMobject("placeholder.png")）
                # 并尝试把这些资源从可能的位置复制到临时目录，避免 manim 在临时工作目录中找不到图片
                try:
                    code_text = python_file.read_text(encoding="utf-8")
                    # 匹配 ImageMobject("...") 的情况
                    asset_names = set(re.findall(r'ImageMobject\(\s*["\']([^"\']+)["\']\s*\)', code_text))
                    # 也匹配直接用相对路径的字符串（例如用于背景/其他加载）
                    asset_names.update(re.findall(r'\b["\']([^"\']+\.(?:png|jpg|jpeg|gif|svg))["\']', code_text))
                except Exception:
                    asset_names = set()

                if asset_names:
                    repo_root = Path(__file__).resolve().parent
                    for asset in asset_names:
                        # 如果是绝对路径或包含目录，直接尝试拷贝
                        candidates = []
                        try:
                            candidates.append(python_file.parent / asset)
                            candidates.append(Path(asset))
                            candidates.append(Path.cwd() / asset)
                            candidates.append(repo_root / asset)
                            # 兼容旧项目结构的 manim_editor/backend
                            candidates.append(repo_root / 'manim_editor' / 'backend' / asset)
                        except Exception:
                            candidates = []

                        found = False
                        for cand in candidates:
                            if cand.exists():
                                try:
                                    shutil.copy2(cand, tmpdir_path / Path(asset).name)
                                    print(f"[ASSET] 已复制资源到临时目录: {cand} -> {tmpdir_path / Path(asset).name}")
                                    found = True
                                    break
                                except Exception:
                                    # 忽略单个资源复制失败
                                    pass
                        if not found:
                            # 未找到资源：打印提示并在临时目录生成一个最小透明 PNG 作为降级占位
                            print(f"[ASSET] 未找到资源: {asset}（已尝试在源目录、工作目录和 manim_editor/backend 中查找），将生成透明占位图")
                            try:
                                # 1x1 透明 PNG 的 base64 表示（无需外部库）
                                _transparent_png_b64 = (
                                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
                                )
                                with open(tmpdir_path / Path(asset).name, "wb") as _f:
                                    _f.write(base64.b64decode(_transparent_png_b64))
                                print(f"[ASSET] 已生成透明占位图: {tmpdir_path / Path(asset).name}")
                            except Exception:
                                pass

                cmd = [
                    "manim",
                    "render",
                    "-q",
                    self.quality,
                    str(tmpdir_path / python_file.name),
                    scene_class,
                ]

                try:
                    result = subprocess.run(
                        cmd,
                        cwd=tmpdir_path,
                        capture_output=True,
                        text=True,
                        timeout=1800,
                    )
                except subprocess.TimeoutExpired:
                    print(f"渲染超时 {python_file.name} -> {scene_class}")
                    return None
                except Exception as exc:
                    print(f"渲染异常 {python_file.name} -> {scene_class}: {exc}")
                    return None

                if result.returncode != 0:
                    print(f"渲染失败 {python_file.name} -> {scene_class}")
                    if result.stderr:
                        print(result.stderr.strip())
                    return None

                # 在临时目录中查找生成的视频
                temp_python = tmpdir_path / python_file.name
                found = self._find_generated_video(temp_python, scene_class)
                if not found:
                    return None

                # 将找到的视频复制到最终输出目录（原子复制）
                copied = self._copy_video_to_output(found, python_file)
                if copied:
                    # 返回最终输出路径
                    return self.output_dir / f"{python_file.stem}{found.suffix}"
                else:
                    return None
        except Exception as exc:
            print(f"渲染过程出错 {python_file.name} -> {scene_class}: {exc}")
            return None

    def _process_file(self, python_file: Path) -> bool:
        scenes = self._extract_scene_classes(python_file)
        if not scenes:
            print(f"未找到 Scene 类: {python_file.name}")
            return False

        for scene in scenes:
            video = self._render_scene(python_file, scene)
            # _render_scene 在成功时会把视频复制到输出目录并返回最终输出路径
            if video:
                print(f"[OK] {python_file.name} -> {scene}")
                return True
        print(f"[FAIL] {python_file.name}")
        return False

    def render_all(self) -> dict:
        python_files = sorted(self.input_dir.glob("*.py"), key=lambda p: p.name)
        if not python_files:
            print(f"在 {self.input_dir} 中未找到 Python 文件")
            return {"total": 0, "success": 0, "failed": 0}

        total = len(python_files)
        print(f"找到 {total} 个文件，使用 {self.workers} 线并发渲染任务")

        iterator = None
        if HAS_TQDM:
            iterator = tqdm(total=total, desc="渲染进度", unit="文件")

        success = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_file = {
                executor.submit(self._process_file, python_file): python_file
                for python_file in python_files
            }
            for future in concurrent.futures.as_completed(future_to_file):
                python_file = future_to_file[future]
                try:
                    if future.result():
                        success += 1
                except Exception as exc:
                    print(f"处理 {python_file.name} 时异常: {exc}")
                if HAS_TQDM:
                    iterator.update(1)

        if HAS_TQDM:
            iterator.close()

        failed = total - success
        print("\n渲染完成")
        print(f"总数: {total}")
        print(f"成功: {success}")
        print(f"失败: {failed}")
        print(f"输出目录: {self.output_dir}")
        return {"total": total, "success": success, "failed": failed}


def main(input_dir: str, output_dir: str, quality: str, workers: int) -> int:
    renderer = ParallelManimRenderer(input_dir, output_dir, quality, workers)
    results = renderer.render_all()
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="并行渲染 Manim 代码")
    parser.add_argument("--input_dir", default="/home/LocalQwen3/model_test/1125_manim_coder", help="包含 Manim Python 代码的目录")
    parser.add_argument("--output_dir", default="/home/LocalQwen3/model_test/1125_manim_coder_output_video", help="输出视频目录")
    parser.add_argument("--quality", "-q", choices=["l", "m", "h", "p", "k"], default="h", help="渲染质量")
    parser.add_argument("--workers", type=int, default=12, help="并行渲染任务数 (>=1)")
    args = parser.parse_args()

    try:
        exit_code = main(args.input_dir, args.output_dir, args.quality, args.workers)
    except KeyboardInterrupt:
        print("\n用户中断操作")
        exit_code = 1
    except Exception as exc:
        print(f"执行失败: {exc}")
        exit_code = 1

    raise SystemExit(exit_code)
