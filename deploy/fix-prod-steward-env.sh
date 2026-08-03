#!/bin/bash
set -e
ENV=/opt/backpack-quant/.env
cd /opt/backpack-quant

if ! grep -qE '^WEBHOOK_SECRET=' "$ENV"; then
  SEC=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
  echo "WEBHOOK_SECRET=$SEC" >> "$ENV"
  echo "added WEBHOOK_SECRET"
else
  echo "WEBHOOK_SECRET already present"
fi

WS=$(grep -E '^WEBHOOK_SECRET=' "$ENV" | head -1 | cut -d= -f2-)
if grep -qE '^AGENT_STEWARD_TOKEN=' "$ENV"; then
  sed -i "s|^AGENT_STEWARD_TOKEN=.*|AGENT_STEWARD_TOKEN=$WS|" "$ENV"
else
  echo "AGENT_STEWARD_TOKEN=$WS" >> "$ENV"
fi

if ! grep -qE '^AGENT_API_BASE=' "$ENV"; then
  echo 'AGENT_API_BASE=http://api:8100' >> "$ENV"
fi

echo "env keys:"
grep -E '^(WEBHOOK_SECRET|AGENT_STEWARD_TOKEN|AGENT_API_BASE)=' "$ENV" | sed 's/=.*/=***/'

export SKIP_MYSQL=1
docker compose up -d --force-recreate api webhook dingtalk-agent
sleep 14
curl -sf http://127.0.0.1:8100/api/health; echo

echo -n "api WEBHOOK len="; docker exec backpack-api printenv WEBHOOK_SECRET | wc -c
echo -n "dingtalk WEBHOOK len="; docker exec backpack-dingtalk-agent printenv WEBHOOK_SECRET | wc -c
echo -n "dingtalk AGENT_API="; docker exec backpack-dingtalk-agent printenv AGENT_API_BASE

docker exec backpack-dingtalk-agent python - <<'PY'
import os, json, urllib.request
base = (os.getenv("AGENT_API_BASE") or "http://api:8100").rstrip("/")
tok = (os.getenv("AGENT_STEWARD_TOKEN") or os.getenv("WEBHOOK_SECRET") or "").strip()
print("token_len", len(tok))
url = base + "/api/steward/command"
body = json.dumps({"text": "查看当前币种监视状态", "staff_id": "fix"}, ensure_ascii=False).encode()
req = urllib.request.Request(
    url,
    data=body,
    method="POST",
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
)
try:
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode())
    md = (data.get("markdown") or "")[:400]
    print("ok=", data.get("ok"))
    print("md=", md.replace("\n", " | "))
except Exception as e:
    print("CALL_FAIL", repr(e))
PY
