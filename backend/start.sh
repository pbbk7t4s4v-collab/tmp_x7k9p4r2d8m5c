#!/bin/bash

# 后端启动脚本

echo "🚀 启动 ML Education Platform 后端服务..."
echo "========================================="

# 检查是否在正确的目录
if [ ! -f "requirements.txt" ]; then
    echo "❌ 请在 backend 目录下运行此脚本"
    exit 1
fi

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
if [ -z "$python_version" ]; then
    echo "❌ Python 3 未找到，请先安装 Python 3.8+"
    exit 1
fi

echo "✅ 检测到 Python $python_version"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建 Python 虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📦 安装 Python 依赖..."
pip install -r requirements.txt

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "📝 创建环境配置文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件设置你的配置"
fi

# 创建必要的目录
mkdir -p uploads static

echo "✅ 后端环境准备完成"
echo ""
echo "🌐 启动后端服务..."
echo "访问地址："
echo "  - API 服务: http://localhost:8000"
echo "  - API 文档: http://localhost:8000/docs"
echo "  - 健康检查: http://localhost:8000/api/v1/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 启动服务
python main.py