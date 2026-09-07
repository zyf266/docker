# -*- coding: utf-8 -*-
"""远程打正式服 adaptive-long webhook（在服务器本机跑）。用法:
  python _tmp_tv_signal.py buy
  python _tmp_tv_signal.py sell
"""
import json
import sys
import urllib.error
import urllib.request

action = (sys.argv[1] if len(sys.argv) > 1 else "buy").lower().strip()
if action not in ("buy", "sell"):
    raise SystemExit("用法: python _tmp_tv_signal.py buy|sell")

payload = {
    "策略名": "ETH自动化交易",
    "symbol": "ETHUSDT.P",
    "action": action,
    "price": 2500,
    "position": "flat" if action == "buy" else "long",
    "interval": "15",
}
url = "http://127.0.0.1:8005/adaptive-long/webhook"
body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
req = urllib.request.Request(
    url, data=body, headers={"Content-Type": "application/json"}, method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        print(resp.status, resp.read().decode("utf-8", errors="replace"))
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode("utf-8", errors="replace"))
except Exception as e:
    print("ERR", e)
