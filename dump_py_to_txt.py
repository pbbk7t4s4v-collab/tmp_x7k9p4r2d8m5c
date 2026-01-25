from __future__ import annotations
import argparse
from pathlib import Path

"""
功能: 递归扫描指定目录下的所有 Python 文件，提取代码内容，写入一个文本文件中。
-r/--root          -- 指定要扫描的根目录（递归）。默认当前目录。
-o/--out           -- 指定输出txt文件名（写到当前运行命令的文件夹），默认 all_python_code.txt。
-e/--exclude-dirs  -- 指定要排除扫描的目录名（逗号分隔，匹配任意层级目录名）。
-x/--exclude-files -- 指定要排除的文件（逗号分隔），支持：
                      1) 文件名：run.py， 注意这里若填写文件名，则会排除所有同名文件。
                      2) 相对路径：providers/base.py 或 providers\\base.py
                      说明：当 root 为当前目录时，会自动排除本脚本文件自身。

示例命令：
仅设定root根目录：python3 dump_py_to_txt.py --root "./test/"

输出格式:
1.relative/path/to/file1.py
<file1.py 的内容>
2.relative/path/to/file2.py
<file2.py 的内容>
...

最后还会输出汇总统计: 
==== SUMMARY ==== 
Root: <扫描的根目录> 
Python files: <扫描到的 Python 文件数量> 
Total lines (all): <所有文件的总行数> 
Total code lines (non-blank & non-#comment): <非空行且非注释行的代码行数>
"""

def is_comment_or_blank(line: str) -> bool:
    s = line.strip()
    return (not s) or s.startswith("#")

def _norm_rel(p: Path) -> str:
    """
    将相对路径统一为 posix 风格并做小写，用于跨平台匹配。
    """
    return p.as_posix().lower()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-r", "--root",
        default=".",
        help="要扫描的根目录（递归）。默认当前目录（.）"
    )
    ap.add_argument(
        "-o", "--out",
        default="all_python_code.txt",
        help="输出txt文件名（写到当前运行命令的文件夹）"
    )
    ap.add_argument(
        "-e", "--exclude-dirs",
        default="__pycache__,.git,.venv,venv,build,dist,WareHouse",
        help="要排除的目录名（逗号分隔，匹配任意层级目录名）"
    )
    ap.add_argument(
        "-x", "--exclude-files",
        default="",
        help="要排除的文件（逗号分隔），可填文件名或相对路径（相对 root）"
    )
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"root 不是目录: {root}")

    out_path = (Path.cwd() / args.out).resolve()

    exclude_dirs = {x.strip() for x in args.exclude_dirs.split(",") if x.strip()}

    # 解析用户指定的排除文件列表
    raw_ex_files = [x.strip() for x in args.exclude_files.split(",") if x.strip()]
    exclude_filenames = {Path(x).name.lower() for x in raw_ex_files if ("/" not in x and "\\" not in x)}
    exclude_relpaths = {_norm_rel(Path(x)) for x in raw_ex_files if ("/" in x or "\\" in x)}

    # 自动排除脚本自身（避免默认 root="." 时把自己也写进输出）
    this_script = Path(__file__).resolve()
    this_script_rel = _norm_rel(this_script.relative_to(root)) if this_script.is_relative_to(root) else None

    py_files: list[Path] = []
    for p in root.rglob("*.py"):
        if not p.is_file():
            continue

        # 1) 排除目录（任意层级目录名命中就排除）
        if any(part in exclude_dirs for part in p.parts):
            continue

        # 2) 自动排除本脚本自身
        p_resolved = p.resolve()
        if p_resolved == this_script:
            continue

        # 3) 排除文件名（大小写不敏感）
        if p.name.lower() in exclude_filenames:
            continue

        # 4) 排除相对路径
        rel_norm = _norm_rel(p.relative_to(root))
        if rel_norm in exclude_relpaths:
            continue

        py_files.append(p)

    py_files.sort(key=lambda x: str(x).lower())

    total_lines_all = 0
    total_code_lines = 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as out:
        for idx, f in enumerate(py_files, start=1):
            rel = f.relative_to(root)

            content = f.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()

            total_lines_all += len(lines)
            total_code_lines += sum(0 if is_comment_or_blank(ln) else 1 for ln in lines)

            out.write(f"{idx}.{rel}\n")
            if lines:
                out.write("\n".join(lines) + "\n")
            out.write("\n")

    # 汇总只输出到控制台
    print(f"Written to: {out_path}")
    print("==== SUMMARY ====")
    print(f"Root: {root}")
    print(f"Python files: {len(py_files)}")
    print(f"Total lines (all): {total_lines_all}")
    print(f"Total code lines (non-blank & non-#comment): {total_code_lines}")

if __name__ == "__main__":
    main()
