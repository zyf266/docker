#!/bin/bash
grep -rn '可以说' /root/.openclaw 2>/dev/null | head -20
grep -rn '评一下分' /root/.openclaw 2>/dev/null | head -20
python3 <<'PY'
import json
from pathlib import Path
p = Path("/root/.openclaw/openclaw.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("keys", list(d.keys()) if isinstance(d, dict) else type(d))
# print channels / plugins briefly
for k in ("channels", "plugins", "agents", "bindings", "gateway", "session"):
    if isinstance(d, dict) and k in d:
        v = d[k]
        s = json.dumps(v, ensure_ascii=False)
        print(f"== {k} ==", s[:800])
PY
