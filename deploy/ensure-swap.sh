#!/bin/bash
# 小内存 ECS 必备：无 swap 时 MySQL 极易被 OOM 杀掉（exit 137）
# 幂等：已存在则跳过；写入 /etc/fstab 保证重启后仍生效
set -euo pipefail

SWAP_FILE="${SWAP_FILE:-/swapfile}"
SWAP_SIZE_GB="${SWAP_SIZE_GB:-2}"

if swapon --show 2>/dev/null | grep -qF "${SWAP_FILE}"; then
  echo "==> Swap 已启用: ${SWAP_FILE}"
  swapon --show
  free -h | grep -E 'Mem|Swap'
  exit 0
fi

if [ -f "${SWAP_FILE}" ]; then
  echo "==> 启用已有 swap 文件: ${SWAP_FILE}"
  chmod 600 "${SWAP_FILE}"
  mkswap "${SWAP_FILE}" >/dev/null 2>&1 || true
  swapon "${SWAP_FILE}"
else
  echo "==> 创建 ${SWAP_SIZE_GB}GB swap: ${SWAP_FILE}"
  fallocate -l "${SWAP_SIZE_GB}G" "${SWAP_FILE}"
  chmod 600 "${SWAP_FILE}"
  mkswap "${SWAP_FILE}"
  swapon "${SWAP_FILE}"
fi

if ! grep -qF "${SWAP_FILE}" /etc/fstab 2>/dev/null; then
  echo "${SWAP_FILE} none swap sw 0 0" >> /etc/fstab
  echo "==> 已写入 /etc/fstab"
fi

echo "==> 当前内存 / swap:"
free -h
swapon --show
