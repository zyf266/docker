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


class MaLabelBoardSymbol(StoreBase):
    """看板展示币种（可增删；默认种子来自 BOARD_SYMBOLS）。"""
    __tablename__ = "ma_label_board_symbols"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False, unique=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


TIMEFRAMES = (
    {"id": "30m", "label": "30分钟"},
    {"id": "60m", "label": "1h"},
    {"id": "120m", "label": "2h"},
    {"id": "4h", "label": "4h"},
    {"id": "1d", "label": "日线"},
)

# 标签看板固定币种（与自选列表一致；Venice Token = VVV）
BOARD_SYMBOLS = (
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "HYPEUSDT",
    "LTCUSDT",
    "AAVEUSDT",
    "UNIUSDT",
    "ENAUSDT",
    "NEARUSDT",
    "SUIUSDT",
    "AVAXUSDT",
    "TAOUSDT",
    "WLDUSDT",
    "VVVUSDT",
    "CRCLUSDT",
    "ZECUSDT",
    "PUMPUSDT",
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
    text = text.replace(".P", "").replace(".PERP", "")
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
        "240": "4h",
        "4": "4h",
        "4h": "4h",
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
    MaLabelBoardSymbol.__table__.create(manager.engine, checkfirst=True)
    return manager.get_session()


def ensure_default_symbols() -> List[str]:
    """库空时写入默认币种；返回当前看板币种顺序。"""
    session = _session()
    try:
        count = session.query(MaLabelBoardSymbol).count()
        if count == 0:
            now = datetime.now()
            for i, sym in enumerate(BOARD_SYMBOLS):
                session.add(
                    MaLabelBoardSymbol(symbol=sym, sort_order=i, created_at=now)
                )
            session.commit()
        rows = (
            session.query(MaLabelBoardSymbol)
            .order_by(MaLabelBoardSymbol.sort_order.asc(), MaLabelBoardSymbol.id.asc())
            .all()
        )
        return [r.symbol for r in rows]
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def list_board_symbols() -> List[str]:
    return ensure_default_symbols()


def add_board_symbol(raw: str) -> str:
    sym = normalize_symbol(raw)
    if not sym:
        raise ValueError("币种无效")
    session = _session()
    try:
        existing = session.query(MaLabelBoardSymbol).filter_by(symbol=sym).first()
        if existing:
            return sym
        max_order = session.query(func.max(MaLabelBoardSymbol.sort_order)).scalar()
        order = int(max_order or 0) + 1
        session.add(MaLabelBoardSymbol(symbol=sym, sort_order=order, created_at=datetime.now()))
        session.commit()
        return sym
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def remove_board_symbol(raw: str) -> bool:
    sym = normalize_symbol(raw)
    if not sym:
        return False
    session = _session()
    try:
        row = session.query(MaLabelBoardSymbol).filter_by(symbol=sym).first()
        if not row:
            return False
        session.delete(row)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


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


def seed_board_mock(now: Optional[datetime] = None) -> int:
    """为看板固定币种 × 全部周期写入模拟趋势/仓位，方便看表格效果。"""
    moment = now or datetime.now()
    # (state, state_cn, sug_pos, side_cn, total)
    bands = (
        ("strong_bull", "极强多头", 100, "做多", 5),
        ("bull", "多头趋势", 60, "做多", 3),
        ("weak_bull", "偏多", 20, "做多", 1),
        ("neutral", "震荡", 0, "观望", 0),
        ("weak_bear", "偏空", -20, "做空", -1),
        ("bear", "空头趋势", -60, "做空", -3),
        ("strong_bear", "极强空头", -100, "做空", -5),
    )
    base_prices = {
        "BTCUSDT": 64880,
        "ETHUSDT": 2446.7,
        "SOLUSDT": 178.4,
        "HYPEUSDT": 28.6,
        "LTCUSDT": 92.3,
        "AAVEUSDT": 186.2,
        "UNIUSDT": 8.45,
        "ENAUSDT": 0.62,
        "NEARUSDT": 5.18,
        "SUIUSDT": 2.34,
        "AVAXUSDT": 28.9,
        "TAOUSDT": 412.5,
        "WLDUSDT": 1.86,
        "VVVUSDT": 3.24,
        "CRCLUSDT": 128.6,
        "ZECUSDT": 48.2,
        "PUMPUSDT": 0.0048,
    }
    count = 0
    for si, symbol in enumerate(BOARD_SYMBOLS):
        price = float(base_prices.get(symbol, 100 + si * 3))
        for ti, tf in enumerate(TIMEFRAMES):
            band = bands[(si + ti * 2) % len(bands)]
            state, state_cn, sug, side, total = band
            frame = {
                "price": price * (1 + (ti - 2) * 0.004),
                "ma5": price * 0.995,
                "ma30": price * 0.98,
                "ma200": price * 0.94,
                "pos_score": 3 if sug > 0 else (-3 if sug < 0 else 0),
                "align_score": 2 if sug >= 60 else (-2 if sug <= -60 else 0),
                "align_text": "短 > 中 > 长" if sug > 0 else "交织",
                "total": total,
                "dev_short": {"pct": 0.5, "side": "线上", "above": True},
                "dev_mid": {"pct": 1.2, "side": "线上", "above": True},
                "dev_long": {"pct": 3.0, "side": "线上", "above": True},
                "state": state,
                "state_cn": state_cn,
                "sug_pos": sug,
                "side_cn": side,
                "bars": ti + 1,
                "duration_text": moment.strftime("%Y-%m-%d %H:%M:%S"),
                "direction": "buy" if sug >= 0 else "sell",
                "strategy": "mock",
                "unresolved_symbol": False,
                "unresolved_tf": False,
            }
            save_snapshot(symbol, tf["id"], frame, moment)
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
    # 未指定时返回看板币种表（可增删；空库会种子默认列表）
    wanted = [normalize_symbol(s) for s in (symbols or [])]
    wanted = [s for s in wanted if s]
    if not wanted:
        wanted = list_board_symbols()
    data = list_latest(wanted)
    data["webhook_path"] = "/api/ma-label-board/tv-webhook"
    return data


def _pick(fields: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in fields and fields.get(key) not in (None, ""):
            return fields.get(key)
    lower = {str(k).lower(): v for k, v in fields.items()}
    for key in keys:
        lk = key.lower()
        if lk in lower and lower.get(lk) not in (None, ""):
            return lower.get(lk)
    return None


def ingest_webhook_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """TradingView → 标签看板：写入快照，同币种同周期只展示最新一条。

    不走钉钉；自动把币种加入看板列表（若尚无）。
    """
    if not isinstance(payload, dict):
        raise ValueError("payload 必须是 JSON 对象")

    fields = {
        "symbol": _pick(payload, "symbol", "交易品种", "币种", "ticker", "coin"),
        "interval": _pick(payload, "interval", "timeframe", "tf", "周期", "K线级别"),
        "close": _pick(payload, "close", "price", "收盘价"),
        "ma5": _pick(payload, "ma5", "MA5"),
        "ma30": _pick(payload, "ma30", "MA30"),
        "ma200": _pick(payload, "ma200", "MA200"),
        "score": _pick(payload, "score", "total", "总分"),
        "pos_score": _pick(payload, "pos_score", "价格分"),
        "align_score": _pick(payload, "align_score", "排列分"),
        "sug_pos": _pick(payload, "sug_pos", "建议仓位", "仓位"),
        "state": _pick(payload, "state"),
        "state_cn": _pick(payload, "state_cn", "状态", "标签"),
        "direction": _pick(payload, "direction", "signal", "action", "方向", "操作"),
        "strategy": _pick(payload, "strategy", "strategy_name", "策略名称", "策略名"),
        "bar_time": _pick(payload, "bar_time", "time", "时间"),
    }

    # 若只给了总分、没给中文状态，用分数推一版
    if not fields.get("state_cn") and fields.get("score") is not None:
        band = classify_score(_to_int(fields.get("score")))
        fields["state"] = fields.get("state") or band["state"]
        fields["state_cn"] = band["state_cn"]
        if fields.get("sug_pos") in (None, ""):
            fields["sug_pos"] = band["sug_pos"]

    snap_id = save_trend_fields(fields)
    symbol = normalize_symbol(str(fields.get("symbol") or ""))
    if not symbol:
        strategy = str(fields.get("strategy") or "").strip()
        symbol = strategy or "未识别品种"
    else:
        try:
            add_board_symbol(symbol)
        except Exception:
            pass

    timeframe = normalize_timeframe(str(fields.get("interval") or "")) or "unknown"
    return {
        "ok": True,
        "id": snap_id,
        "symbol": symbol,
        "timeframe": timeframe,
        "state_cn": str(fields.get("state_cn") or "—"),
        "sug_pos": _to_int(fields.get("sug_pos")),
    }
