#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, sys, json, subprocess, pathlib, argparse
from typing import Tuple, Optional
from openai import OpenAI  # pip install openai>=1.40.0
#注意需要在/home/EduAgent/miniconda3/envs/manim_env下运行，因为那里manim版本是渲染的时候的版本，修复的时候也要确认manim版本
RETRY_MAX = 3
MODEL = "gpt-5"
RENDER_TIMEOUT = 180  # 秒
SCENE = None  # None则渲染文件内所有Scene
MANIM_QUALITY = "l"  # ex: -qk (高清), -qm (中), -ql (低)
VIDEO_FORMAT = "mp4"
MAX_LINES = 30  #保留行数

#注意要在同一目录下面放config.json(被修复的文件夹里不要缺背景图)
config_path = pathlib.Path("config.json")
if config_path.exists():
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    model=cfg.get("debug_settings", {}).get("model", MODEL)
    api_key = cfg.get("llm_key")
    base_url = cfg.get("debug_settings", {}).get("base_url")
    retry_max = cfg.get("debug_settings", {}).get("max_retries", RETRY_MAX)
    client = OpenAI(api_key=api_key, base_url=base_url)
else:
    client = OpenAI()

def run_manim(py_path: str, scene: Optional[str], media_dir: Optional[str] = None) -> Tuple[bool, str]:
    cmd = ["manim", f"-q{MANIM_QUALITY}", py_path]
    if scene:
        cmd.append(scene)
    cmd += ["--format", VIDEO_FORMAT]
    if media_dir:
        cmd += ["--media_dir", str(media_dir)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=RENDER_TIMEOUT)
        ok = (p.returncode == 0)
        out = (p.stdout or "") + "\n" + (p.stderr or "")
        lines = out.splitlines()
        if len(lines) > MAX_LINES:
            out = "\n".join(lines[-MAX_LINES:])
        return ok, out
    except subprocess.TimeoutExpired as e:
        return False, f"[TIMEOUT] {e}\n{e.stdout or ''}\n{e.stderr or ''}"

def extract_full_file_from_response(text: str) -> Optional[str]:
    m = re.search(r'<<<FILE_START\s*(.*?)\s*FILE_END>>>', text, re.S)
    if m:
        return m.group(1)
    if "class " in text and "Scene" in text:
        return text
    return None

def call_gpt_fix(source: str, errlog: str, file_path: str, render_cmd: str, manim_version: str) -> str:
    user_payload = f"""
    [环境]
    - manim 版本: {manim_version}

    [原始程序]
    <<<FILE_START
    {source}
    FILE_END>>>

    [渲染错误日志]
    <<<ERROR_START
    {errlog}
    ERROR_END>>>

    [要求]
    请直接输出“修改后的完整文件内容”，不要输出 diff、不要解释。
    注意做最小限度修改以消除错误，任何无关行一律保持不变。
    必须使用如下格式包裹：
    <<<FILE_START
    ...完整代码...
    FILE_END>>>
    """.strip()

    system_msg = {
        "role": "system",
        "content": "你是严谨的 Manim/Python 修复器。只在最小必要范围内修改以消除错误；除非必要，任何无关行一律保持不变。输出仅为完整文件，使用 <<<FILE_START ... FILE_END>>> 包裹，勿解释。",
    }
    user_msg = {"role": "user", "content": user_payload}

    text = ""

    # 路径 A：responses API
    try:
        if hasattr(client, "responses"):
            resp = client.responses.create(
                model=MODEL,
                input=[system_msg, user_msg],
                temperature=0.0
            )
            if getattr(resp, "output", None):
                for item in resp.output:
                    if getattr(item, "content", None):
                        for c in item.content:
                            if getattr(c, "type", "") == "output_text":
                                text += c.text
            else:
                text = getattr(resp, "output_text", "") or str(resp)
            if text:
                return text
    except Exception:
        pass

    # 路径 B：chat.completions API
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[system_msg, user_msg],
            temperature=0.0
        )
        if hasattr(resp, "choices"):
            choice0 = resp.choices[0]
            content = getattr(getattr(choice0, "message", None), "content", None)
            if not content:
                content = getattr(choice0, "text", None)
            text = content or ""
        else:
            text = resp["choices"][0]["message"]["content"]
        return text
    except Exception as e:
        return f"[ERROR] 调用 API 失败：{e}"

def strip_images_and_animations(py_src: str) -> str:
    TEMPLATE_BASE = r'''#!/usr/bin/env python3
    from manim import *

    class DowngradedScene(Scene):
        def construct(self):
            ###BACKGROUND###
            bg = ImageMobject("background_default.png")
            bg.set_z_index(-100)
            bg.scale(max(
                config.frame_width  / bg.width,
                config.frame_height / bg.height
            ))
            bg.move_to(ORIGIN)
            self.add(bg)
            ###BACKGROUND###
            # 1. Title Setup
            title = Text("A Brief History of Fluid Dynamics", 
                        font_size=34,
                        color=WHITE,
                        weight=BOLD)
            title.to_edge(UP, buff=0.5)
            title_line = Line(LEFT, RIGHT, color=ORANGE).next_to(title, DOWN, buff=0.1)
            title_line.match_width(title)
            title_group = VGroup(title, title_line)

            self.play(
                Write(title, run_time=1.5),
                GrowFromCenter(title_line, run_time=0.8)
            )
            self.wait(0.5)

            # 2. Content Sections
            # Foundational Period
            foundational_title = Text("Foundational Period", weight=BOLD, font_size=28)
            foundational_desc = Text("Archimedes' Buoyancy, Bernoulli's Principle, Euler's Equations", font_size=24).next_to(foundational_title, DOWN, aligned_edge=LEFT, buff=0.15)
            foundational_group = VGroup(foundational_title, foundational_desc)

            # Viscosity and Vorticity
            viscosity_title = Text("Viscosity & Vorticity", weight=BOLD, font_size=28)
            viscosity_desc = Text("Navier-Stokes Equations, Helmholtz/Kelvin Vorticity Theorems", font_size=24).next_to(viscosity_title, DOWN, aligned_edge=LEFT, buff=0.15)
            viscosity_group = VGroup(viscosity_title, viscosity_desc)

            # Boundary Layer Revolution
            boundary_title = Text("Boundary Layer Revolution", weight=BOLD, font_size=28)
            boundary_desc = Text("Prandtl (1904) connects viscous and inviscid flows", font_size=24).next_to(boundary_title, DOWN, aligned_edge=LEFT, buff=0.15)
            boundary_group = VGroup(boundary_title, boundary_desc)

            # Turbulence Theory
            turbulence_title = Text("Turbulence & Statistical Theory", weight=BOLD, font_size=28)
            turbulence_desc = Text("Taylor, von Karman, Kolmogorov (1941) scaling laws", font_size=24).next_to(turbulence_title, DOWN, aligned_edge=LEFT, buff=0.15)
            turbulence_group = VGroup(turbulence_title, turbulence_desc)

            # 3. Layout and Animation
            content_group = VGroup(
                foundational_group,
                viscosity_group,
                boundary_group,
                turbulence_group
            ).arrange(DOWN, buff=0.5, aligned_edge=LEFT)
            
            content_group.next_to(title_group, DOWN, buff=0.5).to_edge(LEFT, buff=1.0)

            self.play(FadeIn(foundational_group, shift=UP*0.5), run_time=1)

            self.wait(0.5)
            self.play(FadeIn(viscosity_group, shift=UP*0.5), run_time=1)
            self.wait(0.5)
            self.play(FadeIn(boundary_group, shift=UP*0.5), run_time=1)

            self.wait(0.5)
            self.play(FadeIn(turbulence_group, shift=UP*0.5), run_time=1)

            self.wait(2)

            self.wait(9.88)
    '''
    #找不到就保持模板类名
    scene_name = None
    m = re.search(r'^\s*class\s+([A-Za-z_]\w*)\s*\(\s*Scene\s*\)\s*:', py_src, re.M)
    if m:
        scene_name = m.group(1)
    system_msg = {
        "role": "system",
        "content": (
            "你是严谨的 Manim/Python 代码迁移器。"
            "基于给定的模板骨架，仅迁移文本内容(标题/段落/列表等具体文本)与wait() 时长，把原来的所有等待时长原封不动移动回来！；"
            "禁止改动其它结构/样式/参数/动画。"
            "输出必须是修改后的完整文件，并用 <<<FILE_START ... FILE_END>>> 包裹，不要解释。"
        )
    }

    # 将模板类名替换为原文件类名（如果有）
    class_rule = ""
    if scene_name:
        class_rule = f"- 将模板中的 Scene 类名统一改为原文件的类名：{scene_name}。\n"

    user_payload = f"""
    [原始文件（含字幕/内容/等待时间）]
    <<<SRC_START
    {py_src}
    SRC_END>>>

    [模板骨架（稳定可渲染基底）]
    <<<TEMPLATE_START
    {TEMPLATE_BASE}
    TEMPLATE_END>>>

    [迁移要求]
    - 其它结构与参数（如布局、组装、颜色、字号、淡入调用等）保持模板的默认写法，缩进也不要改；
    {class_rule}- 禁止引入新依赖/新资源；禁止加入复杂动画与外部图片；
    - 未修改行必须逐字保持一致；

    [输出格式]
    <<<FILE_START
    ...完整代码...
    FILE_END>>>
    """.strip()

    prompt_user_msg = {"role": "user", "content": user_payload}

    def _extract(text: str) -> Optional[str]:
        m = re.search(r'<<<FILE_START\s*(.*?)\s*FILE_END>>>', text, re.S)
        if m:
            return m.group(1)
        c = re.search(r"```(?:python)?\s*(.*?)```", text, re.S)
        return c.group(1) if c else None

    # 路径 A
    try:
        if hasattr(client, "responses"):
            resp = client.responses.create(
                model=MODEL,
                input=[system_msg, prompt_user_msg],
                temperature=0.0
            )
            out_text = ""
            if getattr(resp, "output", None):
                for item in resp.output:
                    if getattr(item, "content", None):
                        for c in item.content:
                            if getattr(c, "type", "") == "output_text":
                                out_text += c.text
            else:
                out_text = getattr(resp, "output_text", "") or str(resp)
            full = _extract(out_text)
            if full:
                return full
            return py_src
    except Exception:
        pass

    # 路径 B
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[system_msg, prompt_user_msg],
            temperature=0.0
        )
        if hasattr(resp, "choices"):
            ch0 = resp.choices[0]
            content = getattr(getattr(ch0, "message", None), "content", None) or getattr(ch0, "text", None) or ""
        else:
            content = resp["choices"][0]["message"]["content"]
        full = _extract(content)
        if full:
            return full
        return py_src
    except Exception:
        pass
    print("[WARN] 降级过程无法解析模型输出，返回原始文本，请手动处理 ERROR!!!")
    return py_src

def main(py_file: str, scene: Optional[str] = SCENE, render_dir: Optional[str] = None):
    if render_dir:
        media_dir = pathlib.Path(render_dir).resolve()
        media_dir.mkdir(parents=True, exist_ok=True)
    src = pathlib.Path(py_file).read_text(encoding="utf-8")
    ok, log = run_manim(py_file, scene, media_dir)
    if ok:
        print("[OK] 初次渲染成功")
        return

    try:
        import manim
        manim_version = manim.__version__
    except Exception:
        manim_version = "unknown"

    render_cmd = f"manim -q{MANIM_QUALITY} {py_file} {scene or ''} --format {VIDEO_FORMAT}".strip()

    working_src = src
    for i in range(1, RETRY_MAX + 1):
        print(f"[INFO] 第 {i} 次 GPT 修复中…")
        suggestion = call_gpt_fix(working_src, log, py_file, render_cmd, manim_version)

        # 先直接抽完整文件
        full = extract_full_file_from_response(suggestion)
        if not full:
            # 若模型返回混杂文本, 尝试用代码块抽取
            code_block = re.search(r"```(?:python)?\s*(.*?)```", suggestion, re.S)
            full = code_block.group(1) if code_block else None
        if not full:
            print("[WARN] 模型输出无法解析，跳过本轮")
            continue

        working_src = full

        pathlib.Path(py_file).write_text(working_src, encoding="utf-8")
        ok, log = run_manim(py_file, scene, media_dir)
        if ok:
            print(f"[OK] 修复成功（已覆盖原文件）：{py_file}")
            return
        else:
            print(f"[FAIL] 修复后仍报错，第 {i} 次失败。")

    # 进入最终降级：删图删动画
    print("[FALLBACK] {RETRY_MAX} 次失败，移除图片与动画指令。")
    stripped = strip_images_and_animations(working_src)
    downgraded = py_file.replace(".py", ".noimg_noanim.py")
    pathlib.Path(downgraded).write_text(stripped, encoding="utf-8")
    ok, log2 = run_manim(downgraded, scene, media_dir)
    if ok:
        print(f"[OK] 降级版本成功：{downgraded}")
    else:
        print(f"[ERROR] 连降级版本也失败，请人工查看：{downgraded}\n{log2}")

#也可以直接运行：python auto_debug_manim.py  your_scene.py -s SceneClassName -r /path/to/media_dir
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto debug & render Manim scene with minimal GPT fixes.")
    parser.add_argument("py_file", help="待渲染的 .py 文件路径")
    parser.add_argument("-s", "--scene", default=SCENE, help="Scene 类名（预设为渲染所有scene）")
    parser.add_argument("-r", "--render_dir", default=None, help="Manim 缓存渲染目录（--media_dir）")
    args = parser.parse_args()

    main(args.py_file, args.scene, args.render_dir)

