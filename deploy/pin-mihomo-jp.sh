#!/bin/bash
set -euo pipefail
CFG=/root/.config/mihomo/config.yaml
API=http://127.0.0.1:9090
TS=$(date +%Y%m%d%H%M%S)
cp -a "$CFG" "${CFG}.bak.sticky.${TS}"

python3 <<'PY'
from pathlib import Path
p = Path("/root/.config/mihomo/config.yaml")
text = p.read_text(encoding="utf-8")

old = """proxy-groups:
  - name: 套餐详情
    type: select
    include-all: true
    filter: \"网址|剩余流量|过期时间|套餐|购买|有效|回家页|官网|订阅|到期\"
  - name: 主代理
    type: select
    proxies:
      - 自动选择
      - 负载均衡
      - us自动切换
      - jp自动切换
      - DIRECT
    include-all: true
    exclude-filter: \"网址|剩余流量|过期时间|套餐|购买|有效\"
  - name: 自动选择
    type: url-test
    include-all: true
    exclude-filter: \"网址|剩余流量|过期时间|套餐|购买|有效\"
    url: 'http://www.gstatic.com/generate_204'
    interval: 180
    tolerance: 25
  - name: 负载均衡
    type: load-balance
    include-all: true
    exclude-filter: \"网址|剩余流量|过期时间|套餐|购买|有效\"
    strategy: consistent-hashing
    url: 'http://www.gstatic.com/generate_204'
    interval: 300
  - name: us自动切换
    type: fallback
    include-all: true
    filter: \"美国\"
    url: 'http://www.gstatic.com/generate_204'
    interval: 60
  - name: jp自动切换
    type: fallback
    include-all: true
    filter: \"日本\"
    url: 'http://www.gstatic.com/generate_204'
    interval: 60
  - name: 国内直连
    type: select
    proxies:
      - DIRECT
      - 主代理
"""

new = """proxy-groups:
  - name: 套餐详情
    type: select
    include-all: true
    filter: \"网址|剩余流量|过期时间|套餐|购买|有效|回家页|官网|订阅|到期\"
  # 固定落地：禁止 url-test/load-balance 自动换节点，避免币安白名单 IP 漂移
  - name: 币安专线
    type: select
    proxies:
      - 日本aw1
      - 日本aw2
      - 日本aw3
      - 日本直连1
      - 日本直连2
      - 日本直连3
      - 日本1
  - name: 主代理
    type: select
    proxies:
      - 币安专线
      - 日本aw1
      - 日本直连1
      - 日本直连2
      - 日本直连3
      - 日本1
      - DIRECT
      - 自动选择
      - 负载均衡
      - jp自动切换
      - us自动切换
    include-all: true
    exclude-filter: \"网址|剩余流量|过期时间|套餐|购买|有效\"
  - name: 自动选择
    type: url-test
    include-all: true
    exclude-filter: \"网址|剩余流量|过期时间|套餐|购买|有效\"
    url: 'http://www.gstatic.com/generate_204'
    interval: 180
    tolerance: 25
  - name: 负载均衡
    type: load-balance
    include-all: true
    exclude-filter: \"网址|剩余流量|过期时间|套餐|购买|有效\"
    strategy: consistent-hashing
    url: 'http://www.gstatic.com/generate_204'
    interval: 300
  - name: us自动切换
    type: fallback
    include-all: true
    filter: \"美国\"
    url: 'http://www.gstatic.com/generate_204'
    interval: 60
  - name: jp自动切换
    type: fallback
    include-all: true
    filter: \"日本\"
    url: 'http://www.gstatic.com/generate_204'
    interval: 60
  - name: 国内直连
    type: select
    proxies:
      - DIRECT
      - 主代理
"""

if old not in text:
    raise SystemExit("proxy-groups block not found; abort")
text = text.replace(old, new, 1)

old_rules = """rules:
  - 'RULE-SET,Local-IP,国内直连,no-resolve'
  - 'RULE-SET,China-Site,国内直连'
  - 'RULE-SET,China-IP,国内直连'
  - 'MATCH,主代理'
"""
new_rules = """rules:
  - 'RULE-SET,Local-IP,国内直连,no-resolve'
  - 'RULE-SET,China-Site,国内直连'
  - 'RULE-SET,China-IP,国内直连'
  # 币安强制走固定专线，避免被主代理/自动选择换 IP
  - 'DOMAIN-SUFFIX,binance.com,币安专线'
  - 'DOMAIN-SUFFIX,binance.me,币安专线'
  - 'DOMAIN-SUFFIX,binance.us,币安专线'
  - 'DOMAIN-SUFFIX,binance.vision,币安专线'
  - 'DOMAIN-SUFFIX,bnstatic.com,币安专线'
  - 'DOMAIN-KEYWORD,binance,币安专线'
  - 'MATCH,主代理'
"""
if old_rules not in text:
    raise SystemExit("rules block not found; abort")
text = text.replace(old_rules, new_rules, 1)
p.write_text(text, encoding="utf-8")
print("config patched ok")
PY

# truncate huge log (disk)
truncate -s 0 /root/.config/mihomo/mihomo.log || true

# reload config
curl -s -X PUT "$API/configs?force=true" -H 'Content-Type: application/json' -d "{\"path\":\"$CFG\"}" || true
sleep 2

# pin selection
for pair in "币安专线/日本直连1" "主代理/币安专线"; do
  g="${pair%%/*}"; n="${pair##*/}"
  enc=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$g'''))")
  code=$(curl -s -o /tmp/mihomo_sel.json -w "%{http_code}" -X PUT "$API/proxies/$enc" \
    -H 'Content-Type: application/json' -d "{\"name\":\"$n\"}")
  echo "select $g -> $n http=$code body=$(cat /tmp/mihomo_sel.json 2>/dev/null)"
done

sleep 1
echo "==== now ===="
curl -s "$API/proxies" | python3 - <<'PY'
import sys, json
ps = json.load(sys.stdin).get("proxies", {})
for k in ("币安专线", "主代理", "GLOBAL"):
    if k in ps:
        print(k, "type=", ps[k].get("type"), "now=", ps[k].get("now"))
PY

echo "==== egress x3 ===="
for i in 1 2 3; do
  curl -s --max-time 12 -x http://127.0.0.1:7891 https://api.ipify.org; echo
  sleep 1
done
echo "==== binance ping ===="
curl -s -o /dev/null -w "%{http_code}\n" --max-time 12 -x http://127.0.0.1:7891 https://fapi.binance.com/fapi/v1/ping
df -h / | tail -1
