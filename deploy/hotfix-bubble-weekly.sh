#!/bin/bash
# 热更：泡沫阶段监测（美股/A股周报 + 钉钉 @分析师 周报入口）
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cd /opt/backpack-quant

inject() {
  local c="$1"
  docker cp backpack_quant_trading/core/bubble_weekly_prompts.py \
    "$c:/app/backpack_quant_trading/core/bubble_weekly_prompts.py"
  docker cp backpack_quant_trading/api/routers/us_weekly_report.py \
    "$c:/app/backpack_quant_trading/api/routers/us_weekly_report.py"
  docker cp backpack_quant_trading/api/main.py \
    "$c:/app/backpack_quant_trading/api/main.py"
  docker cp backpack_quant_trading/agents/coordinator.py \
    "$c:/app/backpack_quant_trading/agents/coordinator.py"
  docker cp backpack_quant_trading/agents/dingtalk_bridge.py \
    "$c:/app/backpack_quant_trading/agents/dingtalk_bridge.py"
  docker cp backpack_quant_trading/agents/a_share_resolve.py \
    "$c:/app/backpack_quant_trading/agents/a_share_resolve.py"
}

# 前端静态资源（若容器内有 frontend/dist，一并注入源文件供下次 build；运行中的 nginx 需 compose build 才生效）
inject backpack-api
inject backpack-dingtalk-agent

docker restart backpack-api backpack-dingtalk-agent
sleep 18
curl -sf http://127.0.0.1:8100/api/health
echo

docker exec backpack-api python - <<'PY'
from backpack_quant_trading.core.bubble_weekly_prompts import normalize_market, get_system_prompt
from backpack_quant_trading.agents.coordinator import _is_bubble_weekly_request, parse_route
assert normalize_market("a_share") == "a_share"
assert "工程师" in get_system_prompt("us")
h = parse_route("@美股分析师 这周美股周报")
assert not h.symbols
assert _is_bubble_weekly_request("@美股分析师 这周美股周报")
print("bubble_weekly_ok")
PY

echo "NOTE: 前端「美股/A股切换」需重新 build web 镜像后才上线；API/钉钉周报已热更。"
