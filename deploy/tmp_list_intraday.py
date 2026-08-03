from datetime import datetime
from backpack_quant_trading.core.a_share_strategy_import import A_SHARE_STRATEGY_SPECS
from backpack_quant_trading.database.models import db_manager
from backpack_quant_trading.api.routers.strategy import StrategyBacktestTrade
import json, urllib.request

def is_entry(t):
    return "进场" in str(getattr(t, "trade_type", "") or "")

def is_exit(t):
    tp = str(getattr(t, "trade_type", "") or "")
    return ("出" in tp) or ("止损" in tp)

for spec in A_SHARE_STRATEGY_SPECS:
    s = db_manager.get_session()
    try:
        rows = (
            s.query(StrategyBacktestTrade)
            .filter_by(strategy_name=spec.strategy_name, symbol=spec.symbol, timeframe="2H")
            .order_by(StrategyBacktestTrade.trade_no, StrategyBacktestTrade.trade_time)
            .all()
        )
    finally:
        s.close()
    by = {}
    for r in rows:
        by.setdefault(int(r.trade_no), []).append(r)
    print("===", spec.code, "n=", len(by))
    for no, g in sorted(by.items()):
        e = next((x for x in g if is_entry(x)), None)
        x = next((x for x in g if is_exit(x)), None)
        if not e or not x:
            print(" incomplete", no)
            continue
        same = e.trade_time.date() == x.trade_time.date()
        mark = "INTRADAY" if same else "ok"
        print(f"  #{no} {mark:8} {e.trade_time} -> {x.trade_time} sig={x.signal} pnl%={float(x.pnl_pct or 0):.2f}")

for path in (
    "/api/strategy/sse-510210-4h/overview",
    "/api/strategy/mnq-dip-4h/overview",
):
    with urllib.request.urlopen("http://127.0.0.1:8100" + path, timeout=15) as resp:
        j = json.loads(resp.read().decode())
    keys = [
        "total_return_pct",
        "annualized_return_pct",
        "max_drawdown_pct",
        "profit_factor",
        "total_trades",
        "initial_capital",
        "start_date",
        "end_date",
    ]
    print(path, {k: j.get(k) for k in keys})
