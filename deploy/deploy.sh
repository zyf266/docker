#!/bin/bash
# 服务器端部署脚本（CI/CD 或手动执行）
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/backpack-quant}"
BRANCH="${BRANCH:-main}"

cd "${APP_DIR}"

echo "==> 拉取最新代码 (${BRANCH})..."
git fetch origin
git reset --hard "origin/${BRANCH}"

echo "==> 构建镜像..."
docker compose build --pull

echo "==> 重启服务..."
docker compose up -d --remove-orphans

echo "==> 清理旧镜像..."
docker image prune -f

echo "==> 服务状态:"
docker compose ps

echo "==> 健康检查..."
sleep 5
curl -sf http://127.0.0.1:8100/api/health && echo "" || echo "API 健康检查失败，请查看日志: docker compose logs api"
