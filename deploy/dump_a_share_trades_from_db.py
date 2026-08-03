import csv
from pathlib import Path
from backpack_quant_trading.core.a_share_strategy_import import get_spec_by_code
from backpack_quant_trading.database.models import db_manager
from backpack_quant_trading.api.routers.strategy import StrategyBacktestTrade

ROOT = Path("/tmp/a_share_csv_dump")
ROOT.mkdir(parents=True, exist_ok=True)
HEADER = [
    "交易编号", "类型", "日期和时间", "信号", "价格 CNY", "大小（数量）", "大小（价值）",
    "净损益 CNY", "净损益 %", "有利波动 CNY", "有利波动 %", "不利波动 CNY", "不利波动 %",
    "累计损益 CNY", "累计损益 %",
]


def dump(code: str, out_name: str) -> int:
    spec = get_spec_by_code(code)
    s = db_manager.get_session()
    try:
        rows = (
            s.query(StrategyBacktestTrade)
            .filter_by(strategy_name=spec.strategy_name, symbol=spec.symbol, timeframe="2H")
            .order_by(StrategyBacktestTrade.trade_no.asc(), StrategyBacktestTrade.trade_time.asc())
            .all()
        )
    finally:
        s.close()
    # TV CSV 习惯：同编号出场在前、进场在后
    by_no = {}
    for r in rows:
        by_no.setdefault(int(r.trade_no), []).append(r)
    ordered = []
    for no in sorted(by_no):
        group = by_no[no]
        exits = [x for x in group if "出" in str(x.trade_type or "")]
        entries = [x for x in group if x not in exits]
        ordered.extend(exits + entries)

    path = ROOT / out_name
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in ordered:
            tt = r.trade_time.strftime("%Y-%m-%d %H:%M") if r.trade_time else ""
            w.writerow([
                r.trade_no,
                r.trade_type,
                tt,
                r.signal,
                float(r.price or 0),
                float(r.position_qty or 0),
                float(r.position_value or 0),
                float(r.pnl or 0) if r.pnl is not None else "",
                float(r.pnl_pct or 0) if r.pnl_pct is not None else "",
                float(r.runup or 0) if r.runup is not None else "",
                float(r.runup_pct or 0) if r.runup_pct is not None else "",
                float(r.drawdown or 0) if r.drawdown is not None else "",
                float(r.drawdown_pct or 0) if r.drawdown_pct is not None else "",
                float(r.cum_pnl or 0) if r.cum_pnl is not None else "",
                float(r.cum_pnl_pct or 0) if r.cum_pnl_pct is not None else "",
            ])
    print(code, "rows", len(ordered), "->", path)
    for r in ordered:
        if str(r.trade_no) == "4" or (r.trade_time and r.trade_time.strftime("%Y-%m-%d") == "2026-07-10"):
            print(" ", r.trade_no, r.trade_type, r.trade_time, r.price, r.signal, r.pnl_pct, r.cum_pnl_pct)
    return len(ordered)


# 兆易创新截图那笔；顺带备份其它 A 股
for code, name in [("603986", "兆易创新.csv"), ("300308", "中际旭创.csv"), ("688146", "中船.csv"), ("002837", "英维克.csv")]:
    dump(code, name)
    # 也写编号 csv
    dump(code, f"{code}.csv")
