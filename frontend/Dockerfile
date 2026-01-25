# 使用一个非常轻量级的 Nginx 服务器来托管静态文件
FROM nginx:1.25-alpine

# 1. 从 'builder' 阶段拷贝构建好的静态文件到 Nginx 的默认托管目录
# 这是多阶段构建的核心，只拷贝必要产物
COPY /build /usr/share/nginx/html

# 2. （可选但推荐）拷贝自定义的 Nginx 配置文件
# 这个配置文件对于处理 React Router 等前端路由至关重要
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露容器的 80 端口
EXPOSE 80

# Nginx 启动命令
CMD ["nginx", "-g", "daemon off;"]