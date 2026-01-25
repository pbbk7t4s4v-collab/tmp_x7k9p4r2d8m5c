#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manim代码规则化位置修改工具
根据拖动日志，直接在代码中追加.shift()调用来修改元素位置，无需调用LLM模型
"""

import re
import ast
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict


def reconstruct_play_statement(play_full_content: str, group_name: str, group_elements: List[str], indent: str) -> str:
    """
    智能重构 play 语句，拆分 Group 调用并保留所有原始动画类型和参数。
    """
    # 提取内部内容
    match = re.search(r'self\.play\s*\((.*)\)', play_full_content, re.DOTALL)
    if not match: return play_full_content
    
    play_inner = match.group(1)
    parts = []
    current_part = ""
    bracket_level = 0
    for char in play_inner:
        if char == ',' and bracket_level == 0:
            if current_part.strip(): parts.append(current_part.strip())
            current_part = ""
        else:
            current_part += char
            if char == '(': bracket_level += 1
            elif char == ')': bracket_level -= 1
    if current_part.strip(): parts.append(current_part.strip())
    
    element_to_call = {}
    group_to_call = {}
    config_parts = []
    kwarg_pattern = r'^\s*\w+\s*='
    
    for p in parts:
        if re.match(kwarg_pattern, p) and not ('(' in p and p.find('=') > p.find('(')):
            config_parts.append(p)
            continue
        
        # 识别被动画化的目标（支持 foo 或 foo_123）
        obj_match = re.search(r'\b(?:Write|FadeIn|Create|ShowCreation|GrowFromCenter|GrowFromPoint|AnimationGroup)\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)', p)
        if obj_match:
            obj_name = obj_match.group(1)
            if obj_name == group_name:
                group_to_call[obj_name] = p
            else:
                element_to_call[obj_name] = p
        else:
            config_parts.append(p)

    # 如果 play 中根本没引用这个 Group，原样返回
    if group_name not in group_to_call and not re.search(rf'\b{re.escape(group_name)}\b', play_inner):
        return play_full_content

    # 执行重组
    final_parts = []
    processed_elements = set()
    
    # 1. 保留原本就有的独立调用（这保证了如 GrowFromCenter(title_line, ...) 这种调用绝对不会被篡改）
    for obj_name, call_str in element_to_call.items():
        final_parts.append(call_str)
        processed_elements.add(obj_name)
    
    # 2. 只有当 Group 调用确实存在时，才将其拆分为成员调用
    if group_name in group_to_call:
        original_group_call = group_to_call[group_name]
        # 获取 Group 使用的动画类型（如 FadeIn）
        anim_type_match = re.match(r'^(\w+)', original_group_call)
        anim_type = anim_type_match.group(1) if anim_type_match else "Write"
        
        for elem in group_elements:
            if elem not in processed_elements:
                final_parts.append(f"{anim_type}({elem})")
                processed_elements.add(elem)
    
    # 3. 加上配置参数
    final_parts.extend(config_parts)
    
    # 4. 生成新语句
    play_indent = indent + "    "
    if len(final_parts) > 1:
        new_inner = "\n" + play_indent + (",\n" + play_indent).join(final_parts) + "\n" + indent
    else:
        new_inner = final_parts[0] if final_parts else ""
    
    return f"{indent}self.play({new_inner})"


def parse_drag_logs(drag_logs: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    解析拖动日志，按元素名称累加dx和dy
    
    Args:
        drag_logs: 拖动事件列表，每个事件包含 element_name/element_id, dx, dy
        
    Returns:
        字典：{element_name: {'dx': total_dx, 'dy': total_dy}}
    """
    element_moves = defaultdict(lambda: {'dx': 0.0, 'dy': 0.0})
    
    for log in drag_logs:
        if not isinstance(log, dict):
            continue
            
        element_name = log.get('element_name') or ''
        element_id = log.get('element_id') or ''
        dx = float(log.get('dx', 0))
        dy = float(log.get('dy', 0))
        
        # 优先使用element_name，如果为空则尝试从element_id推断
        key = element_name if element_name else element_id
        
        if key:
            element_moves[key]['dx'] += dx
            element_moves[key]['dy'] += dy
    
    return dict(element_moves)


def find_position_method_chains(code: str, element_name: str) -> List[Tuple[int, str]]:
    """
    在代码中查找指定元素的所有位置设置方法链
    
    Args:
        code: Manim代码
        element_name: 元素变量名
        
    Returns:
        [(行号, 完整的方法链代码), ...]
    """
    lines = code.split('\n')
    patterns = [
        # 匹配：var_name.to_edge(...)
        # 匹配：var_name.next_to(...)
        # 匹配：var_name.move_to(...)
        # 匹配：var_name.shift(...)
        # 匹配：var_name.to_corner(...)
        # 匹配：var_name.center()
        # 匹配：var_name.align_to(...)
        # 可能包含方法链，如：var_name.to_edge(LEFT, buff=1.5).shift(UP * 0.5)
        rf'\b{re.escape(element_name)}\s*\.(?:to_edge|next_to|move_to|shift|to_corner|center|align_to|to_edge_vect|arrange)'
    ]
    
    results = []
    
    for i, line in enumerate(lines):
        # 查找包含元素名称的位置设置行
        for pattern in patterns:
            if re.search(pattern, line):
                # 尝试提取完整的方法链（可能跨多行）
                method_chain = _extract_method_chain(lines, i, element_name)
                if method_chain:
                    results.append((i, method_chain))
                    break  # 找到一行就够了，避免重复
    
    return results


def _extract_method_chain(lines: List[str], start_line: int, var_name: str) -> Optional[str]:
    """
    从指定行开始提取完整的方法链（支持多行）
    
    Args:
        lines: 代码行列表
        start_line: 起始行号（0-based）
        var_name: 变量名
        
    Returns:
        完整的方法链代码，如果没有找到则返回None
    """
    if start_line >= len(lines):
        return None
    
    line = lines[start_line]
    
    # 检查是否包含该变量的位置设置方法
    if not re.search(rf'\b{re.escape(var_name)}\s*\.(?:to_edge|next_to|move_to|shift|to_corner|center|align_to|to_edge_vect|arrange)', line):
        return None
    
    # 查找变量名在行中的位置
    var_match = re.search(rf'\b{re.escape(var_name)}\s*\.', line)
    if not var_match:
        return None
    
    start_pos = var_match.start()
    
    # 从变量名开始，提取到行末或分号
    current_line = start_line
    current_pos = start_pos
    method_chain = ""
    paren_count = 0
    bracket_count = 0
    brace_count = 0
    in_string = False
    string_char = None
    
    while current_line < len(lines):
        line_content = lines[current_line]
        
        # 处理多行字符串和括号匹配
        i = current_pos if current_line == start_line else 0
        
        while i < len(line_content):
            char = line_content[i]
            
            # 处理字符串
            if char in ('"', "'") and (i == 0 or line_content[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
            
            if not in_string:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                elif char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
            
            method_chain += char
            
            # 如果所有括号都闭合了，且不在字符串中，检查是否可以结束
            if not in_string and paren_count == 0 and bracket_count == 0 and brace_count == 0:
                # 检查后续是否有方法链继续（.method(...)）
                remaining = line_content[i+1:].strip()
                if remaining and remaining[0] == '.':
                    # 还有方法链继续，继续处理
                    i += 1
                    continue
                else:
                    # 方法链结束
                    # 移除行尾的注释和空白
                    method_chain = method_chain.rstrip()
                    return method_chain.strip()
            
            i += 1
        
        # 如果当前行处理完了但括号还没闭合，继续下一行
        if paren_count > 0 or bracket_count > 0 or brace_count > 0 or in_string:
            method_chain += '\n'
            current_line += 1
            current_pos = 0
        else:
            break
    
    # 如果循环结束，返回已提取的部分
    return method_chain.strip() if method_chain.strip() else None


def add_shift_to_method_chain(method_chain: str, dx: float, dy: float) -> str:
    """
    在方法链末尾追加.shift()调用（直接追加，不合并已有的shift）
    
    根据实际修改模式，即使已有.shift()调用，也直接追加新的.shift()
    
    Args:
        method_chain: 原始方法链
        dx: 水平偏移（向右为正）
        dy: 垂直偏移（向上为正）
        
    Returns:
        追加了.shift()的新方法链
    """
    if not method_chain:
        return method_chain
    
    # 构建shift表达式
    shift_parts = []
    if abs(dx) > 1e-10:  # 避免非常小的值
        if dx > 0:
            shift_parts.append(f"RIGHT * {dx}")
        else:
            shift_parts.append(f"LEFT * {abs(dx)}")
    
    if abs(dy) > 1e-10:
        if dy > 0:
            shift_parts.append(f"UP * {dy}")
        else:
            shift_parts.append(f"DOWN * {abs(dy)}")
    
    if not shift_parts:
        return method_chain  # 没有偏移，返回原链
    
    # 组合shift表达式
    shift_expr = " + ".join(shift_parts) if len(shift_parts) > 1 else shift_parts[0]
    
    # 直接追加新的.shift()调用（不合并已有的shift）
    # 移除末尾的空白和注释
    clean_chain = method_chain.rstrip()
    return f"{clean_chain}.shift({shift_expr})"


def _merge_shift_calls(method_chain: str, dx: float, dy: float) -> str:
    """
    合并现有的.shift()调用和新的偏移
    
    Args:
        method_chain: 包含已有.shift()的方法链
        dx: 新的水平偏移
        dy: 新的垂直偏移
        
    Returns:
        合并后的方法链
    """
    # 查找最后一个.shift(...)调用
    shift_pattern = r'\.shift\s*\(([^)]+)\)'
    matches = list(re.finditer(shift_pattern, method_chain))
    
    if not matches:
        # 没找到，直接追加
        return add_shift_to_method_chain(method_chain, dx, dy)
    
    # 获取最后一个匹配
    last_match = matches[-1]
    shift_content = last_match.group(1)
    
    # 解析现有的shift内容，提取dx和dy
    existing_dx, existing_dy = _parse_shift_expression(shift_content)
    
    # 累加偏移
    total_dx = existing_dx + dx
    total_dy = existing_dy + dy
    
    # 构建新的shift表达式
    shift_parts = []
    if abs(total_dx) > 1e-10:
        if total_dx > 0:
            shift_parts.append(f"RIGHT * {total_dx}")
        else:
            shift_parts.append(f"LEFT * {abs(total_dx)}")
    
    if abs(total_dy) > 1e-10:
        if total_dy > 0:
            shift_parts.append(f"UP * {total_dy}")
        else:
            shift_parts.append(f"DOWN * {abs(total_dy)}")
    
    if not shift_parts:
        # 偏移为0，移除shift调用
        new_method_chain = method_chain[:last_match.start()] + method_chain[last_match.end():]
        return new_method_chain.rstrip()
    
    shift_expr = " + ".join(shift_parts) if len(shift_parts) > 1 else shift_parts[0]
    
    # 替换最后一个shift调用
    new_method_chain = (
        method_chain[:last_match.start()] +
        f".shift({shift_expr})" +
        method_chain[last_match.end():]
    )
    
    return new_method_chain.rstrip()


def _parse_shift_expression(expr: str) -> Tuple[float, float]:
    """
    解析shift表达式，提取dx和dy
    
    例如：
    "RIGHT * 1.5 + UP * 2.0" -> (1.5, 2.0)
    "LEFT * 0.5 + DOWN * 1.0" -> (-0.5, -1.0)
    
    Args:
        expr: shift表达式字符串
        
    Returns:
        (dx, dy) 元组
    """
    dx, dy = 0.0, 0.0
    
    # 使用正则表达式匹配 RIGHT/LEFT * value 和 UP/DOWN * value
    # 支持 + 和 - 连接
    
    # 匹配 RIGHT/LEFT * number 或 number * RIGHT/LEFT
    right_left_pattern = r'(?:RIGHT\s*\*\s*([+-]?\d*\.?\d+)|([+-]?\d*\.?\d+)\s*\*\s*RIGHT|LEFT\s*\*\s*([+-]?\d*\.?\d+)|([+-]?\d*\.?\d+)\s*\*\s*LEFT)'
    up_down_pattern = r'(?:UP\s*\*\s*([+-]?\d*\.?\d+)|([+-]?\d*\.?\d+)\s*\*\s*UP|DOWN\s*\*\s*([+-]?\d*\.?\d+)|([+-]?\d*\.?\d+)\s*\*\s*DOWN)'
    
    for match in re.finditer(right_left_pattern, expr):
        groups = match.groups()
        if groups[0] or groups[1]:  # RIGHT * value 或 value * RIGHT
            value = float(groups[0] or groups[1])
            dx += value
        elif groups[2] or groups[3]:  # LEFT * value 或 value * LEFT
            value = float(groups[2] or groups[3])
            dx -= value
    
    for match in re.finditer(up_down_pattern, expr):
        groups = match.groups()
        if groups[0] or groups[1]:  # UP * value 或 value * UP
            value = float(groups[0] or groups[1])
            dy += value
        elif groups[2] or groups[3]:  # DOWN * value 或 value * DOWN
            value = float(groups[2] or groups[3])
            dy -= value
    
    return dx, dy


def extract_group_elements(code: str, group_line_idx: int) -> List[str]:
    """
    从VGroup定义中提取所有元素名称
    严格过滤方法名和常量
    
    Args:
        code: Manim代码
        group_line_idx: Group定义行的行号
        
    Returns:
        元素名称列表
    """
    lines = code.split('\n')
    if group_line_idx >= len(lines):
        return []
    
    group_line = lines[group_line_idx]
    
    # 匹配 Group定义行
    pattern = rf'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*(?:VGroup|Group|MGroup|VMobject)\s*\('
    if not re.search(pattern, group_line):
        return []
    
    # 提取括号内的内容（支持多行）
    paren_start = group_line.find('(')
    if paren_start < 0:
        return []
    
    # 收集括号内的所有内容
    paren_count = 1
    content_lines = [group_line[paren_start + 1:]]
    current_line = group_line_idx + 1
    
    # 如果第一行没有闭合括号，继续查找
    if ')' not in group_line[paren_start:]:
        while current_line < len(lines) and paren_count > 0:
            line = lines[current_line]
            content_lines.append(line)
            paren_count += line.count('(') - line.count(')')
            if paren_count <= 0:
                break
            current_line += 1
    
    # 合并所有内容
    params_content = '\n'.join(content_lines)
    
    # 移除最后一个闭合括号
    if params_content.rstrip().endswith(')'):
        params_content = params_content[:params_content.rfind(')')]
    
    # 按逗号拆分参数，但要避开嵌套括号和方法调用
    parts = []
    current_part = ""
    paren_level = 0
    for char in params_content:
        if char == ',' and paren_level == 0:
            parts.append(current_part.strip())
            current_part = ""
        else:
            current_part += char
            if char == '(':
                paren_level += 1
            elif char == ')':
                paren_level -= 1
    
    if current_part.strip():
        parts.append(current_part.strip())
    
    # 过滤非法元素
    manim_constants = {
        'UP', 'DOWN', 'LEFT', 'RIGHT', 'ORIGIN', 'OUT', 'IN',
        'UL', 'UR', 'DL', 'DR', 'TOP', 'BOTTOM', 'CENTER',
        'WHITE', 'BLACK', 'BLUE', 'RED', 'GREEN', 'YELLOW', 'ORANGE', 'TEAL',
        'arrange', 'aligned_edge', 'buff'
    }
    python_keywords = {
        'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is', 'if', 
        'else', 'for', 'while', 'lambda', 'def', 'class', 'import', 'from'
    }
    
    valid_elements = []
    for part in parts:
        part = part.strip()
        # 跳过关键字参数（包含=号的参数）
        if '=' in part:
            continue
        
        # 跳过包含方法调用的部分（如 .arrange(...)）
        if '.' in part and '(' in part:
            continue
        
        # 提取第一个单词作为变量名
        match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)', part)
        if match:
            var = match.group(1)
            if var not in manim_constants and var not in python_keywords:
                valid_elements.append(var)
    
    return valid_elements


def find_element_in_groups(code: str, element_name: str) -> List[Tuple[int, str, str]]:
    """
    查找元素是否在Group中，以及它在哪个Group中
    支持多行VGroup定义
    
    Args:
        code: Manim代码
        element_name: 元素变量名
        
    Returns:
        [(行号, Group变量名, Group类名), ...] 如果元素不在Group中，返回空列表
    """
    lines = code.split('\n')
    results = []
    
    escaped_var = re.escape(element_name)
    
    # 匹配 Group/VGroup/... 创建语句，支持多行
    # 单行: group = VGroup(elem1, elem2, elem3)
    # 多行: group = VGroup(
    #           elem1,
    #           elem2
    #       )
    pattern = rf'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(VGroup|Group|MGroup|VMobject)\s*\('
    
    for i, line in enumerate(lines):
        match = re.search(pattern, line)
        if match:
            group_name = match.group(1)
            group_class = match.group(2)
            
            # 【关键修复】排除元素本身就是Group变量名的情况
            if group_name == element_name:
                continue  # 跳过，因为元素就是Group本身，不需要从Group中移除
            
            # 检查是否在同一行闭合
            if ')' in line:
                # 单行定义，检查是否包含目标元素作为参数
                # 需要确保元素出现在括号内的参数列表中，而不是作为变量名
                # 提取括号内的内容
                paren_match = re.search(r'\((.*)\)', line)
                if paren_match:
                    params_str = paren_match.group(1)
                    # 检查元素名是否在参数中（作为独立的标识符）
                    if re.search(rf'\b{escaped_var}\b', params_str):
                        results.append((i, group_name, group_class))
            else:
                # 多行定义，查找后续行直到找到闭合括号
                paren_count = line.count('(') - line.count(')')
                j = i + 1
                found_element = False
                
                # 提取第一行中括号后的内容
                paren_start = line.find('(')
                if paren_start >= 0:
                    first_line_params = line[paren_start + 1:]
                    if re.search(rf'\b{escaped_var}\b', first_line_params):
                        found_element = True
                
                # 查找后续行
                while j < len(lines) and paren_count > 0:
                    next_line = lines[j]
                    # 检查这一行是否包含元素（在参数中）
                    if not found_element:
                        # 检查是否在参数部分（排除注释）
                        comment_pos = next_line.find('#')
                        line_content = next_line[:comment_pos] if comment_pos >= 0 else next_line
                        if re.search(rf'\b{escaped_var}\b', line_content):
                            found_element = True
                    
                    paren_count += next_line.count('(') - next_line.count(')')
                    j += 1
                
                if found_element:
                    results.append((i, group_name, group_class))
    
    return results


def find_play_statements(code: str, element_name: str) -> List[Tuple[int, str]]:
    """
    查找包含该元素的play语句
    
    Args:
        code: Manim代码
        element_name: 元素变量名
        
    Returns:
        [(行号, play语句所在行), ...]
    """
    lines = code.split('\n')
    results = []
    
    escaped_var = re.escape(element_name)
    
    # 匹配 self.play(...) 语句，包含该元素
    # 需要匹配多行的情况
    for i, line in enumerate(lines):
        if 'self.play(' in line:
            # 查找从这一行开始的play语句块
            play_lines = [line]
            line_idx = i
            paren_count = line.count('(') - line.count(')')
            
            while paren_count > 0 and line_idx + 1 < len(lines):
                line_idx += 1
                next_line = lines[line_idx]
                play_lines.append(next_line)
                paren_count += next_line.count('(') - next_line.count(')')
            
            play_block = '\n'.join(play_lines)
            
            # 检查是否包含该元素
            if re.search(rf'\b{escaped_var}\b', play_block):
                results.append((i, play_block))
    
    return results


def find_variable_definition_line(lines: List[str], var_name: str) -> int:
    """查找变量定义行"""
    pattern = rf'^\s*(?:self\.)?{re.escape(var_name)}\s*='
    for i, line in enumerate(lines):
        if re.search(pattern, line):
            return i
    return -1


def find_play_statements_after(lines: List[str], element_name: str, after_line: int) -> List[Tuple[int, str]]:
    """在指定行之后查找包含该元素的play语句"""
    results = []
    escaped_var = re.escape(element_name)
    
    for i, line in enumerate(lines):
        if i <= after_line:
            continue
        if 'self.play(' in line:
            # 查找从这一行开始的play语句块
            play_lines = [line]
            line_idx = i
            paren_count = line.count('(') - line.count(')')
            
            while paren_count > 0 and line_idx + 1 < len(lines):
                line_idx += 1
                next_line = lines[line_idx]
                play_lines.append(next_line)
                paren_count += next_line.count('(') - next_line.count(')')
            
            play_block = '\n'.join(play_lines)
            
            # 检查是否包含该元素
            if re.search(rf'\b{escaped_var}\b', play_block):
                results.append((i, play_block))
    return results


def modify_manim_code_rule_based(
    code: str, 
    drag_logs: List[Dict[str, Any]], 
    initial_positions: Optional[Dict[str, Dict[str, float]]] = None
) -> str:
    """
    基于规则的Manim代码位置修改函数 - 最终定位锚点逻辑
    """
    # 0. 预处理：彻底清除旧的锚点逻辑，确保从干净的代码开始
    # 移除所有标记为“物理锚点隔离”的行
    lines = [line for line in code.split('\n') if "# 物理锚点隔离" not in line and "跟随类占位符" not in line]
    code_cleaned = '\n'.join(lines)
    # 将所有的 xxx_init, xxx_init_init 还原为 xxx
    code_cleaned = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_]*)_init(_init)*\b', r'\1', code_cleaned)
    lines = code_cleaned.split('\n')

    # 1. 解析拖动日志
    element_moves = parse_drag_logs(drag_logs)
    if not element_moves:
        return code_cleaned
    
    # 2. 【锚点策略】物理隔离依赖 - 预处理定位最后一步动作
    pos_methods = "next_to|to_edge|to_corner|align_to|arrange|move_to|shift|center|to_edge_vect"
    link_ctors = "Arrow|Line|DoubleArrow"
    follow_ctors = "SurroundingRectangle|BackgroundRectangle|Brace|Underline"
    manim_constants = {'LEFT', 'RIGHT', 'UP', 'DOWN', 'ORIGIN', 'UL', 'UR', 'DL', 'DR', 'TOP', 'BOTTOM', 'CENTER', 'IN', 'OUT'}
    
    # 自动识别所有作为参考对象的变量
    referenced_vars = set()
    for line in lines:
        # 1. 布局方法引用
        for m in re.finditer(rf'\.({pos_methods})\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)', line):
            v = m.group(2)
            if v not in manim_constants and not v.isdigit() and not v.endswith('_init'): 
                referenced_vars.add(v)
        # 2. 构造函数引用（仅连接和跟随类）
        # 此时要支持识别 .become(Follower(...)) 形式中的目标
        for m in re.finditer(rf'\b({link_ctors}|{follow_ctors})\s*\((.*?)\)', line):
            content = m.group(2)
            for p in re.split(r',', content):
                if '=' in p and '==' not in p: continue
                v_match = re.search(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', p)
                if v_match:
                    v = v_match.group(1)
                    if v not in manim_constants and v not in ["VGroup", "Group", "MathTex", "Text", "Tex", "VMobject"] and not v.isdigit() and not v.endswith('_init'): 
                        referenced_vars.add(v)

    # 第一步：计算每个参考变量的“最后动作行”
    # ... (此处逻辑不变)
    var_anchor_points = {} # var -> line_idx
    for v in referenced_vars:
        def_idx = find_variable_definition_line(lines, v)
        if def_idx == -1: continue
        last_action_idx = def_idx
        first_ref_idx = len(lines)
        for i, line in enumerate(lines):
            if i <= def_idx: continue
            if re.search(rf'\.({pos_methods})\s*\(\s*.*?{re.escape(v)}', line) or \
               re.search(rf'\b({link_ctors}|{follow_ctors})\s*\(.*?{re.escape(v)}', line):
                first_ref_idx = i
                break
        for i in range(def_idx, first_ref_idx):
            if re.search(rf'\b{re.escape(v)}\s*\.(?:{pos_methods})\b', lines[i]):
                last_action_idx = i
        var_anchor_points[v] = last_action_idx

    # 第二步：构建新代码，在动作行结束后插入锚点
    new_lines = []
    created_anchors = set()
    paren_level = 0
    pending_anchors = defaultdict(list)

    for i, line in enumerate(lines):
        new_lines.append(line)
        current_paren_diff = (line.count('(') - line.count(')')) + \
                             (line.count('[') - line.count(']')) + \
                             (line.count('{') - line.count('}'))
        for v, anchor_idx in var_anchor_points.items():
            if i == anchor_idx: pending_anchors[anchor_idx].append(v)
        paren_level += current_paren_diff
        completed_vars = []
        for start_idx, vars_to_anchor in pending_anchors.items():
            if i >= start_idx and paren_level == 0:
                for v in vars_to_anchor:
                    indent = re.match(r'^(\s*)', lines[start_idx]).group(1)
                    # 【核心修复】移除 .set_opacity(0).set_z_index(-1000)
                    # 因为：1. .copy() 产生的对象默认不加入场景，本就是不可见的
                    # 2. 变量可能是 numpy 坐标数组，不支持 set_opacity，会导致报错
                    new_lines.append(f"{indent}{v}_init = {v}.copy() # 物理锚点隔离")
                    created_anchors.add(v)
                completed_vars.append(start_idx)
        for idx in completed_vars: del pending_anchors[idx]

    # 第三步：全局替换引用 (精准隔离逻辑)
    preprocessed_lines = []
    follower_updates = {} # var -> {'ctor_call': str, 'indent': str}
    
    for i, line in enumerate(new_lines):
        if "# 物理锚点隔离" in line:
            preprocessed_lines.append(line)
            continue
            
        # 检测跟随类物体定义
        # 模式1: rect = SurroundingRectangle(...)
        follow_def_match = re.search(rf'^(\s*)(?:self\.)?([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*({follow_ctors})\s*\((.*?)\)', line)
        # 模式2: rect.become(SurroundingRectangle(...))  <-- 处理二次修改的关键
        become_match = re.search(rf'^(\s*)(?:self\.)?([a-zA-Z_][a-zA-Z0-9_]*)\.become\s*\(\s*({follow_ctors})\s*\((.*?)\)\s*\)', line)
        
        match = follow_def_match or become_match
        if match:
            indent, var_name, ctor, params = match.groups()
            # 提取参考的目标
            targets = set()
            for p in re.split(r',', params):
                if '=' in p and '==' not in p: continue
                v_m = re.search(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', p)
                if v_m:
                    v = v_m.group(1)
                    if v not in manim_constants and v not in ["VMobject", "VGroup", "Group"] and not v.isdigit(): 
                        targets.add(v)
            
            # 【核心修复】只要识别到跟随类物体（无论是首次定义还是 become 更新），
            # 都统一将其转换为“占位符 + 延迟更新”模式。
            # 这样可以确保：1. 变量定义始终存在（防止 NameError）；2. 始终在动画前捕获最新位置。
            follower_updates[var_name] = {'ctor_call': f"{ctor}({params})", 'indent': indent}
            preprocessed_lines.append(f"{indent}{var_name} = VMobject() # 跟随类占位符")
            continue

        mod_line = line
        for v in created_anchors:
            mod_line = re.sub(rf'(\.({pos_methods})\s*\(\s*.*?)\b{v}\b(?!\s*=)', rf'\1{v}_init', mod_line)
        preprocessed_lines.append(mod_line)
    
    lines = preprocessed_lines

    # 3. 收集所有修改计划
    all_insertions = []  # [(line_idx, content)]
    play_modifications = {}  # {line_idx: new_content}
    
    # 记录每个play语句涉及的Group及其要移除的元素
    play_group_removals = defaultdict(lambda: defaultdict(set))

    # 更新逻辑：在 follower 第一次被播放前，使用 become() 更新其形态和位置
    for f_var, info in follower_updates.items():
        # 查找该 follower 及其所属 Group 第一次被 play 的地方
        # 这里的 find_play_statements 也会检查包含该变量的 VGroup
        plays = find_play_statements("\n".join(lines), f_var)
        if plays:
            first_play_idx = plays[0][0]
            # 在 play 之前注入 become 语句，确保其捕获了 target 移动后的最新位置
            all_insertions.append((first_play_idx, f"{info['indent']}{f_var}.become({info['ctor_call']})"))

    for element_key, moves in element_moves.items():
        dx, dy = moves['dx'], moves['dy']
        if abs(dx) < 1e-10 and abs(dy) < 1e-10:
            continue
            
        candidate_names = [element_key]
        base_name_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)', element_key)
        if base_name_match:
            candidate_names.append(base_name_match.group(1))
        candidate_names = list(dict.fromkeys(candidate_names))
        
        # 查找变量定义行，确保插入在定义之后
        def_line_idx = -1
        for name in candidate_names:
            def_line_idx = find_variable_definition_line(lines, name)
            if def_line_idx != -1:
                break
        
        # 查找该元素的第一个play语句（必须在定义之后）
        play_info = None
        for name in candidate_names:
            plays = find_play_statements_after(lines, name, def_line_idx)
            if plays:
                play_info = plays[0]
                break
        
        # 检查是否在Group中
        element_in_group = False
        group_info = None
        for name in candidate_names:
            groups = find_element_in_groups('\n'.join(lines), name)
            if groups:
                # 检查Group定义是否也在定义之后，且在play之前
                group_info = groups[0]
                if not play_info:
                    # 如果没找到元素的play，找Group的play
                    g_plays = find_play_statements_after(lines, group_info[1], group_info[0])
                    if g_plays:
                        play_info = g_plays[0]
                element_in_group = True
                break

        if not play_info:
            continue

        play_line_idx, play_block = play_info
        indent = re.match(r'^(\s*)', lines[play_line_idx]).group(1) if re.match(r'^(\s*)', lines[play_line_idx]) else "        "
        
        # 构建shift调用
        shift_parts = []
        if abs(dx) > 1e-10:
            shift_parts.append(f"RIGHT * {dx}" if dx > 0 else f"LEFT * {abs(dx)}")
        if abs(dy) > 1e-10:
            shift_parts.append(f"UP * {dy}" if dy > 0 else f"DOWN * {abs(dy)}")
        shift_expr = " + ".join(shift_parts)
        shift_call = f"{candidate_names[0]}.shift({shift_expr})"
        
        if element_in_group and group_info:
            group_name = group_info[1]
            # 记录移除计划
            play_group_removals[play_line_idx][group_name].add(candidate_names[0])
            # 插入remove和shift
            all_insertions.append((play_line_idx, f"{indent}{group_name}.remove({candidate_names[0]})"))
            all_insertions.append((play_line_idx, f"{indent}{shift_call}"))
        else:
            # 直接插入shift
            all_insertions.append((play_line_idx, f"{indent}{shift_call}"))

    # 4. 统一处理 play 语句重构（处理 Group 拆分和空检查）
    for play_idx, group_map in play_group_removals.items():
        indent = re.match(r'^(\s*)', lines[play_idx]).group(1) if re.match(r'^(\s*)', lines[play_idx]) else "        "
        
        # 获取完整的 play 块
        paren_count = lines[play_idx].count('(') - lines[play_idx].count(')')
        end_idx = play_idx
        while paren_count > 0 and end_idx + 1 < len(lines):
            end_idx += 1
            paren_count += lines[end_idx].count('(') - lines[end_idx].count(')')
        
        current_play_content = '\n'.join(lines[play_idx:end_idx+1])
        
        for group_name, removed_elems in group_map.items():
            # 获取该 Group 的所有原始元素
            group_def_idx = -1
            for i, line in enumerate(lines):
                if re.search(rf'^\s*{re.escape(group_name)}\s*=\s*(?:VGroup|Group|MGroup|VMobject)\s*\(', line):
                    group_def_idx = i
                    break
            
            if group_def_idx != -1:
                all_group_elements = extract_group_elements('\n'.join(lines), group_def_idx)
                
                # 检查是否全部移除（空检查）
                if set(all_group_elements).issubset(removed_elems):
                    # 全部移除，彻底拆分 Group 动画
                    current_play_content = reconstruct_play_statement(current_play_content, group_name, all_group_elements, indent)
                else:
                    # 部分移除，不仅要保留 Group 动画，还要显式添加被移出元素的动画
                    # 调用 reconstruct_play_statement，它会将 group 动画转为成员动画
                    current_play_content = reconstruct_play_statement(current_play_content, group_name, all_group_elements, indent)
        
        play_modifications[play_idx] = current_play_content

    # 5. 执行修改
    # 首先处理 play 语句替换
    for idx in sorted(play_modifications.keys(), reverse=True):
        new_content = play_modifications[idx]
        paren_count = lines[idx].count('(') - lines[idx].count(')')
        curr = idx
        while paren_count > 0 and curr + 1 < len(lines):
            curr += 1
            paren_count += lines[curr].count('(') - lines[curr].count(')')
        lines[idx:curr+1] = new_content.split('\n')
    
    # 然后处理插入
    for idx, content in sorted(all_insertions, key=lambda x: x[0], reverse=True):
        lines.insert(idx, content)

    return '\n'.join(lines)


def modify_manim_code_with_layout_changes(
    code_content: str,
    drag_logs: List[Dict[str, Any]],
    initial_positions: Optional[Dict[str, Dict[str, float]]] = None
) -> str:
    """
    主函数：根据布局拖动日志修改Manim代码
    """
    return modify_manim_code_rule_based(code_content, drag_logs, initial_positions)


if __name__ == "__main__":
    # 测试代码
    test_code = """
img1 = ImageMobject("/path/to/image.png")
img1.height = 3.0
img1.to_edge(LEFT, buff=1.5).shift(UP * 0.5)

label1 = Text("标签")
label1.next_to(img1, UP, buff=0.2)
"""
    
    test_logs = [
        {"element_name": "img1", "dx": -1.5, "dy": -3.0},
        {"element_name": "label1", "dx": -1.03, "dy": -1.84}
    ]
    
    result = modify_manim_code_rule_based(test_code, test_logs)
    print("原始代码:")
    print(test_code)
    print("\n修改后代码:")
    print(result)
