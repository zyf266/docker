#!/bin/bash
set -euo pipefail
echo "=== openclaw process ==="
ps aux | grep -E 'openclaw|dingtalk' | grep -v grep
echo "=== openclaw.json channels/plugins ==="
python3 <<'PY'
import json
from pathlib import Path
p = Path("/root/.openclaw/openclaw.json")
d = json.loads(p.read_text(encoding="utf-8"))
print(json.dumps(d, ensure_ascii=False, indent=2)[:4000])
PY
echo "=== search tip / dingtalk ==="
grep -Rni --include='*.{json,md,txt,js,ts,mjs}' -E 'dingtalk|ding7r2n|评一下分|可以说|ETH 2h' /root/.openclaw 2>/dev/null | head -40
echo "=== recent dingtalk agent logs ==="
docker logs backpack-dingtalk-agent --since 15m 2>&1 | grep '入站' | tail -20
