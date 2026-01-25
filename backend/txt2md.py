#!/usr/bin/env python3
import sys
import re
from pathlib import Path

def convert_line(line: str) -> str:
    content = line.strip()
    if not content: return line
    pattern = r"^(\d+(?:\.\d+)*)[.\s]+(.*)$"
    match = re.match(pattern, content)
    if not match: return line
    level = match.group(1).count('.') + 2
    return f"{'#' * level} {match.group(2).strip()}\n"

def get_safe_content(file_path):
    """尝试多种编码读取文件，解决 GBK 和 UTF-8 冲突"""
    encodings = ['utf-8-sig', 'utf-8', 'gb18030', 'cp936', 'latin-1']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue
    raise Exception("无法识别文件编码，请确保文件是 UTF-8 或 GBK 格式。")

def safe_txt_to_md(input_path_str: str):
    try:
        # 清理路径中的换行符和不可见字符
        clean_path = input_path_str.replace('\n', '').replace('\r', '').strip()
        path_obj = Path(clean_path).resolve()

        if not path_obj.exists():
            print(f"Error: File not found {path_obj}")
            sys.exit(1)

        # 获取内容（自动处理编码）
        lines = get_safe_content(path_obj)
        
        # 转换内容
        converted = [convert_line(line) for line in lines]

        # 写入 .md 文件
        output_path = path_obj.with_suffix('.md')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(converted)

        # 验证并删除原文件
        if output_path.exists() and output_path.stat().st_size > 0:
            path_obj.unlink()
            print(f"Success: {output_path}")
        
    except Exception as e:
        print(f"Execution Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    # 拼接所有参数，防止空格导致文件名断开
    safe_txt_to_md(" ".join(sys.argv[1:]))