#!/usr/bin/env python3
"""
Manim自动Wait语句生成器
整合语速分析和Wait语句插入功能

功能：
1. 解析音频时长信息文件
2. 分析每个文件的语速（秒/字）
3. 根据分析结果在Manim代码中自动插入合适的wait语句

使用方法：
python manim_auto_wait_generator.py <时长文件路径> <讲稿文件夹> <manim代码文件夹> <输出文件夹>

示例：
python manim_auto_wait_generator.py audio_duration.txt scripts/ code/ output/
"""

import os
import sys
import re
import glob
import argparse
import time
from pathlib import Path
from typing import List, Tuple, Dict, Optional

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


class ProgressBar:
    """简单的进度条实现，当tqdm不可用时使用"""
    
    def __init__(self, total, desc="Processing"):
        self.total = total
        self.current = 0
        self.desc = desc
        self.start_time = time.time()
        self.width = 50
        
    def update(self, n=1):
        self.current += n
        self._display()
        
    def _display(self):
        if self.total == 0:
            return
            
        percent = (self.current / self.total) * 100
        filled = int(self.width * self.current // self.total)
        bar = '█' * filled + '░' * (self.width - filled)
        
        elapsed = time.time() - self.start_time
        if self.current > 0:
            eta = elapsed * (self.total - self.current) / self.current
            eta_str = f"ETA: {eta:.0f}s"
        else:
            eta_str = "ETA: --s"
        
        sys.stdout.write(f'\r{self.desc}: [{bar}] {percent:6.2f}% ({self.current}/{self.total}) {eta_str}')
        sys.stdout.flush()
        
        if self.current >= self.total:
            print()
            
    def close(self):
        if self.current < self.total:
            self.current = self.total
            self._display()


class ManimAutoWaitGenerator:
    """整合语速分析和Wait语句插入的自动生成器"""
    
    def __init__(self, verbose: bool = True):
        self.duration_map = {}
        self.speed_config = {}
        self.verbose = verbose
        
    def parse_duration_file(self, duration_file_path: str) -> Dict[str, float]:
        """
        解析时长信息文件
        
        Args:
            duration_file_path: 时长信息文件路径
            
        Returns:
            {音频文件名(不含扩展名): 时长(秒)} 的字典
        """
        duration_map = {}
        
        try:
            with open(duration_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                # 解析格式：filename.wav\tduration 或 filename.wav    duration
                parts = re.split(r'\s+', line)  # 支持tab或多个空格分隔
                if len(parts) < 2:
                    print(f"警告：第{line_num}行格式不正确，跳过: {line}")
                    continue
                
                audio_file = parts[0].strip()
                duration_str = parts[1].strip()
                
                # 提取基础文件名（去掉.wav扩展名）
                base_name = os.path.splitext(audio_file)[0]
                
                # 提取时长数字（去掉's'后缀）
                duration_match = re.match(r'([\d.]+)s?', duration_str)
                if duration_match:
                    duration = float(duration_match.group(1))
                    duration_map[base_name] = duration
                else:
                    print(f"警告：第{line_num}行无法解析时长: {duration_str}")
        
        except FileNotFoundError:
            print(f"错误：找不到时长文件 {duration_file_path}")
            return {}
        except Exception as e:
            print(f"错误：读取时长文件时发生错误: {str(e)}")
            return {}
        
        return duration_map
    
    def count_characters_in_file(self, file_path: str) -> int:
        """
        计算文件中的字符数（只计算中文字符和英文字母数字）
        
        Args:
            file_path: 文件路径
            
        Returns:
            字符数
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 只计算中文字符和英文字母数字
            char_count = 0
            for char in content:
                if '\u4e00' <= char <= '\u9fff':  # 中文字符
                    char_count += 1
                elif char.isalnum():  # 英文字母和数字
                    char_count += 1
            
            return char_count
        
        except FileNotFoundError:
            print(f"错误：找不到讲稿文件 {file_path}")
            return 0
        except Exception as e:
            print(f"错误：读取讲稿文件时发生错误: {str(e)}")
            return 0
    
    def find_script_files(self, script_folder: str) -> List[str]:
        """
        查找讲稿文件夹中的txt文件
        
        Args:
            script_folder: 讲稿文件夹路径
            
        Returns:
            讲稿文件路径列表
        """
        script_folder = Path(script_folder)
        if not script_folder.exists():
            print(f"错误：讲稿文件夹不存在: {script_folder}")
            return []
        
        # 查找所有.txt和.md文件
        txt_files = list(script_folder.glob("*.txt"))
        md_files = list(script_folder.glob("*.md"))
        all_files = txt_files + md_files
        
        if not all_files:
            print(f"警告：在文件夹 {script_folder} 中未找到.txt或.md文件")
            return []
        
        # 转换为字符串路径并排序
        script_files = [str(f) for f in all_files]
        script_files.sort()
        
        return script_files
    
    def analyze_speech_rates(self, duration_map: Dict[str, float], script_files: List[str]) -> Dict[str, float]:
        """
        分析语速并生成配置数据
        
        Args:
            duration_map: {基础文件名: 时长} 字典
            script_files: 讲稿文件路径列表
            
        Returns:
            {文件名: 字数/秒} 字典
        """
        speed_config = {}
        matched_count = 0
        total_duration = 0
        total_chars = 0
        
        print("=" * 60)
        print("第一步：分析语速")
        print("=" * 60)
        
        for script_file in script_files:
            # 提取讲稿文件的基础名称
            base_name = os.path.splitext(os.path.basename(script_file))[0]
            
            if base_name in duration_map:
                duration = duration_map[base_name]
                char_count = self.count_characters_in_file(script_file)
                
                if char_count > 0:
                    chars_per_second = char_count / duration  # 字/秒
                    speed_config[base_name] = chars_per_second
                    matched_count += 1
                    total_duration += duration
                    total_chars += char_count
                    print(f"✓ {base_name}: {duration}秒, {char_count}字, {chars_per_second:.2f}字/秒")
                else:
                    print(f"✗ {base_name}: 讲稿文件为空或无有效字符")
            else:
                print(f"✗ {base_name}: 未找到对应的时长信息")
        
        if matched_count > 0:
            overall_speed = total_chars / total_duration
            print(f"\n语速统计摘要:")
            print(f"  匹配成功: {matched_count}/{len(script_files)} 个文件")
            print(f"  总时长: {total_duration:.1f} 秒")
            print(f"  总字数: {total_chars} 字")
            print(f"  整体平均语速: {overall_speed:.2f} 字/秒")
        
        return speed_config
    
    def find_files(self, folder_path: str, file_extension: str) -> List[str]:
        """
        查找指定文件夹下的特定扩展名文件，按字母序排序
        
        Args:
            folder_path: 文件夹路径
            file_extension: 文件扩展名（如'.py', '.txt', '.md'）
            
        Returns:
            排序后的文件路径列表
        """
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        # 查找指定扩展名的文件
        pattern = f"*{file_extension}"
        files = glob.glob(os.path.join(folder_path, pattern))
        
        if not files:
            print(f"WARNING: No {file_extension} files found in folder {folder_path}")
            return []
        
        # 按字母序排序
        files.sort()
        
        return files
    
    def extract_base_filename(self, file_path: str) -> str:
        """
        提取文件的基础名称（无扩展名）
        
        Args:
            file_path: 文件路径
            
        Returns:
            基础文件名
        """
        return os.path.splitext(os.path.basename(file_path))[0]
    
    def match_files(self, manim_files: List[str], script_files: List[str]) -> List[Tuple[str, str]]:
        """
        根据文件名匹配Manim代码文件和讲稿文件
        
        Args:
            manim_files: Manim Python文件列表
            script_files: 讲稿文件列表
            
        Returns:
            匹配的文件对列表 [(manim_file, script_file), ...]
        """
        # 创建讲稿文件的基础名称映射
        script_name_map = {}
        for script_file in script_files:
            base_name = self.extract_base_filename(script_file)
            script_name_map[base_name] = script_file
        
        # 匹配文件
        matched_pairs = []
        unmatched_manim = []
        
        for manim_file in manim_files:
            base_name = self.extract_base_filename(manim_file)
            
            if base_name in script_name_map:
                matched_pairs.append((manim_file, script_name_map[base_name]))
            else:
                unmatched_manim.append(manim_file)
        
        # 报告匹配结果
        print(f"文件匹配结果:")
        print(f"  成功匹配: {len(matched_pairs)} 对文件")
        print(f"  未匹配的Manim文件: {len(unmatched_manim)} 个")
        
        return matched_pairs
    
    def read_file_content(self, file_path: str) -> str:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"ERROR: Failed to read file {file_path}: {e}")
            return ""
    
    def parse_script_breakpoints(self, script_content: str) -> List[Tuple[int, int, str]]:
        """
        解析讲稿中的断点，返回断点信息和段落内容
        
        Args:
            script_content: 讲稿内容
            
        Returns:
            断点信息列表 [(断点序号, 文本长度, 段落内容), ...]
        """
        # 查找所有断点标记 (BREAKPOINT: x) 或 [BREAKPOINT: x]
        breakpoint_pattern = r'[\(\[]BREAKPOINT:\s*(\d+)[\)\]]'
        
        # 分割文本为段落
        segments = []
        last_end = 0
        
        for match in re.finditer(breakpoint_pattern, script_content):
            breakpoint_num = int(match.group(1))
            start_pos = match.start()
            
            # 获取从上一个断点到当前断点之间的文本
            segment_text = script_content[last_end:start_pos].strip()
            
            if segment_text or len(segments) == 0:  # 包含第一个段落（即使为空）
                # 计算纯文本字数（去除标点和空白）
                clean_text = re.sub(r'[^\u4e00-\u9fff\w]', '', segment_text)
                char_count = len(clean_text)
                
                segments.append((breakpoint_num, char_count, segment_text))
            
            last_end = match.end()
        
        # 处理最后一个断点后的内容
        if last_end < len(script_content):
            final_segment = script_content[last_end:].strip()
            if final_segment:
                clean_text = re.sub(r'[^\u4e00-\u9fff\w]', '', final_segment)
                char_count = len(clean_text)
                # 使用一个很大的数字作为最终段落的断点号
                segments.append((9999, char_count, final_segment))
        
        return segments
    
    def calculate_wait_time(self, char_count: int, chars_per_second: float) -> float:
        """
        根据字数计算等待时间
        
        Args:
            char_count: 字符数
            chars_per_second: 该文件的语速（字/秒）
            
        Returns:
            等待时间（秒）
        """
        if char_count == 0:
            return 0.0
        
        wait_time = char_count / chars_per_second
        # 四舍五入到一位小数
        return round(wait_time, 1)
    
    def find_breakpoint_positions(self, manim_code: str) -> List[Tuple[int, int]]:
        """
        在Manim代码中查找断点位置
        
        Args:
            manim_code: Manim代码内容
            
        Returns:
            断点位置列表 [(行号, 断点序号), ...]
        """
        lines = manim_code.split('\n')
        breakpoint_positions = []
        
        # 查找断点注释 #BREAKPOINT: x
        breakpoint_pattern = r'#\s*BREAKPOINT:\s*(\d+)'
        
        for i, line in enumerate(lines):
            match = re.search(breakpoint_pattern, line)
            if match:
                breakpoint_num = int(match.group(1))
                breakpoint_positions.append((i, breakpoint_num))
        
        return breakpoint_positions
    
    def insert_wait_statements(self, manim_code: str, script_segments: List[Tuple[int, int, str]], 
                             chars_per_second: float) -> str:
        """
        在Manim代码中插入wait语句
        
        Args:
            manim_code: 原始Manim代码
            script_segments: 讲稿段落信息
            chars_per_second: 该文件的语速（字/秒）
            
        Returns:
            插入wait语句后的代码
        """
        lines = manim_code.split('\n')
        breakpoint_positions = self.find_breakpoint_positions(manim_code)
        
        if not breakpoint_positions:
            print("    WARNING: 代码中未找到断点标记")
            return manim_code
        
        # 创建断点到字数的映射
        segment_map = {}
        for breakpoint_num, char_count, content in script_segments:
            segment_map[breakpoint_num] = char_count
        
        # 从后往前处理，避免行号变化影响
        breakpoint_positions.sort(reverse=True)
        
        inserted_count = 0
        for line_num, breakpoint_num in breakpoint_positions:
            if breakpoint_num in segment_map:
                char_count = segment_map[breakpoint_num]
                wait_time = self.calculate_wait_time(char_count, chars_per_second)
                
                if wait_time > 0:
                    # 获取当前行的缩进
                    current_line = lines[line_num]
                    indent = len(current_line) - len(current_line.lstrip())
                    indent_str = ' ' * indent
                    
                    # 在断点行后插入wait语句
                    wait_line = f"{indent_str}self.wait({wait_time})  # {char_count}字, {chars_per_second:.1f}字/秒"
                    lines.insert(line_num + 1, wait_line)
                    inserted_count += 1
        
        print(f"    插入了 {inserted_count} 个 wait 语句")
        return '\n'.join(lines)
    
    def save_processed_file(self, processed_code: str, original_manim_file: str, output_dir: str, 
                          chars_per_second: float) -> str:
        """
        保存处理后的代码文件
        
        Args:
            processed_code: 处理后的代码
            original_manim_file: 原始Manim文件路径
            output_dir: 输出目录
            chars_per_second: 该文件的语速
            
        Returns:
            保存的文件路径
        """
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件名
        original_name = os.path.splitext(os.path.basename(original_manim_file))[0]
        output_file_path = os.path.join(output_dir, f"{original_name}.py")
        
        try:
            # 保存文件
            with open(output_file_path, 'w', encoding='utf-8') as f:
                # 添加文件头注释
                header = f'''#!/usr/bin/env python3
"""
Manim动画代码 - 已插入wait语句
原始文件: {os.path.basename(original_manim_file)}
处理时间: {time.strftime("%Y-%m-%d %H:%M:%S")}
语速设置: {chars_per_second:.2f} 字/秒 ({1/chars_per_second:.3f} 秒/字)
自动生成: manim_auto_wait_generator.py
"""

'''
                f.write(header)
                f.write(processed_code)
            
            return output_file_path
            
        except Exception as e:
            print(f"ERROR: Failed to save processed file for {original_name}: {e}")
            return ""
    
    def process_file_pair(self, manim_file: str, script_file: str, output_dir: str) -> Optional[str]:
        """
        处理单个文件对
        
        Args:
            manim_file: Manim代码文件路径
            script_file: 讲稿文件路径
            output_dir: 输出目录
            
        Returns:
            生成的文件路径，如果失败则返回None
        """
        base_name = self.extract_base_filename(manim_file)
        manim_name = os.path.basename(manim_file)
        script_name = os.path.basename(script_file)
        
        print(f"  正在处理: {manim_name} ↔ {script_name}")
        
        # 获取该文件的语速配置
        if base_name not in self.speed_config:
            print(f"    ERROR: 未找到文件 {base_name} 的语速信息")
            return None
        
        chars_per_second = self.speed_config[base_name]
        
        # 读取文件内容
        manim_code = self.read_file_content(manim_file)
        script_content = self.read_file_content(script_file)
        
        if not manim_code or not script_content:
            print(f"    ERROR: 文件读取失败")
            return None
        
        # 解析讲稿断点
        script_segments = self.parse_script_breakpoints(script_content)
        if not script_segments:
            print(f"    WARNING: 讲稿中未找到断点标记")
            return None
        
        total_chars = sum(char_count for _, char_count, _ in script_segments)
        total_time = self.calculate_wait_time(total_chars, chars_per_second)
        print(f"    讲稿分析: {len(script_segments)}个段落, {total_chars}字, {chars_per_second:.1f}字/秒, 预计{total_time}秒")
        
        # 插入wait语句
        processed_code = self.insert_wait_statements(manim_code, script_segments, chars_per_second)
        
        # 保存处理后的文件
        output_file = self.save_processed_file(processed_code, manim_file, output_dir, chars_per_second)
        
        if output_file:
            print(f"    生成文件: {os.path.basename(output_file)}")
            return output_file
        else:
            return None
    
    def process_all(self, duration_file: str, script_folder: str, manim_folder: str, 
                   output_folder: str) -> List[str]:
        """
        处理整个工作流程
        
        Args:
            duration_file: 音频时长文件路径
            script_folder: 讲稿文件夹路径
            manim_folder: Manim代码文件夹路径
            output_folder: 输出文件夹路径
            
        Returns:
            生成的文件路径列表
        """
        print("=" * 80)
        print("Manim自动Wait语句生成器")
        print("=" * 80)
        
        # 步骤1: 解析时长文件
        print("解析音频时长文件...")
        self.duration_map = self.parse_duration_file(duration_file)
        if not self.duration_map:
            print("无法解析时长信息，程序退出")
            return []
        
        print(f"解析到 {len(self.duration_map)} 个音频文件的时长信息")
        
        # 步骤2: 查找讲稿文件并分析语速
        print(f"\n扫描讲稿文件夹: {script_folder}")
        script_files = self.find_script_files(script_folder)
        if not script_files:
            print("未找到讲稿文件，程序退出")
            return []
        
        print(f"找到 {len(script_files)} 个讲稿文件")
        
        # 步骤3: 分析语速
        self.speed_config = self.analyze_speech_rates(self.duration_map, script_files)
        if not self.speed_config:
            print("语速分析失败，程序退出")
            return []
        
        # 步骤4: 查找Manim文件
        print(f"\n第二步：处理Manim代码文件")
        print("=" * 60)
        print(f"扫描Manim代码文件夹: {manim_folder}")
        manim_files = self.find_files(manim_folder, '.py')
        
        if not manim_files:
            print("未找到Manim代码文件，程序退出")
            return []
        
        print(f"找到 {len(manim_files)} 个Manim文件")
        
        # 步骤5: 匹配文件对
        matched_pairs = self.match_files(manim_files, script_files)
        
        if not matched_pairs:
            print("ERROR: 没有找到匹配的文件对")
            return []
        
        print()
        print(f"开始处理 {len(matched_pairs)} 对文件...")
        print("-" * 60)
        
        generated_files = []
        success_count = 0
        
        # 初始化进度条
        if HAS_TQDM:
            pbar = tqdm(
                total=len(matched_pairs),
                desc="处理文件",
                unit="pair",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
            )
        else:
            pbar = ProgressBar(total=len(matched_pairs), desc="处理文件")
        
        for manim_file, script_file in matched_pairs:
            # 处理文件对
            output_file = self.process_file_pair(manim_file, script_file, output_folder)
            
            if output_file:
                generated_files.append(output_file)
                success_count += 1
            
            # 更新进度条
            if HAS_TQDM:
                pbar.update(1)
            else:
                pbar.update()
        
        # 关闭进度条
        if HAS_TQDM:
            pbar.close()
        else:
            pbar.close()
        
        # 输出结果摘要
        print("\n" + "=" * 60)
        print("自动Wait语句生成完成")
        print("=" * 60)
        print(f"处理结果:")
        print(f"  成功处理: {success_count} 个文件")
        print(f"  失败处理: {len(matched_pairs) - success_count} 个文件")
        print(f"  输出目录: {output_folder}")
        
        if generated_files:
            print(f"\n生成的文件:")
            for file_path in generated_files:
                print(f"  - {os.path.basename(file_path)}")
        
        return generated_files
    
    def pipeline(self, duration_file: str, script_folder: str, manim_folder: str, output_folder: str) -> List[str]:
        """
        作为流水线的一部分处理所有步骤
        
        Args:
            duration_file: 音频时长文件路径
            script_folder: 讲稿文件夹路径
            manim_folder: Manim代码文件夹路径
            output_folder: 输出文件夹路径
            
        Returns:
            生成的文件路径列表
        """
        return self.process_all(duration_file, script_folder, manim_folder, output_folder)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Manim自动Wait语句生成器 - 整合语速分析和Wait语句插入",
        epilog="""使用示例:
python manim_auto_wait_generator.py audio_duration.txt scripts/ code/ output/

工作流程:
1. 解析音频时长文件，获取每个文件的播放时长
2. 分析讲稿文件的字数，计算每个文件的个性化语速
3. 根据语速在Manim代码的断点处插入合适的wait语句

文件要求:
- 音频时长文件: 每行格式为 "filename.wav  duration_seconds"
- 讲稿文件: 包含 (BREAKPOINT: x) 或 [BREAKPOINT: x] 标记
- Manim代码: 包含 #BREAKPOINT: x 标记
- 文件名需要匹配（相同的基础文件名）
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "duration_file",
        help="音频时长信息文件路径"
    )
    parser.add_argument(
        "script_folder",
        help="包含讲稿文件的文件夹路径"
    )
    parser.add_argument(
        "manim_folder", 
        help="包含Manim Python代码的文件夹路径"
    )
    parser.add_argument(
        "output_folder",
        help="输出文件夹路径"
    )
    
    args = parser.parse_args()
    
    try:
        # 创建自动生成器
        generator = ManimAutoWaitGenerator()
        
        # 执行完整的工作流程
        generated_files = generator.process_all(
            duration_file=args.duration_file,
            script_folder=args.script_folder,
            manim_folder=args.manim_folder,
            output_folder=args.output_folder
        )
        
        if generated_files:
            print(f"\nSUCCESS: 自动Wait语句生成完成!")
            print(f"生成了 {len(generated_files)} 个处理后的文件")
        else:
            print("\nWARNING: 没有成功生成任何文件")
            exit(1)
            
    except Exception as e:
        print(f"\nERROR: 程序执行失败: {e}")
        print("\n请确保:")
        print("1. 音频时长文件格式正确 (filename.wav  duration)")
        print("2. 讲稿文件中包含 (BREAKPOINT: x) 或 [BREAKPOINT: x] 格式的断点标记")
        print("3. Manim代码文件中包含 #BREAKPOINT: x 格式的断点标记")
        print("4. 文件名匹配（相同的基础文件名）")
        print("5. 输入文件夹路径正确且包含对应的文件")
        exit(1)


if __name__ == "__main__":
    main()