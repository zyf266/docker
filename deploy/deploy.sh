#!/bin/bash
# 服务器端：构建并重启（代码已由 Actions SCP 同步，不再 git pull）
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/backpack-quant}"
cd "${APP_DIR}"

echo "==> 构建镜像..."
docker compose build --pull

echo "==> 重启服务..."
docker compose up -d --remove-orphans

echo "==> 清理旧镜像..."
docker image prune -f

echo "==> 服务状态:"
docker compose ps

echo "==> 健康检查..."
ok=0
i=1
while [ "${i}" -le 10 ]; do
  if curl -sf http://127.0.0.1:8100/api/health >/dev/null; then
    curl -s http://127.0.0.1:8100/api/health
    echo ""
    ok=1
    break
  fi
  echo "等待 API... (${i}/10)"
  sleep 3
  i=$((i + 1))
done

if [ "${ok}" != "1" ]; then
  echo "API 健康检查失败：" >&2
  docker compose logs --tail=80 api || true
  exit 1
fi

echo "==> 部署完成"
