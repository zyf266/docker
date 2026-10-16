"""MA 5/30/200 标签看板。

快照写入表 ma_label_snapshots。同一币种、同一周期只展示 created_at 最新的一条。

价格分：收盘价在每根均线之上 +1，之下 -1，范围 -3..3。
排列分：短>中 且 中>长 为 +2，反之为 -2，其余为 0。
总分 = 价格分 + 排列分，范围 -5..5。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import declarative_base

from backpack_quant_trading.database.models import DatabaseManager

StoreBase = declarative_base()


class MaLabelSnapshot(StoreBase):
    __tablename__ = "ma_label_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False, index=True)
    timeframe = Column(String(8), nullable=False, index=True)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, index=True)

TIMEFRAMES = (
    {"id": "30m", "label": "30分钟"},
    {"id": "60m", "label": "60分钟"},
    {"id": "120m", "label": "120分钟"},
    {"id": "1d", "label": "日线"},
)

def sma(values: List[float], length: int) -> Optional[float]:
    if length <= 0 or len(values) < length:
        return None
    window = values[-length:]
    return sum(window) / length


def _sign_vs(price: float, ma: float) -> int:
    return 1 if price >= ma else -1


def classify_score(total: int) -> Dict[str, Any]:
    if total >= 5:
        state, state_cn, sug, side = "strong_bull", "极强多头", 100, "做多"
    elif total >= 3:
        state, state_cn, sug, side = "bull", "多头趋势", 60, "做多"
    elif total >= 1:
        state, state_cn, sug, side = "weak_bull", "偏多", 20, "做多"
    elif total <= -5:
        state, state_cn, sug, side = "strong_bear", "极强空头", -100, "做空"
    elif total <= -3:
        state, state_cn, sug, side = "bear", "空头趋势", -60, "做空"
    elif total <= -1:
        state, state_cn, sug, side = "weak_bear", "偏空", -20, "做空"
    else:
        state, state_cn, sug, side = "neutral", "震荡", 0, "观望"
    return {
        "state": state,
        "state_cn": state_cn,
        "sug_pos": sug,
        "side_cn": side,
    }


def _deviation(price: float, ma: float) -> Dict[str, Any]:
    pct = (price - ma) / ma * 100 if ma else 0.0
    return {
        "pct": round(pct, 2),
        "side": "线上" if price >= ma else "线下",
        "above": price >= ma,
    }


def score_closes(closes: List[float]) -> Optional[Dict[str, Any]]:
    if len(closes) < 200:
        return None
    price = float(closes[-1])
    ma5 = sma(closes, 5)
    ma30 = sma(closes, 30)
    ma200 = sma(closes, 200)
    if ma5 is None or ma30 is None or ma200 is None:
        return None
    pos = _sign_vs(price, ma5) + _sign_vs(price, ma30) + _sign_vs(price, ma200)
    short_mid = 1 if ma5 >= ma30 else -1
    mid_long = 1 if ma30 >= ma200 else -1
    align = short_mid + mid_long
    total = pos + align
    order = "短 > 中 > 长" if align == 2 else ("短 < 中 < 长" if align == -2 else "交织")
    band = classify_score(total)
    return {
        "price": price,
        "ma5": ma5,
        "ma30": ma30,
        "ma200": ma200,
        "pos_score": pos,
        "align_score": align,
        "align_text": order,
        "total": total,
        "dev_short": _deviation(price, ma5),
        "dev_mid": _deviation(price, ma30),
        "dev_long": _deviation(price, ma200),
        **band,
    }


def state_series(closes: List[float]) -> List[str]:
    """每根已满足 200 均线的 K 线对应状态。前面不足 200 根的位置为空。"""
    out: List[str] = []
    for i in range(len(closes)):
        if i + 1 < 200:
            out.append("")
            continue
        row = score_closes(closes[: i + 1])
        out.append(row["state"] if row else "")
    return out


def snapshot_from_closes(closes: List[float]) -> Optional[Dict[str, Any]]:
    row = score_closes(closes)
    if not row:
        return None
    states = state_series(closes)
    current = row["state"]
    bars = 0
    for st in reversed(states):
        if st != current:
            break
        bars += 1
    row["bars"] = bars
    row["duration_text"] = "延续中" if bars > 0 else "—"
    return row


def normalize_symbol(raw: str) -> str:
    text = (raw or "").strip().upper().replace("/", "").replace("-", "")
    if ":" in text:
        text = text.split(":")[-1]
    if text.startswith("{{") or not text:
        return ""
    if text.endswith("USDT") or text.endswith("USDC"):
        return text
    return f"{text}USDT"


def normalize_timeframe(raw: str) -> str:
    text = (raw or "").strip().lower().replace(" ", "")
    return {
        "1": "1m",
        "1m": "1m",
        "30": "30m",
        "30m": "30m",
        "60": "60m",
        "60m": "60m",
        "1h": "60m",
        "120": "120m",
        "120m": "120m",
        "2h": "120m",
        "d": "1d",
        "1d": "1d",
        "1day": "1d",
        "日线": "1d",
    }.get(text, "")


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any, default: int = 0) -> int:
    number = _to_float(value)
    if number is None:
        return default
    return int(number)


def _session():
    manager = DatabaseManager()
    MaLabelSnapshot.__table__.create(manager.engine, checkfirst=True)
    return manager.get_session()


def save_snapshot(symbol: str, timeframe: str, frame: Dict[str, Any], created_at: Optional[datetime] = None) -> int:
    session = _session()
    try:
        row = MaLabelSnapshot(
            symbol=(symbol or "").strip(),
            timeframe=timeframe,
            payload=json.dumps(frame, ensure_ascii=False),
            created_at=created_at or datetime.now(),
        )
        session.add(row)
        session.commit()
        return int(row.id)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def list_latest(symbols: List[str]) -> Dict[str, Any]:
    """同币种同周期只返回 id 最大（最新写入）的一条。"""
    wanted = []
    for raw in symbols:
        sym = normalize_symbol(raw)
        if sym and sym not in wanted:
            wanted.append(sym)
    session = _session()
    try:
        latest_id = (
            session.query(
                MaLabelSnapshot.symbol,
                MaLabelSnapshot.timeframe,
                func.max(MaLabelSnapshot.id).label("max_id"),
            )
            .group_by(MaLabelSnapshot.symbol, MaLabelSnapshot.timeframe)
            .subquery()
        )
        query = session.query(MaLabelSnapshot).join(
            latest_id,
            MaLabelSnapshot.id == latest_id.c.max_id,
        )
        if wanted:
            query = query.filter(MaLabelSnapshot.symbol.in_(wanted))
        rows = query.all()
    finally:
        session.close()

    by_symbol: Dict[str, Dict[str, Any]] = {sym: {} for sym in wanted}
    for row in rows:
        frame = json.loads(row.payload)
        frame["captured_at"] = row.created_at.strftime("%Y-%m-%d %H:%M:%S")
        by_symbol.setdefault(row.symbol, {})[row.timeframe] = frame
    items = []
    for sym in wanted or sorted(by_symbol):
        frames = by_symbol.get(sym) or {}
        for tf in TIMEFRAMES:
            frames.setdefault(tf["id"], {"error": "暂无记录"})
        items.append({"symbol": sym, "frames": frames})
    return {
        "timeframes": [{"id": tf["id"], "label": tf["label"]} for tf in TIMEFRAMES],
        "items": items,
        "source": "database",
    }


def _demo_frame(
    price: float,
    ma5: float,
    ma30: float,
    ma200: float,
    bars: int,
) -> Dict[str, Any]:
    closes = [ma200] * 199 + [price]
    # 用真实打分函数保持字段一致；均线用传入值覆盖，避免和演示数字不一致。
    row = score_closes([float(i) for i in range(1, 201)])
    assert row is not None
    pos = _sign_vs(price, ma5) + _sign_vs(price, ma30) + _sign_vs(price, ma200)
    align = (1 if ma5 >= ma30 else -1) + (1 if ma30 >= ma200 else -1)
    total = pos + align
    band = classify_score(total)
    order = "短 > 中 > 长" if align == 2 else ("短 < 中 < 长" if align == -2 else "交织")
    row.update({
        "price": price,
        "ma5": ma5,
        "ma30": ma30,
        "ma200": ma200,
        "pos_score": pos,
        "align_score": align,
        "align_text": order,
        "total": total,
        "dev_short": _deviation(price, ma5),
        "dev_mid": _deviation(price, ma30),
        "dev_long": _deviation(price, ma200),
        "bars": bars,
        "duration_text": "延续中",
        **band,
    })
    return row


def seed_demo_snapshots(now: Optional[datetime] = None) -> int:
    """写入两批记录。较早的一批会被同币种同周期的新记录盖住。"""
    moment = now or datetime.now()
    older = moment - timedelta(hours=2)
    samples = [
        ("BTCUSDT", "30m", _demo_frame(64210, 64120, 63880, 61500, 1), older),
        ("BTCUSDT", "30m", _demo_frame(64880, 64610, 64120, 61840, 4), moment),
        ("BTCUSDT", "60m", _demo_frame(64880, 65040, 64330, 62110, 2), moment),
        ("BTCUSDT", "120m", _demo_frame(64880, 63990, 64420, 65200, 6), moment),
        ("BTCUSDT", "1d", _demo_frame(64880, 63220, 61840, 58990, 11), moment),
        ("ETHUSDT", "30m", _demo_frame(2388, 2410, 2360, 2290, 1), older),
        ("ETHUSDT", "30m", _demo_frame(2446.7, 2445.94, 2445.27, 2442.28, 1), moment),
        ("ETHUSDT", "60m", _demo_frame(2446.7, 2452.1, 2438.4, 2410.2, 3), moment),
        ("ETHUSDT", "120m", _demo_frame(2446.7, 2430.2, 2461.5, 2488.0, 2), moment),
        ("ETHUSDT", "1d", _demo_frame(2446.7, 2510.4, 2472.0, 2320.6, 8), moment),
    ]
    count = 0
    for symbol, timeframe, frame, created_at in samples:
        save_snapshot(symbol, timeframe, frame, created_at)
        count += 1
    return count


def save_trend_fields(fields: Dict[str, Any]) -> Optional[int]:
    """把 TradingView「标签信号提醒」字段写成一条快照。不拉行情。"""
    raw_symbol = str(fields.get("symbol") or "")
    raw_interval = str(fields.get("interval") or "")
    symbol = normalize_symbol(raw_symbol)
    unresolved_symbol = not symbol
    if unresolved_symbol:
        strategy = str(fields.get("strategy") or "").strip()
        symbol = strategy or "未识别品种"
    timeframe = normalize_timeframe(raw_interval)
    unresolved_tf = not timeframe
    if unresolved_tf:
        timeframe = "unknown"
    price = _to_float(fields.get("close"))
    ma5 = _to_float(fields.get("ma5"))
    ma30 = _to_float(fields.get("ma30"))
    ma200 = _to_float(fields.get("ma200"))
    total = _to_int(fields.get("score"))
    pos = _to_int(fields.get("pos_score"))
    align = _to_int(fields.get("align_score"))
    sug = _to_int(fields.get("sug_pos"))
    if align == 2:
        align_text = "短 > 中 > 长"
    elif align == -2:
        align_text = "短 < 中 < 长"
    else:
        align_text = "交织"
    if sug > 0:
        side = "做多"
    elif sug < 0:
        side = "做空"
    else:
        side = "观望"
    frame = {
        "price": price,
        "ma5": ma5,
        "ma30": ma30,
        "ma200": ma200,
        "pos_score": pos,
        "align_score": align,
        "align_text": align_text,
        "total": total,
        "dev_short": _deviation(price, ma5) if price is not None and ma5 else {"pct": 0, "side": "—", "above": True},
        "dev_mid": _deviation(price, ma30) if price is not None and ma30 else {"pct": 0, "side": "—", "above": True},
        "dev_long": _deviation(price, ma200) if price is not None and ma200 else {"pct": 0, "side": "—", "above": True},
        "state": str(fields.get("state") or ""),
        "state_cn": str(fields.get("state_cn") or "—"),
        "sug_pos": sug,
        "side_cn": side,
        "bars": None,
        "duration_text": str(fields.get("bar_time") or "—"),
        "direction": str(fields.get("direction") or ""),
        "strategy": str(fields.get("strategy") or ""),
        "unresolved_symbol": unresolved_symbol,
        "unresolved_tf": unresolved_tf,
    }
    return save_snapshot(symbol, timeframe, frame)


def load_board(symbols: List[str]) -> Dict[str, Any]:
    return list_latest(symbols)
