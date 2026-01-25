#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
outline_check.py

功能：
- 读取一个待评测的课程大纲（txt / md 皆可，本质就是纯文本）
- 读取一个用于「语义自包含 + 逻辑关系」检查的中文 prompt
- 调用 LLM，请它对「当前大纲」做一次结构与语义检查
  - 核心关注两点：
    1）每一章及子节之间是否语义自包含
    2）章节之间、知识点之间的逻辑顺序是否合理
- 如果大纲整体合理，模型应返回类似「结构合理，无建议。」
- 如果有问题，返回 1–3 句简短修改建议
- 打印到标准输出，方便上层流程直接展示给用户

依赖：
- pool.py 和 providers.py
"""

import argparse
import asyncio
from pathlib import Path

from pool import load_keypool_from_config
from providers import ProviderAdapter


def _clean_llm_text(s: str) -> str:
    """
    万一模型用 ``` 包裹了一层，这里简单剥一下。
    期望输出是一小段自然语言，而不是 code block / json。
    """
    s = s.strip()
    if s.startswith("```"):
        s = s.lstrip("`").rstrip("`").strip()
        # 有的模型会写 ```json ...```，这里也顺手去掉前缀
        if s.lower().startswith("json"):
            s = s[4:].strip()
    return s


async def semantic_check_once(
    outline_text: str,
    model: str,
    prompt_path: Path,
    config_path: str,
) -> str:
    """
    调用 LLM 做一次「大纲语义与逻辑检查」。
    - outline_text：用户输入的大纲（txt 格式原文）
    - model：模型名称
    - prompt_path：中文说明 prompt 的路径
    - config_path：key 池配置文件路径
    返回值为一小段自然语言建议（或“结构合理，无建议。”）。
    """
    if not prompt_path.exists():
        raise FileNotFoundError(f"找不到大纲校验用的 prompt 文件: {prompt_path}")

    system_prompt = prompt_path.read_text(encoding="utf-8")

    # 初始化 key pool 和 provider
    key_pool = load_keypool_from_config(config_path)
    if not key_pool.have_live_key():
        raise RuntimeError("config_pool.json 中没有可用的 key，请先配置。")

    provider = ProviderAdapter(key_pool)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": outline_text},
    ]

    resp = await provider.chat(messages=messages, model=model)
    await provider.aclose()

    cleaned = _clean_llm_text(resp)
    return cleaned


async def main_async(args):
    txt_path = Path(args.outline_path)
    if not txt_path.exists():
        raise FileNotFoundError(f"找不到要检查的大纲 txt 文件: {txt_path}")

    outline_text = txt_path.read_text(encoding="utf-8")

    try:
        suggestion = await semantic_check_once(
            outline_text=outline_text,
            model=args.model,
            prompt_path=Path(args.prompt),
            config_path=args.config,
        )
        ok = True
        error_msg = ""
    except Exception as e:
        suggestion = ""
        ok = False
        error_msg = str(e)
    if getattr(args, "out_suggestion", None):
        out_dir = Path(args.out_suggestion)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = txt_path.parent

    output_path = out_dir / (txt_path.stem + "_suggestion.txt")

    if ok:
        output_path.write_text(suggestion, encoding="utf-8")
    else:
        output_path.write_text(f"调用失败：{error_msg}", encoding="utf-8")


    return ok


def main():
    ap = argparse.ArgumentParser("TeachMaster 课程大纲校验")
    ap.add_argument(
        "--outline_path",
        required=True,
        help="要检查的课程大纲 txt 文件路径（或任何纯文本大纲）",
    )
    ap.add_argument(
        "--prompt",
        default="/home/TeachMasterAppV2/backend/prompt_templates/Outline_Check.txt",
        help="用于说明检查规则的中文 prompt 文件路径",
    )
    ap.add_argument(
        "--config",
        default="config_pool.json",
        help="key 池配置文件路径（例如 config_pool.json）",
    )
    ap.add_argument(
        "--model",
        default="gpt-5-chat-2025-08-07",
        help="模型名称，例如 gpt-5-chat-2025-08-07",
    )
    ap.add_argument(
        "--out_suggestion",
        default=None,
        help="可选，指定输出建议文件的路径；若不提供则默认写在同目录下 *_suggestion.txt"
    )
    args = ap.parse_args()

    ok = asyncio.run(main_async(args))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
