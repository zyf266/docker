#!/bin/bash
set -e
API=http://127.0.0.1:9090
candidates=("日本直连1" "日本直连2" "日本直连3" "日本1" "日本aw1" "日本aw2" "日本aw3" "v5-日本01|1x|v" "v4-日本01|1x|v")

pick=""
for n in "${candidates[@]}"; do
  enc=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$n'''))")
  # delay test
  code=$(curl -s -o /tmp/delay.json -w "%{http_code}" --max-time 8 \
    "$API/proxies/$enc/delay?timeout=5000&url=http%3A%2F%2Fwww.gstatic.com%2Fgenerate_204" || true)
  delay=$(python3 -c "import json;print(json.load(open('/tmp/delay.json')).get('delay','err'))" 2>/dev/null || echo err)
  echo "probe $n delay=$delay http=$code"
  if [[ "$delay" =~ ^[0-9]+$ ]] && [ "$delay" -gt 0 ] && [ "$delay" -lt 5000 ]; then
    pick="$n"
    break
  fi
done

if [ -z "$pick" ]; then
  echo "NO_WORKING_JP_NODE"
  exit 1
fi

echo "PICK=$pick"
enc_group=$(python3 -c "import urllib.parse; print(urllib.parse.quote('币安专线'))")
curl -s -o /dev/null -w "set_binance=%{http_code}\n" -X PUT "$API/proxies/$enc_group" \
  -H 'Content-Type: application/json' -d "{\"name\":\"$pick\"}"
enc_main=$(python3 -c "import urllib.parse; print(urllib.parse.quote('主代理'))")
curl -s -o /dev/null -w "set_main=%{http_code}\n" -X PUT "$API/proxies/$enc_main" \
  -H 'Content-Type: application/json' -d '{"name":"币安专线"}'

# also set GLOBAL to 币安专线 so mixed-port always sticky
enc_g=$(python3 -c "import urllib.parse; print(urllib.parse.quote('GLOBAL'))")
curl -s -o /dev/null -w "set_global=%{http_code}\n" -X PUT "$API/proxies/$enc_g" \
  -H 'Content-Type: application/json' -d '{"name":"币安专线"}' || true

sleep 2
echo "==== egress x5 ===="
ips=""
for i in 1 2 3 4 5; do
  ip=$(curl -s --max-time 15 -x http://127.0.0.1:7891 https://api.ipify.org || echo FAIL)
  echo "$i $ip"
  ips="$ips $ip"
  sleep 1
done
echo "==== binance ===="
curl -s -o /dev/null -w "ping=%{http_code}\n" --max-time 15 -x http://127.0.0.1:7891 https://fapi.binance.com/fapi/v1/ping

python3 <<PY
import json, urllib.request
ps=json.load(urllib.request.urlopen("http://127.0.0.1:9090/proxies")).get("proxies",{})
for k in ("币安专线","主代理","GLOBAL"):
    if k in ps: print(k, "now=", ps[k].get("now"))
PY
echo "PICKED_NODE=$pick"
