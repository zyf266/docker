#!/bin/bash
# Actions 已把 /tmp/backpack-quant.tgz 传到服务器；本脚本解压并 docker compose 启动
set -euo pipefail

APP_DIR="/opt/backpack-quant"
PKG="/tmp/backpack-quant.tgz"
RELEASE_ROOT="/opt/backpack-quant-releases"

if [ ! -f "${PKG}" ]; then
  echo "缺少 ${PKG}，请确认 Actions SCP 步骤成功" >&2
  exit 1
fi

# 版本号：优先用 Actions 传入的 DEPLOY_VERSION
DEPLOY_VERSION="${DEPLOY_VERSION:-}"
DEPLOY_GIT_SHA="${DEPLOY_GIT_SHA:-}"
if [ -z "${DEPLOY_VERSION}" ]; then
  DEPLOY_VERSION="$(date -u +%Y%m%d-%H%M%S)-manual"
fi
export DEPLOY_VERSION
export DEPLOY_GIT_SHA

echo "==> 发布版本: ${DEPLOY_VERSION} (sha=${DEPLOY_GIT_SHA:-n/a})"

# 归档发布包（回滚兜底：镜像被删仍可重建）
mkdir -p "${RELEASE_ROOT}/${DEPLOY_VERSION}"
cp -f "${PKG}" "${RELEASE_ROOT}/${DEPLOY_VERSION}/backpack-quant.tgz"
echo "${DEPLOY_GIT_SHA}" > "${RELEASE_ROOT}/${DEPLOY_VERSION}/git_sha.txt" || true
echo "${DEPLOY_VERSION}" > "${RELEASE_ROOT}/${DEPLOY_VERSION}/VERSION"

echo "==> 解压到 ${APP_DIR}"
mkdir -p "${APP_DIR}"
# 保留生产 .env / 本地数据目录不被整包误伤：先解压再写 VERSION
tar -xzf "${PKG}" -C "${APP_DIR}"
rm -f "${PKG}"
cd "${APP_DIR}"

printf '%s\n' "${DEPLOY_VERSION}" > "${APP_DIR}/VERSION"

chmod +x deploy/install-docker.sh deploy/deploy.sh deploy/entrypoint.sh deploy/ensure-swap.sh \
  deploy/bootstrap-prod-47.sh deploy/verify-prod.sh deploy/build-frontend.sh deploy/versioning.sh 2>/dev/null || true
chmod +x deploy/*.sh 2>/dev/null || true

# 小内存 ECS：无 swap 时 MySQL 会被 OOM 杀掉（外部 DB 时仍无害）
echo "==> 确保 swap"
bash deploy/ensure-swap.sh

# 已装 Docker 也要跑一遍：写入国内 registry-mirrors（否则拉 docker.io 会超时）
echo "==> 确保 Docker / 镜像加速"
bash deploy/install-docker.sh

if [ ! -f .env ]; then
  echo "==> 创建 .env"
  if [ "${DEPLOY_ENV:-}" = "prod" ] && [ -f deploy/env.prod.example ]; then
    cp deploy/env.prod.example .env
  else
    cp deploy/env.example .env
  fi
  DB_PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
  sed -i "s/请修改为强密码/${DB_PASS}/" .env || true
  echo "已生成 .env，正式机请立即编辑 DB_HOST / 代理 / 业务 Key 后重新部署"
fi

# 正式机 workflow 可设 SKIP_MYSQL=1；否则由 deploy.sh 根据 DB_HOST 判断
export SKIP_MYSQL="${SKIP_MYSQL:-0}"

echo "==> docker compose"
bash deploy/deploy.sh

echo "==> remote-ci 完成 (version=${DEPLOY_VERSION})"
