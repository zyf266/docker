#!/bin/bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cp /tmp/dingtalk_bridge.py /tmp/steward_agent.py /opt/backpack-quant/backpack_quant_trading/agents/
cp /tmp/dingtalk_score_bot.py /opt/backpack-quant/backpack_quant_trading/

docker cp /tmp/dingtalk_bridge.py backpack-dingtalk-agent:/app/backpack_quant_trading/agents/dingtalk_bridge.py
docker cp /tmp/steward_agent.py backpack-dingtalk-agent:/app/backpack_quant_trading/agents/steward_agent.py
docker cp /tmp/dingtalk_score_bot.py backpack-dingtalk-agent:/app/backpack_quant_trading/dingtalk_score_bot.py
docker cp /tmp/steward_agent.py backpack-api:/app/backpack_quant_trading/agents/steward_agent.py
docker cp /tmp/test_steward_route.py backpack-dingtalk-agent:/tmp/test_steward_route.py

docker restart backpack-dingtalk-agent backpack-api
sleep 18
curl -sf http://127.0.0.1:8100/api/health
echo
docker exec backpack-dingtalk-agent python /tmp/test_steward_route.py

TOK=$(grep -E '^WEBHOOK_SECRET=' /opt/backpack-quant/.env | head -1 | cut -d= -f2-)
python3 - <<PY
import json, urllib.request
tok = """$TOK"""
body = json.dumps({"text": "增加一个SOL的合约监控，所有配置都默认"}, ensure_ascii=False).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8100/api/steward/command",
    data=body,
    method="POST",
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
)
print(urllib.request.urlopen(req, timeout=60).read().decode()[:600])
PY

docker ps --format '{{.Names}} {{.Status}}' | grep -E 'api|dingtalk'
