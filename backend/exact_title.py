import re
import sys

def extract_first_level_headings(markdown_file_path):
    """
    提取 Markdown 文件中的所有一级标题 (即以 # 开头的标题)
    
    Args:
        markdown_file_path (str): Markdown 文件的路径
        
    Returns:
        List[str]: Markdown 文件中的所有一级标题列表
    """
    try:
        with open(markdown_file_path, 'r', encoding='utf-8') as file:
            content = file.readlines()
        
        # 使用正则表达式查找以 '#' 开头的行（一级标题）
        headings = [line.strip('#').strip() for line in content if re.match(r'^#\s', line)]
        
        return headings
    except FileNotFoundError:
        print(f"错误: 文件 '{markdown_file_path}' 未找到.")
        return []
    except Exception as e:
        print(f"发生错误: {e}")
        return []

# 从命令行参数获取文件路径
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python extract_headings.py <markdown文件路径>")
        sys.exit(1)

    markdown_path = sys.argv[1]
    headings = extract_first_level_headings(markdown_path)
    
    # 直接返回一级标题名称
    if headings:
        for heading in headings:
            print(heading)
    else:
        print("未找到一级标题.")
