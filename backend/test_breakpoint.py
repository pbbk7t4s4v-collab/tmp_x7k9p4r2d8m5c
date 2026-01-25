#!/usr/bin/env python3
import os
import re
import glob
import json
import argparse
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import time
import sys
from datetime import datetime

# 导入项目现有的LLM API客户端
from llm_api import LLMAPIClient

# 尝试导入tqdm进度条
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


class ManimBreakpointInserter:
    def __init__(self, config_path: str = "config.json", verbose: bool = True):
        """
        初始化Manim断点插入器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.breakpoint_prompt = self._load_breakpoint_prompt()
        self.verbose = verbose
        self.llm_records = []
        
        # 初始化LLM API客户端
        self.llm_client = LLMAPIClient(config_path=config_path)
        
    def _load_breakpoint_prompt(self) -> str:
        """加载BreakPoint.txt prompt模板"""
        prompt_file = Path("prompt_templates/BreakPointtest.txt")
        if not prompt_file.exists():
            raise FileNotFoundError(f"BreakPoint.txt prompt template not found: {prompt_file}")
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
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
        
        if matched_pairs:
            print(f"  匹配的文件对:")
            for manim_file, script_file in matched_pairs:
                print(f"    - {os.path.basename(manim_file)} ↔ {os.path.basename(script_file)}")
        
        if unmatched_manim:
            print(f"  未匹配的Manim文件:")
            for file in unmatched_manim:
                print(f"    - {os.path.basename(file)}")
        
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
    
    def create_breakpoint_prompt(self, manim_code: str, script_content: str) -> str:
        """
        创建用于插入断点的完整prompt
        
        Args:
            manim_code: Manim代码内容
            script_content: 旁白文稿内容
            
        Returns:
            完整的prompt字符串
        """
        # 使用BreakPoint.txt的prompt模板
        full_prompt = f"""{self.breakpoint_prompt}

{manim_code}

{script_content}"""
        
        return full_prompt
    
    def insert_breakpoints(self, manim_code: str, script_content: str, file_name: str) -> Tuple[str, str]:
        """
        使用大模型在Manim代码和旁白文稿中插入断点
        
        Args:
            manim_code: Manim代码内容
            script_content: 旁白文稿内容
            file_name: 文件名（用于日志）
            
        Returns:
            (插入断点后的代码, 插入断点后的文稿)
        """
        # 构建完整的prompt
        full_prompt = self.create_breakpoint_prompt(manim_code, script_content)
        
        try:
            # 调用LLM API
            response = self.llm_client.call_api_with_text(full_prompt)
            # ====== 新增：记录每次模型返回 ======
            self.llm_records.append({
                "file_name": file_name,
                "prompt": full_prompt,
                "response": str(response),
                "success": True,
            })
            # ==================================
            # 解析响应
            processed_code, processed_script = self.parse_llm_response(response)
            
            return processed_code, processed_script
            
        except Exception as e:
            # ====== 新增：记录失败情况 ======
            self.llm_records.append({
                "file_name": file_name,
                "prompt": full_prompt,
                "response": None,
                "success": False,
                "error": str(e),
            })
            # =================================
            print(f"ERROR: Breakpoint insertion failed for {file_name}: {e}")
            return f"# 断点插入失败: {e}\n# 原始Manim代码:\n{manim_code}", f"断点插入失败: {e}\n原始文稿:\n{script_content}"
    '''
    def parse_llm_response(self, response: str) -> Tuple[str, str]:
        """
        解析大模型的响应，分离代码和文稿
        
        Args:
            response: 大模型的原始响应
            
        Returns:
            (处理后的代码, 处理后的文稿)
        """
        # 按照分割符"-----"分割响应
        parts = response.split("-----")
        
        if len(parts) < 2:
            # 如果没有找到分割符，尝试其他可能的分割方式
            print("WARNING: 没有找到标准分割符，尝试其他分割方式")
            # 可以在这里添加更复杂的解析逻辑
            return response.strip(), "解析失败：未找到文稿部分"
        
        # 提取代码和文稿
        processed_code = parts[0].strip()
        processed_script = parts[1].strip()
        
        # 清理可能的markdown标记
        processed_code = self.clean_code_content(processed_code)
        processed_script = self.clean_script_content(processed_script)
        
        return processed_code, processed_script
    '''
    def parse_llm_response(self, response: str) -> Tuple[str, str]:
        """
        解析大模型的响应，优先按自定义标记解析：
        期望格式形如：

            <<<CODE_START
            ...完整的 manim 代码...
            CODE_END>>>

            <<<SPEECH_START
            ...完整的旁白文稿...
            SPEECH_END>>>

        若未找到以上标记，则回退到旧的 JSON / "code-----speech" 解析逻辑。
        """
        # 统一转成字符串
        text = str(response).strip()

        # 先去掉可能包了一层 ```xxx ... ``` 的 markdown 代码块外壳
        if text.startswith("```"):
            lines = text.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # ====== 协议 1：<<<CODE_START ... CODE_END>>> / <<<SPEECH_START ... SPEECH_END>>> ======
        code_match = re.search(r'<<<CODE_START\s*(.*?)\s*CODE_END>>>', text, re.S)
        speech_match = re.search(r'<<<SPEECH_START\s*(.*?)\s*SPEECH_END>>>', text, re.S)

        if code_match and speech_match:
            code_raw = code_match.group(1)
            speech_raw = speech_match.group(1)

            processed_code = self.clean_code_content(code_raw)
            processed_script = self.clean_script_content(speech_raw)
            return processed_code, processed_script

        # ====== 最终兜底：全部当成代码，文稿给一个提示 ======
        return self.clean_code_content(text), "解析失败：未找到 CODE/SPEECH 片段"

    def clean_code_content(self, raw_code: str) -> str:
        """
        清理代码内容，移除 markdown 标记等
        """
        lines = raw_code.split('\n')
        cleaned_lines = []
        in_code_block = False

        for line in lines:
            stripped = line.strip()

            # 检测并处理 markdown 代码块标记
            if stripped.startswith('```'):
                if stripped in ['```python', '```']:
                    in_code_block = not in_code_block
                # 不把 ``` 本身写回去
                continue

            # 如果不在代码块中，且是“顶格的说明文字”，跳过这行
            # 条件：非空、没有前导空白、也不是注释/导入/类/函数定义
            if (
                not in_code_block
                and stripped
                and not line.startswith((' ', '\t'))  # 有缩进的一律当作代码保留
                and not stripped.startswith(('#', 'from ', 'import ', 'class ', 'def '))
            ):
                continue

            # 其余情况：在代码块中，或者是注释/导入/类/函数/空行/缩进行，全部保留
            if (
                in_code_block
                or not stripped
                or stripped.startswith(('#', 'from ', 'import ', 'class ', 'def '))
                or line.startswith((' ', '\t'))  # 有缩进 ⇒ 认为是代码行
            ):
                cleaned_lines.append(line)

        # 重新组合代码
        cleaned_code = '\n'.join(cleaned_lines)
        
        # 移除多余的空行
        while '\n\n\n' in cleaned_code:
            cleaned_code = cleaned_code.replace('\n\n\n', '\n\n')
        
        # 确保代码以换行符结尾
        if not cleaned_code.endswith('\n'):
            cleaned_code += '\n'
        
        return cleaned_code
    
    def clean_script_content(self, raw_script: str) -> str:
        """
        清理文稿内容
        
        Args:
            raw_script: 原始文稿内容
            
        Returns:
            清理后的文稿
        """
        # 移除可能的markdown标记
        cleaned_script = raw_script.strip()
        
        # 移除代码块标记（如果有）
        cleaned_script = re.sub(r'^```.*$', '', cleaned_script, flags=re.MULTILINE)
        
        # 移除多余的空行
        while '\n\n\n' in cleaned_script:
            cleaned_script = cleaned_script.replace('\n\n\n', '\n\n')
        
        return cleaned_script.strip()
    
    def count_breakpoints(self, content: str, file_type: str = "code") -> int:
        """
        统计文件中的断点数量
        
        Args:
            content: 文件内容
            file_type: 文件类型，"code" 或 "script"
            
        Returns:
            断点数量
        """
        if file_type == "code":
            # 统计代码中的 #BREAKPOINT: x 格式断点
            pattern = r'#BREAKPOINT:\s*\d+'
            matches = re.findall(pattern, content)
            return len(matches)
        elif file_type == "script":
            # 统计文稿中的 (BREAKPOINT: idx) 格式断点
            pattern = r'\(BREAKPOINT:\s*\d+\)'
            matches = re.findall(pattern, content)
            return len(matches)
        else:
            return 0
    
    def save_processed_files(self, processed_code: str, processed_script: str, 
                           original_manim_file: str, output_dir: str) -> Tuple[str, str]:
        """
        保存处理后的代码和文稿文件
        
        Args:
            processed_code: 处理后的代码
            processed_script: 处理后的文稿
            original_manim_file: 原始Manim文件路径
            output_dir: 输出目录
            
        Returns:
            (保存的代码文件路径, 保存的文稿文件路径)
        """
        # 创建输出目录结构
        code_dir = os.path.join(output_dir, "Code")
        speech_dir = os.path.join(output_dir, "Speech")
        os.makedirs(code_dir, exist_ok=True)
        os.makedirs(speech_dir, exist_ok=True)
        
        # 生成输出文件名
        original_name = os.path.splitext(os.path.basename(original_manim_file))[0]
        code_file_path = os.path.join(code_dir, f"{original_name}.py")
        script_file_path = os.path.join(speech_dir, f"{original_name}.txt")
        
        try:
            # 保存代码文件
            with open(code_file_path, 'w', encoding='utf-8') as f:
                # 添加文件头注释
                header = f'''#!/usr/bin/env python3
"""
Manim动画代码 - 已插入断点
原始文件: {os.path.basename(original_manim_file)}
处理时间: {time.strftime("%Y-%m-%d %H:%M:%S")}
处理方式: 使用BreakPoint prompt自动插入配对断点
"""

'''
                f.write(header)
                f.write(processed_code)
            
            # 保存文稿文件
            with open(script_file_path, 'w', encoding='utf-8') as f:
                # 直接保存处理后的文稿，不添加头部注释
                f.write(processed_script)
            
            return code_file_path, script_file_path
            
        except Exception as e:
            print(f"ERROR: Failed to save processed files for {original_name}: {e}")
            return "", ""
    
    def process_file_pairs(self, matched_pairs: List[Tuple[str, str]], output_dir: str, verbose: bool = True) -> List[Tuple[str, str]]:
        """
        批量处理匹配的文件对
        
        Args:
            matched_pairs: 匹配的文件对列表
            output_dir: 输出目录
            verbose: 是否显示详细过程
            
        Returns:
            生成的文件路径对列表 [(code_file, script_file), ...]
        """
        if verbose:
            print("=" * 80)
            print("Manim断点插入工具")
            print(f"输出目录: {output_dir}")
            print(f"待处理文件对: {len(matched_pairs)} 对")
            print("=" * 80)
            print()
        
        if not matched_pairs:
            print("ERROR: No matched file pairs found")
            return []
        
        generated_file_pairs = []
        success_count = 0
        breakpoint_stats = []  # 存储断点统计信息
        
        print(f"开始处理 {len(matched_pairs)} 对文件...")
        print("-" * 60)
        
        # 初始化进度条
        if HAS_TQDM and verbose:
            pbar = tqdm(
                total=len(matched_pairs),
                desc="断点插入",
                unit="pair",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
            )
        elif verbose:
            pbar = ProgressBar(total=len(matched_pairs), desc="处理文件")
        else:
            pbar = None
        
        for i, (manim_file, script_file) in enumerate(matched_pairs, 1):
            manim_name = os.path.basename(manim_file)
            script_name = os.path.basename(script_file)
            
            # 更新进度条描述
            if HAS_TQDM and pbar:
                pbar.set_description(f"处理 {manim_name}")
            
            # 读取文件内容
            manim_code = self.read_file_content(manim_file)
            script_content = self.read_file_content(script_file)
            
            if not manim_code or not script_content:
                print(f"WARNING: 跳过文件对 {manim_name} ↔ {script_name} (文件读取失败)")
                if pbar:
                    if HAS_TQDM:
                        pbar.update(1)
                    else:
                        pbar.update()
                continue
            
            if verbose:
                print(f"  正在处理: {manim_name} ↔ {script_name}")
            
            # 执行断点插入处理
            processed_code, processed_script = self.insert_breakpoints(manim_code, script_content, manim_name)
            
            # 统计断点数量
            code_breakpoints = self.count_breakpoints(processed_code, "code")
            script_breakpoints = self.count_breakpoints(processed_script, "script")
            is_matched = code_breakpoints == script_breakpoints
            
            # 如果断点数量不匹配，进行第二次尝试
            if not is_matched:
                if verbose:
                    print(f"    第1次断点统计: 代码({code_breakpoints}) | 文稿({script_breakpoints}) ✗ - 重新处理")
                
                # 再次调用LLM进行断点插入
                processed_code_retry, processed_script_retry = self.insert_breakpoints(manim_code, script_content, f"{manim_name}(重试)")
                
                # 重新统计断点
                code_breakpoints_retry = self.count_breakpoints(processed_code_retry, "code")
                script_breakpoints_retry = self.count_breakpoints(processed_script_retry, "script")
                is_matched_retry = code_breakpoints_retry == script_breakpoints_retry
                
                # 使用第二次的结果
                processed_code = processed_code_retry
                processed_script = processed_script_retry
                code_breakpoints = code_breakpoints_retry
                script_breakpoints = script_breakpoints_retry
                is_matched = is_matched_retry
                
                if verbose:
                    status_icon = "✓" if is_matched else "✗"
                    print(f"    第2次断点统计: 代码({code_breakpoints}) | 文稿({script_breakpoints}) {status_icon}")
                
                # 添加额外延迟（因为进行了两次API调用）
                time.sleep(1)
            else:
                if verbose:
                    print(f"    断点统计: 代码({code_breakpoints}) | 文稿({script_breakpoints}) ✓")
            
            # 记录断点统计信息
            breakpoint_stats.append({
                'file': manim_name,
                'code_breakpoints': code_breakpoints,
                'script_breakpoints': script_breakpoints,
                'matched': is_matched
            })
            
            # 保存处理后的文件
            code_file, script_file_path = self.save_processed_files(processed_code, processed_script, manim_file, output_dir)
            
            if code_file and script_file_path:
                generated_file_pairs.append((code_file, script_file_path))
                success_count += 1
            
            # 更新进度条
            if pbar:
                if HAS_TQDM:
                    pbar.update(1)
                else:
                    pbar.update()
            
            # 添加延迟避免API限制
            if i < len(matched_pairs):
                time.sleep(2)
        
        # 关闭进度条
        if pbar:
            if HAS_TQDM:
                pbar.close()
            else:
                pbar.close()
        
        # 计算断点匹配统计
        matched_breakpoints = sum(1 for stat in breakpoint_stats if stat['matched'])
        total_processed = len(breakpoint_stats)
        
        # 输出结果摘要
        print("\n" + "=" * 60)
        print("MANIM断点插入处理完成")
        print("=" * 60)
        print(f"处理结果:")
        print(f"  成功处理: {success_count} 对文件")
        print(f"  失败处理: {len(matched_pairs) - success_count} 对文件")
        print(f"  断点匹配: {matched_breakpoints}/{total_processed} 对文件")
        print(f"  输出目录: {output_dir}")
        print(f"  代码目录: {os.path.join(output_dir, 'Code')}")
        print(f"  文稿目录: {os.path.join(output_dir, 'Speech')}")
        
        # 显示断点不匹配的文件详情
        mismatched_files = [stat for stat in breakpoint_stats if not stat['matched']]
        if mismatched_files:
            print(f"\n断点不匹配的文件:")
            for stat in mismatched_files:
                print(f"  - {stat['file']}: 代码({stat['code_breakpoints']}) vs 文稿({stat['script_breakpoints']})")
        
        if generated_file_pairs:
            print(f"\n生成的文件对:")
            for code_file, script_file in generated_file_pairs:
                print(f"  - {os.path.basename(code_file)} & {os.path.basename(script_file)}")
        
        return generated_file_pairs
    
    def process_folders(self, manim_folder: str, script_folder: str, 
                       output_folder: str, verbose: bool = True) -> List[Tuple[str, str]]:
        """
        处理两个文件夹中的Manim代码和旁白文稿
        
        Args:
            manim_folder: Manim代码文件夹路径
            script_folder: 旁白文稿文件夹路径  
            output_folder: 输出文件夹路径
            verbose: 是否显示详细过程
            
        Returns:
            生成的文件路径对列表
        """
        # 查找Manim文件（.py）
        print(f"扫描Manim代码文件夹: {manim_folder}")
        manim_files = self.find_files(manim_folder, '.py')
        
        # 查找旁白文稿文件（支持.txt, .md）
        print(f"扫描旁白文稿文件夹: {script_folder}")
        script_files = []
        for ext in ['.txt', '.md']:
            script_files.extend(self.find_files(script_folder, ext))
        
        print(f"找到 {len(manim_files)} 个Manim文件")
        print(f"找到 {len(script_files)} 个旁白文件")
        print()
        
        # 匹配文件对
        matched_pairs = self.match_files(manim_files, script_files)
        
        if not matched_pairs:
            print("ERROR: 没有找到匹配的文件对")
            return []
        
        print()
        
        # 处理匹配的文件对
        return self.process_file_pairs(matched_pairs, output_folder, verbose)
    
    def pipeline(self, manim_folder: str, script_folder: str, output_folder: str, verbose: bool = True) -> List[Tuple[str, str]]:
        """
        处理Manim代码和旁白文稿的完整流水线
        
        Args:
            manim_folder: Manim代码文件夹路径
            script_folder: 旁白文稿文件夹路径  
            output_folder: 输出文件夹路径
            verbose: 是否显示详细过程
            
        Returns:
            生成的文件路径对列表
        """
        # 确保输出文件夹存在
        os.makedirs(output_folder, exist_ok=True)
        
        # 处理文件夹中的文件
        folder_pair = self.process_folders(manim_folder, script_folder, output_folder, verbose)
        return folder_pair


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Manim断点插入工具",
        epilog="示例: python manim_breakpoint_inserter.py Code/regression_sections Scripts/regression_sections Output/regression_sections\n"
               "功能: 根据BreakPoint prompt在Manim代码和旁白文稿中插入配对断点",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "manim_folder",
        help="包含Manim Python代码的文件夹"
    )
    parser.add_argument(
        "script_folder", 
        help="包含旁白文稿的文件夹（支持.txt和.md文件）"
    )
    parser.add_argument(
        "output_folder",
        help="输出文件夹路径（将创建Code/和Speech/子目录）"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="配置文件路径 (默认: config.json)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式，不显示详细过程"
    )
    
    args = parser.parse_args()
    
    try:
        # 创建断点插入器
        inserter = ManimBreakpointInserter(config_path=args.config)
        
        # 执行文件夹处理
        generated_pairs = inserter.process_folders(
            manim_folder=args.manim_folder,
            script_folder=args.script_folder,
            output_folder=args.output_folder,
            verbose=not args.quiet
        )
        
        if generated_pairs:
            print(f"\nSUCCESS: 断点插入处理完成!")
            print(f"生成了 {len(generated_pairs)} 对处理后的文件")
        else:
            print("\nWARNING: 没有成功生成任何文件")
            exit(1)
            
    except Exception as e:
        print(f"\nERROR: 程序执行失败: {e}")
        print("\n请确保:")
        print("1. llm_api.py 文件存在且可以导入")
        print("2. config.json 包含正确的 llm_key 设置")
        print("3. 网络连接正常")
        print("4. prompt_templates/BreakPoint.txt 文件存在")
        print("5. 输入文件夹路径正确且包含对应的文件")
        exit(1)


if __name__ == "__main__":
    main()