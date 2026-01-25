#!/usr/bin/env python3
"""
列出目前所有 GenerationJob，并打印每个 job 的 request_payload
（按「最新的 Job 先打印」的顺序）
"""

import os
import json
import requests

# 后端地址：默认按当前项目配置来
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8888/api/v1")

# 管理员账号（建议改成你自己的，或者用环境变量传）
ADMIN_USERNAME = os.environ.get("TM_ADMIN_USER", "yuhengwang0611@outlook.com")
ADMIN_PASSWORD = os.environ.get("TM_ADMIN_PASS", "wyh040611")


def get_access_token() -> str:
    """
    登录获取 JWT token，如果你已经有 token，也可以直接用环境变量传进来跳过登录。
    """
    # 如果外面已经传了一个 access_token，就直接用
    env_token = os.environ.get("TM_ACCESS_TOKEN")
    if env_token:
        return env_token

    url = f"{API_BASE_URL}/auth/login"
    resp = requests.post(
        url,
        data={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
        },
    )
    resp.raise_for_status()
    body = resp.json()
    if not body.get("success"):
        raise RuntimeError(f"登录失败: {body.get('message')}")
    return body["data"]["access_token"]


def fetch_jobs_page(token: str, page: int, size: int = 100):
    """
    调用 /api/v1/admin/jobs 拿一页数据
    """
    url = f"{API_BASE_URL}/admin/jobs"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page": page, "size": size}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    body = resp.json()
    if not body.get("success"):
        raise RuntimeError(f"获取任务失败: {body.get('message')}")
    # 里面是 PageResponse: {total, page, size, items}
    return body["data"]


def iter_all_jobs(token: str, page_size: int = 100):
    """
    通过分页把所有 job 都迭代出来（保持后端原始顺序）
    """
    page = 1
    while True:
        data = fetch_jobs_page(token, page, page_size)
        items = data.get("items", [])
        if not items:
            break

        for job in items:
            yield job

        # 判断是否已经到最后一页
        total = data["total"]
        size = data["size"]
        if page * size >= total:
            break
        page += 1


def main():
    token = get_access_token()

    # 先把所有 job 拉出来，存成列表
    jobs = list(iter_all_jobs(token))

    # 反转一下列表：现在是「最新的 job 先打印」
    for job in reversed(jobs):
        payload = job.get("request_payload") or {}
        print("=" * 80)
        print(f"Job ID: {job['id']}")
        print(f"User ID: {job.get('user_id')}")
        print(f"Status: {job.get('status')}")
        print("Request Payload:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))

        # 可以在这里加过滤条件，例如：
        # if job.get("status") == "awaiting_preview_decision":
        #     print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
