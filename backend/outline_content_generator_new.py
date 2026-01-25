#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于现有大纲生成详细内容（鲁棒动态层级版）
改进点：
1) 自动选择“生成对象层级”：优先 H2；无 H2 则用 H3；再无则用 H4...直到 H6
2) 为每个目标标题，收集其“下一层及更深层”的完整子结构（任意深度），并传给 LLM
3) 要求 LLM 严格按照传入结构来组织内容（不会硬编码成“四级标题列表”）
4) 其它流程与原来一致：读取 → 解析 → 生成 → 插入 → 写回
"""

import re
import os
import argparse
from typing import List, Tuple, Dict, Any

from llm_api import process_text

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("注意：未安装tqdm包，将使用简单进度显示")


Heading = Tuple[int, str, int]  # (level, title, line_number)

def normalize_heading_levels(md: str, target_level: int) -> str:
    """
    将生成内容中的任何“过浅”标题（级别 <= target_level）下调到 target_level+1，
    防止 LLM 把子小节抬成与本节并列的标题。
    """
    out_lines = []
    for line in md.splitlines():
        stripped = line.lstrip()
        if stripped.startswith('#'):
            # 统计 # 个数
            n = 0
            for ch in stripped:
                if ch == '#':
                    n += 1
                else:
                    break
            if n <= target_level:
                # 统一下调到 target_level+1
                indent = line[:len(line) - len(stripped)]
                rest = stripped[n:].lstrip()
                line = f"{indent}{'#' * (target_level + 1)} {rest}"
        out_lines.append(line)
    return "\n".join(out_lines)

class OutlineContentGenerator:
    """大纲内容生成器（动态层级版）"""

    def __init__(self, config_path="config.json", verbose=True,
                 prompt_template="Section_Content_Generator_new.txt"):
        """初始化"""
        self.config_path = config_path
        self.verbose = verbose
        # 使用新的动态模板，路径仍为 ./prompt_templates/
        self.prompt_template = prompt_template

    # ----------------------------
    # 1) 解析所有标题
    # ----------------------------
    def parse_markdown_outline(self, content: str) -> List[Heading]:
        """
        解析 markdown，提取所有 # 开头的标题行
        Returns: [(level, title, line_number), ...]
        """
        lines = content.split('\n')
        structure: List[Heading] = []

        for i, line in enumerate(lines):
            s = line.lstrip()
            if s.startswith('#'):
                # 连续 # 的数量即 level
                level = 0
                for ch in s:
                    if ch == '#':
                        level += 1
                    else:
                        break
                title = s[level:].strip()
                if title and 1 <= level <= 6:
                    structure.append((level, title, i))

        return structure

    # ----------------------------
    # 2) 选择“生成对象”的目标层级
    # ----------------------------
    def choose_target_level(self, structure: List[Heading]) -> int:
        """
        目标：优先 H2，其次 H3...，找到首个存在的层级作为“生成对象层级”
        若整篇只有 H1，则退化为 H1（不太常见，但保证不报错）
        """
        levels_present = {lvl for (lvl, _, _) in structure}
        for lvl in range(1, 7):
            if lvl in levels_present:
                return lvl
        return 1 if 1 in levels_present else 2  # 兜底：若啥都没有（几乎不可能），按 H2

    # ----------------------------
    # 3) 基于目标层级，构建：路径 + 子树（任意深度）
    # ----------------------------
    def build_section_forest(self, structure: List[Heading], target_level: int) -> Dict[int, Tuple[str, str, List[Dict[str, Any]]]]:
        """
        为每个“目标层级”的标题，构建：
        { line_no_of_target: (path, title, subtree) }
        - path: "H1 > H2 > ... > H_(target-1)" 的路径（不含当前 target 标题）
        - title: 当前 target 标题文本
        - subtree: 该 target 标题下的所有更深层级的结构（任意深度），表示为节点列表：
            node = { "level": int, "title": str, "children": [node, ...] }
          其中 level 是“markdown 真实层级”（如 4、5、6）
        """
        # 先把结构按行号排序（已天然按行）
        structure_sorted = sorted(structure, key=lambda x: x[2])

        # 帮助：从当前位置向后，截取“属于当前 target 节”的所有 heading（直到遇到 <= target_level 的下一个标题）
        def slice_block(start_idx: int) -> List[Heading]:
            lvl, _, line_no = structure_sorted[start_idx]
            assert lvl == target_level
            block: List[Heading] = []
            i = start_idx + 1
            while i < len(structure_sorted):
                l, t, ln = structure_sorted[i]
                if l <= target_level:
                    break
                block.append(structure_sorted[i])
                i += 1
            return block

        # 把线性的 block（都是 >target_level 的标题）构造成树
        def build_tree_from_block(block: List[Heading]) -> List[Dict[str, Any]]:
            """
            用栈构建任意深度的树
            """
            forest: List[Dict[str, Any]] = []
            stack: List[Dict[str, Any]] = []  # 每个元素是节点引用，按照层级严格递增

            for (lvl, title, _) in block:
                node = {"level": lvl, "title": title, "children": []}
                # 弹出比当前层级 >= 的节点，直到栈顶比它浅
                while stack and stack[-1]["level"] >= lvl:
                    stack.pop()
                if not stack:
                    forest.append(node)
                else:
                    stack[-1]["children"].append(node)
                stack.append(node)
            return forest

        # 路径计算：从 start_idx 向上找祖先（level < target_level）
        def compute_path_prefix(start_idx: int) -> str:
            # 回看 start_idx 之前的 heading，找所有 level < target_level 的“最近一条链”
            path_parts: List[str] = []
            # 向后扫描到 start_idx，维护一个简易的祖先栈
            anc_stack: List[Tuple[int, str]] = []
            for i in range(0, start_idx + 1):
                lvl, title, _ = structure_sorted[i]
                if lvl < target_level:
                    # 清理掉 >= 当前 lvl 的
                    while anc_stack and anc_stack[-1][0] >= lvl:
                        anc_stack.pop()
                    anc_stack.append((lvl, title))
                elif lvl == target_level and i == start_idx:
                    # 到达目标时停止
                    break
            # anc_stack 即祖先链（按层级递增）
            path_parts = [t for (_, t) in anc_stack]
            return " > ".join(path_parts) if path_parts else ""

        # 主过程：遍历所有 target_level 的标题，构造 (path, title, subtree)
        result: Dict[int, Tuple[str, str, List[Dict[str, Any]]]] = {}
        for idx, (lvl, title, line_no) in enumerate(structure_sorted):
            if lvl != target_level:
                continue
            # 子块
            block = slice_block(idx)
            subtree = build_tree_from_block(block)
            path = compute_path_prefix(idx)
            result[line_no] = (path, title, subtree)

        return result

    # ----------------------------
    # 4) 把子树渲染为“提示 LLM 的结构文本”
    # ----------------------------
    def render_subtree_for_prompt(self, subtree: List[Dict[str, Any]]) -> str:
        """
        把任意深度子树渲染成“带 # 的结构清单”，示例（当 target 是 H3）：
        #### 四级标题1
        ##### 五级标题1
        #### 四级标题2
        注意：这里使用“markdown 真实层级”的 # 个数，保证 LLM 能按层级生成。
        """
        lines: List[str] = []

        def dfs(nodes: List[Dict[str, Any]]):
            for n in nodes:
                level = n["level"]
                title = n["title"]
                # 为避免 LLM 误解，这里明确地用 # 前缀表达层级
                prefix = "#" * level
                # 只输出 H4+，H3 及以上是否输出？——这里统一输出真实层级（> target 的都在 subtree 里）
                lines.append(f"{prefix} {title}")
                if n["children"]:
                    dfs(n["children"])

        dfs(subtree)
        return "\n".join(lines) if lines else "（无下级标题，请根据章节主题合理组织小节结构）"

    # ----------------------------
    # 5) 生成教学内容
    # ----------------------------
    def generate_section_content(self, course_topic: str, section_path: str,
                                 section_title: str, subtree: List[Dict[str, Any]],
                                 target_level: int) -> str:
        """
        构建 prompt 并调用 LLM 生成内容
        """
        prompt_template = self.load_prompt_template()

        child_structure_text = self.render_subtree_for_prompt(subtree)
        # 告知“允许的最大标题级别”，避免 LLM 乱用更高层级
        # 经验规则：输出内容的最大标题级别 = max( target_level+1, min_child_level )，上限不超过 6
        max_child_level = 6
        def find_min_child_level(nodes: List[Dict[str, Any]], cur_min=6) -> int:
            m = cur_min
            for n in nodes:
                m = min(m, n["level"])
                if n["children"]:
                    m = min(m, find_min_child_level(n["children"], m))
            return m
        if subtree:
            max_child_level = max(target_level + 1, find_min_child_level(subtree))
        else:
            max_child_level = min(6, target_level + 1)

        content_requirements = f"请为“{section_title}”生成详细教学内容，并严格按照下方结构组织。最大标题级别不应超过 H{max_child_level}。"

        prompt = prompt_template.format(
            course_topic=course_topic,
            section_path=(section_path + (" > " if section_path else "")) + section_title,
            child_structure=child_structure_text,
            content_requirements=content_requirements
        )

        content = process_text(prompt, self.config_path)
        return content

    def load_prompt_template(self) -> str:
        """加载 prompt 模板（仍位于 ./prompt_templates/ 下）"""
        template_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "prompt_templates",
            self.prompt_template
        )
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    # ----------------------------
    # 6) 把生成内容插入到 markdown
    # ----------------------------
    def insert_content_into_outline(self, content: str,
                                    section_forest: dict,
                                    course_topic: str, target_level: int,
                                    verbose=True, mode: str = "replace") -> str:
        """
        mode:
        - "append": 在目标标题后面直接追加生成内容（保留旧骨架）
        - "replace": 替换目标标题下的旧内容，直到遇到下一个 ≤ target_level 的标题
        """
        lines = content.split('\n')
        new_lines = []

        target_lines = sorted(section_forest.keys())
        target_set = set(target_lines)
        i = 0
        processed = 0

        pbar = tqdm(total=len(target_lines), desc="生成章节内容", unit="节") if (verbose and HAS_TQDM) else None

        while i < len(lines):
            line = lines[i]
            # 非目标标题：正常抄写
            if i not in target_set:
                new_lines.append(line)
                i += 1
                continue

            # 命中一个目标标题（行号 i）
            new_lines.append(line)  # 写回标题行
            path, section_title, subtree = section_forest[i]

            if verbose and not HAS_TQDM:
                full_path = path + (" > " if path else "") + section_title
                print(f"[{processed+1}/{len(target_lines)}] 生成：{full_path}")

            # 生成新的详细内容
            detailed = self.generate_section_content(
                course_topic, path, section_title, subtree, target_level
            ).strip()
            detailed = normalize_heading_levels(detailed, target_level)

            # 若是替换模式：先跳过旧内容（直到下一个 ≤ target_level 的标题）
            if mode == "replace":
                j = i + 1
                while j < len(lines):
                    nxt = lines[j].lstrip()
                    if nxt.startswith('#'):
                        lvl = 0
                        for ch in nxt:
                            if ch == '#':
                                lvl += 1
                            else:
                                break
                        if lvl <= target_level:
                            break
                    j += 1
                i = j  # 跳过旧内容
            else:
                i += 1  # 追加模式直接下一行

            # ★ 仅写入一次新内容（放在“跳过旧内容”之后）
            if detailed:
                new_lines.append("")
                new_lines.extend(detailed.split('\n'))
                new_lines.append("")

            processed += 1
            if pbar:
                pbar.update(1)

        if pbar:
            pbar.close()

        return "\n".join(new_lines)


    # ----------------------------
    # 7) 对外流程（与旧版 CLI 一致）
    # ----------------------------
    def process_outline_file(self, input_file, output_file=None, course_topic=None, verbose=True):
        """读取 → 解析 → 选择层级 → 构树 → 生成并插入 → 写回"""
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        if verbose:
            print(f"读取大纲文件：{input_file}")

        if not course_topic:
            course_topic = os.path.splitext(os.path.basename(input_file))[0]

        structure = self.parse_markdown_outline(content)
        if not structure:
            raise ValueError("未在文件中检测到任何标题（# / ## / ### / ...）。")

        target_level = self.choose_target_level(structure)
        section_forest = self.build_section_forest(structure, target_level)

        if verbose:
            print(f"本次生成对象层级：H{target_level}，共 {len(section_forest)} 个目标节点")

        updated = self.insert_content_into_outline(
            content, section_forest, course_topic, target_level, verbose
        )

        if not output_file:
            output_file = input_file

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(updated)

        if verbose:
            print(f"完整教学内容已保存到：{output_file}")

    # 兼容旧接口
    def pipeline(self, input_file, output_file=None, course_topic=None, verbose=True):
        self.process_outline_file(input_file, output_file, course_topic, verbose)
        return True

    # 保留：一句话导语流水线（可选）
    def pipeline_oneline_overview(self, input_file, output_file=None, course_topic=None, verbose=True):
        """
        如需“替换为一句导语”，可以复用 build_section_forest，渲染结构后让模板只输出一句话。
        这里为简洁起见不展开，保持接口占位。
        """
        raise NotImplementedError("请为导语模式准备一个只输出一句话的模板，并在此实现。")


def main():
    """主函数（参数与原脚本保持一致）"""
    parser = argparse.ArgumentParser(
        description="基于现有大纲生成详细教学内容（动态层级版）",
        epilog="示例: python outline_content_generator.py outline/Regression.md"
    )
    parser.add_argument("input_file", help="输入的大纲markdown文件路径")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径（默认覆盖原文件）")
    parser.add_argument("--topic", type=str, default=None, help="课程主题（默认使用文件名）")
    parser.add_argument("--config", type=str, default="config.json", help="配置文件路径（默认：config.json）")
    parser.add_argument("--quiet", action="store_true", help="静默模式，不显示过程信息")

    args = parser.parse_args()

    try:
        if not os.path.exists(args.input_file):
            print(f"错误：文件 {args.input_file} 不存在")
            return

        generator = OutlineContentGenerator(config_path=args.config)
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
        print("4. 输入的 markdown 文件格式正确（存在至少一个标题）")


if __name__ == "__main__":
    main()
