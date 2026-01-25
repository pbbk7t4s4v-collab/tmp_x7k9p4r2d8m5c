#!/usr/bin/env python3
"""
分页处理器：为章节内容添加分页标记
使用Brain.txt模板调用大模型对每个section进行分页处理
"""

import argparse
import os
import glob
from llm_api import LLMAPIClient


class Paginator:
    """章节分页处理器"""
    
    def __init__(self, config_path="config.json", verbose=False):
        """初始化LLM客户端"""
        self.llm_client = LLMAPIClient(config_path=config_path)
        self.verbose = verbose

    def paginate_section_file(self, section_file_path):
        """
        对单个章节文件进行分页处理
        
        Args:
            section_file_path: 章节文件路径
            verbose: 是否显示详细过程
        
        Returns:
            分页后的内容
        """
        try:
            # 读取原始文件内容
            with open(section_file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            if self.verbose:
                print(f"正在处理文件: {section_file_path}")
                print(f"原始内容长度: {len(original_content)} 字符")
            
            # 如果内容为空或太短，跳过分页处理
            if len(original_content.strip()) < 100:
                if self.verbose:
                    print("内容太短，跳过分页处理")
                return original_content
            
            # 调用大模型进行分页处理
            paginated_content = self.llm_client.generate_paginated_section(original_content)
            
            if self.verbose:
                print(f"分页处理完成")
            
            return paginated_content
            
        except Exception as e:
            print(f"处理文件 {section_file_path} 时出错: {e}")
            return None
    
    def save_paginated_file(self, original_path, paginated_content, output_dir="scripts", output_suffix="_paginated"):
        """
        保存分页后的文件
        
        Args:
            original_path: 原始文件路径
            paginated_content: 分页后的内容
            output_suffix: 输出文件后缀
        
        Returns:
            保存的文件路径
        """
        # 生成输出文件路径
        dir_name = output_dir
        base_name = os.path.basename(original_path)
        name, ext = os.path.splitext(base_name)
        
        output_path = os.path.join(dir_name, f"{name}{output_suffix}{ext}")
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(paginated_content)
        
        return output_path
    
    def process_sections_directory(self, sections_dir, output_dir="scripts"):
        """
        处理整个sections目录中的所有markdown文件
        
        Args:
            sections_dir: sections目录路径
            verbose: 是否显示详细过程
        
        Returns:
            处理结果统计
        """
        if not os.path.exists(sections_dir):
            print(f"目录不存在: {sections_dir}")
            return None
        
        # 查找所有markdown文件
        md_files = glob.glob(os.path.join(sections_dir, "*.md"))
        
        if not md_files:
            print(f"在目录 {sections_dir} 中未找到markdown文件")
            return None
        
        if self.verbose:
            print(f"找到 {len(md_files)} 个markdown文件")
            print("="*50)
        
        results = {
            'total': len(md_files),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'files': []
        }
        
        # 逐个处理文件
        for i, md_file in enumerate(sorted(md_files), 1):
            if self.verbose:
                print(f"\n[{i}/{len(md_files)}] 处理文件: {os.path.basename(md_file)}")
            
            # 分页处理
            paginated_content = self.paginate_section_file(md_file)
            
            if paginated_content is None:
                results['failed'] += 1
                results['files'].append({'file': md_file, 'status': 'failed'})
                continue
            
            # 保存分页后的文件
            try:
                output_path = self.save_paginated_file(md_file, paginated_content, output_dir=output_dir)
                results['success'] += 1
                results['files'].append({
                    'file': md_file, 
                    'output': output_path,
                    'status': 'success'
                })
                
                if self.verbose:
                    print(f"分页文件已保存: {output_path}")
                    
            except Exception as e:
                print(f"保存文件时出错: {e}")
                results['failed'] += 1
                results['files'].append({'file': md_file, 'status': 'failed'})
        
        return results
    
    def pipeline(self, sections_dir, output_dir="scripts"):
        """简化的流水线接口"""
        os.makedirs(output_dir, exist_ok=True)
        results = self.process_sections_directory(sections_dir, output_dir=output_dir)
        return results
    
    def print_summary(self, results):
        """打印处理结果摘要"""
        if not results:
            return
        
        print("\n" + "="*50)
        print("分页处理完成!")
        print(f"总计文件: {results['total']}")
        print(f"成功处理: {results['success']}")
        print(f"处理失败: {results['failed']}")
        print(f"跳过处理: {results['skipped']}")
        
        if results['success'] > 0:
            print("\n成功处理的文件:")
            for file_info in results['files']:
                if file_info['status'] == 'success':
                    print(f"  {file_info['file']} -> {file_info['output']}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="章节分页处理器 - 为markdown章节添加分页标记",
        epilog="示例: python paginator.py scripts/KNN_1234_sections/"
    )
    parser.add_argument(
        "sections_dir",
        help="包含章节markdown文件的目录路径"
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
        help="静默模式，只显示结果摘要"
    )
    
    args = parser.parse_args()
    
    try:
        # 创建分页处理器
        paginator = Paginator(config_path=args.config)
        
        # 处理sections目录
        results = paginator.process_sections_directory(
            args.sections_dir
        )
        
        # 显示结果摘要
        paginator.print_summary(results)
        
    except Exception as e:
        print(f"错误: {e}")
        print("\n请确保:")
        print("1. 已安装所有依赖包")
        print("2. 在 config.json 中正确设置了所有 API 密钥")
        print("3. sections目录路径正确")


if __name__ == "__main__":
    main()