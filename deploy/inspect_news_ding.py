#!/usr/bin/env python3
import json
from pathlib import Path

env = Path("/opt/backpack-quant/.env")
cfg = Path("/opt/backpack-quant/backpack_quant_trading/data/stock_news_alert_config.json")
print("env_has_stock", "STOCK_NEWS_DINGTALK" in env.read_text(encoding="utf-8", errors="ignore") if env.exists() else False)
print("env_has_ops", "AGENT_OPS_DINGTALK" in env.read_text(encoding="utf-8", errors="ignore") if env.exists() else False)
if cfg.exists():
    c = json.loads(cfg.read_text(encoding="utf-8"))
    wh = str(c.get("dingtalk_webhook") or "")
    print("cfg_wh_tail", wh[-24:] if wh else None)
    print("watch", c.get("watch_names") or c.get("watch") or c.get("keywords"))
