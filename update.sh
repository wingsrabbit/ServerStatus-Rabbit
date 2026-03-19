#!/bin/bash
# ServerStatus-Rabbit 热更新脚本
# 将后端代码和管理页面复制到运行中的容器，无需重建镜像
# 用法: bash update.sh [容器名]
# 示例: bash update.sh ss-server

set -e

CONTAINER="${1:-ss-server}"

# 检查容器是否运行
if ! docker inspect --format='{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -q true; then
  echo "❌ 容器 $CONTAINER 未运行"
  exit 1
fi

echo "📦 正在更新容器 $CONTAINER ..."

# 复制后端 Python 文件
docker cp server/. "$CONTAINER":/app/server/
echo "  ✅ server/ 已更新"

# 复制客户端 Python 文件
docker cp client/. "$CONTAINER":/app/client/
echo "  ✅ client/ 已更新"

# 复制入口脚本
docker cp app.py "$CONTAINER":/app/app.py
echo "  ✅ app.py 已更新"

# 复制管理页面（无需编译）
docker cp web/admin/. "$CONTAINER":/app/web/admin/
echo "  ✅ web/admin/ 已更新"

# 复制恢复脚本
if [ -f recover.py ]; then
  docker cp recover.py "$CONTAINER":/app/recover.py
  echo "  ✅ recover.py 已更新"
fi

# 重启容器使改动生效
echo "🔄 正在重启容器 ..."
docker restart "$CONTAINER"

echo "✅ 更新完成！容器已重启。"
echo ""
echo "⚠️  注意：如果本次更新包含前端监控页（Vue）的改动，"
echo "   需要重新构建镜像：docker build -t serverstatus-rabbit . && docker stop $CONTAINER && docker rm $CONTAINER && docker run ..."
