import os
import time
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path

def run_subprocess_command(command: list, description: str = "", verbose: bool = True) -> bool:
    """
    运行子进程命令，提供更好的错误处理和日志
    
    参数:
        command: 命令列表
        description: 命令描述
        verbose: 是否输出详细信息
    
    返回:
        是否成功执行
    """
    if verbose and description:
        print(f"正在执行: {description}")
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            if verbose:
                print(f"命令执行失败: {description}")
                print(f"返回码: {result.returncode}")
                if result.stdout:
                    print(f"标准输出: {result.stdout}")
                if result.stderr:
                    print(f"标准错误: {result.stderr}")
            return False
        
        if verbose and result.stdout:
            print(f"命令输出: {result.stdout}")
            
        return True
        
    except Exception as e:
        if verbose:
            print(f"执行命令时发生异常: {description}")
            print(f"错误信息: {str(e)}")
        return False

def ensure_directory_exists(directory: str) -> None:
    """确保目录存在，如果不存在则创建"""
    os.makedirs(directory, exist_ok=True)

def video_render_merge(manim_code_path: str, speech_audio_path: str, output_dir: str,
                      quality: str = "h", verbose: bool = True) -> Dict[str, Any]:
    """
    视频渲染和音视频合并
    
    参数:
        manim_code_path: Manim代码路径
        speech_audio_path: 语音音频路径
        output_dir: 输出目录
        quality: 视频质量 (l/m/h/p/k)
        verbose: 是否显示详细日志
    
    返回:
        包含处理结果和时间信息的字典
    """
    start_time = time.time()
    
    if verbose:
        print(f"开始视频渲染和合并处理")
        print(f"Manim代码路径: {manim_code_path}")
        print(f"语音音频路径: {speech_audio_path}")
        print(f"输出目录: {output_dir}")
    
    # 检查输入路径是否存在
    if not os.path.exists(manim_code_path):
        raise FileNotFoundError(f"Manim代码路径不存在: {manim_code_path}")
    if not os.path.exists(speech_audio_path):
        raise FileNotFoundError(f"语音音频路径不存在: {speech_audio_path}")
    
    # 创建输出目录
    ensure_directory_exists(output_dir)
    
    # 1. 渲染视频（无音频）
    video_wo_audio_output_path = os.path.join(output_dir, "video_wo_audio")
    ensure_directory_exists(video_wo_audio_output_path)
    
    render_command = [
        "python",
        "batch_render_manim.py",
        manim_code_path,
        video_wo_audio_output_path,
        "--quality", quality
    ]
    
    success = run_subprocess_command(render_command, "渲染Manim视频", verbose)
    if not success:
        print("警告: 存在视频渲染失败")
    
    render_time = time.time() - start_time
    
    # 2. 合并音频和视频
    video_w_audio_output_path = os.path.join(output_dir, "video_w_audio")
    
    merge_command = [
        "python",
        "video_audio_merge.py",
        speech_audio_path,
        video_wo_audio_output_path,
        video_w_audio_output_path
    ]
    
    success = run_subprocess_command(merge_command, "合并音视频", verbose)
    if not success:
        raise RuntimeError("音视频合并失败")
    
    merge_time = time.time() - start_time - render_time
    total_time = time.time() - start_time
    
    # 保存时间日志
    time_dict = {
        "render_time": render_time,
        "merge_time": merge_time,
        "total_time": total_time
    }
    
    time_log_path = os.path.join(output_dir, f"render_merge_log_{int(time.time())}.txt")
    with open(time_log_path, 'w', encoding='utf-8') as f:
        for key, value in time_dict.items():
            f.write(f"{key}: {value:.2f} 秒\n")
    
    # 返回结果信息
    result_info = {
        "video_w_audio_output_path": video_w_audio_output_path,
        "video_wo_audio_output_path": video_wo_audio_output_path,
        "speech_audio_path": speech_audio_path,
        "output_dir": output_dir,
        "time_dict": time_dict,
        "time_log_path": time_log_path
    }
    
    if verbose:
        print(f"视频渲染和合并完成! 总耗时: {total_time:.2f} 秒")
        print(f"最终视频输出路径: {video_w_audio_output_path}")
        print(f"时间日志已保存至: {time_log_path}")
    
    return result_info

if __name__ == "__main__":
    # 示例用法
    manim_code_path = "/Users/hendrick/Desktop/manim_codes_final"
    speech_audio_path = "/Users/hendrick/Desktop/test_signal/speech_audio"
    output_dir = "/Users/hendrick/Desktop/test_signal/video_w_audio"
    
    try:
        result = video_render_merge(
            manim_code_path=manim_code_path,
            speech_audio_path=speech_audio_path,
            output_dir=output_dir,
            quality="h",
            verbose=True
        )
        print(f"处理成功完成!")
        print(f"最终视频路径: {result['video_w_audio_output_path']}")
    except Exception as e:
        print(f"处理失败: {str(e)}")
        import traceback
        traceback.print_exc()