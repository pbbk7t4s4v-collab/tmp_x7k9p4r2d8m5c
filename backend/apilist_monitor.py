#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import requests
import json
import os
import sys
from datetime import datetime, timedelta

# ================== 配置区 ==================

# 余额查询接口
API_URL = "https://yeysai.com/api/usage/token/"

# 历史数据存储文件
HISTORY_FILE = "api_usage_history.json"

# API Key 列表
# 格式：{"name": "账户名称", "apikey": "sk-..."}
API_KEYS = [
    {"name": "MAC", "apikey": "sk-RFVW2mPV4qEe25RyVR8FOCEmBoZXqAYdlxvWdjE4zAMlrRdA"},
    {"name": "TeachMaster", "apikey": "sk-csrmNpXBGfxgiv5aY2DB9LMX8lnMedzHhvxIdsz93YwoPBvR"},
    {"name": "时瑞杰", "apikey": "sk-YDWCAIw0YBPCJnNV0JXJo64bOrzZeVlPc9wp9T2xzjxs8WaF"},
    {"name": "李易韩", "apikey": "sk-v0WeH7HCUSnHfSPREOSLfi61ErpjOOwe24aSOtzuBRbQJBv6"},
    {"name": "范静如", "apikey": "sk-cBfIwZxU2UbT9eI31Vw97uI5QW5N5oIJrMlQgdRRPuETiugA"},
    {"name": "党余凡", "apikey": "sk-4WGRXEgtSnBBfMZAsSgYQuUAQJEud9w0WvsCnk2lfqNEekTm"},
    # 在此处添加更多账户
]

# 飞书机器人 Webhook 地址
FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/caa3b884-d860-4026-8191-e903fb0d0d43"

# 每天固定两个发送时间（24 小时制）
SEND_HOURS = [8]  # 早上8点
SEND_MINUTE = 0
SEND_SECOND = 0

# ================== 功能函数 ==================

def load_history() -> dict:
    """
    加载历史使用记录
    结构: {"AccountName": [{"timestamp": 1234567890, "used_usd": 123.45}, ...]}
    """
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] 加载历史记录失败: {e}")
        return {}

def save_history(history: dict):
    """
    保存历史使用记录
    """
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"[ERROR] 保存历史记录失败: {e}")

def get_usage_diff(history: dict, name: str, current_used: float) -> tuple:
    """
    计算过去24小时的使用增量
    返回: (usage_diff, time_elapsed_seconds)
    """
    records = history.get(name, [])
    if not records:
        return 0.0, 0.0
    
    # 寻找最接近12小时前的记录 (43200秒)
    now_ts = time.time()
    target_ts = now_ts - 43200
    
    closest_record = None
    min_diff = float('inf')
    
    # 我们只关心过去24小时到25小时之间的数据，或者最近的一条超过24小时的数据
    # 简单策略：找到时间差最接近24小时的那条记录
    for record in records:
        ts = record["timestamp"]
        # 忽略未来的记录（如果有的话）
        if ts > now_ts:
            continue
            
        time_diff = abs((now_ts - ts) - 43200)
        
        # 如果这条记录在24小时左右（比如误差在2小时内），或者是唯一可用的旧记录
        if time_diff < min_diff:
            min_diff = time_diff
            closest_record = record
            
    if closest_record:
        # 如果找到的记录太近了（比如才过1小时），可能不适合做“昨日用量”，但为了有数据还是返回差值
        # 这里设定一个阈值，比如至少要间隔12小时才算“昨日”对比，否则视为0或者N/A
        # 但用户可能刚开始运行，所以只要有旧记录就计算
        old_used = closest_record["used_usd"]
        diff = current_used - old_used
        elapsed = now_ts - closest_record["timestamp"]
        return max(0.0, diff), elapsed # 避免负数（如果API重置）
        
    return 0.0, 0.0

def update_history(history: dict, name: str, current_used: float):
    """
    更新历史记录，并清理过旧数据（保留30天）
    """
    if name not in history:
        history[name] = []
        
    now_ts = time.time()
    history[name].append({
        "timestamp": now_ts,
        "used_usd": current_used
    })
    
    # 清理超过30天的记录
    thirty_days_ago = now_ts - (30 * 86400)
    history[name] = [r for r in history[name] if r["timestamp"] > thirty_days_ago]
    
    # 排序
    history[name].sort(key=lambda x: x["timestamp"])

def fetch_token_usage(name: str, apikey: str) -> dict:
    """
    查询单个 API Key 的使用情况（含重试机制）
    """
    headers = {
        "Authorization": f"Bearer {apikey}",
    }
    
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # 增加超时时间到 30 秒
            resp = requests.get(API_URL, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") is True:
                usage_data = data.get("data", {})
                return {
                    "name": name,
                    "balance_usd": usage_data.get("balance_usd", 0.0),
                    "used_usd": usage_data.get("used_usd", 0.0),
                    "total_usd": usage_data.get("total_usd", 0.0),
                    "user_balance_usd": usage_data.get("user_balance_usd", 0.0),
                    "error": None
                }
            else:
                # 业务逻辑错误，记录并抛出以便重试（或者直接视为失败）
                # 这里选择视为失败并重试，因为有时服务端也会返回临时的业务错误
                last_error = f"API返回错误: {data.get('message')}"
                # 如果不是最后一次，打印警告
                if attempt < max_retries - 1:
                    print(f"[WARN] {name} 第 {attempt+1} 次查询业务报错: {last_error}，准备重试...")
        
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                print(f"[WARN] {name} 第 {attempt+1} 次查询发生异常: {e}，准备重试...")
        
        # 如果成功返回了数据（在 try 块中 return 了），循环会自动结束
        # 如果走到这里，说明发生了异常或业务错误
        
        # 如果不是最后一次尝试，则等待
        if attempt < max_retries - 1:
            wait_time = attempt + 1  # 0->1s, 1->2s
            time.sleep(wait_time)
            
    # 3次都失败，返回最后一次的错误
    return {
        "name": name,
        "error": last_error
    }

def send_feishu_report(report_lines: list) -> None:
    """
    发送飞书通知（含重试机制）
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 构建消息内容
    content_text = f"【💵API 余额监控时报】\n时间：{now}\n\n"
    content_text += "\n".join(report_lines)
    
    payload = {
        "msg_type": "text",
        "content": {
            "text": content_text
        },
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"[DEBUG] 正在发送飞书请求 (第 {attempt+1} 次)，Payload大小: {len(str(payload))} 字符")
            resp = requests.post(
                FEISHU_WEBHOOK_URL,
                json=payload,
                timeout=10,
            )
            
            if resp.status_code != 200:
                print(f"[ERROR] 飞书接口返回非200状态码: {resp.status_code}, 响应内容: {resp.text}")
                # 非200通常是服务端挂了或请求严重错误，稍作等待重试
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue
            
            resp_json = resp.json()
            code = resp_json.get("code")
            
            if code is not None and code != 0:
                print(f"[ERROR] 飞书业务报错: {resp_json}")
                # 针对限流错误 (11232) 或其他临时错误进行重试
                # 简单策略：只要报错就重试，指数退避
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2 # 2s, 4s
                    print(f"[WARN] 飞书发送失败，{wait_time} 秒后重试...")
                    time.sleep(wait_time)
                continue
            else:
                print(f"[INFO] 已发送飞书通知，响应: {resp_json}")
                return # 发送成功，直接退出函数
                 
        except Exception as e:
            print(f"[ERROR] 发送飞书消息异常: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
    print("[ERROR] 飞书通知发送最终失败，已达到最大重试次数。")

def run_once():
    """
    执行一次完整的检查和发送流程
    如果存在失败的查询，每隔30分钟重试，直到全部成功
    """
    while True:
        print("[INFO] 开始执行 API 余额检查...")
        
        # 加载历史数据
        history = load_history()
        
        report_lines = []
        user_balance_usd = 0.0
        has_failure = False
        
        # 暂存需要更新的历史记录，确保全部成功才写入文件
        history_updates = []
        
        for item in API_KEYS:
            name = item["name"]
            apikey = item["apikey"]
            
            result = fetch_token_usage(name, apikey)
            
            if result.get("error"):
                line = f"❌ {name}: 查询失败 - {result['error']}"
                print(f"[WARN] {name} 查询失败: {result['error']}")
                has_failure = True
            else:
                balance = result['balance_usd']
                used = result['used_usd']
                user_balance_usd = result['user_balance_usd']
                
                # 计算昨日用量
                daily_usage, elapsed_seconds = get_usage_diff(history, name, used)
                
                if elapsed_seconds > 0:
                    hours = int(elapsed_seconds // 3600)
                    minutes = int((elapsed_seconds % 3600) // 60)
                    usage_msg = f"在过去的{hours}小时{minutes}分钟用量为：${daily_usage:.4f}"
                else:
                    usage_msg = "暂无历史数据对比"
                
                # 记录需要更新的历史数据
                history_updates.append((name, used))
                
                # 格式化输出：名称 | 剩余 | 已用 | 昨日用量
                line = (f"✅ {name}:\n"
                        f"   剩余: ${balance:.4f} | 已用: ${used:.4f}\n"
                        f"   ⌛{usage_msg}⌛")
                
            report_lines.append(line)
            # 避免请求过快
            time.sleep(0.5)
        
        if has_failure:
            print("[WARN] 本次检查存在失败的账户，不发送通知。30分钟后重试...")
            time.sleep(30 * 60)
            continue # Retry loop
        
        # 全部成功，更新历史并保存
        for name, used in history_updates:
            update_history(history, name, used)
        save_history(history)
        
        # 添加汇总信息
        summary = f"\n💰 所有账户总剩余: ${user_balance_usd:.4f}"
        report_lines.append(summary)
        
        # 添加免责声明
        report_lines.append("\n⚠️注意⚠️ ：受API余额重置影响，计算的使用增量结果可能并不精确。")
        
        # 发送通知
        print(f"[DEBUG] 准备调用 send_feishu_report，共 {len(report_lines)} 行")
        send_feishu_report(report_lines)
        
        # 成功后退出循环
        break

def get_next_run_time(now: datetime) -> datetime:
    """
    计算下一次执行时间
    """
    candidates = []
    for h in SEND_HOURS:
        t = now.replace(hour=h, minute=SEND_MINUTE, second=SEND_SECOND, microsecond=0)
        if t > now:
            candidates.append(t)

    if not candidates:
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
    # 强制 stdout 使用行缓冲，确保日志实时写入文件
    sys.stdout.reconfigure(line_buffering=True)
    print("[INFO] API List 余额监控已启动...")
    print(f"[INFO] 监控账户数: {len(API_KEYS)}")
    
    # 启动时先执行一次，确认功能正常（可选，如果只想定时跑可以注释掉）
    # run_once() 
    
    while True:
        now = datetime.now()
        next_run = get_next_run_time(now)
        sleep_seconds = (next_run - now).total_seconds()

        print(
            f"[INFO] 当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}，"
            f"下一次执行时间：{next_run.strftime('%Y-%m-%d %H:%M:%S')}，"
            f"休眠 {int(sleep_seconds)} 秒..."
        )

        time.sleep(max(1, int(sleep_seconds)))
        run_once()

if __name__ == "__main__":
    main()
