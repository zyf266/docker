#!/bin/bash
# 正式机验收：端口 / health / Nginx / 代理
# 用法: bash deploy/verify-prod.sh
# 环境变量: PROD_HOST=47.110.57.118  VERIFY_VIA_HTTPS=1
set -u

PROD_HOST="${PROD_HOST:-47.110.57.118}"
VERIFY_VIA_HTTPS="${VERIFY_VIA_HTTPS:-1}"
fail=0

ok() { echo "  [OK] $*"; }
bad() { echo "  [FAIL] $*"; fail=1; }
skip() { echo "  [SKIP] $*"; }

echo "==> 1) 本机端口监听"
for p in 8100 8005; do
  if ss -tlnp 2>/dev/null | grep -qE ":${p}\\b" || netstat -tlnp 2>/dev/null | grep -q ":${p} "; then
    ok "监听 :${p}"
  else
    bad "未监听 :${p}"
  fi
done

echo "==> 2) 本机 API health"
if curl -sf --max-time 10 http://127.0.0.1:8100/api/health >/dev/null; then
  ok "http://127.0.0.1:8100/api/health"
  curl -s http://127.0.0.1:8100/api/health || true
  echo ""
else
  bad "本机 /api/health"
fi

echo "==> 3) 经 Nginx HTTPS health"
if [ "${VERIFY_VIA_HTTPS}" = "1" ]; then
  if curl -skf --max-time 15 "https://${PROD_HOST}/api/health" >/dev/null; then
    ok "https://${PROD_HOST}/api/health"
  else
    bad "https://${PROD_HOST}/api/health（检查 Nginx / 与证书）"
  fi
else
  skip "HTTPS（VERIFY_VIA_HTTPS=0）"
fi

echo "==> 4) 容器内经代理 ping Binance"
PROXY=$(docker exec backpack-api printenv HTTPS_PROXY 2>/dev/null || true)
if [ -z "${PROXY}" ]; then
  skip "容器未设 HTTPS_PROXY"
else
  if docker exec backpack-api curl -sf --max-time 20 -x "${PROXY}" \
    https://fapi.binance.com/fapi/v1/ping >/dev/null 2>&1; then
    ok "代理 ${PROXY} → Binance fapi"
  else
    bad "代理 ${PROXY} → Binance 失败（检查宿主机 mihomo :7891）"
  fi
fi

echo "==> 5) Webhook 端口可达（干跑）"
if curl -sf --max-time 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:8005/ >/dev/null 2>&1 \
  || curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:8005/webhook | grep -qE '^[0-9]+$'; then
  ok "8005 有响应"
else
  # webhook 根路径可能 404，只要 TCP 通即可
  if ss -tlnp 2>/dev/null | grep -qE ':8005\\b'; then
    ok "8005 在听（HTTP 路径可能 404）"
  else
    bad "8005 无响应"
  fi
fi

echo ""
if [ "${fail}" = "0" ]; then
  echo "verify-prod: 全部通过（或仅 SKIP）"
  exit 0
else
  echo "verify-prod: 存在失败项" >&2
  exit 1
fi
