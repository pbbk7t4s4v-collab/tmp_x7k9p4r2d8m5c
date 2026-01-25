#!/usr/bin/env python3
"""
基于现有大纲生成详细内容的脚本
根据markdown大纲的层级结构，为每个三级标题生成详细内容并插入到原文件中
"""

import re
import os
import argparse

from llm_api import process_text

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("注意：未安装tqdm包，将使用简单进度显示")


class OutlineContentGenerator:
    """大纲内容生成器"""
    
    def __init__(self, config_path="config.json", verbose=True):
        """初始化"""
        self.config_path = config_path
        self.verbose = verbose
    
    def parse_markdown_outline(self, content):
        """
        解析markdown大纲，提取层级结构
        
        Args:
            content: markdown内容
            
        Returns:
            层级结构列表，每个元素包含 (level, title, line_number)
        """
        lines = content.split('\n')
        structure = []
        
        for i, line in enumerate(lines):
            if line.strip().startswith('#'):
                # 计算标题级别
                level = 0
                for char in line:
                    if char == '#':
                        level += 1
                    else:
                        break
                
                # 提取标题文本
                title = line.strip().lstrip('#').strip()
                
                if title:  # 忽略空标题
                    structure.append((level, title, i))
        
        return structure
    
    def build_section_paths(self, structure):
        """
        构建章节路径，形成 "一级 > 二级 > 三级" 的结构
        并收集每个三级标题下的四级标题
        
        Args:
            structure: 层级结构列表
            
        Returns:
            三级标题及其路径的字典 {line_number: (path, title, subsections)}
        """
        section_paths = {}
        title_stack = [None, None, None, None, None, None]  # 支持最多6级标题
        current_subsections = []  # 当前三级标题下的四级标题
        current_level3_line = None  # 当前三级标题的行号
        
        for level, title, line_number in structure:
            # 更新当前级别的标题
            title_stack[level-1] = title
            
            # 清空比当前级别更深的标题
            for i in range(level, len(title_stack)):
                title_stack[i] = None
                
            # 如果遇到三级标题
            if level == 3:
                # 如果之前有三级标题，保存其信息
                if current_level3_line is not None:
                    path_parts = []
                    for i in range(3):
                        if title_stack[i]:
                            path_parts.append(title_stack[i])
                    
                    path = " > ".join(path_parts[:-1]) + " > " + section_paths[current_level3_line][1]
                    section_paths[current_level3_line] = (path, section_paths[current_level3_line][1], current_subsections)
                
                # 开始新的三级标题
                path_parts = []
                for i in range(3):
                    if title_stack[i]:
                        path_parts.append(title_stack[i])
                
                path = " > ".join(path_parts)
                section_paths[line_number] = (path, title, [])
                current_level3_line = line_number
                current_subsections = []
            
            # 如果遇到四级标题，且当前有三级标题
            elif level == 4 and current_level3_line is not None:
                current_subsections.append(title)
        
        # 处理最后一个三级标题
        if current_level3_line is not None:
            path, title, _ = section_paths[current_level3_line]
            section_paths[current_level3_line] = (path, title, current_subsections)
        
        return section_paths
    
    def generate_section_content(self, course_topic, section_path, section_title, subsections=None):
        """
        为指定章节生成详细内容
        
        Args:
            course_topic: 课程主题
            section_path: 章节路径
            section_title: 章节标题
            subsections: 四级标题列表
            
        Returns:
            生成的详细内容
        """
        # 构建prompt
        prompt_template = self.load_prompt_template()
        
        # 格式化四级标题列表
        if subsections and len(subsections) > 0:
            subsections_text = "\n".join([f"- {sub}" for sub in subsections])
        else:
            subsections_text = "无四级标题，请根据章节主题自由组织内容结构"
        
        prompt = prompt_template.format(
            course_topic=course_topic,
            section_path=section_path,
            subsections=subsections_text,
            content_requirements=f"请为'{section_title}'这个主题生成详细的教学内容"
        )
        
        # 调用LLM生成内容
        content = process_text(prompt, self.config_path)
        
        return content
    
    def load_prompt_template(self):
        """加载prompt模板"""
        template_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "prompt_templates", 
            "Section_Content_Generator.txt"
        )
        
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def insert_content_into_outline(self, content, section_paths, course_topic, verbose=True):
        """
        将生成的内容插入到大纲中
        
        Args:
            content: 原始markdown内容
            section_paths: 三级标题路径字典
            course_topic: 课程主题
            verbose: 是否显示详细过程
            
        Returns:
            更新后的markdown内容
        """
        lines = content.split('\n')
        new_lines = []
        
        # 准备进度条
        sections_to_process = list(section_paths.keys())
        if verbose and HAS_TQDM:
            pbar = tqdm(total=len(sections_to_process), desc="生成章节内容", unit="章节")
        
        processed_count = 0
        skip_until_next_section = False
        current_section_line = None
        
        for i, line in enumerate(lines):
            # 检查是否是当前处理的三级标题的四级标题
            if current_section_line is not None and line.strip().startswith('####'):
                # 如果是当前三级标题下的四级标题，跳过（不添加到new_lines）
                section_path, section_title, subsections = section_paths[current_section_line]
                if any(sub in line for sub in subsections):
                    continue  # 跳过这个四级标题
            
            # 如果当前行是三级标题，且需要生成内容
            if i in section_paths:
                new_lines.append(line)  # 添加三级标题本身
                section_path, section_title, subsections = section_paths[i]
                current_section_line = i
                
                if verbose:
                    if HAS_TQDM:
                        pbar.set_description(f"生成: {section_title[:25]}...")
                    else:
                        subsections_info = f" (含{len(subsections)}个四级标题)" if subsections else ""
                        print(f"[{processed_count+1}/{len(sections_to_process)}] 正在生成内容：{section_path}{subsections_info}")
                
                # 生成详细内容
                detailed_content = self.generate_section_content(
                    course_topic, section_path, section_title, subsections
                )
                
                # 插入生成的内容（添加空行分隔）
                new_lines.append("")
                new_lines.extend(detailed_content.split('\n'))
                new_lines.append("")
                
                processed_count += 1
                
                if verbose:
                    if HAS_TQDM:
                        pbar.update(1)
                    else:
                        print(f"已生成内容，长度：{len(detailed_content)} 字符")
            else:
                # 不是三级标题，正常添加
                new_lines.append(line)
                # 如果这不是三级标题行，重置current_section_line
                if not line.strip().startswith('###'):
                    current_section_line = None
        
        if verbose and HAS_TQDM:
            pbar.close()
        
        return '\n'.join(new_lines)
    
    def process_outline_file(self, input_file, output_file=None, course_topic=None, verbose=True):
        """
        处理大纲文件，生成完整的教学内容
        
        Args:
            input_file: 输入的大纲文件路径
            output_file: 输出文件路径（如果为None，则覆盖原文件）
            course_topic: 课程主题（如果为None，则使用文件名）
            verbose: 是否显示详细过程
        """
        # 读取原始大纲
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if verbose:
            print(f"读取大纲文件：{input_file}")
        
        # 如果没有指定课程主题，使用文件名
        if not course_topic:
            course_topic = os.path.splitext(os.path.basename(input_file))[0]
        
        # 解析大纲结构
        structure = self.parse_markdown_outline(content)
        section_paths = self.build_section_paths(structure)
        
        if verbose:
            print(f"找到 {len(section_paths)} 个三级标题需要生成内容")
        
        # 生成并插入内容
        updated_content = self.insert_content_into_outline(
            content, section_paths, course_topic, verbose
        )
        
        # 确定输出文件
        if not output_file:
            output_file = input_file
        
        # 保存更新后的内容
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        if verbose:
            print(f"完整教学内容已保存到：{output_file}")

    def pipeline(self, input_file, output_file=None, course_topic=None, verbose=True):
        """
        一体化处理流程
        
        Args:
            input_file: 输入的大纲文件路径
            output_file: 输出文件路径（如果为None，则覆盖原文件）
            course_topic: 课程主题（如果为None，则使用文件名）
            verbose: 是否显示详细过程
        """
        self.process_outline_file(input_file, output_file, course_topic, verbose)
        return True
        


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="基于现有大纲生成详细教学内容",
        epilog="示例: python outline_content_generator.py outline/Regression.md"
    )
    parser.add_argument(
        "input_file",
        help="输入的大纲markdown文件路径"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出文件路径（默认覆盖原文件）"
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="课程主题（默认使用文件名）"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="配置文件路径（默认：config.json）"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式，不显示过程信息"
    )
    
    args = parser.parse_args()
    
    try:
        # 检查输入文件是否存在
        if not os.path.exists(args.input_file):
            print(f"错误：文件 {args.input_file} 不存在")
            return
        
        # 创建生成器
        generator = OutlineContentGenerator(config_path=args.config)
        
        # 处理大纲文件
        generator.process_outline_file(
            args.input_file,
            output_file=args.output,
            course_topic=args.topic,
            verbose=not args.quiet
        )
        
    except Exception as e:
        print(f"错误: {e}")
        print("\n请确保:")
        print("1. 已安装所有依赖包")
        print("2. 在 config.json 中正确设置了所有 API 密钥")
        print("3. 网络连接正常")
        print("4. 输入的markdown文件格式正确")


if __name__ == "__main__":
    main()