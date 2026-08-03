#!/bin/bash
set -e
curl -sf http://127.0.0.1:8100/api/health; echo
docker exec backpack-api python /tmp/verify_crcl_parse.py 2>/dev/null || true
curl -sS -o /dev/null -w "alpha_html %{http_code}\n" http://127.0.0.1:8100/strategies/alpha-eth
curl -sS -o /dev/null -w "alpha_api %{http_code}\n" http://127.0.0.1:8100/api/strategy/alpha-eth-2h/overview
docker cp /tmp/verify_ops_push2.py backpack-api:/tmp/verify_ops_push2.py
docker exec backpack-api python /tmp/verify_ops_push2.py
# re-apply coordinator if needed
if ! docker exec backpack-api grep -q 'Webhook 新链路常见' /app/backpack_quant_trading/agents/coordinator.py 2>/dev/null; then
  echo NEED_COORDINATOR_FIX
fi
if ! docker exec backpack-api grep -q 'AGENT_OPS_DINGTALK' /app/backpack_quant_trading/agents/dingtalk_push.py 2>/dev/null; then
  echo NEED_OPS_PUSH
fi
grep -n 'strategies/{full_path' /opt/backpack-quant/backpack_quant_trading/api/main.py | head -2
docker exec backpack-api grep -n 'strategies/{full_path' /app/backpack_quant_trading/api/main.py | head -2 || echo NEED_SPA
