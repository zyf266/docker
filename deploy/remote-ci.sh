#!/bin/bash
# Actions 已把 /tmp/backpack-quant.tgz 传到服务器；本脚本解压并 docker compose 启动
set -euo pipefail

APP_DIR="/opt/backpack-quant"
PKG="/tmp/backpack-quant.tgz"

if [ ! -f "${PKG}" ]; then
  echo "缺少 ${PKG}，请确认 Actions SCP 步骤成功" >&2
  exit 1
fi

echo "==> 解压到 ${APP_DIR}"
mkdir -p "${APP_DIR}"
tar -xzf "${PKG}" -C "${APP_DIR}"
rm -f "${PKG}"
cd "${APP_DIR}"

chmod +x deploy/install-docker.sh deploy/deploy.sh deploy/entrypoint.sh

if ! command -v docker >/dev/null 2>&1; then
  echo "==> 安装 Docker"
  bash deploy/install-docker.sh
fi

if [ ! -f .env ]; then
  echo "==> 创建 .env"
  cp deploy/env.example .env
  DB_PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
  sed -i "s/请修改为强密码/${DB_PASS}/" .env
fi

echo "==> docker compose"
bash deploy/deploy.sh

echo "==> remote-ci 完成"
