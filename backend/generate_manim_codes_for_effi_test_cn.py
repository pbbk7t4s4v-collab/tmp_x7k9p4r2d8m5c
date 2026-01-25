#!/usr/bin/env python3
"""
机器学习课程讲义 Manim 代码生成器

功能：
1. 读取指定文件夹下的所有 *_*.md 文件
2. 使用 Page_Coder.txt 作为 prompt 调用大模型
3. 生成对应的 Manim Python 代码
4. 保存到 Code/文件夹名/ 目录下

作者：EduAgent ML Assistant
"""

import os
import re
import glob
import json
import argparse
from pathlib import Path
from typing import List, Tuple
import time
import concurrent.futures

# 大模型 API 配置
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class ManimCodeGenerator_cn:
    def __init__(self, config_path: str = "config.json", verbose: bool = False):
        """
        初始化代码生成器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.prompt_template = self._load_prompt_template()
        self.verbose = verbose
        
        # 初始化API客户端
        if HAS_OPENAI:
            openai.api_key = self.config["llm_key"]
            openai.base_url = self.config["llm_settings"]["base_url"]
        else:
            raise ImportError("OpenAI library not found. Please install: pip install openai")
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_prompt_template(self) -> str:
        """加载 Page_Coder.txt 作为 prompt 模板"""
        prompt_file = Path("prompt_templates/Page_Coder_cn.txt")
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt template not found: {prompt_file}")
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def find_section_files(self, folder_path: str) -> List[Tuple[str, str]]:
        """
        查找文件夹下所有符合 数字_数字.md 格式的文件
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            List of (filename, filepath) tuples
        """
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        # 查找所有 .md 文件，然后筛选符合 数字_数字.md 格式的文件
        all_files = glob.glob(os.path.join(folder_path, "*.md"))
        files = []
        
        # 只保留符合 前缀_数字.md 格式的文件
        pattern = re.compile(r'^(.+)_(\d+)\.md$')
        for filepath in all_files:
            filename = os.path.basename(filepath)
            if pattern.match(filename):
                files.append(filepath)
        
        # 排序确保按前缀和数字顺序处理
        def sort_key(filepath):
            filename = os.path.basename(filepath)
            match = pattern.match(filename)
            if match:
                prefix = match.group(1)
                num = int(match.group(2))
                return (prefix, num)
            return ("", 0)
        
        files.sort(key=sort_key)
        
        result = []
        for filepath in files:
            filename = os.path.basename(filepath)
            result.append((filename, filepath))
        
        print(f"Found {len(result)} section files (前缀_数字.md format) in {folder_path}")
        print("Files to be processed:")
        for i, (filename, _) in enumerate(result, 1):
            print(f"  {i:2d}. {filename}")
        return result
    
    def read_markdown_content(self, filepath: str) -> str:
        """读取 Markdown 文件内容"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def call_llm_api(self, markdown_content: str) -> str:
        """
        调用大模型 API 生成 Manim 代码
        
        Args:
            markdown_content: Markdown 格式的课程内容
            
        Returns:
            生成的 Manim Python 代码
        """
        # 构建完整的 prompt
        full_prompt = f"{self.prompt_template}\n\n以下是需要转换为 Manim 动画的课程内容：\n\n{markdown_content}"
        
        try:
            client = openai.OpenAI(
                api_key=self.config["llm_key"],
                base_url=self.config["llm_settings"]["base_url"]
            )
            
            response = client.chat.completions.create(
                model="gemini-3-pro-preview",
                messages=[
                    {"role": "system", "content": "你是一位专业的 Manim 动画专家，专门为课程制作教学动画。"},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=self.config["llm_settings"]["max_tokens"],
                temperature=self.config["llm_settings"]["temperature"]
            )
            raw_content = response.choices[0].message.content.strip()
            return self.clean_generated_code(raw_content)
            
        except Exception as e:
            print(f"API call failed: {e}")
            return f"# Error generating code for this section\n# Error: {e}\npass"
    
    def clean_generated_code(self, raw_code: str) -> str:
        """
        清理生成的代码，去除 Markdown 代码块标记符号
        
        Args:
            raw_code: 原始生成的代码（可能包含 ```python 等标记）
            
        Returns:
            清理后的纯 Python 代码
        """
        # 去除开头的代码块标记
        lines = raw_code.strip().split('\n')
        
        # 检查并去除开头的 ```python 或 ```
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        
        # 检查并去除结尾的 ```
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        
        # 重新组合代码
        cleaned_code = '\n'.join(lines).strip()
        
        # 确保代码不为空
        if not cleaned_code:
            cleaned_code = "# Empty code generated\npass"
        
        return cleaned_code
    
    def save_python_code(self, code: str, output_filepath: str):
        """保存生成的 Python 代码到文件"""
        # 确保输出目录存在
        output_dir = os.path.dirname(output_filepath)
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存代码
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        
        print(f"Saved: {output_filepath}")
    
    def process_single_file(self, filename_filepath, output_base_dir, delay_seconds):
        """
        处理单个文件
        
        Args:
            filename_filepath: (filename, filepath) tuple
            output_base_dir: 输出基础目录
            delay_seconds: 延迟秒数
        """
        filename, filepath = filename_filepath
        try:
            # 读取Markdown内容
            markdown_content = self.read_markdown_content(filepath)
            if self.verbose:
                print(f"  Loaded {len(markdown_content)} characters from {filename}")
            
            # 调用LLM生成代码
            if self.verbose:
                print(f"  Calling LLM API for {filename}...")
            manim_code = self.call_llm_api(markdown_content)
            
            # 保存Python代码
            output_filename = filename.replace('.md', '.py')
            output_filepath = os.path.join(output_base_dir, output_filename)
            self.save_python_code(manim_code, output_filepath)
            
            if self.verbose:
                print(f"  Saved: {output_filepath}")
            
            # 延迟避免API频率限制
            time.sleep(delay_seconds)
            
            return f"Success: {filename}"
            
        except Exception as e:
            error_msg = f"Error processing {filename}: {e}"
            print(error_msg)
            return error_msg
    def process_folder(self, input_folder: str, output_dir: str, delay_seconds: float = 1.0, max_workers: int = 4):
        """
        处理整个文件夹，使用并行处理提高效率
        
        Args:
            input_folder: 输入文件夹路径
            delay_seconds: API调用之间的延迟（避免频率限制）
        """
        start_time = time.time()  # 开始计时
        
        # 获取文件夹名称
        output_base_dir = output_dir
        
        print(f"Processing folder: {input_folder}")
        print(f"Output directory: {output_base_dir}")
        
        # 查找所有section文件
        section_files = self.find_section_files(input_folder)
        
        if not section_files:
            print("No section files found!")
            return
        
        # 使用线程池并行处理文件
        # max_workers = 4  # 设置最大并发数，避免API限制
        print(f"Starting parallel processing with {max_workers} workers...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.process_single_file, filename_filepath, output_base_dir, delay_seconds): filename_filepath
                for filename_filepath in section_files
            }
            
            total_tasks = len(future_to_file)
            completed_tasks = 0
            print(f"📤 Submitted {total_tasks} tasks to thread pool (max {max_workers} concurrent workers)")
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_file):
                filename_filepath = future_to_file[future]
                try:
                    result = future.result()
                    if self.verbose:
                        print(result)
                except Exception as exc:
                    print(f'{filename_filepath[0]} generated an exception: {exc}')
                
                completed_tasks += 1
                remaining_tasks = total_tasks - completed_tasks
                active_workers = min(max_workers, remaining_tasks + (1 if remaining_tasks > 0 else 0))  # 估算活跃工作线程
                print(f"🔄 Progress: {completed_tasks}/{total_tasks} completed, {remaining_tasks} remaining, ~{active_workers} active workers")
        
        end_time = time.time()  # 结束计时
        total_time = end_time - start_time
        
        print(f"\n✅ Parallel processing completed! Output saved to: {output_base_dir}")
        print(f"⏱️  Total processing time: {total_time:.2f} seconds")
        print(f"📊 Processed {len(section_files)} files in parallel with {max_workers} workers")
    
    def pipeline(self, input_folder: str, output_dir: str, delay_seconds: float = 1.0, max_workers: int = 4):
        """
        简化的流水线接口
        
        Args:
            input_folder: 输入文件夹路径
            delay_seconds: API调用之间的延迟（避免频率限制）
        """
        pipeline_start_time = time.time()
        result = self.process_folder(input_folder, output_dir, delay_seconds=delay_seconds, max_workers=max_workers)
        pipeline_end_time = time.time()
        pipeline_total_time = pipeline_end_time - pipeline_start_time
        print(f"🔄 Pipeline execution time: {pipeline_total_time:.2f} seconds")
        return result


def main():
    parser = argparse.ArgumentParser(description="Generate Manim codes from ML course sections")
    parser.add_argument("--folder", default="./effi_test/markdown", help="Input folder containing *_*.md files")
    parser.add_argument("--config", default="config.json", help="Config file path")
    parser.add_argument("--output_dir", default="./effi_test/output_code", help="Output directory for generated python files")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay between API calls in seconds")
    parser.add_argument("--workers", type=int, default=4,
                        help="Number of parallel workers to use")

    args = parser.parse_args()

    try:
        # 创建生成器并处理文件夹
        generator = ManimCodeGenerator(config_path=args.config)
        generator.pipeline(args.folder, output_dir=args.output_dir, delay_seconds=args.delay, max_workers=args.workers)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()