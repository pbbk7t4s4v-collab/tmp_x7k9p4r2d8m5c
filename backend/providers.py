import asyncio, httpx
from typing import Dict, Any, List, Tuple
from pool import KeyPool, APIKey
from openai import OpenAI
#from zai import ZhipuAiClient

DEBUG_PROVIDER = True

VENDOR_BY_MODEL = {
    # OpenAI
    "gpt-5-chat-2025-08-07": "openai",
    "gpt-5": "openai",
    "gpt-4o-mini": "openai",
    "gpt-4o": "openai",
    "gpt-3.5-turbo": "openai",
    # Gemini
    "gemini-1.5-pro": "gemini",
    "gemini-1.5-flash": "gemini",
    # BigModel
    "glm-4.5": "bigmodel",
}

def _flatten_to_text_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    把多模态 content 转成纯文本，保证 BigModel SDK 可以吃。
    """
    out = []
    for m in messages:
        role = m.get("role", "user")
        c = m.get("content")
        if isinstance(c, list):
            parts = []
            for p in c:
                if isinstance(p, dict) and p.get("type") == "text":
                    parts.append(p.get("text", ""))
                elif isinstance(p, str):
                    parts.append(p)
            out.append({"role": role, "content": "\n".join(parts)})
        elif isinstance(c, str):
            out.append({"role": role, "content": c})
        else:
            out.append({"role": role, "content": str(c)})
    return out


# 封装pool.py，提供统一的调用接口
class ProviderAdapter:
    def __init__(self, key_pool: KeyPool):
        self.pool = key_pool
        self.client = httpx.AsyncClient(timeout=60)

    async def aclose(self):
        await self.client.aclose()

    async def chat(self, messages: List[Dict[str, Any]], model: str, max_retries: int = 3) -> str:
        vendor = VENDOR_BY_MODEL.get(model)
        if not vendor:
            raise ValueError(f"Unknown model: {model}")

        # 统一成纯文本（BigModel SDK 不吃多模态列表）
        def _flatten_to_text_messages(msgs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
            out = []
            for m in msgs:
                role = m.get("role", "user")
                c = m.get("content")
                if isinstance(c, list):
                    parts = []
                    for p in c:
                        if isinstance(p, dict) and p.get("type") == "text":
                            parts.append(p.get("text", ""))
                        elif isinstance(p, str):
                            parts.append(p)
                    out.append({"role": role, "content": "\n".join(parts)})
                elif isinstance(c, str):
                    out.append({"role": role, "content": c})
                else:
                    out.append({"role": role, "content": str(c)})
            return out

        norm_messages = _flatten_to_text_messages(messages)

        last_err = None
        attempt = 0
        if DEBUG_PROVIDER:
            print(f"[provider] model={model} → vendor={vendor}; retries={max_retries}")

        while attempt < max_retries:
            attempt += 1
            k = await self.pool.acquire_key(vendor=vendor)
            if not k:
                # 没有可用key，等一小会
                await asyncio.sleep(3)
                continue

            try:
                if DEBUG_PROVIDER:
                    key_mask = (k.key[:4] + "…" + k.key[-4:]) if isinstance(k.key, str) and len(k.key) > 8 else "****"
                    print(f"[provider] attempt={attempt} use key vendor={k.vendor} weight={getattr(k, 'weight', '?')} key={key_mask}")

                if k.vendor == "openai":
                    text, meta = await self._call_openai(k, norm_messages, model)
                elif k.vendor == "gemini":
                    text, meta = await self._call_gemini(k, norm_messages, model)
                elif k.vendor == "bigmodel":
                    text, meta = await self._call_bigmodel_sdk(k, norm_messages, model)  # ← 改为 SDK
                else:
                    raise RuntimeError(f"unsupported vendor: {k.vendor}")

                await self.pool.report_success(k)
                return text


            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                retry_after = None
                if 'retry-after' in e.response.headers:
                    try:
                        retry_after = float(e.response.headers['retry-after'])
                    except:
                        retry_after = None

                if status in (401, 403):
                    await self.pool.report_failure(k, 'auth')
                elif status == 429:
                    await self.pool.report_failure(k, 'rate', retry_after=retry_after)
                elif 500 <= status < 600:
                    await self.pool.report_failure(k, 'server')
                else:
                    await self.pool.report_failure(k, 'other')
                last_err = e
                # 尝试换 key
                await asyncio.sleep(0.0)
                continue

            except (httpx.RequestError, httpx.ReadTimeout) as e:
                await self.pool.report_failure(k, 'network')
                last_err = e
                # 换 key
                await asyncio.sleep(0.0)
                continue

        raise RuntimeError(f"all retries exhausted; last error: {last_err}")
    '''
    async def _call_openai(self, k: APIKey, messages, model) -> Tuple[str, Dict[str, Any]]:
        # 支持代理 base_url（若 metadata 里有，否则走官方）
        base_url = (k.metadata.get("base_url") if isinstance(k.metadata, dict) else None) or "https://api.openai.com/v1"
        url = f"{base_url.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {k.key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            # max_tokens 也可以从 config 读
        }

        r = await self.client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

        # 优先 message.content，退回 text
        choice = data.get("choices", [{}])[0]
        text = ""
        if "message" in choice and choice["message"].get("content"):
            text = choice["message"]["content"]
        elif "text" in choice:
            text = choice["text"]

        return text, {"usage": data.get("usage")}
    '''

    async def _call_openai(self, k: APIKey, messages, model) -> Tuple[str, Dict[str, Any]]:
        """
        最小化实现：仅用 OpenAI SDK，同步调用 + 简单重试；不依赖 ProviderAdapter 的成员变量。
        - attempts: 固定 3 次
        - temperature: 固定 0.2
        - 不设置 max_tokens（走服务端/模型默认）
        """
        base_url = (k.metadata.get("base_url") if isinstance(k.metadata, dict) else None) or "https://api.openai.com/v1"
        client = OpenAI(api_key=k.key, base_url=base_url)

        attempts = 3
        for i in range(1, attempts + 1):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.2
                )
                # 取文本
                text = ""
                if getattr(resp, "choices", None):
                    ch0 = resp.choices[0]
                    msg = getattr(ch0, "message", None)
                    if msg and getattr(msg, "content", None):
                        text = msg.content
                    elif getattr(ch0, "text", None):
                        text = ch0.text
                if not text:
                    text = str(resp)  # 兜底避免空字符串

                return text, {"usage": getattr(resp, "usage", None)}

            except Exception as e:
                print(f"[openai] 调用失败 第 {i}/{attempts} 次：{e}")
                if i >= attempts:
                    # 最小改动：不抛出 httpx 异常，直接返回错误文本（避免打破上层异常分类逻辑）
                    return f"错误：达到最大重试次数后API调用失败。最后错误: {e}", {}
                # 简单线性退避
                await asyncio.sleep(5 * i)

        return "未能获取模型响应", {}

# Gemini这里还没做好，之前我就用过gpt5
    async def _call_gemini(self, k: APIKey, messages, model) -> Tuple[str, Dict[str, Any]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={k.key}"
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }
        r = await self.client.post(url, json=body)
        if r.status_code >= 400:
            r.raise_for_status()
        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text, {}

    async def _call_bigmodel(self, k: APIKey, messages, model) -> Tuple[str, Dict[str, Any]]:
        
        print("当前使用bigmodel")

        norm_msgs: List[Dict[str, str]] = []
        for m in messages:
            role = m.get("role", "user")
            c = m.get("content")
            if isinstance(c, list):
                txt_parts = []
                for part in c:
                    if isinstance(part, dict) and part.get("type") == "text":
                        txt_parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        txt_parts.append(part)
                norm_msgs.append({"role": role, "content": "\n".join(txt_parts)})
            elif isinstance(c, str):
                norm_msgs.append({"role": role, "content": c})
            else:
                norm_msgs.append({"role": role, "content": str(c)})
        base_url = (k.metadata.get("base_url") if isinstance(k.metadata, dict) else None) \
                   or "https://open.bigmodel.cn/api/paas/v4"
        url = f"{base_url.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {k.key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": norm_msgs, 
            "temperature": 0.2, 
            "stream": False 
        }

        r = await self.client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

        text = ""
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}

        content = msg.get("content")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            # 有些实现会把内容拆成多段对象，尝试拼接 text 字段
            parts = []
            for part in content:
                if isinstance(part, dict):
                    # 常见结构：{"type":"text","text":"..."}
                    t = part.get("text") or part.get("content") or ""
                    if t:
                        parts.append(t)
                elif isinstance(part, str):
                    parts.append(part)
            text = "".join(parts)
        else:
            # 兜底：有些实现把文本放在 choice.text
            t = choice.get("text")
            if isinstance(t, str):
                text = t

        if not text:
            # 最后兜底：转成字符串避免报错（不引入 json.dumps 以免新增 import）
            text = str(data)

        return text, {"usage": data.get("usage"), "id": data.get("id")}

    async def _call_bigmodel_sdk(self, k: APIKey, messages, model) -> Tuple[str, Dict[str, Any]]:
        if ZhipuAiClient is None:
            raise RuntimeError("zai-sdk 未安装，请先 `pip install zai-sdk==0.0.3.3`")

        def _sync_invoke():
            if DEBUG_PROVIDER:
                print(f"[provider] bigmodel via zai-sdk model={model} messages_len={len(messages)}")
            client = ZhipuAiClient(api_key=k.key)
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2
            )
            # 解析文本
            text = ""
            try:
                choice = resp.choices[0]
                if hasattr(choice, "message") and getattr(choice.message, "content", None):
                    text = choice.message.content
                elif hasattr(choice, "text"):
                    text = choice.text
            except Exception as e:
                text = str(resp)
            meta = {}
            if hasattr(resp, "usage"):
                meta["usage"] = getattr(resp, "usage")
            return text, meta

        # zai-sdk 是同步的，用 to_thread 避免阻塞事件循环
        return await asyncio.to_thread(_sync_invoke)

