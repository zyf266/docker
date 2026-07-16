#!/bin/bash
# 云服务器一次性初始化脚本（在 ECS 上以 root 执行）
# 用法: curl -fsSL <raw-url>/deploy/bootstrap-server.sh | bash
#   或: bash deploy/bootstrap-server.sh
set -euo pipefail

APP_DIR="/opt/backpack-quant"
REPO_URL="${REPO_URL:-git@github.com:zyf266/docker.git}"
BRANCH="${BRANCH:-main}"

echo "==> 安装依赖..."
if command -v dnf &>/dev/null; then
  dnf install -y git curl openssl 2>/dev/null || true
elif command -v yum &>/dev/null; then
  yum install -y git curl openssl 2>/dev/null || true
fi

echo "==> 克隆/更新代码到 ${APP_DIR}..."
if [ -d "${APP_DIR}/.git" ]; then
  cd "${APP_DIR}"
  git fetch origin
  git reset --hard "origin/${BRANCH}"
else
  git clone -b "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
  cd "${APP_DIR}"
fi

echo "==> 确保 swap（小内存 ECS 防 MySQL OOM）..."
chmod +x deploy/ensure-swap.sh deploy/install-docker.sh
bash deploy/ensure-swap.sh

echo "==> 安装 Docker（阿里云镜像，不走 get.docker.com）..."
bash deploy/install-docker.sh

if [ ! -f .env ]; then
  echo "==> 创建 .env（请编辑后重新部署）..."
  cp deploy/env.example .env
  # 生成随机数据库密码
  DB_PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
  sed -i "s/请修改为强密码/${DB_PASS}/" .env
  echo "已生成数据库密码，保存在 ${APP_DIR}/.env"
fi

echo "==> 构建并启动容器..."
docker compose build
docker compose up -d

echo ""
echo "=========================================="
echo "  部署完成！"
echo "  API + 前端: http://$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}'):8100"
echo "  Webhook:    端口 8005"
echo "  健康检查:   http://<IP>:8100/api/health"
echo ""
echo "  请在阿里云安全组放行: 8100, 8005"
echo "  编辑配置: nano ${APP_DIR}/.env"
echo "  查看日志: docker compose -f ${APP_DIR}/docker-compose.yml logs -f"
echo "=========================================="
