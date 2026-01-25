#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, json, subprocess, pathlib, argparse
from typing import Tuple, Optional
from openai import OpenAI  # pip install openai>=1.40.0
import asyncio
from pool import load_keypool_from_config
from providers import ProviderAdapter, VENDOR_BY_MODEL
from pathlib import Path
#注意需要在/home/EduAgent/miniconda3/envs/manim_env下运行，因为那里manim版本是渲染的时候的版本，修复的时候也要确认manim版本
RETRY_MAX = 3
MODEL = "gpt-5"
RENDER_TIMEOUT = 300  # 秒
SCENE = None  # None则渲染文件内所有Scene
MANIM_QUALITY = "l"  # ex: -qk (高清), -qm (中), -ql (低)
VIDEO_FORMAT = "mp4"
MAX_LINES = 30  #保留行数

# 注意：优先读 config_pool.json（如果没有，就退回 config.json）
config_pool = pathlib.Path("config_pool.json")
config_path = config_pool if config_pool.exists() else pathlib.Path("config.json")

# 默认
_model_raw = MODEL
retry_max = RETRY_MAX

if config_path.exists():
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    # 兼容两种结构：老结构 debug_settings / 新结构 settings.debug_settings
    debug_settings = (
        cfg.get("settings", {}).get("debug_settings", {}) 
        if "settings" in cfg else cfg.get("debug_settings", {})
    )
    _model_raw = debug_settings.get("model", MODEL)
    retry_max = debug_settings.get("max_retries", RETRY_MAX)
else:
    cfg = {}

# —— 规范化模型名（映射到 providers.VENDOR_BY_MODEL 里存在的 key）——
def _norm_model(m: str) -> str:
    if m in VENDOR_BY_MODEL:
        return m
    s = (m or "").strip().lower()
    if s.startswith("gpt-5"): return "gpt-5"
    if s.startswith("gpt-4o-mini"): return "gpt-4o-mini"
    if s.startswith("gpt-4o"): return "gpt-4o"
    if s.startswith("gpt-3.5"): return "gpt-3.5-turbo"
    if s.startswith("gemini-1.5-pro"): return "gemini-1.5-pro"
    if s.startswith("gemini-1.5-flash"): return "gemini-1.5-flash"
    if s.startswith("glm-4.5"): return "glm-4.5"  # bigmodel
    return "gpt-5"

MODEL = _norm_model(_model_raw)

# —— 初始化 KeyPool + ProviderAdapter（从当前 config 文件加载）——
_pool = load_keypool_from_config(str(config_path))  # 你的 pool.load_keypool_from_config 已支持传路径
_adapter = ProviderAdapter(_pool)

# —— 一个同步包装，供下面函数直接调用 —— 
def _chat_via_providers(messages):
    return asyncio.run(_adapter.chat(messages, model=MODEL, max_retries=retry_max))


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
        # ====== 新增：根据目录结构判断渲染是否真正成功 ======
        if ok and media_dir:
            media_dir_path = Path(media_dir)
            videos_root = media_dir_path / "videos"

            # 当前 py 文件名，例如 1_1.py → "1_1"
            module_name = Path(py_path).stem

            # 目标目录：media/videos/<py文件名>/
            module_dir = videos_root / module_name

            mp4_candidates = []
            if module_dir.exists():
                # 在该模块目录下递归查找 mp4
                for mp4_path in module_dir.rglob("*.mp4"):
                    # 排除片段文件：partial_movie_files 下的是分段
                    if "partial_movie_files" in mp4_path.parts:
                        continue
                    mp4_candidates.append(mp4_path)

            # 如果在对应模块目录下找不到任何成品 mp4，则视为失败
            if not mp4_candidates:
                warn = (
                    f"[WARN] manim 返回码为 0，但在 {module_dir} 下 "
                    f"未找到任何成品 mp4（仅有 partial_movie_files 或完全无输出）；将视为渲染失败。"
                )
                out = out + "\n" + warn
                ok = False
        # ====== 新增结束 ======
        return ok, out
    except subprocess.TimeoutExpired as e:
        return False, f"[TIMEOUT] {e}\n{e.stdout or ''}\n{e.stderr or ''}"

def extract_full_file_from_response(text: str) -> Optional[str]:
    # 1) 优先：FILE_START … FILE_END 夹心（容忍前缀 <<<、END 后任意数量的 >，以及换行）
    m = re.search(
        r'<<<\s*FILE_START[>\s]*\n?(.*?)\n?\s*(?:<<<\s*)?FILE_END\s*>*\s*$',
        text,
        re.S | re.I
    )
    if not m:
        # 2) 没有 FILE_END：从 FILE_START 提取到 EOF
        m = re.search(r'<<<\s*FILE_START[>\s]*\n?(.*)\Z', text, re.S | re.I)

    if m:
        extracted = m.group(1)
        return _sanitize_extracted(extracted)

    # 3) 退路：markdown 三引号
    c = re.search(r"```(?:python)?\s*(.*?)```", text, re.S | re.I)
    if c:
        return _sanitize_extracted(c.group(1))

    # 4) 最后退路：看起来像 Manim 文件
    if "class " in text and "Scene" in text and "from manim import" in text:
        return _sanitize_extracted(text)

    return None



# 清洗器
# 匹配所有“标记行” + “孤立尖括号/反斜杠数字行”
_MARKER_LINE_RE = re.compile(
    r'^\s*(?:'
    r'(?:<<<\s*)?(?:FILE|SRC|TEMPLATE|ERROR)_(?:START|END)\b.*|'  # 允许 _START/_END 前可有 <<< 前缀
    r'```.*|'                                                    # markdown 围栏
    r'[<>\\]{2,}\s*$|\\\d+\s*$'                                  # 只有尖括号或 \数字 的垃圾行（如 <<<、>>>>、\2）
    r')\s*$',
    re.I
)

def _sanitize_extracted(code: str) -> str:
    # 1) 行级清洗：删除所有标记/围栏/孤立尖括号与 \数字
    lines = code.splitlines()
    lines = [ln for ln in lines if not _MARKER_LINE_RE.match(ln)]

    cleaned = "\n".join(lines)

    # 2) 片内清洗：若某些标记混在一行中间（不单独成行），也抹掉
    cleaned = re.sub(
        r'(?:<<<\s*)?(?:FILE|SRC|TEMPLATE|ERROR)_(?:START|END)\s*>*(?:\\\d+)?',
        '',
        cleaned,
        flags=re.I
    )

    # 3) 末尾保底：砍掉最后一个 *_END 及其后的任何内容（如果还有）
    cleaned = re.sub(r'(?:<<<\s*)?(?:FILE|SRC|TEMPLATE|ERROR)_END.*\Z', '', cleaned, flags=re.I | re.S)

    # 4) 再保底：若末尾只剩尖括号或 \数字，去掉
    cleaned = re.sub(r'[ \t\r\f\v]*[<>\\]+\s*\Z', '\n', cleaned)

    # 5) 去零宽字符，并保证以换行结尾
    cleaned = cleaned.replace('\u200b', '').rstrip() + "\n"
    return cleaned



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
    必须使用如下格式包裹，注意一定要遵守这个格式！包裹代码的<<<FILE_START和FILE_END>>>一定不要多写或写错！！！：
    <<<FILE_START
    ...完整代码...
    FILE_END>>>
    [注意]：Code()不支持font_size参数，不支持code参数，insert_line_no参数和insert_line_number参数和file_path参数，同时Code物件也没有.code这个属性，要千万注意哦！！！
    """.strip()

    system_msg = {
        "role": "system",
        "content": "你是严谨的 Manim/Python 修复器。只在最小必要范围内修改以消除错误；除非必要，任何无关行一律保持不变。输出仅为完整文件，使用 <<<FILE_START ... FILE_END>>> 包裹，勿解释。",
    }
    user_msg = {"role": "user", "content": user_payload}

    text = ""

    # —— 统一改为：走 ProviderAdapter（KeyPool）——
    try:
        text = _chat_via_providers([system_msg, user_msg])
        return text
    except Exception as e:
        return f"[ERROR] 调用 API 失败：{e}"

def strip_images_and_animations(py_src: str) -> str:
    TEMPLATE_BASE = r'''#!/usr/bin/env python3
    from manim import *

    class DowngradedScene(Scene):
        def construct(self):
            bg = ImageMobject("background_default.png")
            bg.set_z_index(-100)
            bg.scale(max(
                config.frame_width  / bg.width,
                config.frame_height / bg.height
            ))
            bg.move_to(ORIGIN)
            self.add(bg)
            # 1. Title Setup
            title = Text("A Brief History of Fluid Dynamics", 
                        font_size=34,
                        font="AR PL UKai CN",
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
            foundational_title = Text("Foundational Period", font="AR PL UKai CN",weight=BOLD, font_size=28)
            foundational_desc = Text("Archimedes' Buoyancy, Bernoulli's Principle, Euler's Equations", font="AR PL UKai CN", font_size=24).next_to(foundational_title, DOWN, aligned_edge=LEFT, buff=0.15)
            foundational_group = VGroup(foundational_title, foundational_desc)

            # Viscosity and Vorticity
            viscosity_title = Text("Viscosity & Vorticity",font="AR PL UKai CN", weight=BOLD, font_size=28)
            viscosity_desc = Text("Navier-Stokes Equations, Helmholtz/Kelvin Vorticity Theorems", font="AR PL UKai CN", font_size=24).next_to(viscosity_title, DOWN, aligned_edge=LEFT, buff=0.15)
            viscosity_group = VGroup(viscosity_title, viscosity_desc)

            # Boundary Layer Revolution
            boundary_title = Text("Boundary Layer Revolution",font="AR PL UKai CN", weight=BOLD, font_size=28)
            boundary_desc = Text("Prandtl (1904) connects viscous and inviscid flows", font="AR PL UKai CN", font_size=24).next_to(boundary_title, DOWN, aligned_edge=LEFT, buff=0.15)
            boundary_group = VGroup(boundary_title, boundary_desc)

            # Turbulence Theory
            turbulence_title = Text("Turbulence & Statistical Theory", weight=BOLD, font_size=28)
            turbulence_desc = Text("Taylor, von Karman, Kolmogorov (1941) scaling laws", font="AR PL UKai CN", font_size=24).next_to(turbulence_title, DOWN, aligned_edge=LEFT, buff=0.15)
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
            "基于给定的模板骨架，仅迁移文本内容(标题/段落/列表等具体文本)"
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
    - 在模板基础上，仅迁移“可见文本”（标题/段落/列表等）
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
        m = re.search(
            r'<<<\s*FILE_START[>\s]*\n?(.*?)\n?\s*(?:<<<\s*)?FILE_END\s*>*\s*$',
            text,
            re.S | re.I
        )
        if not m:
            m = re.search(r'<<<\s*FILE_START[>\s]*\n?(.*)\Z', text, re.S | re.I)
        if m:
            return _sanitize_extracted(m.group(1))
        c = re.search(r"```(?:python)?\s*(.*?)```", text, re.S | re.I)
        return _sanitize_extracted(c.group(1)) if c else None



    # —— 统一改为：走 ProviderAdapter（KeyPool）——
    try:
        out_text = _chat_via_providers([system_msg, prompt_user_msg])
        full = _extract(out_text)
        if full:
            return full
        return py_src
    except Exception as e:
        print(f"[ERROR] 降级过程异常: {e}")
        import traceback
        traceback.print_exc()  # 打印完整堆栈，方便定位
        print("[WARN] 降级过程无法解析模型输出，返回原始文本，请手动处理 ERROR!!!")
        return py_src

def main(py_file: str, scene: Optional[str] = SCENE, render_dir: Optional[str] = None):
    media_dir = None
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
    i = 1
    while i <= RETRY_MAX:
        print(f"[INFO] 第 {i} 次 GPT 修复中…")
        suggestion = call_gpt_fix(working_src, log, py_file, render_cmd, manim_version)

        # 先直接抽完整文件
        full = extract_full_file_from_response(suggestion)
        if not full:
            # 若模型返回混杂文本, 尝试用代码块抽取
            code_block = re.search(r"```(?:python)?\s*(.*?)```", suggestion, re.S)
            full = code_block.group(1) if code_block else None
        if not full:
            print("[WARN] 模型输出无法解析，跳过本轮，本轮不计入次数")
            continue
        i += 1
        working_src = full
        if working_src and (
            "FILE_END" in working_src or "FILE_START" in working_src or
            "<<<" in working_src or "```" in working_src or
            re.search(r'[<>\\]{2,}\s*$', working_src, re.I) or
            re.search(r'(?:<<<\s*)?(?:FILE|SRC|TEMPLATE|ERROR)_(?:START|END)\b', working_src, re.I)
        ):
            working_src = _sanitize_extracted(working_src)
        import ast

        def _is_syntax_ok(code: str) -> bool:
            try:
                ast.parse(code)
                return True
            except SyntaxError as e:
                return False

        # 第一次语法检查
        if not _is_syntax_ok(working_src):
            # 清洗后再检查一次
            working_src = re.sub(
                r'(?s)(.*?)(?:<<<\s*)?(?:FILE|SRC|TEMPLATE|ERROR)_END.*\Z',
                r'\1',
                working_src,
                flags=re.I
            )
            working_src = _sanitize_extracted(working_src)

            if not _is_syntax_ok(working_src):
                print(f"[WARN] 修复结果仍然是语法错误，本轮跳过，进入下一次 GPT 修复。")
                # 注意：这里不要 write 文件、不要 run_manim，直接进入下一轮
                # 这时 i 已经 i += 1 了（你现在的逻辑是计数一次尝试），保持一致即可
                continue


        pathlib.Path(py_file).write_text(working_src, encoding="utf-8")
        ok, log = run_manim(py_file, scene, media_dir)
        if ok:
            print(f"[OK] 修复成功（已覆盖原文件）：{py_file}")
            return
        else:
            print(f"[FAIL] 修复后仍报错，第 {i-1} 次失败。")
    # 进入最终降级：删图删动画
    print(f"[FALLBACK] {retry_max} 次失败，移除图片与动画指令。")
    stripped = strip_images_and_animations(working_src)
    stripped = re.sub(
        r'(?m)^(?P<prefix>\s*bg\s*=\s*ImageMobject\(\s*)(?P<q>["\'])background_default\.png(?P=q)(?P<suffix>\s*\))',
        r'\g<prefix>\g<q>background_baodi.png\g<q>\g<suffix>',
        stripped,
        count=1
    )

    # 覆盖原 py 文件，尝试用“无图/降级版本”再渲染一次
    Path(py_file).write_text(stripped, encoding="utf-8")
    ok, log2 = run_manim(py_file, scene, media_dir)

    if ok:
        print(f"[OK] 降级版本成功：{py_file}")
        return
    else:
        print(f"[ERROR] 连降级版本也失败，将删除对应文件：{py_file}\n{log2}")

        # 关键逻辑：降级也失败，则删除这个 py 文件
        try:
            Path(py_file).unlink()
            print(f"[CLEANUP] 已删除降级失败的文件：{py_file}")
        except Exception as e:
            # 这里不要再抛异常，否则有可能影响上层流程，打印 warning 即可
            print(f"[WARN] 删除降级失败文件时出错：{e}")
        return

#也可以直接运行：python auto_debug_manim.py  your_scene.py -s SceneClassName -r /path/to/media_dir
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto debug & render Manim scene with minimal GPT fixes.")
    parser.add_argument("py_file", help="待渲染的 .py 文件路径")
    parser.add_argument("-s", "--scene", default=SCENE, help="Scene 类名（预设为渲染所有scene）")
    parser.add_argument("-r", "--render_dir", default=None, help="Manim 缓存渲染目录（--media_dir）")
    args = parser.parse_args()

    main(args.py_file, args.scene, args.render_dir)

