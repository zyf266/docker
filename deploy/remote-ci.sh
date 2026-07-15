#!/bin/bash
# 由 GitHub Actions 经 SSH 下发执行（首次部署 + 后续更新）
# 勿使用 bash 数组以外的冷门语法；以 bash -n 校验通过为准
set -euo pipefail

APP_DIR="/opt/backpack-quant"
BRANCH="main"

echo "==> 安装基础依赖..."
if command -v dnf >/dev/null 2>&1; then
  dnf install -y git curl openssl 2>/dev/null || true
elif command -v yum >/dev/null 2>&1; then
  yum install -y git curl openssl 2>/dev/null || true
fi

try_fetch() {
  url="$1"
  echo "尝试 fetch: ${url}"
  git remote set-url origin "${url}"
  git fetch origin
  git reset --hard "origin/${BRANCH}"
}

try_clone() {
  url="$1"
  echo "尝试 clone: ${url}"
  rm -rf "${APP_DIR}"
  git clone -b "${BRANCH}" "${url}" "${APP_DIR}"
  cd "${APP_DIR}"
  git remote set-url origin "${url}"
}

update_or_clone() {
  if [ -d "${APP_DIR}/.git" ]; then
    echo "==> 已有仓库，更新代码..."
    cd "${APP_DIR}"
    try_fetch "https://gitclone.com/github.com/zyf266/docker.git" \
      || try_fetch "https://ghproxy.net/https://github.com/zyf266/docker.git" \
      || try_fetch "https://mirror.ghproxy.com/https://github.com/zyf266/docker.git" \
      || try_fetch "https://github.com/zyf266/docker.git" \
      || { echo "所有镜像 git fetch 均失败" >&2; exit 1; }
    return 0
  fi

  echo "==> 首次克隆仓库..."
  try_clone "https://gitclone.com/github.com/zyf266/docker.git" \
    || try_clone "https://ghproxy.net/https://github.com/zyf266/docker.git" \
    || try_clone "https://mirror.ghproxy.com/https://github.com/zyf266/docker.git" \
    || try_clone "https://github.com/zyf266/docker.git" \
    || { echo "所有镜像 git clone 均失败（ECS 访问 GitHub 网络问题）" >&2; exit 1; }
}

update_or_clone
cd "${APP_DIR}"

chmod +x deploy/install-docker.sh deploy/deploy.sh deploy/entrypoint.sh 2>/dev/null || true

if ! command -v docker >/dev/null 2>&1; then
  echo "==> 安装 Docker..."
  bash deploy/install-docker.sh
fi

if [ ! -f .env ]; then
  echo "==> 创建 .env"
  cp deploy/env.example .env
  DB_PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
  sed -i "s/请修改为强密码/${DB_PASS}/" .env
fi

echo "==> 执行 deploy.sh"
SYNC_SKIP_GIT=1 bash deploy/deploy.sh

echo "==> remote-ci 完成"
