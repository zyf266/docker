#!/usr/bin/env python3
"""Inspect latest us bubble history in api container."""
import json
from pathlib import Path

cands = [
    Path("/app/backpack_quant_trading/data/us_bubble_history.json"),
    Path("/opt/backpack-quant/backpack_quant_trading/data/us_bubble_history.json"),
]
try:
    from backpack_quant_trading.config.settings import config
    cands.insert(0, Path(config.data_dir) / "us_bubble_history.json")
except Exception as e:
    print("config_err", e)

items = []
used = None
for c in cands:
    print("try", c, "exists", c.exists())
    if c.exists():
        items = json.loads(c.read_text(encoding="utf-8"))
        used = c
        break
print("used", used, "n", len(items))
for x in items[-3:]:
    r = x.get("report") or {}
    st = x.get("structured") or {}
    md = x.get("markdown") or ""
    print("---", x.get("report_date"), x.get("generated_at_utc"))
    print(" score", x.get("bubble_total_score"), "state", x.get("market_state"))
    print(" report_keys", list(r.keys())[:15], "top5", bool(r.get("top5_events")), "syn", bool(r.get("synthesis")))
    print(" st_keys", list(st.keys())[:12], "st_report", isinstance(st.get("report"), dict))
    print(" md_len", len(md), "has_json_fence", "```json" in md)
    # show end of markdown for truncation clues
    print(" md_tail", md[-180:].replace("\n", " | "))
