#!/usr/bin/env bash
# Hotfix trading start path on prod 47
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
HOST="${1:-47.110.57.118}"
KEY="${SSH_KEY:-$HOME/.ssh/github_actions_prod}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

scp -i "$KEY" -o StrictHostKeyChecking=accept-new \
  "$ROOT/backpack_quant_trading/api/routers/trading.py" \
  "$ROOT/backpack_quant_trading/database/models.py" \
  "$ROOT/backpack_quant_trading/core/binance_client.py" \
  "root@$HOST:/tmp/trading_hotfix/"

ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "root@$HOST" bash -s <<'REMOTE'
set -euo pipefail
mkdir -p /tmp/trading_hotfix
# scp already put files; ensure dir
docker cp /tmp/trading_hotfix/trading.py backpack-api:/app/backpack_quant_trading/api/routers/trading.py
docker cp /tmp/trading_hotfix/models.py backpack-api:/app/backpack_quant_trading/database/models.py
docker cp /tmp/trading_hotfix/binance_client.py backpack-api:/app/backpack_quant_trading/core/binance_client.py
# also sync host bind path if any
cp -f /tmp/trading_hotfix/trading.py /opt/backpack-quant/backpack_quant_trading/api/routers/trading.py 2>/dev/null || true
cp -f /tmp/trading_hotfix/models.py /opt/backpack-quant/backpack_quant_trading/database/models.py 2>/dev/null || true
cp -f /tmp/trading_hotfix/binance_client.py /opt/backpack-quant/backpack_quant_trading/core/binance_client.py 2>/dev/null || true
docker restart backpack-api
sleep 8
docker exec backpack-api python -c "from backpack_quant_trading.api.routers.trading import _run_adaptive_long_in_thread; from backpack_quant_trading.database.models import DatabaseManager; print('import_ok')"
docker logs backpack-api --since 30s 2>&1 | tail -20
REMOTE
