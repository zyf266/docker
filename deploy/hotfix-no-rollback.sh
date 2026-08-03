#!/bin/bash
# 热更时禁止用宿主机「旧 dist / 旧策略」覆盖容器。
# 用法：先把本地最新源码 scp 到 /tmp，再执行本脚本；或由 CI 在同步源码后调用。
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
ROOT="${ROOT:-/opt/backpack-quant}"
cd "$ROOT"

echo "==> 同步关键 Python 模块到宿主机与容器（避免 trading 新、strategy 旧）"
PY_FILES=(
  backpack_quant_trading/strategy/adaptive_long_strategy.py
  backpack_quant_trading/strategy/adaptive_short_strategy.py
  backpack_quant_trading/api/routers/trading.py
  backpack_quant_trading/frontend/src/layouts/MainLayout.jsx
  backpack_quant_trading/frontend/src/views/UsWeeklyReport.jsx
  backpack_quant_trading/frontend/src/views/Dashboard.jsx
)
for f in "${PY_FILES[@]}"; do
  if [ -f "/tmp/$(basename "$f")" ] && [[ "$f" == *.py || "$f" == *.jsx ]]; then
    :
  fi
done

# 若 /tmp 有明确投放的文件则优先用
[ -f /tmp/binance_client.py ] && cp -f /tmp/binance_client.py backpack_quant_trading/core/
[ -f /tmp/adaptive_long_strategy.py ] && cp -f /tmp/adaptive_long_strategy.py backpack_quant_trading/strategy/
[ -f /tmp/adaptive_short_strategy.py ] && cp -f /tmp/adaptive_short_strategy.py backpack_quant_trading/strategy/
[ -f /tmp/auto_close_strategy.py ] && cp -f /tmp/auto_close_strategy.py backpack_quant_trading/strategy/
[ -f /tmp/trading.py ] && cp -f /tmp/trading.py backpack_quant_trading/api/routers/trading.py
[ -f /tmp/MainLayout.jsx ] && cp -f /tmp/MainLayout.jsx backpack_quant_trading/frontend/src/layouts/
[ -f /tmp/UsWeeklyReport.jsx ] && cp -f /tmp/UsWeeklyReport.jsx backpack_quant_trading/frontend/src/views/
[ -f /tmp/Dashboard.jsx ] && cp -f /tmp/Dashboard.jsx backpack_quant_trading/frontend/src/views/

echo "==> 确保 lighter-sdk 在 api 容器内"
docker exec backpack-api python3 -c "import lighter" 2>/dev/null || \
  docker exec backpack-api pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn "lighter-sdk>=1.1.0"

echo "==> 拷贝客户端/策略/路由到容器（成套同步，避免 margin_type 半更新）"
docker cp backpack_quant_trading/core/binance_client.py backpack-api:/app/backpack_quant_trading/core/binance_client.py
docker cp backpack_quant_trading/strategy/adaptive_long_strategy.py backpack-api:/app/backpack_quant_trading/strategy/adaptive_long_strategy.py
docker cp backpack_quant_trading/strategy/adaptive_short_strategy.py backpack-api:/app/backpack_quant_trading/strategy/adaptive_short_strategy.py
docker cp backpack_quant_trading/strategy/auto_close_strategy.py backpack-api:/app/backpack_quant_trading/strategy/auto_close_strategy.py 2>/dev/null || true
docker cp backpack_quant_trading/api/routers/trading.py backpack-api:/app/backpack_quant_trading/api/routers/trading.py
if docker ps --format '{{.Names}}' | grep -q '^backpack-webhook$'; then
  docker cp backpack_quant_trading/core/binance_client.py backpack-webhook:/app/backpack_quant_trading/core/binance_client.py
  docker cp backpack_quant_trading/strategy/adaptive_long_strategy.py backpack-webhook:/app/backpack_quant_trading/strategy/adaptive_long_strategy.py
  docker cp backpack_quant_trading/strategy/adaptive_short_strategy.py backpack-webhook:/app/backpack_quant_trading/strategy/adaptive_short_strategy.py
  docker cp backpack_quant_trading/api/routers/trading.py backpack-webhook:/app/backpack_quant_trading/api/routers/trading.py 2>/dev/null || true
fi

echo "==> 用当前宿主机 frontend/src 重新 build（禁止回退到旧 dist）"
docker run --rm -v "$ROOT/backpack_quant_trading/frontend:/app" -w /app node:20-alpine sh -c 'npm ci && npm run build'
# 校验关键文案未回退
js=$(ls -1 backpack_quant_trading/frontend/dist/assets/index-*.js | head -1)
grep -q '泡沫检测' "$js" || { echo "FAIL: dist 缺少「泡沫检测」"; exit 1; }
grep -q 'label:"学习中心"' "$js" && { echo "FAIL: dist 仍暴露学习中心入口"; exit 1; } || true
grep -q '美股泡沫阶段监测' "$js" && { echo "FAIL: dist 仍含旧文案 美股泡沫阶段监测"; exit 1; } || true
echo "frontend checks OK: $js"

docker exec backpack-api rm -rf /app/backpack_quant_trading/frontend/dist
docker cp backpack_quant_trading/frontend/dist backpack-api:/app/backpack_quant_trading/frontend/dist

docker restart backpack-api
for i in $(seq 1 30); do curl -fsS http://127.0.0.1:8100/api/health >/dev/null 2>&1 && break; sleep 2; done

docker exec backpack-api python3 -c "
import inspect
from backpack_quant_trading.strategy.adaptive_long_strategy import AdaptiveLongStrategy
sig = inspect.signature(AdaptiveLongStrategy.__init__)
assert 'margin_type' in sig.parameters, sig
print('margin_type OK')
"
echo DONE
