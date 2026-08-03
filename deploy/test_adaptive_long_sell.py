#!/usr/bin/env python3
import json
import urllib.request

payload = {
    "策略名": "DRAM自动化交易",
    "symbol": "DRAMUSDT.P",
    "action": "sell",
    "price": 48.8,
    "position": "long",
    "interval": "15",
}
req = urllib.request.Request(
    "http://127.0.0.1:8100/api/trading/adaptive-long/webhook",
    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
        print(resp.status, body)
except Exception as e:
    if hasattr(e, "read"):
        print(getattr(e, "code", "?"), e.read().decode("utf-8", errors="replace"))
    else:
        print("ERR", e)
