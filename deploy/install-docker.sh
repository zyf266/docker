#!/bin/bash
# 在国内 ECS 上安装 Docker（不走 get.docker.com，避免 SSL/墙导致失败）
set -euo pipefail

if command -v docker >/dev/null 2>&1; then
  echo "==> Docker 已安装: $(docker --version)"
else
  echo "==> 使用阿里云 Docker CE 镜像安装..."
  if command -v dnf >/dev/null 2>&1; then
    dnf -y install dnf-plugins-core 2>/dev/null || true
    dnf config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
  elif command -v yum >/dev/null 2>&1; then
    yum -y install yum-utils 2>/dev/null || true
    yum-config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
  else
    echo "不支持的包管理器，请手动安装 Docker" >&2
    exit 1
  fi

  # Alibaba Cloud Linux 等发行版 $releasever 可能不是 7/8，强制用 8 源
  if [ -f /etc/yum.repos.d/docker-ce.repo ]; then
    sed -i 's/\$releasever/8/g' /etc/yum.repos.d/docker-ce.repo
  fi

  if command -v dnf >/dev/null 2>&1; then
    dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  else
    yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  fi

  systemctl enable docker
  systemctl start docker
  echo "==> Docker 安装完成: $(docker --version)"
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "==> 安装 docker compose 插件..."
  if command -v dnf >/dev/null 2>&1; then
    dnf install -y docker-compose-plugin
  elif command -v yum >/dev/null 2>&1; then
    yum install -y docker-compose-plugin
  fi
fi

docker compose version
echo "==> Docker / Compose 就绪"
