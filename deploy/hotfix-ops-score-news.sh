#!/bin/bash
# 热更：运维 webhook / 评分识别 / 新闻过滤 / 代理告警改群
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cd /opt/backpack-quant

OPS_WH='https://oapi.dingtalk.com/robot/send?access_token=215ff15f30cda41d24ba0067f27a746b49696656108f3649aec5d3bbbe49f65f'

if grep -q '^AGENT_OPS_DINGTALK_WEBHOOK=' .env; then
  sed -i "s|^AGENT_OPS_DINGTALK_WEBHOOK=.*|AGENT_OPS_DINGTALK_WEBHOOK=${OPS_WH}|" .env
else
  printf '\nAGENT_OPS_DINGTALK_WEBHOOK=%s\n' "$OPS_WH" >> .env
fi

# 币种监视等若仍指向山寨群 token，一并切到运维机器人（新群通常用关键词「提醒」，清掉旧加签）
OPS_TOKEN='215ff15f30cda41d24ba0067f27a746b49696656108f3649aec5d3bbbe49f65f'
if grep -q '^DINGTALK_TOKEN=' .env; then
  sed -i "s|^DINGTALK_TOKEN=.*|DINGTALK_TOKEN=${OPS_TOKEN}|" .env
fi
if grep -q '^DINGTALK_SECRET=' .env; then
  sed -i 's|^DINGTALK_SECRET=.*|DINGTALK_SECRET=|' .env
fi

cp -f /tmp/hotfix_ops/{coordinator.py,scheduler_hooks.py} backpack_quant_trading/agents/ 2>/dev/null || true
cp -f /tmp/hotfix_ops/stock_news_alert.py backpack_quant_trading/core/
cp -f /tmp/hotfix_ops/stock_news_feeds.py backpack_quant_trading/core/
cp -f /tmp/hotfix_ops/binance-proxy-watchdog.sh deploy/
chmod +x deploy/binance-proxy-watchdog.sh

# 新闻：只关「仅自定义影响面」（否则几乎推不出去）；webhook 保持新闻群，绝不改成运维群
python3 <<'PY'
import json
from pathlib import Path
p = Path("backpack_quant_trading/data/stock_news_alert_config.json")
cfg = json.loads(p.read_text(encoding="utf-8"))
# 勿改 dingtalk_webhook —— 新闻固定「新闻提醒」群
cfg["only_extra_impact_keywords"] = False
p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("news_wh_tail", (cfg.get("dingtalk_webhook") or "")[-12:])
print("only_extra", cfg["only_extra_impact_keywords"], "only_material", cfg.get("only_material"))
PY

for c in backpack-api backpack-webhook backpack-dingtalk-agent; do
  docker cp backpack_quant_trading/agents/coordinator.py "$c:/app/backpack_quant_trading/agents/coordinator.py"
  docker cp backpack_quant_trading/agents/scheduler_hooks.py "$c:/app/backpack_quant_trading/agents/scheduler_hooks.py" || true
done
docker cp backpack_quant_trading/core/stock_news_alert.py backpack-api:/app/backpack_quant_trading/core/stock_news_alert.py
docker cp backpack_quant_trading/core/stock_news_feeds.py backpack-api:/app/backpack_quant_trading/core/stock_news_feeds.py

# 注入 OPS env（不 recreate 以免 DB 挂）
docker exec backpack-api sh -c "grep -q AGENT_OPS_DINGTALK_WEBHOOK /proc/1/environ || true"
# api 已有 OPS；webhook 也写入便于日志
docker restart backpack-webhook backpack-dingtalk-agent
# news 配置热读，api 不必强重启；重启以加载 DINGTALK_TOKEN 改动到 monitor（settings 启动时读）
docker restart backpack-api

echo "wait healthy..."
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8100/api/health >/dev/null 2>&1 || curl -fsS http://127.0.0.1:8100/health >/dev/null 2>&1; then
    echo "api ok"
    break
  fi
  sleep 2
done

docker exec backpack-webhook python3 - <<'PY'
from backpack_quant_trading.agents.scheduler_hooks import build_agent_signal_text
from backpack_quant_trading.agents.coordinator import parse_route
for sym in ["INTC","MU","AMD","AVGO","DRAM","NVDA"]:
    t = build_agent_signal_text(sym, market="us_stock", timeframe="30", action="buy")
    h = parse_route(t)
    print(sym, "->", h.symbols, "|", t)
PY

docker exec backpack-api python3 - <<'PY'
from backpack_quant_trading.core.stock_news_alert import (
    load_config,
    _impact_keyword_list,
    is_material_news,
    resolve_dingtalk_webhook,
)
from backpack_quant_trading.agents.dingtalk_push import push_dingtalk_markdown
c = load_config()
kw = _impact_keyword_list(c)
print("wh", (resolve_dingtalk_webhook(c) or "")[-16:])
print("only_extra", c.get("only_extra_impact_keywords"), "n_kw", len(kw))
print("mat_earnings", is_material_news("NVDA report earnings beat", 0, kw, True))
ok, msg = push_dingtalk_markdown(
    "运维群验证",
    "### 提醒 · 运维 webhook 验证\n\n代理告警/复盘已切到本群（新闻仍走原群）",
    use_ops_webhook=True,
)
print("ops_push", ok, msg)
print("news_wh_kept", (resolve_dingtalk_webhook(c) or "")[-16:])
PY

echo DONE
