#!/bin/bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cd /opt/backpack-quant

grep -q '^AGENT_API_BASE=' .env || echo 'AGENT_API_BASE=http://api:8100' >> .env

inject() {
  local c="$1"
  docker cp backpack_quant_trading/api/deps.py "$c:/app/backpack_quant_trading/api/deps.py"
  docker cp backpack_quant_trading/api/main.py "$c:/app/backpack_quant_trading/api/main.py"
  docker cp backpack_quant_trading/api/routers/steward.py "$c:/app/backpack_quant_trading/api/routers/steward.py"
  docker cp backpack_quant_trading/agents/steward_agent.py "$c:/app/backpack_quant_trading/agents/steward_agent.py"
  docker cp backpack_quant_trading/agents/dingtalk_bridge.py "$c:/app/backpack_quant_trading/agents/dingtalk_bridge.py"
  docker cp backpack_quant_trading/core/dingtalk_manual_score.py "$c:/app/backpack_quant_trading/core/dingtalk_manual_score.py"
}

# Keep running containers; inject then restart (no compose recreate)
inject backpack-api
inject backpack-dingtalk-agent
docker restart backpack-api backpack-dingtalk-agent
sleep 20
curl -sf http://127.0.0.1:8100/api/health
echo

docker exec backpack-api python -c "from backpack_quant_trading.api.routers import steward; from backpack_quant_trading.api.deps import steward_token_ok; print('route_ok', len(steward.router.routes))"

TOK=$(grep -E '^WEBHOOK_SECRET=' .env | head -1 | cut -d= -f2-)
export STEWARD_TOK="$TOK"

python3 - <<'PY'
import json, os, urllib.request

tok = os.environ["STEWARD_TOK"]
url = "http://127.0.0.1:8100/api/steward/command"

def call(text):
    body = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("HTTP", resp.status, "| ok=", data.get("ok"), "| steward=", data.get("steward"))
            md = (data.get("markdown") or "")[:280]
            print(md.replace("\n", " | "))
            print("---")
            return data
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode("utf-8", "replace")[:300])
        print("---")
        return None

cases = [
    "@小管家",
    "@小管家 帮我新增一个ETH 2h的币种监视",
    "@小管家 新增一个BTC 1分钟合约监视，除了订单薄改成2000000，其他参数默认",
    "@小管家 给我增加一个MACD金叉形态 ETH 1h，死叉转水上金叉",
    "@小管家 给我增加一个NVDA 上调评级的新闻监控",
    "@小管家 当前监视状态",
]
for c in cases:
    print("CASE:", c)
    call(c)
PY

docker ps --format '{{.Names}} {{.Status}}' | grep -E 'api|dingtalk'
