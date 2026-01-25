#!/usr/bin/env python3
"""
教案讲义生成器：完整的流水线程序
1. Noter生成课程纲要 -> 2. 逐章节检索 -> 3. 逐章节生成讲义 -> 4. 拼接成完整讲义
"""

import argparse
from llm_api import LLMAPIClient
from search_api import SearchAPI
from auto_search import AutoSearcher
import re
import random


class ScriptGenerator:
    """教案讲义生成器"""
    
    def __init__(self, config_path="config.json"):
        """初始化所有必要的客户端"""
        self.llm_client = LLMAPIClient(config_path=config_path)
        self.search_client = SearchAPI(config_path=config_path)
        self.auto_searcher = AutoSearcher(config_path=config_path)
    
    def generate_course_outline(self, keyword, verbose=False):
        """
        生成课程纲要
        
        Args:
            keyword: 关键词
            verbose: 是否显示详细过程
        
        Returns:
            课程纲要列表
        """
        if verbose:
            print(f"正在为关键词 '{keyword}' 生成课程纲要...")
        
        # 使用Noter生成课程纲要
        noter_output = self.llm_client.generate_course_notes(keyword)
        if verbose:
            print(f"课程纲要：\n{noter_output}\n")
        
        # 解析纲要项目
        outline_items = self.auto_searcher.parse_search_items(noter_output)
        
        if not outline_items:
            return []
        
        if verbose:
            print(f"共解析出 {len(outline_items)} 个章节")
        
        return outline_items
    
    def generate_chapter_content(self, keyword, chapter_topic, max_results=2, verbose=False):
        """
        为单个章节生成详细的讲义内容
        
        Args:
            keyword: 课程关键词
            chapter_topic: 章节主题
            max_results: 检索结果数量
            verbose: 是否显示详细过程
        
        Returns:
            该章节的详细讲义内容
        """
        if verbose:
            print(f"正在为章节 '{chapter_topic}' 收集资料...")
        
        # 1. 为该章节检索相关资料
        result = self.auto_searcher.search_single_item(chapter_topic, max_results)
        # result = ""
        
        # 2. 整理检索结果
        search_results = ""
        if result and hasattr(result, 'results') and result.results:
            search_results = f"# {chapter_topic} - 检索资料\n\n"
            
            for j, res in enumerate(result.results[:max_results], 1):
                search_results += f"## 资料 {j}: {res.title}\n"
                search_results += f"来源: {res.url}\n\n"
                
                if hasattr(res, 'text') and res.text:
                    # 取前800字符作为内容（比之前更多，因为是单个章节）
                    content = res.text.strip()[:800]
                    if len(res.text) > 800:
                        content += "..."
                    search_results += f"内容:\n{content}\n\n"
        else:
            search_results = f"# {chapter_topic} - 检索资料\n\n未找到相关资料。\n\n"
        
        if verbose:
            print(f"正在生成章节 '{chapter_topic}' 的详细讲义...")
        
        # 3. 生成该章节的详细讲义
        chapter_content = self.llm_client.generate_chapter_script(chapter_topic, search_results)
        
        if verbose:
            print(f"章节 '{chapter_topic}' 讲义生成完成")
        
        return chapter_content
    
    def generate_full_script(self, keyword, max_results_per_item=2, verbose=True):
        """
        生成完整的教案讲义（新流程：纲要->逐章节生成->拼接）
        
        Args:
            keyword: 关键词
            max_results_per_item: 每个章节的最大检索结果数
            verbose: 是否显示详细过程
        
        Returns:
            完整的教案讲义
        """
        if verbose:
            print(f"开始为 '{keyword}' 生成完整教案讲义...")
            print("="*60)
        
        # 1. 生成课程纲要
        outline_items = self.generate_course_outline(keyword, verbose=verbose)
        
        if not outline_items:
            return f"无法为关键词 '{keyword}' 生成有效的课程纲要。"
        
        # 2. 逐章节生成详细讲义
        all_chapters = []
        
        for i, chapter_topic in enumerate(outline_items, 1):
            if verbose:
                print(f"\n[{i}/{len(outline_items)}] 正在处理章节: {chapter_topic}")
                print("-" * 40)
            
            # 生成该章节的详细内容
            chapter_content = self.generate_chapter_content(
                keyword, 
                chapter_topic, 
                max_results=max_results_per_item, 
                verbose=verbose
            )
            
            all_chapters.append(chapter_content)
        
        # 3. 拼接所有章节形成完整讲义
        if verbose:
            print("\n正在拼接所有章节...")
        
        # 创建完整讲义的标题和整体结构
        full_script = f"# {keyword} 完整教案讲义\n\n"
        full_script += f"## 课程大纲\n\n"
        
        # 添加目录
        for i, chapter_topic in enumerate(outline_items, 1):
            full_script += f"{i}. {chapter_topic}\n"
        
        full_script += "\n---\n\n"
        
        # 拼接所有章节内容
        for chapter_content in all_chapters:
            full_script += chapter_content + "\n\n---\n\n"
        
        if verbose:
            print("教案讲义生成完成！\n")
            print("="*60)
        
        return full_script
    
    def save_script_to_file(self, keyword, script, output_dir="scripts"):
        """
        将生成的讲义保存到文件
        
        Args:
            keyword: 关键词
            script: 讲义内容
            output_dir: 输出目录
        
        Returns:
            保存的文件路径
        """
        import os
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 生成随机数（4位数字）
        random_num = random.randint(1000, 9999)
        
        # 生成文件名：关键词_随机数.md
        filename = f"{keyword}_{random_num}.md"
        filepath = os.path.join(output_dir, filename)
        
        # 保存文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(script)
        
        return filepath
    
    def pipeline(self, keyword, max_results_per_item=2, output_dir="scripts", verbose=True):
        """
        一键执行完整流水线：生成讲义并保存到文件
        
        Args:
            keyword: 关键词
            max_results_per_item: 每个章节的最大检索结果数
            output_dir: 输出目录
            verbose: 是否显示详细过程
        
        Returns:
            包含讲义文件路径和章节信息的字典
        """
        if verbose:
            print("="*80)
            print(f"开始完整流水线处理关键词: {keyword}")
            print("="*80)
        
        # 第一步：生成完整讲义
        if verbose:
            print("第一步：生成完整讲义")
            print("-"*50)
        
        script = self.generate_full_script(
            keyword, 
            max_results_per_item=max_results_per_item
        )
        # 第二步：保存到文件
        if verbose:
            print("第二步：保存到文件")
            print("-"*50)
        
        filepath = self.save_script_to_file(
            keyword, 
            script, 
            output_dir=output_dir
        )
        
        return filepath


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="教案讲义生成器 - 完整的从检索到生成的流水线（自动保存到scripts文件夹）",
        epilog="示例: python script_generator.py \"KNN\""
    )
    parser.add_argument(
        "keyword",
        help="要生成教案的关键词"
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=2,
        help="每个检索项目返回的最大结果数 (默认: 2)"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="scripts",
        help="输出目录 (默认: scripts)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式，不显示过程信息"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="配置文件路径 (默认: config.json)"
    )
    
    args = parser.parse_args()
    
    try:
        # 创建生成器
        generator = ScriptGenerator(config_path=args.config)
        
        # 生成完整讲义
        script = generator.generate_full_script(
            args.keyword,
            max_results_per_item=args.max_results,
            verbose=not args.quiet
        )
        
        # 输出结果
        print(script)
        
        # 默认保存到文件
        filepath = generator.save_script_to_file(
            args.keyword, 
            script, 
            output_dir=args.output_dir
        )
        print(f"\n讲义已保存到: {filepath}")
        
    except Exception as e:
        print(f"错误: {e}")
        print("\n请确保:")
        print("1. 已安装所有依赖包")
        print("2. 在 config.json 中正确设置了所有 API 密钥")
        print("3. 网络连接正常")


if __name__ == "__main__":
    main()