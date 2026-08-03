#!/bin/bash
# 将「币安专线」改为多地区 fallback，并写回主代理/GLOBAL
set -euo pipefail
CFG=/root/.config/mihomo/config.yaml
API=http://127.0.0.1:9090
TS=$(date +%Y%m%d%H%M%S)
cp -a "$CFG" "${CFG}.bak.fallback.${TS}"

python3 <<'PY'
from pathlib import Path
import re
p = Path("/root/.config/mihomo/config.yaml")
text = p.read_text(encoding="utf-8")
new_block = """  - name: 币安专线
    type: fallback
    proxies:
      - 香港pump1
      - v5-香港02|1x|v-人少推荐
      - 日本aw7
      - 日本aw5
      - 美国aw1
      - 美国aw3
    url: 'https://fapi.binance.com/fapi/v1/ping'
    interval: 60
    timeout: 5000
"""
m = re.search(r"  - name: 币安专线\n(?:    .+\n)+?(?=  - name: )", text)
if not m:
    raise SystemExit("币安专线 block not found")
text = text[: m.start()] + new_block + text[m.end() :]
p.write_text(text, encoding="utf-8")
print("patched 币安专线 -> fallback multi-region")
PY

curl -s -X PUT "$API/configs?force=true" -H 'Content-Type: application/json' \
  -d "{\"path\":\"$CFG\"}" >/tmp/mihomo_reload.json || true
sleep 2

python3 <<'PY'
import json, urllib.request, urllib.parse
API = "http://127.0.0.1:9090"
for group, node in (("主代理", "币安专线"), ("GLOBAL", "币安专线")):
    body = json.dumps({"name": node}).encode()
    req = urllib.request.Request(
        API + "/proxies/" + urllib.parse.quote(group),
        data=body,
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    urllib.request.urlopen(req, timeout=5)
    print("set", group, "->", node)
ps = json.load(urllib.request.urlopen(API + "/proxies")).get("proxies", {})
for k in ("币安专线", "主代理", "GLOBAL"):
    if k in ps:
        print("NOW", k, "type=", ps[k].get("type"), "now=", ps[k].get("now"))
PY

echo "==== binance ping ===="
curl -s -o /dev/null -w "http=%{http_code}\n" --max-time 20 -x http://127.0.0.1:7891 \
  https://fapi.binance.com/fapi/v1/ping
curl -s --max-time 15 -x http://127.0.0.1:7891 https://api.ipify.org; echo

cat > /root/.config/mihomo/STICKY_NODE.txt <<EOF
币安专线: fallback 多地区（香港/日本/美国）
节点: 香港pump1, v5-香港02, 日本aw7, 日本aw5, 美国aw1, 美国aw3
探测: https://fapi.binance.com/fapi/v1/ping 每60s
白名单 IP 见 /opt/backpack-quant/deploy/binance-proxy-nodes.json
EOF
echo "DONE apply-binance-fallback"
