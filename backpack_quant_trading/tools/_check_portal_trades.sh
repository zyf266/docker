#!/bin/bash
set -e
docker exec backpack-api python <<'PY'
from sqlalchemy import text
from backpack_quant_trading.database.models import DatabaseManager
c = DatabaseManager().engine.connect()
print("count", c.execute(text("select count(*) from portal_trades")).scalar())
print("sample", c.execute(text("select id,user_id,symbol,status,pnl from portal_trades order by id desc limit 3")).fetchall())
c.close()
PY
code=$(curl -s -o /tmp/pt.json -w "%{http_code}" http://127.0.0.1:8100/api/portal/trades)
echo "HTTP /api/portal/trades => $code"
head -c 200 /tmp/pt.json; echo
grep -o '/api/portal/trades' /tmp/tr.json 2>/dev/null | head -1 || true
curl -s http://127.0.0.1:8100/openapi.json | grep -o 'portal/trades' | head -3
