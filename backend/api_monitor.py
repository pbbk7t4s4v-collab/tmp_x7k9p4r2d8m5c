#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import requests
from datetime import datetime, timedelta

# ================== 配置区 ==================

# 余额查询接口
API_URL = "https://yeysai.com/api/usage/token/"

# 你的 Bearer Token（建议改成从环境变量读取，这里先写死）
API_TOKEN = "sk-csrmNpXBGfxgiv5aY2DB9LMX8lnMedzHhvxIdsz93YwoPBvR"

# 飞书自建机器人 Webhook 地址
FEISHU_WEBHOOK_URL = (
    "https://open.feishu.cn/open-apis/bot/v2/hook/"
    "c7a0faad-9b73-4800-bdd9-745e4bea92c7"
)

# 每天固定两个发送时间（24 小时制）
SEND_HOURS = [8, 20]
SEND_MINUTE = 0
SEND_SECOND = 0

# ================== 功能函数 ==================


def fetch_balance() -> float:
    """
    调用 yeysai 的接口，获取当前余额（balance_usd）
    返回 float，如 152.68575
    """
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
    }
    resp = requests.get(API_URL, headers=headers, timeout=10)
    resp.raise_for_status()

    data = resp.json()
    # 按你提供的结构：{"code":true,"data":{"balance_usd":152.68575, ...}}
    balance = data["data"]["balance_usd"]
    return float(balance)


def send_feishu_balance(balance: float) -> None:
    """
    把余额发到飞书群里
    文本示例：
    当前 yeysai 账户余额为：152.68575 美元，请相关负责人员及时关注。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"当前API账户余额为：{balance} 美元，"
        f"时间：{now}，请相关负责人员及时查看。"
    )

    payload = {
        "msg_type": "text",
        "content": {
            "text": text
        },
    }

    try:
        resp = requests.post(
            FEISHU_WEBHOOK_URL,
            json=payload,
            timeout=5,
        )
        resp.raise_for_status()
        print(f"[INFO] 已发送飞书余额通知：{text}")
    except Exception as e:
        print(f"[ERROR] 发送飞书消息失败: {e}")


def run_once():
    """
    单次执行：查询余额 -> 发送飞书
    """
    try:
        balance = fetch_balance()
        print(f"[INFO] 当前余额：{balance}")
        send_feishu_balance(balance)
    except Exception as e:
        print(f"[ERROR] 查询或发送过程中出错: {e}")


def get_next_run_time(now: datetime) -> datetime:
    """
    根据当前时间，计算下一次应该发送的时间（当天 8:00 / 20:00 或明天 8:00）
    """
    candidates = []

    for h in SEND_HOURS:
        t = now.replace(hour=h, minute=SEND_MINUTE, second=SEND_SECOND, microsecond=0)
        if t > now:
            candidates.append(t)

    if not candidates:
        # 今天两个时间点都过了，就排到明天的第一个时间点（8:00）
        tomorrow = now + timedelta(days=1)
        t = tomorrow.replace(
            hour=SEND_HOURS[0],
            minute=SEND_MINUTE,
            second=SEND_SECOND,
            microsecond=0,
        )
        candidates.append(t)

    return min(candidates)


def main():
    print("[INFO] yeysai 余额监控已启动，每天 08:00 和 20:00 各发送一次余额通知...")
    while True:
        now = datetime.now()
        next_run = get_next_run_time(now)
        sleep_seconds = (next_run - now).total_seconds()

        print(
            f"[INFO] 当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}，"
            f"下一次执行时间：{next_run.strftime('%Y-%m-%d %H:%M:%S')}，"
            f"休眠 {int(sleep_seconds)} 秒..."
        )

        # 休眠直到下一次执行时间
        time.sleep(max(1, int(sleep_seconds)))

        # 醒来后执行一次
        run_once()


if __name__ == "__main__":
    main()
