"""删除 A 股同日进/出（日内）交易，并按出场顺序重算累计损益。"""
from __future__ import annotations

from decimal import Decimal

from backpack_quant_trading.core.a_share_strategy_import import A_SHARE_STRATEGY_SPECS
from backpack_quant_trading.database.models import db_manager
from backpack_quant_trading.api.routers.strategy import StrategyBacktestTrade


def _is_entry(t) -> bool:
    return "进场" in str(t.trade_type or "")


def _is_exit(t) -> bool:
    tp = str(t.trade_type or "")
    return ("出" in tp) or ("止损" in tp)


def purge_intraday_for_spec(spec) -> dict:
    s = db_manager.get_session()
    removed = []
    try:
        rows = (
            s.query(StrategyBacktestTrade)
            .filter_by(
                strategy_name=spec.strategy_name,
                symbol=spec.symbol,
                timeframe="2H",
            )
            .order_by(StrategyBacktestTrade.trade_no.asc(), StrategyBacktestTrade.trade_time.asc())
            .all()
        )
        by = {}
        for r in rows:
            by.setdefault(int(r.trade_no), []).append(r)

        drop_nos = []
        for no, g in by.items():
            e = next((x for x in g if _is_entry(x)), None)
            x = next((x for x in g if _is_exit(x)), None)
            if e and x and e.trade_time and x.trade_time and e.trade_time.date() == x.trade_time.date():
                drop_nos.append(no)
                removed.append(
                    {
                        "trade_no": no,
                        "entry": str(e.trade_time),
                        "exit": str(x.trade_time),
                        "pnl_pct": float(x.pnl_pct or 0),
                    }
                )

        if not drop_nos:
            return {"code": spec.code, "removed": [], "kept": len(by)}

        for no in drop_nos:
            for r in by[no]:
                s.delete(r)
        s.flush()

        # 重算剩余出场累计
        remain = (
            s.query(StrategyBacktestTrade)
            .filter_by(
                strategy_name=spec.strategy_name,
                symbol=spec.symbol,
                timeframe="2H",
            )
            .order_by(StrategyBacktestTrade.trade_time.asc(), StrategyBacktestTrade.trade_no.asc())
            .all()
        )
        by2 = {}
        for r in remain:
            by2.setdefault(int(r.trade_no), []).append(r)

        initial = float(spec.initial_capital_cny)
        cum = 0.0
        # 按出场时间排序推进累计
        ordered_nos = sorted(
            by2.keys(),
            key=lambda n: next(x.trade_time for x in by2[n] if _is_exit(x)),
        )
        for no in ordered_nos:
            g = by2[no]
            ex = next(x for x in g if _is_exit(x))
            pnl = float(ex.pnl or 0)
            cum += pnl
            cum_pct = cum / initial * 100.0
            for r in g:
                r.cum_pnl = Decimal(str(round(cum, 6)))
                r.cum_pnl_pct = Decimal(str(round(cum_pct, 4)))

        s.commit()
        return {"code": spec.code, "removed": removed, "kept": len(by2), "final_cum_pct": round(cum / initial * 100, 4)}
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


if __name__ == "__main__":
    for spec in A_SHARE_STRATEGY_SPECS:
        print(purge_intraday_for_spec(spec))
