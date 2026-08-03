#!/bin/bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
docker cp /tmp/steward_agent.py backpack-api:/app/backpack_quant_trading/agents/steward_agent.py
docker cp /tmp/steward_agent.py backpack-dingtalk-agent:/app/backpack_quant_trading/agents/steward_agent.py
docker cp /tmp/dingtalk_bridge.py backpack-dingtalk-agent:/app/backpack_quant_trading/agents/dingtalk_bridge.py
docker restart backpack-api backpack-dingtalk-agent
sleep 16
curl -sf http://127.0.0.1:8100/api/health
echo
python3 - <<'PY'
import json, urllib.request
tok = open("/opt/backpack-quant/.env", encoding="utf-8").read().split("WEBHOOK_SECRET=",1)[1].splitlines()[0].strip()

def call(text):
    body = json.dumps({"text": text}, ensure_ascii=False).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8100/api/steward/command",
        data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
    )
    raw = urllib.request.urlopen(req, timeout=90).read().decode()
    data = json.loads(raw)
    print(text)
    print(" ok=", data.get("ok"), (data.get("markdown") or "")[:260].replace("\n", " | "))
    print("---")
    return data

# ensure something to remove then remove
call("新增 ZEC 1h 币种监视")
call("给我把zec 1h的币种监视给停止了")
call("停止 ETH 1h 死叉转水下金叉")
call("删除 BTC 合约预警")
print("STOP_API_OK")
PY
