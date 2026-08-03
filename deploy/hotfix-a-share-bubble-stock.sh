#!/bin/bash
# 热更：策略A 钉钉调用 + 个股报告 UI + 东财直连
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cd /opt/backpack-quant

inject_py() {
  local c="$1"
  docker exec "$c" mkdir -p \
    /app/backpack_quant_trading/core \
    /app/backpack_quant_trading/api/routers \
    /app/backpack_quant_trading/agents || true
  docker cp backpack_quant_trading/core/bubble_weekly_prompts.py \
    "$c:/app/backpack_quant_trading/core/bubble_weekly_prompts.py"
  docker cp backpack_quant_trading/api/routers/us_weekly_report.py \
    "$c:/app/backpack_quant_trading/api/routers/us_weekly_report.py"
  docker cp backpack_quant_trading/agents/coordinator.py \
    "$c:/app/backpack_quant_trading/agents/coordinator.py"
  docker cp backpack_quant_trading/agents/dingtalk_bridge.py \
    "$c:/app/backpack_quant_trading/agents/dingtalk_bridge.py"
  docker cp backpack_quant_trading/agents/intent_router.py \
    "$c:/app/backpack_quant_trading/agents/intent_router.py"
  docker cp backpack_quant_trading/agents/a_share_resolve.py \
    "$c:/app/backpack_quant_trading/agents/a_share_resolve.py"
  docker cp backpack_quant_trading/dingtalk_score_bot.py \
    "$c:/app/backpack_quant_trading/dingtalk_score_bot.py" || true
}

inject_py backpack-api
inject_py backpack-dingtalk-agent

if [ -d backpack_quant_trading/frontend/dist ]; then
  docker exec backpack-api mkdir -p /app/backpack_quant_trading/frontend/dist
  docker cp backpack_quant_trading/frontend/dist/. \
    backpack-api:/app/backpack_quant_trading/frontend/dist/
  echo "frontend dist injected"
fi

docker restart backpack-api backpack-dingtalk-agent
sleep 22
curl -sf http://127.0.0.1:8100/api/health
echo

docker exec backpack-api python - <<'PY'
from backpack_quant_trading.agents.coordinator import _parse_stock_strategy_request
from backpack_quant_trading.agents.dingtalk_bridge import should_route_to_agent
from backpack_quant_trading.api.routers.us_weekly_report import (
    markdown_for_dingtalk,
    _resolve_stock_symbol,
)

assert _parse_stock_strategy_request("给我一份利通电子 策略A的报告")[0] == "A"
assert _parse_stock_strategy_request("给我一份 NVDA 策略A的报告")[0] == "A"
assert should_route_to_agent("给我一份 NVDA 策略A的报告")
code, name, mkt, err = _resolve_stock_symbol("NVDA")
assert mkt == "us" and code == "NVDA" and not err
md = markdown_for_dingtalk("|a|b|\n|---|---|\n|1|2|\n")
assert "- " in md and "|" not in md.splitlines()[0]
print("dingtalk_stock_strategy_ok")
PY

if docker exec backpack-api sh -c 'grep -Rql "市场周报\|个股分析\|NVDA" /app/backpack_quant_trading/frontend/dist/assets 2>/dev/null'; then
  echo "frontend_strings_ok"
fi

echo "DONE: 网页 Ctrl+F5；个股分析可输 NVDA；钉钉「给我一份 NVDA 策略A的报告」"
