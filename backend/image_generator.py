#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import base64
from pathlib import Path
import openai


BASE_URL = "https://yeysai.com/v1/"
LLM_KEY = "sk-csrmNpXBGfxgiv5aY2DB9LMX8lnMedzHhvxIdsz93YwoPBvR"
MODEL_NAME = "gemini-3-pro-image-preview"


def generate_image(prompt: str, output_path: Path) -> bool:
    """
    调用 gemini-3-pro-image-preview 生成图片，并保存到 output_path
    """
    try:
        client = openai.OpenAI(
            api_key=LLM_KEY,
            base_url=BASE_URL
        )

        full_prompt = f"根据以下描述生成一张高质量图片：{prompt}。图片的宽高比必须为1:1。"

        print(f"[INFO] Generating image for prompt: {prompt}")

        response_stream = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": full_prompt}],
            stream=True
        )

        # 拼接流式内容
        full_content = ""
        for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                full_content += chunk.choices[0].delta.content

        # 查找 markdown 图片链接 ![image](...)
        start_index = full_content.find("![image](")
        if start_index == -1:
            print("[ERROR] 找不到 markdown 图片格式 ![image](...)")
            return False

        end_index = full_content.find(")", start_index)
        if end_index == -1:
            print("[ERROR] markdown 图片链接格式不完整")
            return False

        image_url = full_content[start_index + 9 : end_index]

        # 必须是 base64 图片
        if image_url.startswith("data:image"):
            try:
                b64_str = image_url.split(",")[1]
                img_bytes = base64.b64decode(b64_str)

                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(img_bytes)

                print(f"[SUCCESS] 图片已保存到: {output_path}")
                return True

            except Exception as e:
                print(f"[ERROR] base64 解码失败: {e}")
                return False

        else:
            print(f"[ERROR] 不支持的图片URL格式: {image_url[:50]}")
            return False

    except Exception as e:
        print(f"[ERROR] Image generation failed: {e}")
        return False


def main():
    if len(sys.argv) < 3:
        print("用法：python image_generator.py <prompt> <输出图片路径>")
        sys.exit(1)

    prompt = sys.argv[1]
    output_path = Path(sys.argv[2])

    ok = generate_image(prompt, output_path)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
