#!/bin/bash
# 币安代理健康巡检：挂了尝试探测节点；全部不可用则钉钉告警（带冷却）
# 告警优先走 AGENT_OPS_DINGTALK_WEBHOOK（运维群），不再默认推山寨标的群 DINGTALK_TOKEN
set -uo pipefail
API="${MIHOMO_API:-http://127.0.0.1:9090}"
PROXY="${BINANCE_PROXY:-http://127.0.0.1:7891}"
STATE_DIR="${STATE_DIR:-/var/lib/backpack-quant}"
STATE_FILE="$STATE_DIR/binance_proxy_watchdog.state"
LOG_FILE="${LOG_FILE:-/var/log/binance-proxy-watchdog.log}"
COOLDOWN_SEC="${ALERT_COOLDOWN_SEC:-1800}"
NODES_JSON="${NODES_JSON:-/opt/backpack-quant/deploy/binance-proxy-nodes.json}"
ENV_FILE="${ENV_FILE:-/opt/backpack-quant/.env}"

mkdir -p "$STATE_DIR"
touch "$LOG_FILE"

log() { echo "$(date '+%F %T') $*" | tee -a "$LOG_FILE"; }

binance_ok() {
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 -x "$PROXY" \
    https://fapi.binance.com/fapi/v1/ping 2>/dev/null || echo 000)
  [[ "$code" == "200" ]]
}

load_dingtalk_url() {
  WEBHOOK_URL=""
  if [[ -f "$ENV_FILE" ]]; then
    WEBHOOK_URL=$(grep -E '^AGENT_OPS_DINGTALK_WEBHOOK=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
    if [[ -z "$WEBHOOK_URL" ]]; then
      local token secret
      token=$(grep -E '^DINGTALK_TOKEN=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
      secret=$(grep -E '^DINGTALK_SECRET=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
      if [[ -n "$token" ]]; then
        WEBHOOK_URL="https://oapi.dingtalk.com/robot/send?access_token=${token}"
        if [[ -n "$secret" ]]; then
          local ts sign
          ts=$(date +%s%3N)
          sign=$(python3 - "$secret" "$ts" <<'PY'
import sys, hmac, hashlib, base64, urllib.parse
secret, ts = sys.argv[1], sys.argv[2]
s = f"{ts}\n{secret}"
sign = urllib.parse.quote_plus(base64.b64encode(hmac.new(secret.encode(), s.encode(), hashlib.sha256).digest()))
print(sign)
PY
)
          WEBHOOK_URL="${WEBHOOK_URL}&timestamp=${ts}&sign=${sign}"
        fi
      fi
    fi
  fi
  WEBHOOK_URL="${WEBHOOK_URL:-${AGENT_OPS_DINGTALK_WEBHOOK:-}}"
}

send_dingtalk() {
  local title="$1" text="$2"
  load_dingtalk_url
  if [[ -z "$WEBHOOK_URL" ]]; then
    log "ALERT skip: no AGENT_OPS_DINGTALK_WEBHOOK / DINGTALK_TOKEN"
    return 1
  fi
  local payload
  payload=$(python3 - "$title" "$text" <<'PY'
import json,sys
title, text = sys.argv[1], sys.argv[2]
# 真实换行（调用方传入的 \n 字面量也转成换行）
text = text.replace("\\n", "\n")
print(json.dumps({
  "msgtype": "markdown",
  "markdown": {"title": title, "text": text[:3500]},
}, ensure_ascii=False))
PY
)
  curl -sS --max-time 10 -H 'Content-Type: application/json' -d "$payload" "$WEBHOOK_URL" | tee -a "$LOG_FILE"
  echo >> "$LOG_FILE"
}

probe_nodes() {
  python3 - "$API" "$NODES_JSON" <<'PY'
import json, sys, urllib.request, urllib.parse
api, path = sys.argv[1], sys.argv[2]
nodes = []
try:
    data = json.load(open(path, encoding="utf-8"))
    nodes = [x["name"] for x in data.get("nodes") or []]
except Exception as e:
    print("nodes_json_err", e)
    sys.exit(0)
ok = []
for name in nodes:
    enc = urllib.parse.quote(name)
    url = f"{api}/proxies/{enc}/delay?timeout=4000&url=https%3A%2F%2Ffapi.binance.com%2Ffapi%2Fv1%2Fping"
    try:
        d = json.load(urllib.request.urlopen(url, timeout=6))
        delay = d.get("delay")
        if isinstance(delay, int) and delay > 0:
            ok.append((delay, name))
            print(f"node_ok {delay}ms {name}")
    except Exception as e:
        print(f"node_fail {name} {e}")
if not ok:
    print("ALL_NODES_DOWN")
    sys.exit(2)
ok.sort()
best = ok[0][1]
print("BEST", best)
for group, node in (("GLOBAL", "币安专线"), ("主代理", "币安专线")):
    body = json.dumps({"name": node}).encode()
    req = urllib.request.Request(
        api + "/proxies/" + urllib.parse.quote(group),
        data=body, headers={"Content-Type": "application/json"}, method="PUT",
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass
sys.exit(0)
PY
}

should_alert() {
  local now last
  now=$(date +%s)
  last=0
  if [[ -f "$STATE_FILE" ]]; then
    last=$(python3 -c "import json;print(json.load(open('$STATE_FILE')).get('last_alert_ts',0))" 2>/dev/null || echo 0)
  fi
  [[ $((now - last)) -ge $COOLDOWN_SEC ]]
}

mark_alert() {
  python3 - <<PY
import json, time
from pathlib import Path
p=Path("$STATE_FILE")
obj={}
if p.exists():
  try: obj=json.loads(p.read_text())
  except: obj={}
obj["last_alert_ts"]=int(time.time())
obj["last_status"]="down"
p.write_text(json.dumps(obj))
PY
}

mark_ok() {
  python3 - <<PY
import json, time
from pathlib import Path
p=Path("$STATE_FILE")
obj={}
if p.exists():
  try: obj=json.loads(p.read_text())
  except: obj={}
prev=obj.get("last_status")
obj["last_ok_ts"]=int(time.time())
obj["last_status"]="ok"
p.write_text(json.dumps(obj))
print(prev or "")
PY
}

# --- main ---
if binance_ok; then
  prev=$(mark_ok)
  ip=$(curl -s --max-time 10 -x "$PROXY" https://api.ipify.org 2>/dev/null || echo "?")
  log "OK binance ping via $PROXY egress=$ip"
  if [[ "$prev" == "down" ]]; then
    # 用 $'...' 产生真实换行，避免钉钉显示字面 \n
    send_dingtalk "币安代理已恢复" \
      $'### 币安代理已恢复\n\n- 时间: '"$(date '+%F %T')"$'\n- 出口: `'"$ip"$'`\n- 探测: fapi.binance.com/ping → 200\n'
  fi
  exit 0
fi

log "WARN binance ping failed, probing nodes..."
set +e
probe_out=$(probe_nodes 2>&1)
probe_rc=$?
set -e
log "$probe_out"

sleep 2
if binance_ok; then
  mark_ok >/dev/null
  ip=$(curl -s --max-time 10 -x "$PROXY" https://api.ipify.org 2>/dev/null || echo "?")
  log "RECOVERED after probe egress=$ip"
  exit 0
fi

log "CRITICAL all binance proxy paths down"
if should_alert; then
  send_dingtalk "币安代理全部不可用" \
    $'### ⚠️ 币安代理全部不可用\n\n- 时间: '"$(date '+%F %T')"$'\n- 影响: 合约余额/下单/评分透传可能失败，TradingView 信号可能无法成交\n- 探测: `fapi.binance.com/ping` 经 `7891` 失败\n- 节点探测:\n```\n'"${probe_out}"$'\n```\n- 请检查 mihomo 订阅/节点，并确认白名单 IP 仍有效\n'
  mark_alert
else
  log "alert suppressed (cooldown ${COOLDOWN_SEC}s)"
fi
exit 1
