#!/usr/bin/env python
"""生成单只 A 股 strategy_backtest_trade INSERT SQL。"""
import sys
from datetime import datetime, time as dt_time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backpack_quant_trading.core.a_share_strategy_import import (
    TIMEFRAME,
    get_spec_by_code,
    recompound_trades_from_csv,
)


def main(code: str) -> None:
    spec = get_spec_by_code(code)
    if not spec:
        raise SystemExit(f"未知代码: {code}")
    csv = ROOT / spec.csv_filename
    if not csv.exists():
        raise SystemExit(f"CSV 不存在: {csv}")

    ts = datetime.combine(spec.trade_start_date, dt_time(9, 30))
    start_sig = "除权开盘价" if spec.trade_start_open_price else "研报次日开盘"
    rows = recompound_trades_from_csv(
        csv,
        initial_capital=spec.initial_capital_cny,
        trade_start=ts,
        open_price_on_start=spec.trade_start_open_price,
        start_entry_signal=start_sig,
    )
    if not rows:
        raise SystemExit(f"{code} 无有效交易")

    sn, sym, tf = spec.strategy_name, spec.symbol, TIMEFRAME
    out = ROOT / f"{code}_insert.sql"
    trade_nos = sorted({r["trade_no"] for r in rows})
    final = rows[-1]["cum_pnl"] + spec.initial_capital_cny
    lines = [
        "-- 先删旧数据",
        f"DELETE FROM strategy_backtest_trade WHERE strategy_name='{sn}' AND symbol='{sym}' AND timeframe='{tf}';",
        "",
    ]
    for r in rows:
        tt = r["trade_time"].strftime("%Y-%m-%d %H:%M:%S")
        sig = (r.get("signal") or "").replace("'", "''")
        lines.append(
            "INSERT INTO strategy_backtest_trade "
            "(strategy_name,symbol,timeframe,trade_no,trade_type,`signal`,trade_time,price,"
            "position_qty,position_value,pnl,pnl_pct,runup,runup_pct,drawdown,drawdown_pct,cum_pnl,cum_pnl_pct) VALUES "
            f"('{sn}','{sym}','{tf}',{r['trade_no']},'{r['trade_type']}','{sig}','{tt}',"
            f"{r['price']},{r['position_qty']},{r['position_value']},{r['pnl']},{r['pnl_pct']},"
            f"{r['runup']},{r['runup_pct']},{r['drawdown']},{r['drawdown_pct']},{r['cum_pnl']},{r['cum_pnl_pct']});"
        )
    lines.append("")
    lines.append(f"-- 共 {len(trade_nos)} 笔完整交易, {len(rows)} 条记录, 期末资金 {final:.2f}")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out)
    print(f"trades={len(trade_nos)} rows={len(rows)} final={final:.2f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "002837")
