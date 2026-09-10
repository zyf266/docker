"""A股 AI Agent — 日内 T0 规则与信号台账。

规则（仅 30 分钟周期）：
1. 底仓不动：当日尚无「已执行买入」时，卖出信号一律忽略。
2. 买卖配对：有未平日内仓时禁止再买；必须先卖出后才能再买。
3. 当日买入当日平：未平仓在尾盘强制卖出。
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

T0_INTERVAL = "30"

# 程序化出场（仅 30m 有未平日内仓时）：止损 ≥ 止盈 ≥ 午后近乎持平
T0_TAKE_PROFIT_PCT = 0.008  # +0.8%
T0_STOP_LOSS_PCT = 0.0045  # -0.45%
T0_AFTERNOON_FLAT_PCT = 0.0015  # 浮盈不足 0.15%
T0_AFTERNOON_HOUR = 14
T0_AFTERNOON_MINUTE = 30


def is_t0_interval(interval: str) -> bool:
    return str(interval or "") == T0_INTERVAL


def apply_t0_pnl_exits(
    decision: Dict[str, Any],
    *,
    interval: str,
    open_buy: Optional[Dict[str, Any]],
    last_price: Optional[float],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """有未平日内仓时，按浮盈/浮亏/午后时间强制 sell（覆盖 LLM hold）。"""
    d = dict(decision or {})
    if not is_t0_interval(interval):
        return d
    if not open_buy:
        return d
    try:
        entry = float(open_buy.get("price") or 0)
        last = float(last_price or 0)
    except (TypeError, ValueError):
        return d
    if entry <= 0 or last <= 0:
        return d

    pnl_pct = (last / entry) - 1.0
    override = None
    note = ""
    if pnl_pct <= -T0_STOP_LOSS_PCT:
        override = "t0_sl"
        note = f"T0止损：浮亏 {pnl_pct * 100:.2f}% ≤ -{T0_STOP_LOSS_PCT * 100:.2f}%"
    elif pnl_pct >= T0_TAKE_PROFIT_PCT:
        override = "t0_tp"
        note = f"T0止盈：浮盈 {pnl_pct * 100:.2f}% ≥ +{T0_TAKE_PROFIT_PCT * 100:.2f}%"
    else:
        ts = now or datetime.now()
        if (ts.hour > T0_AFTERNOON_HOUR) or (
            ts.hour == T0_AFTERNOON_HOUR and ts.minute >= T0_AFTERNOON_MINUTE
        ):
            if pnl_pct < T0_AFTERNOON_FLAT_PCT:
                override = "t0_time"
                note = (
                    f"T0午后时间止损：≥14:30 且浮盈 {pnl_pct * 100:.2f}% "
                    f"< {T0_AFTERNOON_FLAT_PCT * 100:.2f}%，避免拖到尾盘强平"
                )

    if not override:
        return d

    d["action"] = "sell"
    d["valid"] = True
    d["t0_exit_override"] = override
    d["t0_exit_pnl_pct"] = round(pnl_pct * 100.0, 4)
    d["invalid_reason"] = None
    risks = list(d.get("risk_notes") or [])
    if override not in risks:
        risks.append(override)
    d["risk_notes"] = risks
    thesis = str(d.get("thesis") or "").strip()
    prefix = f"【{note}】"
    if not thesis.startswith("【"):
        d["thesis"] = (prefix + (" " + thesis if thesis else "")).strip()
    elif note not in thesis:
        d["thesis"] = prefix + " " + thesis
    return d


def _row_to_dict(row: Any) -> Dict[str, Any]:
    return {
        "id": row.id,
        "trade_date": row.trade_date,
        "code": row.code,
        "name": row.name,
        "interval": row.interval,
        "side": row.side,
        "status": row.status,
        "reason": row.reason,
        "price": float(row.price) if row.price is not None else None,
        "confidence": float(row.confidence) if row.confidence is not None else None,
        "thesis": row.thesis,
        "pair_id": row.pair_id,
        "source": row.source,
        "as_of": row.as_of,
        "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else None,
    }


def get_open_intraday_buy(
    code: str,
    interval: str,
    trade_date: str,
) -> Optional[Dict[str, Any]]:
    """当日未配对卖出的已执行买入。"""
    from backpack_quant_trading.database.models import AShareAiAgentSignal, DatabaseManager

    code = str(code or "").zfill(6)
    interval = str(interval or T0_INTERVAL)
    db = DatabaseManager()
    session = db.get_session()
    try:
        buys = (
            session.query(AShareAiAgentSignal)
            .filter_by(
                code=code,
                interval=interval,
                trade_date=trade_date,
                side="buy",
                status="executed",
            )
            .order_by(AShareAiAgentSignal.id.asc())
            .all()
        )
        for b in buys:
            closed = (
                session.query(AShareAiAgentSignal)
                .filter(
                    AShareAiAgentSignal.pair_id == b.id,
                    AShareAiAgentSignal.side == "sell",
                    AShareAiAgentSignal.status.in_(("executed", "force_close")),
                )
                .first()
            )
            if not closed:
                return _row_to_dict(b)
        return None
    finally:
        session.close()


def build_t0_position(code: str, interval: str, trade_date: str) -> Dict[str, Any]:
    """供 LLM / 硬规则使用的 T0 持仓视图。"""
    open_buy = get_open_intraday_buy(code, interval, trade_date) if is_t0_interval(interval) else None
    open_ = open_buy is not None
    return {
        "holding": True,
        "has_base_position": True,
        "intraday_ok": True,
        "intraday_open": open_,
        "sellable": open_,
        "bought_today": open_,
        "can_buy": not open_,
        "open_buy_id": (open_buy or {}).get("id"),
        "note": (
            "T0：底仓不动。当前有未平日内仓，只允许卖出平仓，禁止再买。"
            if open_
            else "T0：底仓不动。当前无日内仓，允许买入；卖出信号将被忽略。"
        ),
    }


def apply_t0_rules(
    decision: Dict[str, Any],
    *,
    interval: str,
    intraday_open: bool,
) -> Dict[str, Any]:
    """在硬规则之前套 T0；可能把 buy/sell 改成 hold。"""
    from backpack_quant_trading.core.a_share_ai_agent import normalize_action

    d = dict(decision or {})
    if not is_t0_interval(interval):
        return d
    action = normalize_action(d.get("action"))
    d["action"] = action
    d["t0_raw_action"] = action
    if action == "sell" and not intraday_open:
        d["action"] = "hold"
        d["valid"] = False
        d["t0_ignored"] = True
        d["invalid_reason"] = "T0：当日首笔/无日内买入仓，忽略卖出（底仓不动）"
        return d
    if action == "buy" and intraday_open:
        d["action"] = "hold"
        d["valid"] = False
        d["t0_ignored"] = True
        d["invalid_reason"] = "T0：已有未平日内仓，须先卖出后再买"
        return d
    d["t0_ignored"] = False
    return d


def record_signal(
    *,
    code: str,
    name: str,
    interval: str,
    side: str,
    status: str,
    trade_date: str,
    as_of: str = "",
    price: Optional[float] = None,
    confidence: Optional[float] = None,
    thesis: str = "",
    reason: str = "",
    pair_id: Optional[int] = None,
    source: str = "scan",
    decision: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    from backpack_quant_trading.database.models import AShareAiAgentSignal, DatabaseManager

    code = str(code or "").zfill(6)
    side = str(side or "").lower()
    if side not in ("buy", "sell"):
        return None
    db = DatabaseManager()
    try:
        db.create_tables()
    except Exception:
        pass
    session = db.get_session()
    try:
        row = AShareAiAgentSignal(
            trade_date=trade_date,
            code=code,
            name=(name or code)[:64],
            interval=str(interval or T0_INTERVAL),
            side=side,
            status=status,
            reason=(reason or "")[:255] or None,
            price=price,
            confidence=confidence,
            thesis=(thesis or "")[:4000] or None,
            pair_id=pair_id,
            source=source or "scan",
            decision_json=json.dumps(decision or {}, ensure_ascii=False)[:12000] if decision else None,
            as_of=as_of or None,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _row_to_dict(row)
    except Exception as exc:
        session.rollback()
        logger.exception("record_signal failed: %s", exc)
        return None
    finally:
        session.close()


def persist_decision_trades(
    result: Dict[str, Any],
    *,
    trade_date: str,
    price: Optional[float] = None,
    open_buy: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """根据 decide_once 结果写入买卖台账（含 T0 忽略记录）。"""
    d = result.get("decision") or {}
    if not isinstance(d, dict):
        return None
    interval = str(result.get("interval") or "")
    code = str(result.get("code") or "")
    name = str(result.get("name") or code)
    as_of = str(result.get("as_of") or "")
    conf = d.get("confidence")
    try:
        conf_f = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf_f = None
    thesis = str(d.get("thesis") or "")
    final = str(d.get("action") or "hold").lower()
    raw = str(d.get("t0_raw_action") or final).lower()

    # 忽略的买卖：仍落库便于复盘
    if d.get("t0_ignored") and raw in ("buy", "sell"):
        return record_signal(
            code=code,
            name=name,
            interval=interval,
            side=raw,
            status="ignored",
            trade_date=trade_date,
            as_of=as_of,
            price=price,
            confidence=conf_f,
            thesis=thesis,
            reason=str(d.get("invalid_reason") or "t0_ignored"),
            source="scan",
            decision=d,
        )

    if final == "buy":
        return record_signal(
            code=code,
            name=name,
            interval=interval,
            side="buy",
            status="executed",
            trade_date=trade_date,
            as_of=as_of,
            price=price,
            confidence=conf_f,
            thesis=thesis,
            reason="scan_buy",
            source="scan",
            decision=d,
        )

    if final == "sell":
        pair_id = (open_buy or {}).get("id")
        ov = str(d.get("t0_exit_override") or "").strip()
        sell_reason = "scan_sell"
        if ov and ov not in thesis:
            thesis = (f"【{ov}】 " + thesis).strip()
        return record_signal(
            code=code,
            name=name,
            interval=interval,
            side="sell",
            status="executed",
            trade_date=trade_date,
            as_of=as_of,
            price=price,
            confidence=conf_f,
            thesis=thesis,
            reason=sell_reason,
            pair_id=int(pair_id) if pair_id else None,
            source="scan",
            decision=d,
        )
    return None


def force_close_open_buy(
    *,
    code: str,
    name: str,
    interval: str,
    trade_date: str,
    as_of: str,
    price: Optional[float] = None,
    push: bool = True,
) -> Optional[Dict[str, Any]]:
    """尾盘强制平掉今日买入仓。"""
    if not is_t0_interval(interval):
        return None
    open_buy = get_open_intraday_buy(code, interval, trade_date)
    if not open_buy:
        return None
    thesis = "尾盘强制卖出：今日买入仓位日内未出现卖出信号，按 T0 规则平仓（底仓不动）。"
    decision = {
        "action": "sell",
        "valid": True,
        "confidence": 1.0,
        "thesis": thesis,
        "risk_notes": ["force_eod"],
        "t0_force_close": True,
    }
    row = record_signal(
        code=code,
        name=name or code,
        interval=interval,
        side="sell",
        status="force_close",
        trade_date=trade_date,
        as_of=as_of,
        price=price,
        confidence=1.0,
        thesis=thesis,
        reason="force_eod",
        pair_id=int(open_buy["id"]),
        source="force_eod",
        decision=decision,
    )
    result = {
        "ok": True,
        "code": str(code).zfill(6),
        "name": name or code,
        "interval": interval,
        "interval_label": "30分钟",
        "as_of": as_of,
        "decision": decision,
        "trade_record": row,
        "force_eod": True,
    }
    if push:
        try:
            from backpack_quant_trading.core.a_share_ai_agent import can_push_now
            from backpack_quant_trading.core.a_share_ai_agent_dingtalk import push_signal_action_card

            if can_push_now():
                ok, msg = push_signal_action_card(result)
                result["dingtalk_ok"] = ok
                result["dingtalk_msg"] = msg
        except Exception as exc:
            result["dingtalk_ok"] = False
            result["dingtalk_msg"] = str(exc)
    return result


def list_signals(
    *,
    code: str = "",
    interval: str = "",
    trade_date: str = "",
    date_from: str = "",
    date_to: str = "",
    status: str = "",
    limit: int = 200,
) -> List[Dict[str, Any]]:
    from backpack_quant_trading.database.models import AShareAiAgentSignal, DatabaseManager

    db = DatabaseManager()
    try:
        db.create_tables()
    except Exception:
        pass
    session = db.get_session()
    try:
        q = session.query(AShareAiAgentSignal)
        if code:
            q = q.filter(AShareAiAgentSignal.code == str(code).zfill(6))
        if interval:
            q = q.filter(AShareAiAgentSignal.interval == str(interval))
        if trade_date:
            q = q.filter(AShareAiAgentSignal.trade_date == trade_date)
        if date_from:
            q = q.filter(AShareAiAgentSignal.trade_date >= date_from)
        if date_to:
            q = q.filter(AShareAiAgentSignal.trade_date <= date_to)
        if status:
            q = q.filter(AShareAiAgentSignal.status == status)
        rows = q.order_by(AShareAiAgentSignal.id.desc()).limit(max(1, min(int(limit or 200), 500))).all()
        return [_row_to_dict(r) for r in rows]
    finally:
        session.close()


def list_symbol_summaries(*, limit: int = 50) -> List[Dict[str, Any]]:
    """按标的汇总买卖笔数与最近交易日。"""
    from backpack_quant_trading.database.models import AShareAiAgentSignal, DatabaseManager

    db = DatabaseManager()
    try:
        db.create_tables()
    except Exception:
        pass
    session = db.get_session()
    try:
        rows = (
            session.query(AShareAiAgentSignal)
            .order_by(AShareAiAgentSignal.id.desc())
            .limit(3000)
            .all()
        )
        agg: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            key = f"{r.code}|{r.interval}"
            if key not in agg:
                agg[key] = {
                    "code": r.code,
                    "name": r.name or r.code,
                    "interval": r.interval,
                    "buy_n": 0,
                    "sell_n": 0,
                    "ignored_n": 0,
                    "force_n": 0,
                    "last_date": r.trade_date,
                    "last_side": r.side,
                    "last_status": r.status,
                }
            a = agg[key]
            if r.status == "ignored":
                a["ignored_n"] += 1
            elif r.status == "force_close":
                a["force_n"] += 1
                a["sell_n"] += 1
            elif r.side == "buy" and r.status == "executed":
                a["buy_n"] += 1
            elif r.side == "sell" and r.status == "executed":
                a["sell_n"] += 1
        out = list(agg.values())
        out.sort(key=lambda x: (x.get("last_date") or "", x.get("code") or ""), reverse=True)
        return out[: max(1, min(int(limit or 50), 200))]
    finally:
        session.close()


def last_bar_price(bars: Optional[List[Dict[str, Any]]]) -> Optional[float]:
    if not bars:
        return None
    try:
        return float(bars[-1].get("close") or 0) or None
    except (TypeError, ValueError, IndexError):
        return None


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def calc_round_pnl(buy_price: Any, sell_price: Any) -> Dict[str, Optional[float]]:
    """单笔（买+卖）盈亏：点差 + 收益率%。"""
    bp = _safe_float(buy_price)
    sp = _safe_float(sell_price)
    if bp is None or sp is None or bp <= 0:
        return {"pnl_abs": None, "pnl_pct": None}
    pnl_abs = round(sp - bp, 4)
    pnl_pct = round((sp / bp - 1.0) * 100.0, 4)
    return {"pnl_abs": pnl_abs, "pnl_pct": pnl_pct}


def build_closed_rounds_from_rows(rows: List[Any]) -> List[Dict[str, Any]]:
    """
    一笔买入 + 一笔卖出（pair_id=buy.id）= 一笔成交。
    rows 为 ORM 或含 id/side/status/pair_id/price 的 dict。
    """
    by_id: Dict[int, Any] = {}
    for r in rows:
        rid = int(getattr(r, "id", None) or (r.get("id") if isinstance(r, dict) else 0) or 0)
        if rid:
            by_id[rid] = r

    def _g(obj: Any, key: str, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    rounds: List[Dict[str, Any]] = []
    for r in rows:
        side = str(_g(r, "side") or "").lower()
        status = str(_g(r, "status") or "")
        if side != "sell" or status not in ("executed", "force_close"):
            continue
        pair_id = _g(r, "pair_id")
        if pair_id is None:
            continue
        try:
            buy = by_id.get(int(pair_id))
        except (TypeError, ValueError):
            buy = None
        if not buy:
            continue
        buy_price = _g(buy, "price")
        sell_price = _g(r, "price")
        pnl = calc_round_pnl(buy_price, sell_price)
        rounds.append(
            {
                "sell_id": int(_g(r, "id") or 0),
                "buy_id": int(pair_id),
                "code": str(_g(r, "code") or _g(buy, "code") or ""),
                "name": str(_g(r, "name") or _g(buy, "name") or ""),
                "interval": str(_g(r, "interval") or _g(buy, "interval") or ""),
                "trade_date": str(_g(r, "trade_date") or ""),
                "buy_date": str(_g(buy, "trade_date") or ""),
                "buy_price": _safe_float(buy_price),
                "sell_price": _safe_float(sell_price),
                "pnl_abs": pnl["pnl_abs"],
                "pnl_pct": pnl["pnl_pct"],
                "status": status,
                "reason": _g(r, "reason"),
                "as_of": _g(r, "as_of") or _g(r, "created_at"),
            }
        )
    rounds.sort(key=lambda x: (x.get("trade_date") or "", x.get("sell_id") or 0), reverse=True)
    return rounds


def _agg_rounds(rounds: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = 0
    win_n = 0
    sum_abs = 0.0
    sum_pct = 0.0
    for r in rounds:
        if r.get("pnl_pct") is None:
            continue
        n += 1
        sum_abs += float(r.get("pnl_abs") or 0)
        sum_pct += float(r["pnl_pct"])
        if float(r["pnl_pct"]) > 0:
            win_n += 1
    return {
        "n": n,
        "win_n": win_n,
        "win_rate_pct": round(win_n / n * 100.0, 2) if n else 0.0,
        "pnl_abs_sum": round(sum_abs, 4),
        "pnl_pct_sum": round(sum_pct, 4),
        "pnl_pct_avg": round(sum_pct / n, 4) if n else 0.0,
    }


def summarize_pnl(
    *,
    code: str = "",
    interval: str = "",
    as_of: Optional[date] = None,
    limit_rows: int = 3000,
) -> Dict[str, Any]:
    """台账盈亏：单笔回合 + 单日单票 + 近7/30天（按卖出日）。"""
    from backpack_quant_trading.database.models import AShareAiAgentSignal, DatabaseManager

    today = as_of or date.today()
    d7 = (today - timedelta(days=6)).isoformat()
    d30 = (today - timedelta(days=29)).isoformat()
    today_s = today.isoformat()

    db = DatabaseManager()
    try:
        db.create_tables()
    except Exception:
        pass
    session = db.get_session()
    try:
        q = session.query(AShareAiAgentSignal)
        if code:
            q = q.filter(AShareAiAgentSignal.code == str(code).zfill(6))
        if interval:
            q = q.filter(AShareAiAgentSignal.interval == str(interval))
        # 拉足够买卖腿以便 pair 对得上
        rows = q.order_by(AShareAiAgentSignal.id.desc()).limit(max(100, min(int(limit_rows or 3000), 8000))).all()
        rounds = build_closed_rounds_from_rows(rows)

        day_by_code: Dict[str, Dict[str, Any]] = {}
        for r in rounds:
            if r.get("trade_date") != today_s:
                continue
            if r.get("pnl_pct") is None:
                continue
            c = r["code"]
            bucket = day_by_code.setdefault(
                c,
                {
                    "code": c,
                    "name": r.get("name") or c,
                    "n": 0,
                    "pnl_abs_sum": 0.0,
                    "pnl_pct_sum": 0.0,
                },
            )
            bucket["n"] += 1
            bucket["pnl_abs_sum"] = round(bucket["pnl_abs_sum"] + float(r["pnl_abs"] or 0), 4)
            bucket["pnl_pct_sum"] = round(bucket["pnl_pct_sum"] + float(r["pnl_pct"]), 4)
            bucket["name"] = r.get("name") or bucket["name"]

        day_list = sorted(day_by_code.values(), key=lambda x: x["pnl_pct_sum"], reverse=True)
        r7 = [r for r in rounds if (r.get("trade_date") or "") >= d7]
        r30 = [r for r in rounds if (r.get("trade_date") or "") >= d30]

        return {
            "as_of": today_s,
            "rounds": rounds[:80],
            "today_by_code": day_list,
            "today": _agg_rounds([r for r in rounds if r.get("trade_date") == today_s]),
            "d7": _agg_rounds(r7),
            "d30": _agg_rounds(r30),
            "all": _agg_rounds(rounds),
        }
    finally:
        session.close()


def enrich_signals_with_pnl(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """给卖出腿挂上配对买入价与单笔盈亏（就地拷贝）。"""
    if not items:
        return items
    buy_ids = []
    for it in items:
        if str(it.get("side") or "").lower() != "sell":
            continue
        if it.get("status") not in ("executed", "force_close"):
            continue
        if it.get("pair_id") is None:
            continue
        try:
            buy_ids.append(int(it["pair_id"]))
        except (TypeError, ValueError):
            pass
    buy_ids = list({i for i in buy_ids if i})
    buys: Dict[int, Dict[str, Any]] = {}
    if buy_ids:
        from backpack_quant_trading.database.models import AShareAiAgentSignal, DatabaseManager

        db = DatabaseManager()
        session = db.get_session()
        try:
            for row in session.query(AShareAiAgentSignal).filter(AShareAiAgentSignal.id.in_(buy_ids)).all():
                buys[int(row.id)] = _row_to_dict(row)
        finally:
            session.close()
        # 同批 items 里已有的 buy 也可补全
        for it in items:
            if str(it.get("side") or "").lower() == "buy" and it.get("id") is not None:
                buys.setdefault(int(it["id"]), it)

    out: List[Dict[str, Any]] = []
    for it in items:
        row = dict(it)
        if (
            str(row.get("side") or "").lower() == "sell"
            and row.get("status") in ("executed", "force_close")
            and row.get("pair_id") is not None
        ):
            try:
                bid = int(row["pair_id"])
            except (TypeError, ValueError):
                bid = None
            buy = buys.get(bid) if bid is not None else None
            if buy:
                pnl = calc_round_pnl(buy.get("price"), row.get("price"))
                row["buy_price"] = _safe_float(buy.get("price"))
                row["pnl_abs"] = pnl["pnl_abs"]
                row["pnl_pct"] = pnl["pnl_pct"]
        out.append(row)
    return out
