#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import requests

from webhook_feishu import get_access_token, iter_all_jobs

FEISHU_WEBHOOK_URL = (
    "https://open.feishu.cn/open-apis/bot/v2/hook/"
    "c7a0faad-9b73-4800-bdd9-745e4bea92c7"
)

# 轮询时间间隔（秒）
POLL_INTERVAL_SECONDS = 10

# =======================
# 状态说明文案映射
# =======================
STATUS_MESSAGES = {
    "manim_code_generation": "🚀 任务开始啦",
    "awaiting_preview_decision": "⏳ 视频已生成，正在等待预览和校验～",
    "completed": "🎉 视频生成完成啦！可以查看并投入使用了～",
    "failed": "❌ 任务生成失败，请尽快排查原因！",
}

# 哪些状态变化需要告警（直接用上面的 key）
ALERT_STATUSES = set(STATUS_MESSAGES.keys())

# 记录每个 job 上一次看到的状态，避免重复刷通知
job_status_cache: dict[str, str | None] = {}

# =======================
# 教师 → 负责人映射表
# （未来可随时调整负责人姓名）
# =======================
PROFESSOR_OWNER_MAP: dict[str, str] = {
    # —— 负责人：汪宇恒 ——
    "闻立杰": "汪宇恒",
    "曲香竹": "汪宇恒",
    "林雷蕾": "汪宇恒",
    "吴志博": "汪宇恒",
    "苏德启": "汪宇恒",
    "唐异垒": "汪宇恒",
    "高云": "汪宇恒",
    "傅晗玮": "汪宇恒",
    "王伟": "汪宇恒",
    "杨眉": "汪宇恒",
    "李友林": "汪宇恒",
    "葛志磊": "汪宇恒",
    "周栋焯": "汪宇恒",
    "何峰": "汪宇恒",
    "钱忱": "汪宇恒",

    # —— 负责人：杨润德 ——
    "杨薛雯": "杨润德",
    "徐思语": "杨润德",
    "肖双九": "杨润德",
    "岳子焕": "杨润德",
    "郭晓霞": "杨润德",
    "管先生": "杨润德",
    "蒋瑞": "杨润德",
    "陈洁": "杨润德",
    "程金华": "杨润德",
    "董德礼": "杨润德",
    "董兵": "杨润德",
    "张小群": "杨润德",

    # —— 负责人：张洁 ——
    "蓝丹": "张洁",
    "孙敬云": "张洁",
    "杨瑞龙": "张洁",
    "王威": "张洁",
    "廖明": "张洁",
    "张吟": "张洁",

    # —— 负责人：武霖 ——
    "林丽": "武霖",
    "高楠": "武霖",
    "后晓囝": "武霖",
    "任利强": "武霖",
    "林芳竹": "武霖",
    "范琪琳": "武霖",
    "陈老师": "武霖",
    "李康化": "武霖",

    # —— 负责人：周天乐 ——
    "范歆琦 Fan Xinqi": "周天乐",
    "廖翠婷": "周天乐",
    "陈婕": "周天乐",
    "宋国辉": "周天乐",
    "黄雪梅": "周天乐",
    "刘嘉雯": "周天乐",
    "徐笑然": "周天乐",
    "潘慧兰": "周天乐",

    # —— 负责人：傅若瑜 ——
    "苏聪": "傅若瑜",
    "杨璐": "傅若瑜",
    "周张恒": "傅若瑜",
    "陈维维": "傅若瑜",
    "魏婷": "傅若瑜",
    "郭靖": "傅若瑜",
    "张玲": "傅若瑜",

    # —— 负责人：范静如 ——
    "许珩": "范静如",
    "皮玲": "范静如",
    "刘成杰": "范静如",
    "潘葳": "范静如",
    "沈耀": "范静如",
    "王亚光": "范静如",
    "张佩国": "范静如",

    # —— 负责人：李易韩 ——
    "曹骎": "李易韩",
    "杜鹃": "李易韩",
    "杜志敏": "李易韩",
    "周春琴": "李易韩",
}


def send_feishu_alert(item: dict) -> None:
    """
    把某个任务的状态变化，通过飞书机器人发到群里
    """
    school = item.get("school") or "无"
    college = item.get("college") or "无"
    professor_name = item.get("professor_name") or "未知教师"
    course_title = item.get("course_title") or "未命名课程"
    job_status = item.get("status") or "未知状态"
    job_id = item.get("job_id", "unknown")

    # 友好的状态说明文案（找不到就用原始状态字符串）
    status_desc = STATUS_MESSAGES.get(job_status, job_status)

    # 从映射表找到负责人
    owner_name = PROFESSOR_OWNER_MAP.get(professor_name, "")
    if owner_name:
        owner_suffix = f"@{owner_name}"
    else:
        # 没配负责人时，也给个兜底文案
        owner_suffix = "请相关同学/老师留意"

    # 飞书文本内容（纯 text 模式，兼容性最好）
    text = (
        f"{status_desc}\n\n"
        f"📌 学校：{school}\n"
        f"🏫 学院：{college}\n"
        f"👤 教师：{professor_name}\n"
        f"📚 课程：{course_title}\n"
        f"🧩 Job ID：{job_id}\n"
        f"🔔 后端状态值：{job_status}\n\n"
        f"👉 {owner_suffix}"
    )

    payload = {
        "msg_type": "text",
        "content": {"text": text},
    }

    try:
        resp = requests.post(FEISHU_WEBHOOK_URL, json=payload, timeout=5)
        resp.raise_for_status()
        print(f"[INFO] 已发送告警: {job_id} -> {job_status} ({professor_name}-{course_title})")
    except Exception as e:
        print(f"[ERROR] 发送告警失败: {e}")


def init_cache(token: str) -> None:
    """
    启动时初始化 job 状态缓存，不触发任何告警
    """
    print("[INFO] 初始化 job 状态缓存（不告警）...")
    count = 0
    for job in iter_all_jobs(token):
        job_status_cache[job["id"]] = job.get("status")
        count += 1
    print(f"[INFO] 初始化完成，缓存 {count} 个任务。")


def check_and_notify(token: str) -> None:
    """
    每轮轮询调用：遍历所有 job，检测状态变化，必要时发送飞书通知
    """
    for job in iter_all_jobs(token):
        job_id = job["id"]
        status = job.get("status")

        # 取出上一次记录的状态
        prev_status = job_status_cache.get(job_id)
        # 更新缓存
        job_status_cache[job_id] = status

        # 符合两条件才告警：
        # 1）状态在 ALERT_STATUSES 中
        # 2）状态和上一次不同（避免重复刷屏）
        if status in ALERT_STATUSES and status != prev_status:
            payload = job.get("request_payload") or {}

            info = {
                "job_id": job_id,
                "status": status,
                "school": payload.get("school", ""),
                "college": payload.get("college", ""),
                "course_title": payload.get("course_title", ""),
                "professor_name": payload.get("professor_name", ""),
            }

            send_feishu_alert(info)


def main() -> None:
    token = get_access_token()
    init_cache(token)

    print(
        "[INFO] TeachMaster 监控已启动："
        "pre_processing / awaiting_preview_decision / completed / failed "
        "状态变化将自动推送飞书提醒（含负责人标注）..."
    )

    while True:
        try:
            token = get_access_token()
            check_and_notify(token)
        except Exception as e:
            print(f"[ERROR] 轮询时出错: {e}")
        print("[INFO] 本轮结束")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
