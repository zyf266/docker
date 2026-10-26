from sqlalchemy import text
from backpack_quant_trading.core.env_loader import load_project_env
from backpack_quant_trading.database.models import DatabaseManager

load_project_env()
c = DatabaseManager().engine.connect()
rows = c.execute(text(
    "SELECT user_id, platform, status, LEFT(config_json,120) FROM portal_exchange_bindings ORDER BY user_id, platform"
)).fetchall()
for r in rows:
    print(r)
print("watch connected:")
for r in c.execute(text(
    "SELECT id,user_id,symbol,strategy_name,timeframe,status,exchange,require_short,require_mid,require_long,take_profit,stop_loss,leverage "
    "FROM portal_watch_configs WHERE status='connected'"
)).fetchall():
    print(r)
c.close()
