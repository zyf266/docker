#!/bin/bash
# 正式机一次性引导：目录、端口检查、mihomo、.env 模板
# 用法（在 47.110.57.118 上）: bash deploy/bootstrap-prod-47.sh
# 本脚本不杀 nginx / mihomo；不自动停旧栈，只检测并提示。
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/backpack-quant}"
PORTS=(8100 8005 8050)
PROXY_PORT="${PROXY_PORT:-7891}"

echo "==> 创建 ${APP_DIR}"
mkdir -p "${APP_DIR}"

echo "==> 检查占用端口: ${PORTS[*]}"
busy=0
for p in "${PORTS[@]}"; do
  if command -v ss >/dev/null 2>&1; then
    line=$(ss -tlnp "sport = :${p}" 2>/dev/null || true)
  else
    line=$(netstat -tlnp 2>/dev/null | grep ":${p} " || true)
  fi
  if echo "${line}" | grep -qE ":${p}\\b|: ${p}\\b|:${p} "; then
    echo "  [占用] :${p}"
    echo "${line}" | head -n 5
    busy=1
  else
    echo "  [空闲] :${p}"
  fi
done

if [ "${busy}" = "1" ]; then
  echo ""
  echo "请手动停掉旧栈后再部署（勿杀 nginx / mihomo），例如："
  echo "  # 查进程: ss -tlnp | grep -E '8100|8005|8050'"
  echo "  # 若旧目录在 /opt/trading/ending：停其 systemd/screen/nohup 进程"
  echo "  # 确认空闲后继续: bash deploy/deploy.sh"
fi

echo ""
echo "==> 检查宿主机代理 :${PROXY_PORT}"
if command -v ss >/dev/null 2>&1; then
  proxy_line=$(ss -tlnp "sport = :${PROXY_PORT}" 2>/dev/null || true)
else
  proxy_line=$(netstat -tlnp 2>/dev/null | grep ":${PROXY_PORT} " || true)
fi
if echo "${proxy_line}" | grep -qE ":${PROXY_PORT}"; then
  echo "  mihomo/Clash 似在监听 :${PROXY_PORT}"
else
  echo "  [未监听] :${PROXY_PORT}"
  echo "  请在宿主机启动: cd ${APP_DIR} && bash backpack_quant_trading/tools/proxy/start_clash.sh"
  echo "  或确认现有 Clash/mihomo mixed 端口，并写入 .env 的 HTTP(S)_PROXY"
fi

if [ ! -f "${APP_DIR}/.env" ]; then
  echo ""
  echo "==> 写入 .env 模板"
  if [ -f "${APP_DIR}/deploy/env.prod.example" ]; then
    cp "${APP_DIR}/deploy/env.prod.example" "${APP_DIR}/.env"
  elif [ -f "${APP_DIR}/deploy/env.example" ]; then
    cp "${APP_DIR}/deploy/env.example" "${APP_DIR}/.env"
  else
    echo "缺少 env 模板，请先 SCP/解压代码到 ${APP_DIR}" >&2
    exit 1
  fi
  echo "  已创建 ${APP_DIR}/.env — 请编辑 DB_* / HTTPS_PROXY / WEBHOOK_SECRET / 交易所 Key"
else
  echo "==> 已存在 ${APP_DIR}/.env（不覆盖）"
fi

echo ""
echo "=========================================="
echo "  bootstrap-prod 完成"
echo "  1) 释放 8100/8005/8050（若占用）"
echo "  2) 确认 mihomo :${PROXY_PORT}"
echo "  3) nano ${APP_DIR}/.env"
echo "  4) 合并 Nginx 片段: deploy/nginx/prod-443-snippet.conf"
echo "  5) 触发 GitHub Actions: Deploy to Prod ECS"
echo "  6) bash ${APP_DIR}/deploy/verify-prod.sh"
echo "=========================================="
