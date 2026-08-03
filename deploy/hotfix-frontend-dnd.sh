#!/bin/bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cd /opt/backpack-quant

# 若文件已在 /tmp，先落到源码目录
[ -f /tmp/StrategyMatrixAlt.jsx ] && cp -f /tmp/StrategyMatrixAlt.jsx backpack_quant_trading/frontend/src/views/StrategyMatrixAlt.jsx
[ -f /tmp/StrategyCardMatrix.jsx ] && cp -f /tmp/StrategyCardMatrix.jsx backpack_quant_trading/frontend/src/components/StrategyCardMatrix.jsx

grep -n "拖拽卡片\|ORDER_STORAGE_KEY\|GripVertical\|draggable" \
  backpack_quant_trading/frontend/src/views/StrategyMatrixAlt.jsx \
  backpack_quant_trading/frontend/src/components/StrategyCardMatrix.jsx | head -15

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

echo "health: $(curl -sf http://127.0.0.1:8100/api/health)"
# 确认新 bundle 含拖拽文案
docker exec backpack-api sh -c 'grep -l "strategy-matrix-card-order\|拖拽卡片" /app/backpack_quant_trading/frontend/dist/assets/*.js | head -3 || true'
echo DONE
