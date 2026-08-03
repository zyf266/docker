#!/bin/bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cd /opt/backpack-quant

OPS_WH='https://oapi.dingtalk.com/robot/send?access_token=215ff15f30cda41d24ba0067f27a746b49696656108f3649aec5d3bbbe49f65f'

# 写入 / 更新 AGENT_OPS_DINGTALK_WEBHOOK
if grep -q '^AGENT_OPS_DINGTALK_WEBHOOK=' .env 2>/dev/null; then
  sed -i "s|^AGENT_OPS_DINGTALK_WEBHOOK=.*|AGENT_OPS_DINGTALK_WEBHOOK=${OPS_WH}|" .env
else
  printf '\n# 自动复盘 / 日巡检专用钉钉群\nAGENT_OPS_DINGTALK_WEBHOOK=%s\n' "$OPS_WH" >> .env
fi
grep '^AGENT_OPS_DINGTALK_WEBHOOK=' .env | sed 's/access_token=.*/access_token=***/'

# 热更新代码
for f in \
  backpack_quant_trading/agents/dingtalk_push.py \
  backpack_quant_trading/agents/patrol_agent.py \
  backpack_quant_trading/api/main.py \
  backpack_quant_trading/core/stock_news_alert.py
do
  docker cp "$f" "backpack-api:/app/$f"
done

docker restart backpack-api
for i in $(seq 1 25); do
  curl -sf http://127.0.0.1:8100/api/health >/dev/null && break
  sleep 2
done

docker exec backpack-api python - <<'PY'
import os
from backpack_quant_trading.agents.dingtalk_push import resolve_ops_dingtalk_webhook, push_dingtalk_markdown
from backpack_quant_trading.core.stock_news_alert import matches_watch

wh = resolve_ops_dingtalk_webhook()
print("ops_wh_ok", wh.endswith("be49f65f"))
item = {"related_tickers": ["INTC"], "text": "Why Goldman is cautious on outperforming Intel stock (NVDA)"}
print("false_pos_fixed", matches_watch(item["text"], ["NVDA"], item) is False)
print("intc_ok", matches_watch(item["text"], ["INTC"], item) is True)
ok, msg = push_dingtalk_markdown(
    "Agent 日巡检",
    "## 提醒 · Agent 日巡检\n\n（配置验证：复盘/巡检已切换到本群）",
    use_ops_webhook=True,
)
print("test_push", ok, msg)
PY

echo DONE
