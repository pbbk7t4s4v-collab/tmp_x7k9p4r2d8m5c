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
import base64
from pathlib import Path
from typing import List, Tuple
import time
import concurrent.futures
import shutil

# 大模型 API 配置
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

class ManimCodeGenerator:
    def __init__(self, config_path: str = "config.json", verbose: bool = False):
        """
        初始化代码生成器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.prompt_template = self._load_prompt_template("prompt_templates/Page_Coder.txt")
        self.prompt_template_no_pic = self._load_prompt_template("prompt_templates/Page_Coder_with_no_pic.txt")
        self.planner_prompt_template = self._load_prompt_template("prompt_templates/Page_Pic_Planner.txt")
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
    
    def _load_prompt_template(self, path: str) -> str:
        """加载 prompt 模板"""
        prompt_file = Path(path)
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
    
    def plan_images(self, markdown_content: str, output_base_dir: str, filename: str) -> dict:
        """
        调用 Planner 判断是否需要图片
        """
        full_prompt = f"{self.planner_prompt_template}\n\n以下是课程内容：\n\n{markdown_content}"
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                client = openai.OpenAI(
                    api_key=self.config["llm_key"],
                    base_url=self.config["llm_settings"]["base_url"]
                )
                
                response = client.chat.completions.create(
                    model="gemini-3-pro-preview",
                    messages=[
                        {"role": "system", "content": "你是一位专业的教学内容策划专家。"},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=self.config["llm_settings"]["max_tokens"],
                    temperature=self.config["llm_settings"]["temperature"]
                )
                raw_content = response.choices[0].message.content.strip()
                
                if not raw_content:
                    print(f"  Planner response is empty. Retrying ({attempt + 1}/{max_retries})...")
                    time.sleep(1)
                    continue

                # 保存原始响应日志，方便调试 JSON 解析失败的问题
                try:
                    log_dir = Path(output_base_dir).parent / "logs"
                    log_dir.mkdir(parents=True, exist_ok=True)
                    log_path = log_dir / f"{Path(filename).stem}_planner_response.txt"
                    with open(log_path, 'w', encoding='utf-8') as f:
                        f.write(f"File: {filename}\n")
                        f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write("-" * 40 + "\n")
                        f.write(raw_content)
                except Exception as e:
                    print(f"Failed to write planner log: {e}")

                # 解析 JSON
                plan_result = {"needs_image": False, "images": []} # 默认保底值
                parse_success = False

                try:
                    # 1. 尝试清理 Markdown 代码块标记
                    content_to_parse = raw_content
                    if "```json" in content_to_parse:
                        content_to_parse = content_to_parse.split("```json")[1].split("```")[0]
                    elif "```" in content_to_parse:
                        content_to_parse = content_to_parse.split("```")[1].split("```")[0]
                    
                    content_to_parse = content_to_parse.strip()
                    
                    # 2. 尝试直接解析
                    plan_result = json.loads(content_to_parse)
                    parse_success = True
                except json.JSONDecodeError:
                    # 3. 如果失败，尝试用正则提取第一个 { ... }
                    try:
                        match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                        if match:
                            json_str = match.group(0)
                            plan_result = json.loads(json_str)
                            parse_success = True
                    except Exception:
                        pass
                
                if not parse_success:
                    print(f"Failed to parse planner JSON for {filename}. Raw content preview: {raw_content[:100]}...")
                    # 使用默认值，但继续执行保存逻辑
                
                # 保存 Planner 结果 (无论是解析成功的，还是保底的)
                planner_dir = Path(output_base_dir).parent / "planner"
                planner_dir.mkdir(parents=True, exist_ok=True)
                
                output_filename = filename.replace('.md', '.json')
                output_filepath = planner_dir / output_filename
                
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    json.dump(plan_result, f, indent=4, ensure_ascii=False)
                    
                if self.verbose:
                    if parse_success:
                        print(f"  Planner result saved to: {output_filepath}")
                    else:
                        print(f"  Planner parsing failed. Saved default JSON to: {output_filepath}")
                    
                return plan_result
                
            except Exception as e:
                print(f"Planner API call failed (Attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    # 即使 API 调用失败，也尝试保存一个保底 JSON，以便后续流程知道这里出错了但有文件
                    try:
                        planner_dir = Path(output_base_dir).parent / "planner"
                        planner_dir.mkdir(parents=True, exist_ok=True)
                        output_filename = filename.replace('.md', '.json')
                        output_filepath = planner_dir / output_filename
                        with open(output_filepath, 'w', encoding='utf-8') as f:
                            json.dump({"needs_image": False, "images": []}, f, indent=4, ensure_ascii=False)
                    except Exception:
                        pass
                    return {"needs_image": False, "images": []}
        
        return {"needs_image": False, "images": []}

    def call_llm_api(self, markdown_content: str, prompt_template: str) -> str:
        """
        调用大模型 API 生成 Manim 代码
        
        Args:
            markdown_content: Markdown 格式的课程内容
            prompt_template: 使用的 prompt 模板
            
        Returns:
            生成的 Manim Python 代码
        """
        # 构建完整的 prompt
        full_prompt = f"{prompt_template}\n\n以下是需要转换为 Manim 动画的课程内容：\n\n{markdown_content}"
        
        max_retries = 5
        for attempt in range(max_retries):
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
                
                if not raw_content:
                    print(f"  Coder response is empty. Retrying ({attempt + 1}/{max_retries})...")
                    time.sleep(1)
                    continue
                
                return self.clean_generated_code(raw_content)
                
            except Exception as e:
                print(f"API call failed (Attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    return f"# Error generating code for this section\n# Error: {e}\npass"
        
        return f"# Error generating code for this section\n# Failed after {max_retries} attempts\npass"
    
    def generate_image(self, prompt: str, output_path: Path) -> bool:
        """
        调用 gemini-3-pro-image-preview 生成图片
        """
        max_retries = 5
        for attempt in range(max_retries):
            try:
                client = openai.OpenAI(
                    api_key=self.config["llm_key"],
                    base_url=self.config["llm_settings"]["base_url"]
                )
                
                # 构造提示词
                full_prompt = f"Generate a high-quality image based on the following description: {prompt}. The aspect ratio of the image must be 1:1."
                
                if self.verbose:
                    print(f"    Generating image for: {prompt[:30]}... (Attempt {attempt + 1}/{max_retries})")
                
                response_stream = client.chat.completions.create(
                    model=self.config.get("picture_settings", {}).get("model", "gemini-3-pro-image-preview"),
                    messages=[
                        {"role": "user", "content": full_prompt}
                    ],
                    stream=True
                )

                full_content = ""
                for chunk in response_stream:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        full_content += chunk.choices[0].delta.content
                
                # 解析 Markdown 图片链接
                image_url = None
                start_index = full_content.find('![image](')
                if start_index != -1:
                    end_index = full_content.find(')', start_index)
                    if end_index != -1:
                        image_url = full_content[start_index + 9 : end_index]

                if not image_url:
                    print(f"    Failed to find image url in response.")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        break

                if image_url.startswith("data:image"):
                    b64_str = image_url.split(",")[1]
                    img_bytes = base64.b64decode(b64_str)
                    
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(img_bytes)
                    return True
                else:
                    print(f"    Unsupported image URL format: {image_url[:30]}...")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        break

            except Exception as e:
                print(f"    Image generation failed (Attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    break
        
        # Fallback mechanism
        print(f"    All {max_retries} attempts failed. Using placeholder.")
        try:
            # Try to find placeholder.png in the same directory as the script
            script_dir = Path(__file__).parent
            placeholder_path = script_dir / "placeholder.png"
            
            if not placeholder_path.exists():
                 # Try current working directory
                 placeholder_path = Path("placeholder.png")
            
            if placeholder_path.exists():
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(placeholder_path, output_path)
                print(f"    Copied placeholder to {output_path}")
                return True
            else:
                print(f"    Placeholder not found at {placeholder_path}")
                return False
        except Exception as e:
            print(f"    Failed to use fallback placeholder: {e}")
            return False

    def process_images_in_code(self, code: str, output_dir: str, filename: str) -> str:
        """
        处理代码中的图片生成请求
        """
        # 匹配 ImageMobject("1.png") # 描述
        pattern = re.compile(r'ImageMobject\("([^"]+)"\)\s*#\s*(.*)')
        
        lines = code.split('\n')
        new_lines = []
        
        file_stem = Path(filename).stem # e.g. 1_1
        # parent(<output_dir>)/pictures/<n>_<m>
        pictures_dir = Path(output_dir).parent / "pictures" / file_stem
        
        for line in lines:
            match = pattern.search(line)
            if match:
                img_filename = match.group(1) # 1.png
                description = match.group(2).strip() # 描述
                
                img_path = pictures_dir / img_filename
                
                # 生成图片
                if self.generate_image(description, img_path):
                    # 替换为绝对路径
                    abs_path = str(img_path.absolute()).replace('\\', '/')
                    new_line = line.replace(f'"{img_filename}"', f'"{abs_path}"')
                    new_lines.append(new_line)
                else:
                    new_lines.append(line) # 生成失败则保留原样
            else:
                new_lines.append(line)
                
        return '\n'.join(new_lines)

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
            
            # 1. 调用 Planner
            if self.verbose:
                print(f"  Calling Planner for {filename}...")
            plan_result = self.plan_images(markdown_content, output_base_dir, filename)
            needs_image = plan_result.get("needs_image", False)
            
            # 2. 选择 Prompt 模板并准备图片建议
            image_plan_str = ""
            if needs_image:
                selected_prompt = self.prompt_template
                if self.verbose:
                    print(f"  Planner decided: Images NEEDED. Using standard prompt.")
                
                # 格式化图片建议
                images = plan_result.get("images", [])
                if images:
                    image_plan_str = "\n\n【Planner 图片建议】\n请参考使用以下图片，并严格按照描述生成代码：\n"
                    for img in images:
                        idx = img.get("index")
                        desc = img.get("description")
                        image_plan_str += f"- 图片 {idx} (ImageMobject(\"{idx}.png\")): {desc}\n"
            else:
                selected_prompt = self.prompt_template_no_pic
                if self.verbose:
                    print(f"  Planner decided: NO images needed. Using no-pic prompt.")

            # 3. 调用LLM生成代码
            if self.verbose:
                print(f"  Calling LLM API for {filename}...")
            
            # 将图片建议附加到 markdown_content 之前，作为上下文的一部分
            content_with_plan = image_plan_str + "\n" + markdown_content
            
            manim_code = self.call_llm_api(content_with_plan, selected_prompt)
            
            # 4. 处理图片生成 (仅当 needs_image 为 True 时)
            if needs_image:
                if self.verbose:
                    print(f"  Processing images for {filename}...")
                manim_code = self.process_images_in_code(manim_code, output_base_dir, filename)
            else:
                if self.verbose:
                    print(f"  Skipping image processing as per planner decision.")
            
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
    parser.add_argument("--folder", default="/home/TeachMaster/ML/nano_test/test_markdown", help="Input folder containing *_*.md files")
    parser.add_argument("--config", default="config.json", help="Config file path")
    parser.add_argument("--output_dir", default="/home/TeachMaster/ML/nano_test/12_13_2/output_code", help="Output directory for generated python files")
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