import os
import sys
import subprocess
import re

def parse_speech_txt(speech_txt_path):
    """
    解析时长信息文件，提取音频文件信息
    
    Args:
        speech_txt_path (str): 时长信息文件路径
    
    Returns:
        list: 包含(音频文件名, 时长)的元组列表
    """
    audio_info = []
    
    try:
        with open(speech_txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 解析格式：filename.wav	duration
            parts = line.split('\t')
            if len(parts) != 2:
                print(f"⚠️  警告：跳过格式不正确的行: {line}")
                continue
            
            audio_file = parts[0].strip()
            duration_str = parts[1].strip()
            
            # 提取时长数字（去掉's'后缀）
            duration_match = re.match(r'([\d.]+)s?', duration_str)
            if duration_match:
                duration = float(duration_match.group(1))
                audio_info.append((audio_file, duration))
            else:
                print(f"⚠️  警告：无法解析时长: {duration_str}")
    
    except FileNotFoundError:
        print(f"❌ 错误：找不到文件 {speech_txt_path}")
        return []
    except Exception as e:
        print(f"❌ 错误：读取文件时发生错误: {str(e)}")
        return []
    
    return audio_info

def get_corresponding_code_file(audio_filename):
    """
    根据音频文件名生成对应的代码文件名
    
    Args:
        audio_filename (str): 音频文件名，如 "1_1.wav"
    
    Returns:
        str: 对应的代码文件名，如 "1_1.py"
    """
    # 移除.wav扩展名，直接添加.py扩展名
    base_name = os.path.splitext(audio_filename)[0]
    code_filename = base_name + '.py'
    
    return code_filename

def run_wait_time_calculator(duration, code_file_path):
    """
    运行video_audio_calcu.py脚本
    
    Args:
        duration (float): 目标时长
        code_file_path (str): 代码文件路径
    
    Returns:
        bool: 是否成功执行
    """
    try:
        cmd = ['python3', 'video_audio_calcu.py', str(duration), code_file_path]
        print(f"🔧 执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"⚠️  stderr: {result.stderr}")
        
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败，退出码: {e.returncode}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 执行过程中发生错误: {str(e)}")
        return False

def align_audio_with_video(speech_folder, manim_code_folder):
    # 解析时长信息文件
    print("📖 解析时长信息文件...")
    audio_info = parse_speech_txt(speech_folder)
    
    if not audio_info:
        print("❌ 没有找到有效的音频信息")
        sys.exit(1)
    
    print(f"✅ 找到 {len(audio_info)} 个音频文件")
    
    # 处理每个音频文件
    success_count = 0
    total_count = len(audio_info)
    
    for i, (audio_file, duration) in enumerate(audio_info, 1):
        print(f"\n🎵 [{i}/{total_count}] 处理: {audio_file}")
        print(f"   时长: {duration}s")
        
        # 生成对应的代码文件名
        code_filename = get_corresponding_code_file(audio_file)
        code_file_path = os.path.join(manim_code_folder, code_filename)
        
        print(f"   对应代码文件: {code_filename}")
        
        # 检查代码文件是否存在
        if not os.path.exists(code_file_path):
            print(f"   ❌ 代码文件不存在: {code_file_path}")
            continue
        
        # 运行video_audio_calcu.py
        print(f"   🔧 调整代码文件以匹配音频时长...")
        if run_wait_time_calculator(duration, code_file_path):
            print(f"   ✅ 处理完成")
            success_count += 1
        else:
            print(f"   ❌ 处理失败")

    return success_count == total_count

def main():
    if len(sys.argv) != 3:
        print("❌ 错误: 请提供时长信息文件路径和代码目录路径")
        print("📝 使用方法: python3 video_audio_align.py <SPEECH_TXT_PATH> <CODE_DIR_PATH>")
        print("📝 示例: python3 video_audio_align.py Audio/KNN_9757_sections/KNN_9757_sections.txt Code/KNN_9757_sections")
        print("📝 示例: python3 video_audio_align.py ./Audio/regression_sections/regression_sections.txt ./Code/regression_sections")
        sys.exit(1)
    
    speech_txt_path = sys.argv[1]
    code_dir = sys.argv[2]

    print("🎬 开始音视频对齐处理")
    print(f"📄 时长信息文件路径: {speech_txt_path}")
    print(f"📁 Code目录: {code_dir}")
    print("=" * 50)
    
    # 检查必要的文件和目录是否存在
    if not os.path.exists(speech_txt_path):
        print(f"❌ 错误：时长信息文件不存在: {speech_txt_path}")
        sys.exit(1)
    
    if not os.path.exists(code_dir):
        print(f"❌ 错误：Code目录不存在: {code_dir}")
        sys.exit(1)
    
    # 解析时长信息文件
    print("📖 解析时长信息文件...")
    audio_info = parse_speech_txt(speech_txt_path)
    
    if not audio_info:
        print("❌ 没有找到有效的音频信息")
        sys.exit(1)
    
    print(f"✅ 找到 {len(audio_info)} 个音频文件")
    
    # 处理每个音频文件
    success_count = 0
    total_count = len(audio_info)
    
    for i, (audio_file, duration) in enumerate(audio_info, 1):
        print(f"\n🎵 [{i}/{total_count}] 处理: {audio_file}")
        print(f"   时长: {duration}s")
        
        # 生成对应的代码文件名
        code_filename = get_corresponding_code_file(audio_file)
        code_file_path = os.path.join(code_dir, code_filename)
        
        print(f"   对应代码文件: {code_filename}")
        
        # 检查代码文件是否存在
        if not os.path.exists(code_file_path):
            print(f"   ❌ 代码文件不存在: {code_file_path}")
            continue
        
        # 运行video_audio_calcu.py
        print(f"   🔧 调整代码文件以匹配音频时长...")
        if run_wait_time_calculator(duration, code_file_path):
            print(f"   ✅ 处理完成")
            success_count += 1
        else:
            print(f"   ❌ 处理失败")
    
    print("\n" + "=" * 50)
    print(f"🎊 音视频对齐处理完成！")
    print(f"📊 处理结果: {success_count}/{total_count} 个文件成功处理")
    
    if success_count == total_count:
        print("✨ 所有文件都已成功对齐！")
    elif success_count > 0:
        print(f"⚠️  部分文件处理失败，请检查错误信息")
    else:
        print("❌ 所有文件处理都失败了，请检查配置和文件路径")

if __name__ == "__main__":
    main() 