docker volume create mysql_data
docker volume create redis_data

docker run -d \
  --name tm_db_dev \
  -e MYSQL_ROOT_PASSWORD=tm_root \
  -e MYSQL_DATABASE=tm_db \
  -e MYSQL_USER=tm_user \
  -e TZ=Asia/Shanghai \
  -e MYSQL_PASSWORD=tm_user \
  -p 3307:3306 \
  -v mysql_data:/var/lib/mysql \
  --restart unless-stopped \
  mysql:8.0

# docker run -d \
#   --name tm_redis \
#   -p 6379:6379 \
#   -v redis_data:/data \
#   -v /etc/localtime:/etc/localtime \
#   --restart unless-stopped \
#   quay.io/opstree/redis:v7.0.5 \
#   redis-server --save ""

docker run -d \
  --name tm_redis \
  -p 127.0.0.1:6380:6379 \
  -v redis_data:/data \
  -v /etc/localtime:/etc/localtime \
  -v /home/TeachMasterAppV3/redis.conf:/usr/local/etc/redis/redis.conf \
  --restart unless-stopped \
  quay.io/opstree/redis:v7.0.5 \
  redis-server /usr/local/etc/redis/redis.conf

docker exec -it tm_redis redis-cli
config set stop-writes-on-bgsave-error no

arq app.workers.arq_worker.WorkerSettings > arq.log 2>&1


# 提取纯代码文件并打包成压缩包
find . -type d \( -name "node_modules" -o -name "venv" -o -name ".git" -o -name "__pycache__" -o -name "generated_content" \) -prune -o \
-type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) -print0 \
| tar -czvf clean_code.tar.gz --null -T -