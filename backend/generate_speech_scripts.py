#!/usr/bin/env python3
"""
机器学习课程讲解稿生成器

功能：
1. 匹配两个文件夹下的同名文件（.md 和 .py）
2. 使用 Page_Speaker.txt 作为 prompt 调用大模型
3. 生成连贯的讲解稿
4. 保存到 Speech/文件夹名/ 目录下

作者：EduAgent ML Assistant
"""

import os
import re
import glob
import json
import argparse
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import time

# 大模型 API 配置
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

MAX_RETRIES = 3  # 最大重试次数

class SpeechScriptGenerator:
    def __init__(self, config_path: str = "config.json", verbose: bool = False):
        """
        初始化讲解稿生成器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.prompt_template = self._load_prompt_template()
        self.previous_speech = ""  # 用于保持连贯性
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
        """加载 Page_Speaker.txt 作为 prompt 模板"""
        prompt_file = Path("prompt_templates/Page_Speaker.txt")
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt template not found: {prompt_file}")
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def find_matching_files(self, md_folder: str, py_folder: str) -> List[Tuple[str, str, str]]:
        """
        查找两个文件夹下的匹配文件
        
        Args:
            md_folder: Markdown 文件夹路径
            py_folder: Python 文件夹路径
            
        Returns:
            List of (base_name, md_path, py_path) tuples
        """
        if not os.path.exists(md_folder):
            raise FileNotFoundError(f"Markdown folder not found: {md_folder}")
        if not os.path.exists(py_folder):
            raise FileNotFoundError(f"Python folder not found: {py_folder}")
        
        # 查找所有 数字_数字.md 格式的文件
        md_files = {}
        pattern = re.compile(r'^(\d+)_(\d+)\.md$')
        for filepath in glob.glob(os.path.join(md_folder, "*.md")):
            filename = os.path.basename(filepath)
            if pattern.match(filename):
                base_name = filename[:-3]  # 去掉 .md
                md_files[base_name] = filepath
        
        # 查找对应的 .py 文件
        matching_files = []
        for base_name, md_path in md_files.items():
            py_path = os.path.join(py_folder, f"{base_name}.py")
            if os.path.exists(py_path):
                matching_files.append((base_name, md_path, py_path))
        
        # 排序确保按数字顺序处理
        def sort_key(item):
            base_name = item[0]
            match = re.match(r'(\d+)_(\d+)', base_name)
            if match:
                return (int(match.group(1)), int(match.group(2)))
            return (0, 0)
        
        matching_files.sort(key=sort_key)
        
        print(f"Found {len(matching_files)} matching file pairs")
        print("Files to be processed:")
        for i, (base_name, _, _) in enumerate(matching_files, 1):
            print(f"  {i:2d}. {base_name}.md <-> {base_name}.py")
        
        return matching_files
    
    def read_file_content(self, filepath: str) -> str:
        """读取文件内容"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def call_llm_api(self, previous_speech: str, md_content: str, py_content: str, max_retries: int = 3) -> str:
        """
        调用大模型 API 生成讲解稿
        
        Args:
            previous_speech: 上一页的讲解稿内容
            md_content: Markdown 课程内容
            py_content: Python 动画脚本内容
            
        Returns:
            生成的讲解稿
        """
        # 构建完整的 prompt
        input_content = f"""
以下是三部分输入：

1. 上一个页面的讲稿内容：
{previous_speech if previous_speech else "这是第一页，没有上一页内容。"}

2.课程讲义内容：
{md_content}

3. 对应的 Manim 动画脚本：
{py_content}
"""
        
        full_prompt = f"{self.prompt_template}\n\n{input_content}"
        
        try:
            client = openai.OpenAI(
                api_key=self.config["llm_key"],
                base_url=self.config["llm_settings"]["base_url"]
            )

            last_err = None
            for attempt in range(1, max_retries + 1):
                try:
                    response = client.chat.completions.create(
                        model=self.config["llm_settings"]["model"],
                        messages=[
                            {"role": "system", "content": "你是一位专业的课程教学专家，专门为教学视频撰写配音讲解稿。"},
                            {"role": "user", "content": full_prompt}
                        ],
                        max_tokens=self.config["llm_settings"]["max_tokens"],
                        temperature=self.config["llm_settings"]["temperature"]
                    )

                    raw_speech = response.choices[0].message.content.strip()
                    return self.clean_speech_content(raw_speech)

                except Exception as e:
                    err_str = str(e)
                    last_err = err_str

                    should_retry = (
                        ("openai_error" in err_str) or
                        ("bad_response_status_code" in err_str) or
                        ("Error code: 502" in err_str) or
                        ("502" in err_str)
                    )

                    if should_retry and attempt < max_retries:
                        print(f"API transient error, retry {attempt}/{max_retries}: {err_str}")
                        time.sleep(min(2 ** (attempt - 1), 8))  # 指数退避，最多8s
                        continue

                    print(f"API call failed (final): {err_str}")
                    break

            # 失败时返回一个“可识别的失败标记”，供上层跳过
            return f"__LLM_FAILED__ {last_err}"

            
        except Exception as e:
            print(f"API call failed: {e}")
            return f"__LLM_FAILED__：生成讲解稿时出现错误：{e}"
    
    def clean_speech_content(self, raw_speech: str) -> str:
        """
        清理生成的讲解稿内容
        
        Args:
            raw_speech: 原始生成的讲解稿
            
        Returns:
            清理后的讲解稿
        """
        # 去除可能的 Markdown 标记和多余的换行
        cleaned = raw_speech.strip()
        
        # 去除多余的换行和空格，合并为一段连续文字
        cleaned = ' '.join(cleaned.split())
        
        # 去除可能的特殊符号
        cleaned = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。、；：？！（）\[\]""''《》\-—\.\s]', '', cleaned)
        
        return cleaned
    
    def save_speech_script(self, speech: str, output_filepath: str):
        """保存生成的讲解稿到文件"""
        # 确保输出目录存在
        output_dir = os.path.dirname(output_filepath)
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存讲解稿
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(speech)
        
        print(f"Saved: {output_filepath}")
    
    def process_folders(self, md_folder: str, py_folder: str, output_dir: str="speech", delay_seconds: float = 1.0):
        """
        处理两个文件夹，生成讲解稿
        
        Args:
            md_folder: Markdown 文件夹路径
            py_folder: Python 文件夹路径
            delay_seconds: API调用之间的延迟（避免频率限制）
        """
        # 获取文件夹名称用于输出路径
        output_base_dir = output_dir
        
        print(f"Processing folders:")
        print(f"  Markdown folder: {md_folder}")
        print(f"  Python folder: {py_folder}")
        print(f"  Output directory: {output_base_dir}")
        
        # 查找匹配的文件对
        matching_files = self.find_matching_files(md_folder, py_folder)
        
        if not matching_files:
            print("No matching files found!")
            return
        
        # 重置上一页讲解稿
        self.previous_speech = ""
        
        # 处理每个文件对
        for i, (base_name, md_path, py_path) in enumerate(matching_files, 1):
            print(f"\n[{i}/{len(matching_files)}] Processing: {base_name}")
            
            try:
                # 读取文件内容
                md_content = self.read_file_content(md_path)
                py_content = self.read_file_content(py_path)
                print(f"  Loaded MD: {len(md_content)} chars, PY: {len(py_content)} chars")
                
                # 调用LLM生成讲解稿
                print("  Calling LLM API...")
                speech = self.call_llm_api(self.previous_speech, md_content, py_content, max_retries=MAX_RETRIES)
                if "__LLM_FAILED__" in speech:
                    print(f"  Skip {base_name} due to openai_error")
                    continue
                
                # 保存讲解稿
                output_filename = f"{base_name}.txt"
                output_filepath = os.path.join(output_base_dir, output_filename)
                self.save_speech_script(speech, output_filepath)
                
                # 更新上一页讲解稿（用于保持连贯性）
                self.previous_speech = speech
                print(f"  Generated speech: {len(speech)} chars")
                
                # 延迟避免API频率限制
                if i < len(matching_files):
                    print(f"  Waiting {delay_seconds}s...")
                    time.sleep(delay_seconds)
                    
            except Exception as e:
                print(f"  Error processing {base_name}: {e}")
                continue
        
        print(f"\n✅ Processing completed! Output saved to: {output_base_dir}")

        # 打印总结
    def pipeline(self, markdown_folder: str, manim_folder: str, output_dir: str="speech", delay_seconds: float = 1.0):
        """
        简化的流水线接口
        
        Args:
            markdown_folder: Markdown 文件夹路径
            manim_folder: Python 文件夹路径
            delay_seconds: API调用之间的延迟（避免频率限制）
        """
        self.process_folders(markdown_folder, manim_folder, output_dir, delay_seconds=delay_seconds)


def main():
    parser = argparse.ArgumentParser(description="Generate speech scripts from MD and PY files")
    parser.add_argument("md_folder", help="Folder containing .md files")
    parser.add_argument("py_folder", help="Folder containing .py files")
    parser.add_argument("--config", default="config.json", help="Config file path")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay between API calls in seconds")
    
    args = parser.parse_args()
    
    try:
        # 创建生成器并处理文件夹
        generator = SpeechScriptGenerator(config_path=args.config)
        generator.process_folders(args.md_folder, args.py_folder, delay_seconds=args.delay)
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()