#!/bin/bash

set -e

# 当脚本退出时（例如按 Ctrl+C），此函数将被调用
cleanup() {
    echo -e "\n\n SIGINT 或 TERM 信号捕获... 正在关闭..."
    
    # 停止后台的 ARQ Worker
    if [ "$ARQ_PID" -ne 0 ]; then
        echo "Stopping ARQ Worker (PID $ARQ_PID)..."
        # 使用 kill 发送 TERM 信号，允许 ARQ 优雅关闭
        kill -TERM "$ARQ_PID"
        wait "$ARQ_PID" 2>/dev/null
    fi
    
    echo "后端已关闭。"
    exit 0
}
# 捕获 INT (Ctrl+C) 和 TERM (正常终止) 信号，并调用 cleanup 函数
# 初始化 ARQ_PID
ARQ_PID=0
trap cleanup INT TERM

# 这允许你从任何地方运行此脚本
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"
echo "已切换到项目根目录: $SCRIPT_DIR"


source ./activate_edu.sh
conda activate manim_env

cd backend
echo "正在后台启动 ARQ Worker..."
# 将日志重定向到 arq_worker.log 文件
nohup python -m arq app.workers.arq_worker.WorkerSettings > arq_worker.log 2>&1 &
ARQ_PID=$! # 保存 ARQ 进程的 PID
echo "ARQ Worker 已启动 (PID: $ARQ_PID)。日志文件: arq_worker.log"
sleep 2 # 给 worker 一点启动时间


python main.py
