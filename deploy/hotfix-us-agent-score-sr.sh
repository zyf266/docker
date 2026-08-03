#!/bin/bash
# 热更：停用宿主机 tradingview_bot 旧美股评分海报，统一 Agent；过滤贴价 S/R
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"

BQ=/opt/backpack-quant
END=/opt/trading/ending

sync_tree() {
  local dest="$1"
  mkdir -p "$dest/backpack_quant_trading/core" "$dest/backpack_quant_trading/agents"
  cp -f "$BQ/backpack_quant_trading/core/crypto_signal_scorer.py" \
    "$dest/backpack_quant_trading/core/crypto_signal_scorer.py"
  cp -f "$BQ/backpack_quant_trading/core/us_stock_signal_scorer.py" \
    "$dest/backpack_quant_trading/core/us_stock_signal_scorer.py"
  cp -f "$BQ/backpack_quant_trading/core/dingtalk_manual_score.py" \
    "$dest/backpack_quant_trading/core/dingtalk_manual_score.py" 2>/dev/null || true
  cp -f "$BQ/backpack_quant_trading/agents/scheduler_hooks.py" \
    "$dest/backpack_quant_trading/agents/scheduler_hooks.py"
  cp -f "$BQ/tradingview_bot.py" "$dest/tradingview_bot.py"
}

# 1) Docker 栈
cd "$BQ"
for c in backpack-api backpack-webhook backpack-dingtalk-agent; do
  docker exec "$c" mkdir -p /app/backpack_quant_trading/core /app/backpack_quant_trading/agents
  docker cp backpack_quant_trading/core/crypto_signal_scorer.py \
    "$c:/app/backpack_quant_trading/core/crypto_signal_scorer.py"
  docker cp backpack_quant_trading/core/us_stock_signal_scorer.py \
    "$c:/app/backpack_quant_trading/core/us_stock_signal_scorer.py"
  docker cp backpack_quant_trading/agents/scheduler_hooks.py \
    "$c:/app/backpack_quant_trading/agents/scheduler_hooks.py"
done
docker restart backpack-api backpack-webhook backpack-dingtalk-agent

# 2) 宿主机旧链路 /opt/trading/ending（美股「实盘交易」走这里）
sync_tree "$END"
# 同步到 backpack-quant 根目录副本
cp -f "$BQ/tradingview_bot.py" "$BQ/tradingview_bot.py.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true

# 重启 tradingview_bot（pid 可能变化）
OLD_PID=$(ss -tlnp 2>/dev/null | grep ':5001' | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1 || true)
if [ -n "${OLD_PID:-}" ]; then
  echo "stopping tradingview_bot pid=$OLD_PID"
  kill "$OLD_PID" || true
  sleep 2
  kill -9 "$OLD_PID" 2>/dev/null || true
fi

cd "$END"
export AGENT_ORCH_ENABLED=1
export AGENT_REPLACE_LEGACY_PUSH=1
nohup python tradingview_bot.py >> /opt/trading/ending/log/tradingview_bot.out 2>&1 &
sleep 3
ss -tlnp | grep 5001 || { echo "FAIL: port 5001 not up"; exit 1; }
curl -sf http://127.0.0.1:5001/health
echo
curl -sf http://127.0.0.1:8100/api/health
echo
echo "DONE: tradingview_bot + docker 已切 Agent 评分；S/R 最小距离已抬高"
