#!/bin/bash
# 服务器端：构建并重启（代码已由 Actions SCP 同步，不再 git pull）
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/backpack-quant}"
cd "${APP_DIR}"

echo "==> 构建镜像..."
docker compose build --pull

echo "==> 先启动 mysql + api（避免 webhook 因 api 尚未健康而拖垮整次 up）..."
docker compose up -d --remove-orphans mysql api

echo "==> 等待 API 健康..."
ok=0
i=1
while [ "${i}" -le 40 ]; do
  if curl -sf http://127.0.0.1:8100/api/health >/dev/null; then
    curl -s http://127.0.0.1:8100/api/health
    echo ""
    ok=1
    break
  fi
  state=$(docker inspect -f '{{.State.Status}}' backpack-api 2>/dev/null || echo missing)
  health=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' backpack-api 2>/dev/null || echo none)
  if [ "${state}" = "exited" ] || [ "${state}" = "dead" ] || [ "${state}" = "missing" ]; then
    echo "API 容器状态异常: ${state}" >&2
    docker compose logs --tail=120 api || true
    exit 1
  fi
  echo "等待 API... (${i}/40) state=${state} health=${health}"
  sleep 5
  i=$((i + 1))
done

if [ "${ok}" != "1" ]; then
  echo "API 健康检查失败：" >&2
  docker compose logs --tail=120 api || true
  docker compose ps -a || true
  exit 1
fi

echo "==> 启动 webhook..."
docker compose up -d webhook

echo "==> 清理旧镜像..."
docker image prune -f

echo "==> 服务状态:"
docker compose ps -a

echo "==> 部署完成"
