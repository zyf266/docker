from backpack_quant_trading.database.models import db_manager
from sqlalchemy import text
with db_manager.get_session() as s:
    n = s.execute(text("SELECT COUNT(*) FROM strategy_backtest_trade WHERE strategy_name='603986_2H'")).scalar()
    print("db_count_603986", n)
    rows = s.execute(text(
        "SELECT trade_no,trade_type,signal,trade_time,price,pnl_pct FROM strategy_backtest_trade "
        "WHERE strategy_name='603986_2H' ORDER BY trade_time"
    )).fetchall()
    for r in rows:
        print(tuple(r))
    for code in ("300308","688146","002837"):
        c = s.execute(text("SELECT COUNT(*) FROM strategy_backtest_trade WHERE strategy_name=:n"), {"n": f"{code}_2H"}).scalar()
        print(f"db_count_{code}", c)
