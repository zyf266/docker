#!/bin/bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cd /opt/backpack-quant
docker cp /tmp/dingtalk_bridge.py backpack-dingtalk-agent:/app/backpack_quant_trading/agents/dingtalk_bridge.py
docker cp /tmp/steward_agent.py backpack-dingtalk-agent:/app/backpack_quant_trading/agents/steward_agent.py
docker cp /tmp/steward_agent.py backpack-api:/app/backpack_quant_trading/agents/steward_agent.py
docker restart backpack-api backpack-dingtalk-agent
sleep 16
curl -sf http://127.0.0.1:8100/api/health
echo
docker exec backpack-dingtalk-agent python -c "
from backpack_quant_trading.agents.dingtalk_bridge import should_route_to_agent
from backpack_quant_trading.agents.steward_agent import parse_steward_intent
s='给我新增一个  ETH  1H 水下死叉转水上金叉'
i=parse_steward_intent(s)
print(should_route_to_agent(s), i.action, i.params)
assert should_route_to_agent(s) and i.action=='macd_add'
print('ROUTE_OK')
"
TOK=$(grep -E '^WEBHOOK_SECRET=' .env | head -1 | cut -d= -f2-)
python3 - <<PY
import json, urllib.request
tok = """$TOK"""
text = "给我新增一个  ETH  1H 水下死叉转水上金叉"
body = json.dumps({"text": text}, ensure_ascii=False).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8100/api/steward/command",
    data=body, method="POST",
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
)
print(urllib.request.urlopen(req, timeout=60).read().decode()[:500])
PY
pgrep -af openclaw-gateway || echo NO_OPENCLAW
