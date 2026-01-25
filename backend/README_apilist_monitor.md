# API 余额监控脚本使用说明

本文档旨在说明 `apilist_monitor.py` 脚本的配置与使用方法。该脚本用于定时监控多个 API 账户的余额及使用情况，并通过飞书 Webhook 发送通知。

## 1. 功能概述

*   **多账户监控**：支持配置多个 API Key，批量查询余额。
*   **定时通知**：默认每天 **09:00** 和 **21:00** 发送两次监控日报/晚报。
*   **用量统计**：自动记录历史数据，计算并展示过去一段时间（如过去 12-24 小时）的使用增量。
*   **异常提醒**：当 API 查询失败或余额不足时，会在消息中体现。

## 2. 配置方法

所有配置项均位于脚本文件 `apilist_monitor.py` 的顶部 **配置区**。

### 2.1 配置 API Key 列表

找到 `API_KEYS` 变量，按照以下格式添加或修改账户信息：

```python
API_KEYS = [
    {"name": "账户名称1", "apikey": "sk-xxxxxxxxxxxxxxxxxxxxxxxx"},
    {"name": "账户名称2", "apikey": "sk-yyyyyyyyyyyyyyyyyyyyyyyy"},
    # 可以继续添加更多...
]
```

*   `name`: 用于在通知中显示的账户别名。
*   `apikey`: 对应的 API 密钥 (Bearer Token)。

### 2.2 配置飞书机器人

找到 `FEISHU_WEBHOOK_URL` 变量，替换为您自己的飞书群组机器人 Webhook 地址：

```python
FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### 2.3 配置发送时间

找到 `SEND_HOURS` 变量，设置每天发送通知的小时数（24小时制）：

```python
# 例如：每天上午 9 点和晚上 21 点发送
SEND_HOURS = [9, 21]
```

### 2.4 历史数据存储

脚本会自动在同目录下生成 `api_usage_history.json` 文件用于存储历史记录。
*   变量名：`HISTORY_FILE`
*   默认值：`"api_usage_history.json"`
*   **注意**：请勿随意删除此文件，否则将无法计算“过去 X 小时用量”。

## 3. 运行与维护

### 3.1 启动脚本

建议使用 `nohup` 命令在后台运行脚本，并将日志输出到文件，示例使用代码：

```bash
cd /home/TeachMasterAppV2/backend
chmod +x apilist_monitor.py
nohup ./apilist_monitor.py > apilist_monitor.log 2>&1 &
```

*   `> apilist_monitor.log`: 将标准输出重定向到日志文件。
*   `2>&1`: 将错误输出也重定向到同一个日志文件。
*   `&`: 在后台运行。

### 3.2 查看运行状态

**查看进程：**
```bash
ps -ef | grep apilist_monitor.py
```

**查看实时日志：**
```bash
tail -f apilist_monitor.log
```

### 3.3 停止脚本

先查找到进程 ID (PID)，然后 kill 掉：

```bash
# 方法 1：自动查找并停止
pkill -f apilist_monitor.py

# 方法 2：手动查找 PID 后停止
ps -ef | grep apilist_monitor.py
kill <PID>
```

## 4. 通知内容说明

飞书通知将包含以下信息：

1.  **标题**：【💵API 余额监控时报】及当前时间。
2.  **账户详情**：
    *   ✅ **状态**：查询成功显示 ✅，失败显示 ❌。
    *   **剩余**：当前账户余额 (balance_usd)。
    *   **已用**：当前账户累计已使用金额 (used_usd)。
    *   **时段用量**：显示“在过去的 X 小时 X 分钟用量为：$X.XXXX”。
    *   **总额**：账户总额度。
3.  **汇总信息**：所有监控账户的总剩余金额。
4.  **注意事项**：关于 API 余额重置可能影响计算精度的提示。