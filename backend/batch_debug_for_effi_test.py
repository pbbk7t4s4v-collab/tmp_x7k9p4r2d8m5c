#!/usr/bin/env python3
"""并行调试 Manim 代码脚本"""
import argparse
import concurrent.futures
import pathlib
from typing import Optional
import time
import datetime
import auto_debug_manim as adm


def _run_single_debug(file_path: pathlib.Path, render_dir: Optional[str]) -> bool:
    print(f"\n=== 开始调试 {file_path.name} ===")
    try:
        adm.main(str(file_path), render_dir=render_dir)
        print(f"[OK] {file_path.name} 调试完成")
        return True
    except Exception as exc:  # 记录失败但不中断其它任务
        print(f"[ERROR] {file_path.name}: {exc}")
        return False


def main(folder: str, render_dir: Optional[str], workers: int) -> int:
    target_dir = pathlib.Path(folder)
    if not target_dir.exists():
        raise FileNotFoundError(f"调试目录不存在: {target_dir}")

    files = [
        f for f in sorted(target_dir.glob("*.py"))
        if f.name not in {"auto_debug_manim.py", "batch_debug.py", "batch_debug_for_effi_test.py"}
    ]
    if not files:
        print(f"在 {target_dir} 中未找到需要调试的文件")
        return 0

    workers = max(1, workers)
    print(f"共 {len(files)} 个文件，使用 {workers} 个并发任务进行调试")

    success = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_file = {executor.submit(_run_single_debug, file_path, render_dir): file_path for file_path in files}
        for future in concurrent.futures.as_completed(future_to_file):
            if future.result():
                success += 1

    failed = len(files) - success
    print("\n调试完成")
    print(f"成功: {success}")
    print(f"失败: {failed}")
    return failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="并行调试 Manim 代码")
    parser.add_argument("--folder", default="/home/TeachMaster/ML/effi_test/1_planner_output_code/coder_outputs_debugged", help="待调试的代码目录")
    parser.add_argument("--render_dir", nargs="?", default="./effi_test/1_planner_output_vedio", help="可选的渲染输出目录")
    parser.add_argument("--workers", type=int, default=4, help="并行调试任务数 (>=1)")
    args = parser.parse_args()

    # 记录开始时间，便于后续效率对比
    start_perf = time.perf_counter()
    start_dt = datetime.datetime.now()
    print(f"开始时间: {start_dt.isoformat(sep=' ')}")

    exit_code = 0
    try:
        failures = main(args.folder, args.render_dir, args.workers)
        if failures > 0:
            exit_code = 1
    except KeyboardInterrupt:
        print("\n用户中断操作")
        exit_code = 1
    except Exception as exc:
        print(f"执行失败: {exc}")
        exit_code = 1
    finally:
        end_perf = time.perf_counter()
        elapsed = end_perf - start_perf
        end_dt = start_dt + datetime.timedelta(seconds=elapsed)
        # 打印可读的总耗时与开始/结束时间
        print(f"结束时间: {end_dt.isoformat(sep=' ')}")
        print(f"总运行时间: {elapsed:.2f} 秒")

    raise SystemExit(exit_code)
