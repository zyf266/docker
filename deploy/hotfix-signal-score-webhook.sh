#!/bin/bash
# 热更：加密/美股 Webhook 信号 → Agent 评分卡 → 信号评分钉钉群（停用旧海报链路）
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cd /opt/backpack-quant

inject_py() {
  local c="$1"
  docker exec "$c" mkdir -p \
    /app/backpack_quant_trading/core \
    /app/backpack_quant_trading/agents || true
  docker cp backpack_quant_trading/core/crypto_signal_scorer.py \
    "$c:/app/backpack_quant_trading/core/crypto_signal_scorer.py"
  docker cp backpack_quant_trading/core/dingtalk_manual_score.py \
    "$c:/app/backpack_quant_trading/core/dingtalk_manual_score.py"
  docker cp backpack_quant_trading/agents/scheduler_hooks.py \
    "$c:/app/backpack_quant_trading/agents/scheduler_hooks.py"
}

# 确保信号评分 webhook 指向目标群
mkdir -p backpack_quant_trading/data
CFG=backpack_quant_trading/data/crypto_signal_scorer_config.json
TARGET_TOKEN="5dea0e1540ba7759a8dc65304552cfea54b468bba572f8a655fb71ec062c2f03"
if [ -f "$CFG" ]; then
  python3 - <<PY
import json
from pathlib import Path
p = Path("$CFG")
cfg = json.loads(p.read_text(encoding="utf-8"))
url = (
    "https://oapi.dingtalk.com/robot/send?"
    f"access_token=$TARGET_TOKEN"
)
if cfg.get("dingtalk_webhook") != url:
    cfg["dingtalk_webhook"] = url
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("updated dingtalk_webhook in config")
else:
    print("dingtalk_webhook already correct")
PY
else
  echo "WARN: $CFG missing, using DEFAULT_WEBHOOK in code"
fi

for c in backpack-api backpack-webhook backpack-dingtalk-agent; do
  inject_py "$c"
  if [ -f "$CFG" ]; then
    docker exec "$c" mkdir -p /app/backpack_quant_trading/data
    docker cp "$CFG" "$c:/app/backpack_quant_trading/data/crypto_signal_scorer_config.json"
  fi
done

docker restart backpack-api backpack-webhook backpack-dingtalk-agent
sleep 22
curl -sf http://127.0.0.1:8100/api/health
echo

docker exec backpack-api python - <<'PY'
from backpack_quant_trading.core.crypto_signal_scorer import resolve_signal_score_dingtalk_webhook
from backpack_quant_trading.agents.scheduler_hooks import (
    agent_replace_legacy_push,
    _push_agent_markdown_to_score_group,
)

url = resolve_signal_score_dingtalk_webhook()
assert "5dea0e1540ba7759a8dc65304552cfea54b468bba572f8a655fb71ec062c2f03" in url
assert agent_replace_legacy_push(), "AGENT_REPLACE_LEGACY_PUSH should be on by default"
print("signal_score_webhook_ok", url[:60] + "...")
PY

echo "DONE: 加密/美股 Webhook 信号将推送到信号评分钉钉群（Agent 评分卡，旧海报链路已停用）"
