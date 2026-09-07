# -*- coding: utf-8 -*-
"""Probe strategy_backtest_trade for NVDA/INTC/MU/英维克/中船特气/HYPE."""
from backpack_quant_trading.database.models import DatabaseManager
from backpack_quant_trading.api.routers.strategy import StrategyBacktestTrade

db = DatabaseManager()
s = db.get_session()
try:
    names = (
        s.query(StrategyBacktestTrade.strategy_name, StrategyBacktestTrade.symbol)
        .distinct()
        .all()
    )
    print("ALL_STRATEGIES")
    for n, sym in sorted(names, key=lambda x: (x[0] or "", x[1] or "")):
        print(f"  {n} | {sym}")

    keys = [
        "NVDA",
        "INTC",
        "MU",
        "英维克",
        "中船",
        "688146",
        "002837",
        "HYPE",
        "ALPHA",
        "NAS",
        "MNQ",
    ]
    for row in names:
        sn, sym = row[0] or "", row[1] or ""
        blob = f"{sn} {sym}"
        if not any(k.lower() in blob.lower() for k in keys):
            # also chinese
            if not any(k in blob for k in ("英维克", "中船", "特气")):
                continue
        print("\n===", sn, sym, "===")
        trades = (
            s.query(StrategyBacktestTrade)
            .filter_by(strategy_name=sn, symbol=sym)
            .order_by(StrategyBacktestTrade.trade_no.desc(), StrategyBacktestTrade.trade_time.desc())
            .limit(12)
            .all()
        )
        for t in trades:
            print(
                t.trade_no,
                t.trade_type,
                t.trade_time,
                t.signal,
                float(t.price) if t.price is not None else None,
                float(t.position_qty) if t.position_qty is not None else None,
                float(t.pnl) if t.pnl is not None else None,
                float(t.cum_pnl) if t.cum_pnl is not None else None,
            )
finally:
    s.close()
