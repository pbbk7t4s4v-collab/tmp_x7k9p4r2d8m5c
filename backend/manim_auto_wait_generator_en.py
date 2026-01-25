#!/usr/bin/env python3
"""
Manim自动Wait语句生成器
整合语速分析和Wait语句插入功能

功能：
1. 解析音频时长信息文件
2. 分析每个文件的语速（单词/秒）
   - 英文：连续字母数字下划线序列（\w+）视为一个单词
   - 中文：每个汉字计为一个“词”（便于中英混合脚本统一处理）
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


class ManimAutoWaitGenerator_en:
    """整合语速分析和Wait语句插入的自动生成器"""

    def __init__(self, verbose: bool = True):
        self.duration_map: Dict[str, float] = {}
        self.speed_config: Dict[str, float] = {}
        self.verbose = verbose

    # ---------- 基础解析 ----------

    def parse_duration_file(self, duration_file_path: str) -> Dict[str, float]:
        """
        解析时长信息文件
        Returns: {音频文件名(不含扩展名): 时长(秒)}
        """
        duration_map: Dict[str, float] = {}
        try:
            with open(duration_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                # 支持tab或多个空格：filename.wav <sep> duration
                parts = re.split(r'\s+', line)
                if len(parts) < 2:
                    print(f"警告：第{line_num}行格式不正确，跳过: {line}")
                    continue
                audio_file = parts[0].strip()
                duration_str = parts[1].strip()
                base_name = os.path.splitext(audio_file)[0]
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

    # ---------- 统一“词”计数（英文单词 + 汉字逐字）----------

    @staticmethod
    def count_words_in_text(text: str) -> int:
        """
        统计文本“词”数量：
        - 英文/数字/下划线：按 \w+ 作为一个单词
        - 中文：每个汉字按1个“词”
        """
        english_words = re.findall(r'\w+', text)
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        return len(english_words) + len(chinese_chars)

    def count_words_in_file(self, file_path: str) -> int:
        """计算文件中的“词”数（见上面的定义）"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.count_words_in_text(content)
        except FileNotFoundError:
            print(f"错误：找不到讲稿文件 {file_path}")
            return 0
        except Exception as e:
            print(f"错误：读取讲稿文件时发生错误: {str(e)}")
            return 0

    def find_script_files(self, script_folder: str) -> List[str]:
        """查找讲稿文件夹中的 .txt 与 .md 文件"""
        script_folder_path = Path(script_folder)
        if not script_folder_path.exists():
            print(f"错误：讲稿文件夹不存在: {script_folder}")
            return []
        txt_files = list(script_folder_path.glob("*.txt"))
        md_files = list(script_folder_path.glob("*.md"))
        all_files = txt_files + md_files
        if not all_files:
            print(f"警告：在文件夹 {script_folder} 中未找到.txt或.md文件")
            return []
        script_files = [str(f) for f in all_files]
        script_files.sort()
        return script_files

    # ---------- 语速分析：单词/秒 ----------

    def analyze_speech_rates(self, duration_map: Dict[str, float], script_files: List[str]) -> Dict[str, float]:
        """
        分析语速并生成配置数据
        Returns: {文件基础名: 单词/秒}
        """
        speed_config: Dict[str, float] = {}
        matched_count = 0
        total_duration = 0.0
        total_words = 0

        print("=" * 60)
        print("第一步：分析语速（单位：单词/秒）")
        print("=" * 60)

        for script_file in script_files:
            base_name = os.path.splitext(os.path.basename(script_file))[0]
            if base_name in duration_map:
                duration = duration_map[base_name]
                word_count = self.count_words_in_file(script_file)
                if word_count > 0 and duration > 0:
                    wps = word_count / duration
                    speed_config[base_name] = wps
                    matched_count += 1
                    total_duration += duration
                    total_words += word_count
                    print(f"✓ {base_name}: {duration:.1f}秒, {word_count}词, {wps:.2f}词/秒")
                else:
                    print(f"✗ {base_name}: 讲稿为空/无有效词或时长为0")
            else:
                print(f"✗ {base_name}: 未找到对应的时长信息")

        if matched_count > 0 and total_duration > 0:
            overall_speed = total_words / total_duration
            print(f"\n语速统计摘要:")
            print(f"  匹配成功: {matched_count}/{len(script_files)} 个文件")
            print(f"  总时长: {total_duration:.1f} 秒")
            print(f"  总词数: {total_words} 词")
            print(f"  整体平均语速: {overall_speed:.2f} 词/秒")

        return speed_config

    # ---------- 文件与内容处理 ----------

    @staticmethod
    def find_files(folder_path: str, file_extension: str) -> List[str]:
        """查找指定文件夹下的特定扩展名文件，按字母序排序"""
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        files = glob.glob(os.path.join(folder_path, f"*{file_extension}"))
        if not files:
            print(f"WARNING: No {file_extension} files found in folder {folder_path}")
            return []
        files.sort()
        return files

    @staticmethod
    def extract_base_filename(file_path: str) -> str:
        """提取文件的基础名称（无扩展名）"""
        return os.path.splitext(os.path.basename(file_path))[0]

    def match_files(self, manim_files: List[str], script_files: List[str]) -> List[Tuple[str, str]]:
        """根据文件名匹配Manim代码文件和讲稿文件"""
        script_name_map: Dict[str, str] = {}
        for script_file in script_files:
            base_name = self.extract_base_filename(script_file)
            script_name_map[base_name] = script_file

        matched_pairs: List[Tuple[str, str]] = []
        unmatched_manim: List[str] = []

        for manim_file in manim_files:
            base_name = self.extract_base_filename(manim_file)
            if base_name in script_name_map:
                matched_pairs.append((manim_file, script_name_map[base_name]))
            else:
                unmatched_manim.append(manim_file)

        print("文件匹配结果:")
        print(f"  成功匹配: {len(matched_pairs)} 对文件")
        print(f"  未匹配的Manim文件: {len(unmatched_manim)} 个")
        return matched_pairs

    @staticmethod
    def read_file_content(file_path: str) -> str:
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"ERROR: Failed to read file {file_path}: {e}")
            return ""

    def parse_script_breakpoints(self, script_content: str) -> List[Tuple[int, int, str]]:
        """
        解析讲稿中的断点，返回 [(断点序号, 段内“词”数, 段落原文), ...]
        断点标记： (BREAKPOINT: x) 或 [BREAKPOINT: x]
        """
        breakpoint_pattern = r'[\(\[]BREAKPOINT:\s*(\d+)[\)\]]'
        segments: List[Tuple[int, int, str]] = []
        last_end = 0

        for match in re.finditer(breakpoint_pattern, script_content):
            breakpoint_num = int(match.group(1))
            start_pos = match.start()
            segment_text = script_content[last_end:start_pos].strip()

            # 即使第一段为空也纳入（方便与代码断点对齐），词数可能为0
            word_count = self.count_words_in_text(segment_text)
            segments.append((breakpoint_num, word_count, segment_text))
            last_end = match.end()

        # 最后一个断点后的内容
        if last_end < len(script_content):
            final_segment = script_content[last_end:].strip()
            if final_segment:
                word_count = self.count_words_in_text(final_segment)
                segments.append((9999, word_count, final_segment))

        return segments

    @staticmethod
    def calculate_wait_time(word_count: int, words_per_second: float) -> float:
        """根据单词数和语速（词/秒）计算等待时间（秒）"""
        if word_count <= 0 or words_per_second <= 0:
            return 0.0
        wait_time = word_count / words_per_second
        return round(wait_time, 1)

    def find_breakpoint_positions(self, manim_code: str) -> List[Tuple[int, int]]:
        """
        在Manim代码中查找断点位置
        返回 [(行号, 断点序号), ...]
        """
        lines = manim_code.split('\n')
        positions: List[Tuple[int, int]] = []
        pattern = r'#\s*BREAKPOINT:\s*(\d+)'
        for i, line in enumerate(lines):
            m = re.search(pattern, line)
            if m:
                positions.append((i, int(m.group(1))))
        return positions

    def insert_wait_statements(
        self,
        manim_code: str,
        script_segments: List[Tuple[int, int, str]],
        words_per_second: float
    ) -> str:
        """
        在Manim代码中插入self.wait(...)语句
        script_segments: [(断点号, 段内词数, 段落文本)]
        """
        lines = manim_code.split('\n')
        breakpoint_positions = self.find_breakpoint_positions(manim_code)
        if not breakpoint_positions:
            print("    WARNING: 代码中未找到断点标记")
            return manim_code

        # 断点号 -> 段内词数
        segment_map: Dict[int, int] = {bp: wc for (bp, wc, _) in script_segments}

        # 从后往前插入，避免行号偏移
        breakpoint_positions.sort(reverse=True)

        inserted_count = 0
        for line_num, breakpoint_num in breakpoint_positions:
            if breakpoint_num in segment_map:
                word_count = segment_map[breakpoint_num]
                wait_time = self.calculate_wait_time(word_count, words_per_second)
                if wait_time > 0:
                    current_line = lines[line_num]
                    indent = len(current_line) - len(current_line.lstrip())
                    indent_str = ' ' * indent
                    wait_line = (
                        f"{indent_str}self.wait({wait_time})  "
                        f"# {word_count}词, {words_per_second:.1f}词/秒"
                    )
                    lines.insert(line_num + 1, wait_line)
                    inserted_count += 1

        print(f"    插入了 {inserted_count} 个 wait 语句")
        return '\n'.join(lines)

    def save_processed_file(
        self,
        processed_code: str,
        original_manim_file: str,
        output_dir: str,
        words_per_second: float
    ) -> str:
        """保存处理后的代码文件"""
        os.makedirs(output_dir, exist_ok=True)
        original_name = os.path.splitext(os.path.basename(original_manim_file))[0]
        output_file_path = os.path.join(output_dir, f"{original_name}.py")
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                header = f'''#!/usr/bin/env python3
"""
Manim动画代码 - 已插入wait语句
原始文件: {os.path.basename(original_manim_file)}
处理时间: {time.strftime("%Y-%m-%d %H:%M:%S")}
语速设置: {words_per_second:.2f} 词/秒 ({1/words_per_second:.3f} 秒/词)
自动生成: manim_auto_wait_generator.py
"""

'''
                f.write(header)
                f.write(processed_code)
            return output_file_path
        except Exception as e:
            print(f"ERROR: Failed to save processed file for {original_name}: {e}")
            return ""

    # ---------- 单文件对处理与总流程 ----------

    def process_file_pair(self, manim_file: str, script_file: str, output_dir: str) -> Optional[str]:
        """处理单个 manim/script 文件对"""
        base_name = self.extract_base_filename(manim_file)
        manim_name = os.path.basename(manim_file)
        script_name = os.path.basename(script_file)

        print(f"  正在处理: {manim_name} ↔ {script_name}")

        if base_name not in self.speed_config:
            print(f"    ERROR: 未找到文件 {base_name} 的语速信息")
            return None

        words_per_second = self.speed_config[base_name]

        manim_code = self.read_file_content(manim_file)
        script_content = self.read_file_content(script_file)
        if not manim_code or not script_content:
            print("    ERROR: 文件读取失败")
            return None

        script_segments = self.parse_script_breakpoints(script_content)
        if not script_segments:
            print("    WARNING: 讲稿中未找到断点标记")
            return None

        total_words = sum(wc for _, wc, _ in script_segments)
        total_time = self.calculate_wait_time(total_words, words_per_second)
        print(f"    讲稿分析: {len(script_segments)}个段落, {total_words}词, "
              f"{words_per_second:.1f}词/秒, 预计{total_time}秒")

        processed_code = self.insert_wait_statements(manim_code, script_segments, words_per_second)
        output_file = self.save_processed_file(processed_code, manim_file, output_dir, words_per_second)

        if output_file:
            print(f"    生成文件: {os.path.basename(output_file)}")
            return output_file
        return None

    def process_all(self, duration_file: str, script_folder: str, manim_folder: str, output_folder: str) -> List[str]:
        """处理整个工作流程"""
        print("=" * 80)
        print("Manim自动Wait语句生成器")
        print("=" * 80)

        print("解析音频时长文件...")
        self.duration_map = self.parse_duration_file(duration_file)
        if not self.duration_map:
            print("无法解析时长信息，程序退出")
            return []
        print(f"解析到 {len(self.duration_map)} 个音频文件的时长信息")

        print(f"\n扫描讲稿文件夹: {script_folder}")
        script_files = self.find_script_files(script_folder)
        if not script_files:
            print("未找到讲稿文件，程序退出")
            return []
        print(f"找到 {len(script_files)} 个讲稿文件")

        self.speed_config = self.analyze_speech_rates(self.duration_map, script_files)
        if not self.speed_config:
            print("语速分析失败，程序退出")
            return []

        print(f"\n第二步：处理Manim代码文件")
        print("=" * 60)
        print(f"扫描Manim代码文件夹: {manim_folder}")
        manim_files = self.find_files(manim_folder, '.py')
        if not manim_files:
            print("未找到Manim代码文件，程序退出")
            return []
        print(f"找到 {len(manim_files)} 个Manim文件")

        matched_pairs = self.match_files(manim_files, script_files)
        if not matched_pairs:
            print("ERROR: 没有找到匹配的文件对")
            return []

        print()
        print(f"开始处理 {len(matched_pairs)} 对文件...")
        print("-" * 60)

        generated_files: List[str] = []
        success_count = 0

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
            output_file = self.process_file_pair(manim_file, script_file, output_folder)
            if output_file:
                generated_files.append(output_file)
                success_count += 1
            if HAS_TQDM:
                pbar.update(1)
            else:
                pbar.update()

        pbar.close()

        print("\n" + "=" * 60)
        print("自动Wait语句生成完成")
        print("=" * 60)
        print("处理结果:")
        print(f"  成功处理: {success_count} 个文件")
        print(f"  失败处理: {len(matched_pairs) - success_count} 个文件")
        print(f"  输出目录: {output_folder}")

        if generated_files:
            print("\n生成的文件:")
            for file_path in generated_files:
                print(f"  - {os.path.basename(file_path)}")

        return generated_files

    # 供流水线调用的别名
    def pipeline(self, duration_file: str, script_folder: str, manim_folder: str, output_folder: str) -> List[str]:
        return self.process_all(duration_file, script_folder, manim_folder, output_folder)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Manim自动Wait语句生成器 - 整合语速分析和Wait语句插入（单位：单词/秒）",
        epilog="""使用示例:
python manim_auto_wait_generator.py audio_duration.txt scripts/ code/ output/

工作流程:
1. 解析音频时长文件，获取每个文件的播放时长
2. 分析讲稿文件的“词”数，计算每个文件的个性化语速（词/秒）
3. 根据语速在Manim代码的断点处插入合适的wait语句

文件要求:
- 音频时长文件: 每行格式 "filename.wav  duration_seconds"
- 讲稿文件: 包含 (BREAKPOINT: x) 或 [BREAKPOINT: x] 标记
- Manim代码: 包含 #BREAKPOINT: x 标记
- 文件名需要匹配（相同的基础文件名）
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("duration_file", help="音频时长信息文件路径")
    parser.add_argument("script_folder", help="包含讲稿文件的文件夹路径（.txt/.md）")
    parser.add_argument("manim_folder", help="包含Manim Python代码的文件夹路径")
    parser.add_argument("output_folder", help="输出文件夹路径")

    args = parser.parse_args()

    try:
        generator = ManimAutoWaitGenerator()
        generated_files = generator.process_all(
            duration_file=args.duration_file,
            script_folder=args.script_folder,
            manim_folder=args.manim_folder,
            output_folder=args.output_folder
        )
        if generated_files:
            print(f"\nSUCCESS: 自动Wait语句生成完成! 共生成 {len(generated_files)} 个文件")
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
