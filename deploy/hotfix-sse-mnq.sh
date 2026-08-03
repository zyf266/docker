#!/bin/bash
# 正式机热更新：上证510210 + 纳指抄底 MNQ
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cd /opt/backpack-quant

echo "==> 注入后端 + CSV"
docker cp backpack_quant_trading/api/routers/strategy.py \
  backpack-api:/app/backpack_quant_trading/api/routers/strategy.py
docker cp backpack_quant_trading/core/a_share_strategy_import.py \
  backpack-api:/app/backpack_quant_trading/core/a_share_strategy_import.py
docker cp backpack_quant_trading/core/massive_klines.py \
  backpack-api:/app/backpack_quant_trading/core/massive_klines.py

docker cp "SSE_DLY_510210, 240_8936e.csv" \
  "backpack-api:/app/SSE_DLY_510210, 240_8936e.csv"
docker cp "【沐龙】纳指趋势追踪增强策略_SSE_510210_2026-07-29_1c9aa.csv" \
  "backpack-api:/app/【沐龙】纳指趋势追踪增强策略_SSE_510210_2026-07-29_1c9aa.csv"
docker cp "CME_MINI_DL_MNQ1!, 240_c233a.csv" \
  "backpack-api:/app/CME_MINI_DL_MNQ1!, 240_c233a.csv"
docker cp "纳指抄底策略.csv" \
  "backpack-api:/app/纳指抄底策略.csv"

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
for i in $(seq 1 40); do
  if curl -sf http://127.0.0.1:8100/api/health >/dev/null; then
    echo "API healthy"
    break
  fi
  sleep 2
done

echo "==> 导入 CSV"
curl -sS -X POST http://127.0.0.1:8100/api/strategy/sse-510210-4h/import-klines; echo
curl -sS -X POST http://127.0.0.1:8100/api/strategy/sse-510210-4h/import-trades; echo
curl -sS -X POST http://127.0.0.1:8100/api/strategy/mnq-dip-4h/import-klines; echo
curl -sS -X POST http://127.0.0.1:8100/api/strategy/mnq-dip-4h/import-trades; echo

echo "==> 验证 overview"
curl -sS http://127.0.0.1:8100/api/strategy/sse-510210-4h/overview | head -c 400; echo
curl -sS http://127.0.0.1:8100/api/strategy/mnq-dip-4h/overview | head -c 400; echo
curl -sS -o /dev/null -w "sse_page %{http_code}\n" http://127.0.0.1:8100/strategies/sse-510210
curl -sS -o /dev/null -w "mnq_page %{http_code}\n" http://127.0.0.1:8100/strategies/mnq-dip
echo "==> hotfix-sse-mnq 完成"
