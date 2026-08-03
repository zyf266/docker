#!/bin/bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cd /opt/backpack-quant
grep -n "沐龙" backpack_quant_trading/frontend/src/views/AlphaEthStrategy.jsx \
  backpack_quant_trading/frontend/src/views/StrategyMatrixAlt.jsx \
  backpack_quant_trading/api/routers/strategy.py | head -10

docker cp backpack_quant_trading/api/routers/strategy.py \
  backpack-api:/app/backpack_quant_trading/api/routers/strategy.py

docker run --rm \
  -v /opt/backpack-quant/backpack_quant_trading/frontend:/build \
  -w /build node:20-alpine \
  sh -c 'npm ci --ignore-scripts 2>/dev/null || npm install; npm run build'

docker exec backpack-api rm -rf /app/backpack_quant_trading/frontend/dist
docker cp backpack_quant_trading/frontend/dist \
  backpack-api:/app/backpack_quant_trading/frontend/dist
docker restart backpack-api

for i in $(seq 1 20); do
  curl -sf http://127.0.0.1:8100/api/health >/dev/null && break
  sleep 2
done

curl -sS http://127.0.0.1:8100/api/strategy/alpha-eth-2h/overview
echo
echo DONE
