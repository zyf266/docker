#!/bin/bash
set -euo pipefail
cd /opt/backpack-quant

cp /tmp/dingtalk_bridge.py /tmp/steward_agent.py backpack_quant_trading/agents/ 2>/dev/null || true
cp /tmp/dingtalk_score_bot.py backpack_quant_trading/ 2>/dev/null || true

# keep openclaw masked
if [ ! -L /root/.config/systemd/user/openclaw-gateway.service ] || [ "$(readlink /root/.config/systemd/user/openclaw-gateway.service)" != "/dev/null" ]; then
  export XDG_RUNTIME_DIR=/run/user/0
  systemctl --user stop openclaw-gateway 2>/dev/null || true
  systemctl --user disable openclaw-gateway 2>/dev/null || true
  mv -f /root/.config/systemd/user/openclaw-gateway.service /root/.config/systemd/user/openclaw-gateway.service.disabled 2>/dev/null || true
  ln -sfn /dev/null /root/.config/systemd/user/openclaw-gateway.service
  systemctl --user daemon-reload 2>/dev/null || true
fi
pkill -9 -f 'openclaw-gateway' 2>/dev/null || true

inject() {
  local c="$1"
  docker cp /tmp/dingtalk_bridge.py "$c:/app/backpack_quant_trading/agents/dingtalk_bridge.py"
  docker cp /tmp/steward_agent.py "$c:/app/backpack_quant_trading/agents/steward_agent.py"
}
inject backpack-dingtalk-agent
inject backpack-api
docker cp /tmp/dingtalk_score_bot.py backpack-dingtalk-agent:/app/backpack_quant_trading/dingtalk_score_bot.py
docker cp /tmp/test_steward_route.py backpack-dingtalk-agent:/tmp/test_steward_route.py

docker restart backpack-api backpack-dingtalk-agent
sleep 18
curl -sf http://127.0.0.1:8100/api/health
echo

docker exec backpack-dingtalk-agent python /tmp/test_steward_route.py

TOK=$(grep -E '^WEBHOOK_SECRET=' .env | head -1 | cut -d= -f2-)
python3 - <<PY
import json, urllib.request
tok = """$TOK"""
for text in [
    "增加一个SOL 2h的币种监视",
    "给我监控一个NVDA关于财报的新闻",
]:
    body = json.dumps({"text": text}, ensure_ascii=False).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8100/api/steward/command",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
    )
    raw = urllib.request.urlopen(req, timeout=90).read().decode()
    print(text)
    print(raw[:450])
    print("---")
PY

echo "=== openclaw ==="
pgrep -af 'openclaw-gateway' || echo NO_OPENCLAW
echo "=== stream ==="
docker logs backpack-dingtalk-agent --tail 10 2>&1
