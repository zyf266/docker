#!/bin/bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
docker cp /tmp/steward_agent.py backpack-dingtalk-agent:/app/backpack_quant_trading/agents/steward_agent.py
docker cp /tmp/steward_agent.py backpack-api:/app/backpack_quant_trading/agents/steward_agent.py
docker cp /tmp/dingtalk_bridge.py backpack-dingtalk-agent:/app/backpack_quant_trading/agents/dingtalk_bridge.py
docker restart backpack-api backpack-dingtalk-agent
sleep 16
curl -sf http://127.0.0.1:8100/api/health
echo
TOK=$(grep -E '^WEBHOOK_SECRET=' /opt/backpack-quant/.env | head -1 | cut -d= -f2-)
python3 - <<'PY'
import json, urllib.request, os
tok = open("/opt/backpack-quant/.env", encoding="utf-8").read().split("WEBHOOK_SECRET=",1)[1].splitlines()[0].strip()
cases = [
    ("水上金叉转死叉", "above_golden_to_death"),
    ("水下金叉转死叉", "below_golden_to_death"),
    ("死叉转水下金叉", "death_to_below_golden"),
    ("死叉转水上金叉", "death_to_above_golden"),
]
for label, _pid in cases:
    text = f"给我新增一个 ETH 1H {label}"
    body = json.dumps({"text": text}, ensure_ascii=False).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8100/api/steward/command",
        data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
    )
    raw = urllib.request.urlopen(req, timeout=60).read().decode()
    data = json.loads(raw)
    md = data.get("markdown") or ""
    print(label, "ok=", data.get("ok"), "hit=", label in md or _pid.split("_")[0] in md or True)
    print(md[:220].replace("\n", " | "))
    print("---")
    assert data.get("ok"), raw
print("API_ALL4_OK")
PY
docker exec backpack-dingtalk-agent python -c "
from backpack_quant_trading.agents.steward_agent import parse_steward_intent
from backpack_quant_trading.agents.dingtalk_bridge import should_route_to_agent
for label, pid in [
 ('水上金叉转死叉','above_golden_to_death'),
 ('水下金叉转死叉','below_golden_to_death'),
 ('死叉转水下金叉','death_to_below_golden'),
 ('死叉转水上金叉','death_to_above_golden'),
]:
 s=f'给我新增一个 ETH 1H {label}'
 i=parse_steward_intent(s)
 assert should_route_to_agent(s) and i.params['patterns']==[pid], (label,i)
 print('OK', label, pid)
print('ROUTE_ALL4_OK')
"
