#!/bin/bash

echo "构建前端应用..."
npm run build

echo "正在复制构建结果到目标目录..."
cp -r /home/TeachMasterAppV2/frontend/build /usr/share/nginx/html/teach-app

echo "正在重新加载 Nginx 配置..."
nginx -s reload
nginx -s reload
echo "前端应用部署完成！"

echo "正在测试前端应用..."
curl https://www.teachmaster.cn/
echo "\n"

echo "正在测试 API 服务..."
curl https://www.teachmaster.cn/api/v1/ping
echo "\n"