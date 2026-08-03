#!/bin/bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cd /opt/backpack-quant

OPS_WH='https://oapi.dingtalk.com/robot/send?access_token=215ff15f30cda41d24ba0067f27a746b49696656108f3649aec5d3bbbe49f65f'
if grep -q '^AGENT_OPS_DINGTALK_WEBHOOK=' .env; then
  sed -i "s|^AGENT_OPS_DINGTALK_WEBHOOK=.*|AGENT_OPS_DINGTALK_WEBHOOK=${OPS_WH}|" .env
else
  printf '\nAGENT_OPS_DINGTALK_WEBHOOK=%s\n' "$OPS_WH" >> .env
fi

# 若容器没带上 OPS 环境变量，再 recreate 一次（compose 已修好）
if [ "$(docker exec backpack-api printenv AGENT_OPS_DINGTALK_WEBHOOK 2>/dev/null || true)" = "" ]; then
  set -a; source .env; set +a
  docker compose up -d --force-recreate --no-deps api
  sleep 8
fi

FILES=(
  backpack_quant_trading/agents/coordinator.py
  backpack_quant_trading/agents/dingtalk_push.py
  backpack_quant_trading/agents/patrol_agent.py
  backpack_quant_trading/api/main.py
  backpack_quant_trading/core/stock_news_alert.py
  backpack_quant_trading/api/routers/strategy.py
)
for f in "${FILES[@]}"; do
  if [ -f "$f" ]; then
    docker cp "$f" "backpack-api:/app/$f"
    echo "cp $f"
  fi
done

if [ -f "阿尔法策略_ETHUSDT_2H_交易数据.csv" ]; then
  docker cp "阿尔法策略_ETHUSDT_2H_交易数据.csv" "backpack-api:/app/阿尔法策略_ETHUSDT_2H_交易数据.csv"
fi

# 禁止用宿主机「过期 dist」覆盖容器（会导致学习中心/泡沫检测等 UI 回退）。
# 前端请用 deploy/hotfix-no-rollback.sh：先同步最新 src，再 npm build，校验文案后再 docker cp。
if [ "${FORCE_COPY_STALE_DIST:-}" = "1" ] && [ -d backpack_quant_trading/frontend/dist/assets ]; then
  echo "WARN: FORCE_COPY_STALE_DIST=1，仍复制宿主机 dist（可能回退）"
  docker exec backpack-api rm -rf /app/backpack_quant_trading/frontend/dist
  docker cp backpack_quant_trading/frontend/dist backpack-api:/app/backpack_quant_trading/frontend/dist
  echo "frontend dist copied"
else
  echo "skip stale dist copy (set FORCE_COPY_STALE_DIST=1 to override)"
fi

# dingtalk-agent 也要 coordinator
if docker ps --format '{{.Names}}' | grep -q '^backpack-dingtalk-agent$'; then
  docker cp backpack_quant_trading/agents/coordinator.py backpack-dingtalk-agent:/app/backpack_quant_trading/agents/coordinator.py || true
fi

docker restart backpack-api
sleep 12
curl -sf http://127.0.0.1:8100/api/health; echo
curl -sS -o /dev/null -w "strategies %{http_code}\n" http://127.0.0.1:8100/strategies
curl -sS -o /dev/null -w "alpha_html %{http_code}\n" http://127.0.0.1:8100/strategies/alpha-eth
curl -sS -o /dev/null -w "alpha_api %{http_code}\n" http://127.0.0.1:8100/api/strategy/alpha-eth-2h/overview

docker exec backpack-api printenv AGENT_OPS_DINGTALK_WEBHOOK | sed 's/access_token=.*/access_token=***/'
docker exec backpack-api python - <<'PY'
from backpack_quant_trading.agents.coordinator import parse_route
from backpack_quant_trading.core.stock_news_alert import matches_watch, send_dingtalk_markdown
import os
h = parse_route("@美股分析师 CRCL 2h 做多开仓")
print("crcl", h.symbols)
item = {"related_tickers": ["INTC"], "text": "Intel stock (NVDA)"}
print("news_fix", matches_watch(item["text"], ["NVDA"], item) is False)
wh = os.environ.get("AGENT_OPS_DINGTALK_WEBHOOK") or ""
print("ops", bool(wh))
if wh:
    print("push", send_dingtalk_markdown(wh, "提醒", "【提醒】自动复盘/日巡检已切换到本群（配置验证）"))
PY
echo DONE
