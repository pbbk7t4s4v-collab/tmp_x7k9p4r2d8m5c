#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
两阶段版 MiniMax 批量语音生成：
1. 先克隆音色（/v1/voice_clone），只做一次
2. 再用克隆出的 voice_id 调 TTS（/v1/t2a_v2）批量生成
3. 把最终用到的 voice_id 写到 output_dir/voice_id.txt
"""
from __future__ import annotations
import os
import argparse
import requests
import base64
from pathlib import Path
from urllib.parse import urlparse
import re
from io import BytesIO
from pydub import AudioSegment 
import time


PUNCT_SPLIT_PATTERN = re.compile(r'([。！？!?.])')  # 中英标点都切
SILENCE_MS = 130  # 静音时长（毫秒）


UPLOAD_URL = "https://api.minimax.io/v1/files/upload"
CLONE_URL = "https://api.minimax.io/v1/voice_clone"
TTS_URL = "https://api.minimax.io/v1/t2a_v2"  # 官方这个名字

def add_edge_silence(seg: AudioSegment, ms: int = SILENCE_MS) -> AudioSegment:
    sil = AudioSegment.silent(duration=ms)
    return sil + seg + sil

def resp_to_audiosegment(resp_json: dict) -> AudioSegment:
    # 跟 fetch_audio_and_save 取 URL 的逻辑保持一致，不过这是返回 bytes
    data_audio = resp_json.get("data", {}).get("audio") \
        or resp_json.get("demo_audio") \
        or resp_json.get("audio_url") \
        or resp_json.get("output_audio_url")
    if not data_audio:
        raise RuntimeError(f"no audio url in resp: {resp_json}")

    # 下载音频时增加重试机制，避免偶发 SSL/网络错误导致整批失败
    r = _get_with_retry(data_audio)
    if r is None:
        # 多次重试仍失败：不抛异常，返回一段静音，由上层继续拼接
        print("[!] download audio failed after retries, use silence instead.")
        return AudioSegment.silent(duration=SILENCE_MS * 4)

    audio_bytes = BytesIO(r.content)

    # 现在返回的是 mp3，所以这里用 from_file(..., format="mp3")
    return AudioSegment.from_file(audio_bytes, format="mp3")

def split_text_into_sentences(text: str):
    text = text.strip()
    if not text:
        return []
    parts = PUNCT_SPLIT_PATTERN.split(text)
    sentences = []
    buf = ""
    for p in parts:
        if not p:
            continue
        buf += p
        if PUNCT_SPLIT_PATTERN.match(p):
            sentences.append(buf.strip())
            buf = ""
    if buf.strip():
        sentences.append(buf.strip())
    return sentences

def upload_file(api_key: str, file_path: str, purpose: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}"}
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        data = {"purpose": purpose}
        resp = requests.post(UPLOAD_URL, headers=headers, data=data, files=files)
    resp.raise_for_status()
    return resp.json()["file"]["file_id"]


def fetch_audio_and_save(resp_json: dict, out_path: Path):
    data_audio = resp_json.get("data", {}).get("audio")

    audio_url = (
        data_audio
        or resp_json.get("demo_audio")
        or resp_json.get("audio_url")
        or resp_json.get("output_audio_url")
    )
    if audio_url:
        r = requests.get(audio_url)
        r.raise_for_status()
        suffix = ".wav"
        parsed = urlparse(audio_url)
        filename = os.path.basename(parsed.path)
        if "." in filename:
            suffix = "." + filename.split(".")[-1]
        real_out_path = out_path.with_suffix(suffix)
        real_out_path.write_bytes(r.content)
        return

    # 2. base64 类返回
    audio_b64 = (
        resp_json.get("audio_base64")
        or resp_json.get("audio")
        or resp_json.get("output_audio_base64")
    )
    if audio_b64:
        audio_bytes = base64.b64decode(audio_b64)
        real_out_path = out_path.with_suffix(".wav")
        real_out_path.write_bytes(audio_bytes)
        return

    # 3. 都没有就把 json 存下来
    out_path.with_suffix(".json").write_text(str(resp_json), encoding="utf-8")


def do_voice_clone(
    api_key: str,
    cloned_file_id: str,
    prompt_file_id: str | None,
    voice_id: str,
    model: str,
    prompt_text: str | None = None
):
    """
    做一次真正的克隆，用短文本，避免 300 限制。
    成功就说明这个 voice_id 可以拿来后面 TTS。
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "file_id": cloned_file_id,
        "voice_id": voice_id,
        "text": "This voice is cloned for later TTS generation.",
        "model": model,
    }
    if prompt_file_id:
        payload["clone_prompt"] = {
            "prompt_audio": prompt_file_id,
            "prompt_text": prompt_text,
        }

    resp = requests.post(CLONE_URL, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    if data.get("base_resp", {}).get("status_code", 0) != 0:
        raise RuntimeError(f"voice_clone failed: {data}")
    return data

def _get_with_retry(url: str, max_retries: int = 5, timeout: int = 30):
    """
    对 GET 请求做有限次重试，用于下载音频文件。
    成功：返回 response 对象
    超过最大重试：打印警告并返回 None
    """
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                print(f"[!] GET {url} failed after {max_retries} attempts: {e}")
                return None
            sleep_time = 1.5 ** (attempt - 1)
            print(
                f"[!] GET {url} error (attempt {attempt}/{max_retries}), "
                f"retry after {sleep_time:.1f}s: {e}"
            )
            time.sleep(sleep_time)

def _post_with_retry(url: str, headers: dict, json_payload: dict,
                     max_retries: int = 5, timeout: int = 30):
    """
    对单次 POST 做有限次重试。
    - 成功：返回 response 物件
    - 超过最大重试：打印警告並返回 None，不丟异常
    """
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=json_payload, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                print(f"[!] TTS request failed after {max_retries} attempts: {e}")
                return None
            sleep_time = 1.5 ** (attempt - 1)
            print(f"[!] TTS request error (attempt {attempt}/{max_retries}), "
                  f"retry after {sleep_time:.1f}s: {e}")
            time.sleep(sleep_time)

def tts_with_cloned_voice(
    api_key: str,
    voice_id: str,
    text: str,
    model: str,
):
    """
    调官方 /v1/t2a_v2
    关键点：voice_id 要放在 voice_setting 里

    成功：返回 resp.json()
    失败且重试用完：返回 None，不抛异常
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "text": text,
        "output_format": "url",
        "voice_setting": {
            "voice_id": voice_id,
        },
    }
    resp = _post_with_retry(TTS_URL, headers, payload)
    if resp is None:
        # 不抛异常，交给上层用静音占位
        return None
    return resp.json()


def main():
    parser = argparse.ArgumentParser(
        description="Two-stage MiniMax voice cloning + batch TTS"
    )
    parser.add_argument("--input_dir", required=True, help="包含若干 .txt 的目录")
    parser.add_argument("--output_dir", required=True, help="输出音频目录")

    parser.add_argument(
        "--clone_audio",
        required=False,
        help="用来做 voice_clone 的音频（可以长，10s~5min）",
    )
    parser.add_argument(
        "--prompt_audio",
        required=False,
        help="用来做 prompt_audio 的音频（要短，<8s），不传则不用 prompt",
    )
    parser.add_argument(
        "--voice_id", required=True, help="这次克隆要创建/使用的 voice_id"
    )
    parser.add_argument(
        "--model",
        default="speech-02-hd",
        help="可选，默认 speech-02-hd",
    )
    parser.add_argument(
        "--prompt_text",
        required=False,
        help="用于 voice_clone 的文本提示，可为字符串或指向 .txt 文件的路径"
    )
    parser.add_argument(
        "--use_existing_voice",
        action="store_true",
        help="使用已经克隆好的 voice_id，跳过这次的克隆步骤",
    )
    args = parser.parse_args()

    # 固定 MiniMax API Key（后面不能公布啊
    api_key = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiJBbmRyZXcgQWxsZW5kZXIiLCJVc2VyTmFtZSI6IkFuZHJldyBBbGxlbmRlciIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxOTg3NzkwNDY2MzM4MjYzMjMxIiwiUGhvbmUiOiIiLCJHcm91cElEIjoiMTk4Nzc5MDQ2NjMzNDA3MzAyMyIsIlBhZ2VOYW1lIjoiIiwiTWFpbCI6InlhbmdydW5kZW1kakBnbWFpbC5jb20iLCJDcmVhdGVUaW1lIjoiMjAyNS0xMS0xMCAxNjoyMzoxNyIsIlRva2VuVHlwZSI6MSwiaXNzIjoibWluaW1heCJ9.TMAZ6NmJZU_H1E0XcUA1G5mmMrZ1ahTJO9_VZaYh_jgSlxLuwoTk7rgwmXoo0hu1xZbeAn9zGH0_um3y9zuLI9faoiKN1BGSDqeXX9HYUBWbbTmvckY1BDpr0tZvy7sJHdwkauOD91XUChjERlUBMbSj_FtogMpSukvSj5Vh680FZmvDgEICBwEcRIQJD_ypeBP7ICQqMJEghOM5Qki0-qa92QJFc0YhprT9QtvS3Cgq8uSQTzUK-c2aCS9WVEYHbs6i3U2fneaMHodtYrUfjD2cpaA8oryUSC-rJmROWwEFyFVk1dtxExI4Fm5v0Pb-pyLZ2dJr8AO4TsNgrFTmRQ"  # ← 这里换成你自己的 key

    if not api_key:
        raise RuntimeError("未设置 MiniMax API Key，请在代码中填写或通过环境变量提供")


    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not args.use_existing_voice:
        # 1) 上传克隆源
        print("[*] uploading source (voice_clone)...")
        cloned_file_id = upload_file(api_key, args.clone_audio, "voice_clone")
        print(f"[+] source file_id = {cloned_file_id}")

        # 2) （可选）上传 prompt_audio
        prompt_file_id = None
        if args.prompt_audio:
            print("[*] uploading prompt audio...")
            prompt_file_id = upload_file(api_key, args.prompt_audio, "prompt_audio")
            print(f"[+] prompt file_id = {prompt_file_id}")
        else:
            print("[*] no prompt_audio provided, clone will use default style.")

        # 3) 真正做一次克隆
        print("[*] cloning voice once ...")

        # 处理 prompt_text 参数：可为纯字符串或 .txt 路径
        prompt_text = None
        if args.prompt_text:
            if os.path.isfile(args.prompt_text) and args.prompt_text.lower().endswith(".txt"):
                prompt_text = Path(args.prompt_text).read_text(encoding="utf-8").strip()
            else:
                prompt_text = args.prompt_text.strip()

        do_voice_clone(
            api_key=api_key,
            cloned_file_id=cloned_file_id,
            prompt_file_id=prompt_file_id,
            voice_id=args.voice_id,
            model=args.model,
            prompt_text=prompt_text, 
        )

        print("[+] voice clone success.")

    else:
        print("[*] use_existing_voice = True, skip cloning.")
    # 4) 把 voice_id 存起来
    (output_dir / "voice_id.txt").write_text(args.voice_id, encoding="utf-8")
    print(f"[+] voice_id saved to {output_dir / 'voice_id.txt'}")

    # 5) 遍历所有 txt，走 TTS
    txt_files = sorted(input_dir.glob("*.txt"))
    if not txt_files:
        print("没有找到任何 .txt 文件")
        return

    for txt_path in txt_files:
        text = txt_path.read_text(encoding="utf-8").strip()
        if not text:
            print(f"[!] {txt_path.name} 是空的，跳过")
            continue

        sentences = split_text_into_sentences(text)
        print(f"[*] {txt_path.name} -> {len(sentences)} sentences")

        full_audio = AudioSegment.silent(duration=0)

        for idx, sent in enumerate(sentences, start=1):
            print(f"    -> TTS sentence {idx}/{len(sentences)}")
            tts_resp = tts_with_cloned_voice(
                api_key=api_key,
                voice_id=args.voice_id,
                text=sent,
                model=args.model,
            )

            if tts_resp is None:
                # 超过最大重试次数仍失败：不报错，这一句用静音占位
                print(f"[!] sentence {idx}/{len(sentences)} failed after retries, "
                      f"use silence instead.")
                seg = AudioSegment.silent(duration=SILENCE_MS * 4)
            else:
                seg = resp_to_audiosegment(tts_resp)
                seg = add_edge_silence(seg, SILENCE_MS)

            full_audio += seg

        out_audio_path = output_dir / txt_path.stem
        # 导出成 mp3
        final_mp3_path = out_audio_path.with_suffix(".mp3")
        full_audio.export(str(final_mp3_path), format="mp3")
        # 再用 ffmpeg 显式转成 wav（16k 单声道，兼容性最好）
        final_wav_path = out_audio_path.with_suffix(".wav")
        os.system(
            f"ffmpeg -y -i '{final_mp3_path}' '{final_wav_path}' >/dev/null 2>&1"
        )
        # >>> 在这里插入删除 mp3 的代码 <<<
        try:
            os.remove(final_mp3_path)
        except Exception as e:
            print(f"[!] delete mp3 failed: {e}")
        # <<< 结束插入 >>>

        # 去除拼接爆音 adeclick（先输出到临时文件，再覆盖原文件）
        temp_wav = final_wav_path.with_name(final_wav_path.stem + "_tmp.wav")
        os.system(f"ffmpeg -y -i '{final_wav_path}' -af adeclick '{temp_wav}' >/dev/null 2>&1")
        os.replace(temp_wav, final_wav_path)  # 覆盖原 wav

        # 追加写入一个 speech.txt，给后面的 pipeline 用
        speech_txt_path = output_dir / "speech.txt"
        duration_sec = len(full_audio) / 1000.0
        with open(speech_txt_path, "a", encoding="utf-8") as f:
            f.write(f"{final_wav_path.name}\t{duration_sec:.2f}\n")


        print(f"[+] saved {out_audio_path}")

    print("[√] all done.")


if __name__ == "__main__":
    main()
