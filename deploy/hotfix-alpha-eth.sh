#!/bin/bash
# 正式机热更新：阿尔法策略·ETH（避免全量 apt 重建卡住）
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cd /opt/backpack-quant

echo "==> 停掉卡住的全量部署（如有）"
pkill -f '/opt/backpack-quant/deploy/remote-ci.sh' 2>/dev/null || true
pkill -f 'bash deploy/deploy.sh' 2>/dev/null || true
sleep 1

echo "==> 注入后端 strategy.py + CSV"
docker cp backpack_quant_trading/api/routers/strategy.py \
  backpack-api:/app/backpack_quant_trading/api/routers/strategy.py
docker cp "阿尔法策略_ETHUSDT_2H_交易数据.csv" \
  "backpack-api:/app/阿尔法策略_ETHUSDT_2H_交易数据.csv"

echo "==> 用 node 镜像构建前端"
docker run --rm \
  -v /opt/backpack-quant/backpack_quant_trading/frontend:/build \
  -w /build node:20-alpine \
  sh -c 'npm ci --ignore-scripts 2>/dev/null || npm install; npm run build'

echo "==> 注入前端 dist"
docker exec backpack-api rm -rf /app/backpack_quant_trading/frontend/dist
docker cp backpack_quant_trading/frontend/dist \
  backpack-api:/app/backpack_quant_trading/frontend/dist

echo "==> 重启 api"
docker restart backpack-api
echo "等待健康..."
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8100/api/health >/dev/null; then
    echo "API healthy"
    break
  fi
  sleep 2
done

echo "==> 验证 alpha overview"
curl -sS -w "\nHTTP %{http_code}\n" \
  http://127.0.0.1:8100/api/strategy/alpha-eth-2h/overview | head -c 600
echo
echo "==> hotfix-alpha-eth 完成"
