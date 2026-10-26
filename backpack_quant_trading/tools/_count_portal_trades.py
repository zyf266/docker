from sqlalchemy import text
from backpack_quant_trading.core.env_loader import load_project_env
from backpack_quant_trading.database.models import DatabaseManager

load_project_env()
c = DatabaseManager().engine.connect()
n = c.execute(text("select count(*) from portal_trades")).scalar()
print("portal_trades_count", n)
rows = c.execute(
    text(
        "select user_id, symbol, strategy_name, status, pnl, created_at "
        "from portal_trades where detail like 'mock seed%' order by id desc limit 5"
    )
).fetchall()
for r in rows:
    print(r)
c.close()
