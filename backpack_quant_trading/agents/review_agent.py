"""复盘 Agent：对比历史建议与当前价，写入 agent_reviews。"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Any, Dict, Optional

from backpack_quant_trading.core.agent_memory_store import query_memory, upsert_memory

logger = logging.getLogger(__name__)


def _parse_report_doc(doc: str) -> Dict[str, Any]:
    """从 persist_report 文本解析 action/support/resistance。"""
    out: Dict[str, Any] = {"raw": doc}
    m = re.search(r"action=(\w+)", doc or "")
    if m:
        out["action"] = m.group(1)
    m = re.search(r"support=([0-9.]+|None)", doc or "")
    if m and m.group(1) != "None":
        try:
            out["support"] = float(m.group(1))
        except Exception:
            pass
    m = re.search(r"resistance=([0-9.]+|None)", doc or "")
    if m and m.group(1) != "None":
        try:
            out["resistance"] = float(m.group(1))
        except Exception:
            pass
    m = re.search(r"\]\s*(\S+)\s+action=", doc or "")
    if m:
        out["symbol"] = m.group(1)
    return out


def _estimate_last_price(symbol: str, market: str) -> Optional[float]:
    """尽力取现价；失败返回 None（仍可出结构化复盘）。"""
    try:
        if market == "us_stock":
            from backpack_quant_trading.core.us_stock_signal_scorer import build_us_stock_indicator_snapshot

            snap, _ = build_us_stock_indicator_snapshot(symbol)
            bars = (snap or {}).get("recent_bars") or []
            if bars:
                return float(bars[-1].get("close"))
        elif market == "crypto":
            from backpack_quant_trading.core.crypto_signal_scorer import build_indicator_snapshot

            coin = symbol.upper().replace("USDT", "")
            snap, _ = build_indicator_snapshot(coin)
            bars = (snap or {}).get("recent_bars") or []
            if bars:
                return float(bars[-1].get("close"))
        elif market == "a_share":
            from backpack_quant_trading.core.stock_kline_cache import get_daily_klines_from_cache

            df = get_daily_klines_from_cache(symbol, lookback_days=30)
            if df is not None and not df.empty:
                return float(df["close"].iloc[-1])
    except Exception as exc:
        logger.debug("review price fetch failed: %s", exc)
    return None


def review(
    symbol: str,
    *,
    market: str = "",
    query: str = "",
) -> Dict[str, Any]:
    sym = (symbol or "").strip().upper()
    q = query or f"{sym} 历史建议"
    rows = query_memory("agent_reports", q, n_results=5, filters={"symbol": sym} if sym else None)
    if not rows:
        rows = query_memory("agent_reports", q, n_results=5)

    if not rows:
        return {
            "ok": False,
            "symbol": sym,
            "error": "无历史分析报告可复盘",
            "verdict": "n/a",
        }

    top = rows[0]
    parsed = _parse_report_doc(str(top.get("document") or ""))
    mkt = market or str((top.get("metadata") or {}).get("market") or "")
    last = _estimate_last_price(sym or parsed.get("symbol") or "", mkt)
    action = str(parsed.get("action") or "hold")
    support = parsed.get("support")
    resistance = parsed.get("resistance")

    verdict = "inconclusive"
    note = "缺少现价，仅回顾历史建议"
    if last is not None:
        if action == "buy" and support is not None:
            if last >= float(support):
                verdict = "favorable"
                note = f"现价 {last} 仍在支撑 {support} 上方，买入建议暂未失效"
            else:
                verdict = "unfavorable"
                note = f"现价 {last} 跌破支撑 {support}，买入建议偏误"
        elif action == "sell" and resistance is not None:
            if last <= float(resistance):
                verdict = "favorable"
                note = f"现价 {last} 仍在压力 {resistance} 下方，卖出建议暂未失效"
            else:
                verdict = "unfavorable"
                note = f"现价 {last} 突破压力 {resistance}，卖出建议偏误"
        else:
            note = f"现价 {last}；历史 action={action}"

    result = {
        "ok": True,
        "symbol": sym or parsed.get("symbol"),
        "market": mkt,
        "action_then": action,
        "support_then": support,
        "resistance_then": resistance,
        "last_price": last,
        "verdict": verdict,
        "note": note,
        "source_report_id": top.get("id"),
        "source_document": top.get("document"),
    }

    mid = "rev_" + hashlib.sha1(f"{sym}|{top.get('id')}|{int(time.time())}".encode()).hexdigest()[:16]
    upsert_memory(
        "agent_reviews",
        mid,
        f"[复盘] {result['symbol']} verdict={verdict} | {note}",
        {
            "symbol": str(result["symbol"] or "").upper(),
            "market": mkt,
            "verdict": verdict,
            "scope": "review",
            "ts": int(time.time()),
        },
    )
    result["review_id"] = mid
    return result


def auto_review_due_reports(*, days: int = 3, limit: int = 20) -> Dict[str, Any]:
    """
    扫 agent_reports：ts 早于 N 天、同 symbol 尚无较新 agent_reviews 的条目，批量 review。
    """
    import os
    from datetime import datetime, timezone

    try:
        days = int(os.getenv("AGENT_AUTO_REVIEW_DAYS", str(days)) or days)
    except Exception:
        days = max(1, int(days))
    days = max(1, days)
    cutoff = int(time.time()) - days * 86400

    # 取一批较旧报告：用宽泛 query 再按 metadata.ts 过滤
    reports = query_memory("agent_reports", "历史分析建议 复盘", n_results=min(limit * 2, 40))
    due: list = []
    seen_sym = set()
    for row in reports:
        meta = row.get("metadata") or {}
        sym = str(meta.get("symbol") or "").upper()
        if not sym:
            parsed = _parse_report_doc(str(row.get("document") or ""))
            sym = str(parsed.get("symbol") or "").upper()
        if not sym or sym in seen_sym:
            continue
        ts = meta.get("ts")
        try:
            ts_i = int(ts) if ts not in (None, "") else 0
        except Exception:
            ts_i = 0
        if ts_i and ts_i > cutoff:
            # 仍太新，跳过
            continue
        # 是否已有较新复盘
        revs = query_memory(
            "agent_reviews",
            f"{sym} 复盘",
            n_results=3,
            filters={"symbol": sym},
        )
        has_fresh = False
        for rv in revs:
            rmeta = rv.get("metadata") or {}
            try:
                rts = int(rmeta.get("ts") or 0)
            except Exception:
                rts = 0
            if rts >= (ts_i or 0) and rts >= cutoff:
                has_fresh = True
                break
        if has_fresh:
            continue
        seen_sym.add(sym)
        due.append((sym, str(meta.get("market") or ""), row))
        if len(due) >= limit:
            break

    results = []
    parts = []
    for sym, mkt, _row in due:
        r = review(sym, market=mkt)
        results.append(r)
        parts.append(format_review_markdown(r))

    md = "## 提醒 · 自动复盘\n\n" + ("\n\n".join(parts) if parts else "（本轮无到期报告）")
    return {
        "ok": True,
        "days": days,
        "reviewed": len(results),
        "results": results,
        "markdown": md[:3500],
        "cutoff": cutoff,
        "cutoff_iso": datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat(),
    }


def format_review_markdown(result: Dict[str, Any]) -> str:
    if not result.get("ok"):
        return f"### 复盘\n- 失败: {result.get('error')}"
    return (
        f"### 复盘 · {result.get('symbol')}\n"
        f"- **历史建议**: {result.get('action_then')}\n"
        f"- **当时支撑/压力**: {result.get('support_then')} / {result.get('resistance_then')}\n"
        f"- **现价**: {result.get('last_price')}\n"
        f"- **结论**: {result.get('verdict')} — {result.get('note')}"
    )
