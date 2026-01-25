#!/usr/bin/env python3
"""
自动检索程序：结合Noter生成的检索需求和搜索API
"""

import re
import argparse
from llm_api import LLMAPIClient
from search_api import SearchAPI


class AutoSearcher:
    """自动检索器，结合Noter和搜索功能"""
    
    def __init__(self, config_path="config.json"):
        """初始化Noter和搜索API客户端"""
        self.llm_client = LLMAPIClient(config_path=config_path)
        self.search_client = SearchAPI(config_path=config_path)
    
    def parse_search_items(self, noter_output):
        """
        解析Noter输出的检索项目列表
        
        Args:
            noter_output: Noter的输出文本
        
        Returns:
            检索项目列表
        """
        # 匹配格式：1.xxx、2.xxx等
        pattern = r'^\d+\.\s*(.+)$'
        items = []
        
        for line in noter_output.strip().split('\n'):
            line = line.strip()
            if line:
                match = re.match(pattern, line)
                if match:
                    items.append(match.group(1))
                else:
                    # 如果不是数字格式，但是非空行，也当作检索项目
                    if line and not line.startswith('=') and not line.startswith('-'):
                        items.append(line)
        
        return items
    
    def search_single_item(self, query, max_results=2):
        """
        搜索单个项目
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
        
        Returns:
            搜索结果
        """
        try:
            result = self.search_client.search_and_contents(
                query=query,
                max_results=max_results
            )
            return result
        except Exception as e:
            print(f"搜索错误 '{query}': {e}")
            return None
    
    def format_search_result(self, query, result):
        """
        格式化搜索结果
        
        Args:
            query: 搜索查询
            result: 搜索结果
        
        Returns:
            格式化的结果字符串
        """
        if not result or not hasattr(result, 'results') or not result.results:
            return f"=== {query} ===\n未找到相关结果\n"
        
        formatted = f"=== {query} ===\n"
        
        for i, item in enumerate(result.results[:2], 1):  # 只显示前2个结果
            formatted += f"\n{i}. {item.title}\n"
            formatted += f"   URL: {item.url}\n"
            
            # 显示内容摘要
            if hasattr(item, 'text') and item.text:
                # 截取前300字符作为摘要
                preview = item.text.strip()[:300]
                if len(item.text) > 300:
                    preview += "..."
                formatted += f"   摘要: {preview}\n"
        
        formatted += "\n" + "="*60 + "\n"
        return formatted
    
    def auto_search(self, keyword, max_results_per_item=2):
        """
        自动检索流程：生成检索需求 -> 逐项搜索 -> 输出结果
        
        Args:
            keyword: 关键词
            max_results_per_item: 每个检索项目的最大结果数
        """
        print(f"正在为关键词 '{keyword}' 生成检索需求...")
        
        # 1. 使用Noter生成检索需求
        noter_output = self.llm_client.generate_course_notes(keyword)
        print(f"检索需求生成完成：\n{noter_output}\n")
        
        # 2. 解析检索项目
        search_items = self.parse_search_items(noter_output)
        
        if not search_items:
            print("未能解析出有效的检索项目")
            return
        
        print(f"共解析出 {len(search_items)} 个检索项目\n")
        print("开始逐项检索...\n")
        
        # 3. 逐项检索并输出结果
        for i, item in enumerate(search_items, 1):
            print(f"[{i}/{len(search_items)}] 正在检索: {item}")
            
            # 搜索当前项目
            result = self.search_single_item(item, max_results_per_item)
            
            # 格式化并输出结果
            formatted_result = self.format_search_result(item, result)
            print(formatted_result)


def main():
    """主函数：处理命令行参数并执行自动检索"""
    parser = argparse.ArgumentParser(
        description="自动检索工具 - 根据关键词生成检索需求并自动搜索",
        epilog="示例: python auto_search.py \"KNN\""
    )
    parser.add_argument(
        "keyword",
        help="要检索的关键词"
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=2,
        help="每个检索项目返回的最大结果数 (默认: 2)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="配置文件路径 (默认: config.json)"
    )
    
    args = parser.parse_args()
    
    try:
        # 创建自动检索器
        searcher = AutoSearcher(config_path=args.config)
        
        # 执行自动检索
        searcher.auto_search(args.keyword, max_results_per_item=args.max_results)
        
    except Exception as e:
        print(f"错误: {e}")
        print("\n请确保:")
        print("1. 已安装所有依赖包")
        print("2. 在 config.json 中正确设置了 API 密钥")
        print("3. 网络连接正常")


if __name__ == "__main__":
    main()