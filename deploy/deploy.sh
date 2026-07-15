#!/bin/bash
# 服务器端部署脚本（CI/CD 或手动执行）
# SYNC_SKIP_GIT=1 时跳过 git 拉取（由 workflow 已更新代码时使用）
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/backpack-quant}"
BRANCH="${BRANCH:-main}"

cd "${APP_DIR}"

if [ "${SYNC_SKIP_GIT:-0}" = "1" ]; then
  echo "==> 跳过 git 拉取（workflow 已更新代码）"
else
  echo "==> 拉取最新代码 (${BRANCH})..."
  REPO_URLS=(
    "https://gitclone.com/github.com/zyf266/docker.git"
    "https://ghproxy.net/https://github.com/zyf266/docker.git"
    "https://mirror.ghproxy.com/https://github.com/zyf266/docker.git"
    "https://github.com/zyf266/docker.git"
  )
  ok=0
  for url in "${REPO_URLS[@]}"; do
    echo "尝试 fetch: ${url}"
    git remote set-url origin "${url}" || true
    if git fetch origin && git reset --hard "origin/${BRANCH}"; then
      ok=1
      break
    fi
  done
  if [ "${ok}" != "1" ]; then
    echo "git fetch 失败" >&2
    exit 1
  fi
fi

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
