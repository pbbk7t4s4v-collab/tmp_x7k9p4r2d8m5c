#!/usr/bin/env python3
"""
批量给Manim文件添加页码
按照自然排序确定文件顺序（1_1, 1_2, ..., 1_10, 1_11, ...）

使用方法：
    python add_pagenum.py /path/to/folder
"""

import os
import re
import sys
import glob
from pathlib import Path

def natural_sort_key(filename):
    """
    自然排序的键函数
    将 "1_10.py" 转换为 [1, 10] 用于排序
    """
    # 提取数字部分
    numbers = re.findall(r'\d+', filename)
    return [int(num) for num in numbers]

def find_title_animation_position(content):
    """
    找到 Write(title) 和 GrowFromCenter(title_line) 动画所在的位置
    返回插入页码代码的位置
    """
    lines = content.split('\n')
    
    # 寻找包含 self.play 的行
    for i, line in enumerate(lines):
        if 'self.play(' in line:
            # 找到这个play块的结束位置
            j = i + 1
            paren_count = line.count('(') - line.count(')')
            
            while j < len(lines) and paren_count > 0:
                paren_count += lines[j].count('(') - lines[j].count(')')
                j += 1
            
            # 检查这个play块是否包含Write(title)和GrowFromCenter(title_line)
            play_block = '\n'.join(lines[i:j])
            if 'Write(title' in play_block and 'GrowFromCenter(title_line' in play_block:
                return j  # 返回play块结束后的位置
    
    return None

def add_page_number(file_path, page_num):
    """
    给指定文件添加页码
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经有页码
    if 'page_number = Text(' in content:
        print(f"跳过 {file_path.name}：已经包含页码")
        return False
    
    # 找到插入位置
    insert_pos = find_title_animation_position(content)
    if insert_pos is None:
        print(f"跳过 {file_path.name}：未找到标题动画")
        return False
    
    lines = content.split('\n')
    
    # 构造页码代码
    page_code = [
        "",
        f"        # Page number",
        f"        page_number = Text(\"{page_num}\", font_size=20, color=GRAY_C)",
        f"        page_number.to_corner(DR, buff=0.3)",
        f"        self.play(FadeIn(page_number))"
    ]
    
    # 插入页码代码
    lines[insert_pos:insert_pos] = page_code
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✓ 已添加页码 {page_num} 到 {file_path.name}")
    return True

def main():
    # 检查命令行参数
    if len(sys.argv) != 2:
        print("使用方法：python add_page_numbers.py /path/to/folder")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    
    if not os.path.exists(folder_path):
        print(f"错误：文件夹 {folder_path} 不存在")
        sys.exit(1)
    
    # 获取所有.py文件
    py_files = list(Path(folder_path).glob("*.py"))
    
    if not py_files:
        print(f"错误：文件夹 {folder_path} 中没有找到.py文件")
        sys.exit(1)
    
    # 自然排序
    py_files.sort(key=lambda x: natural_sort_key(x.name))
    
    print(f"找到 {len(py_files)} 个.py文件，按自然排序:")
    for i, file_path in enumerate(py_files, 1):
        print(f"  {i:2d}. {file_path.name}")
    
    print(f"\n开始批量添加页码...")
    
    # 批量处理
    success_count = 0
    for i, file_path in enumerate(py_files, 1):
        if add_page_number(file_path, i):
            success_count += 1
    
    print(f"\n完成！成功处理了 {success_count}/{len(py_files)} 个文件")

if __name__ == "__main__":
    main()