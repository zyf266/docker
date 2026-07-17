"""A股分析师 Agent。"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from backpack_quant_trading.agents.analysts.base import run_analyst_pipeline
from backpack_quant_trading.agents.prompts import A_SHARE_ANALYST_SYSTEM
from backpack_quant_trading.agents.types import AgentId, AnalyzeReport, AnalyzeRequest, Market


def _snapshot(symbol: str, req: AnalyzeRequest) -> Tuple[Dict[str, Any], str]:
    code = (symbol or "").strip().upper().replace(".SH", "").replace(".SZ", "")
    try:
        from backpack_quant_trading.core.stock_kline_cache import get_daily_klines_from_cache

        df = get_daily_klines_from_cache(code, lookback_days=120)
        if df is None or getattr(df, "empty", True):
            return {
                "symbol": code,
                "last_close": None,
                "metrics": {"note": "无本地A股K线，降级分析"},
                "recent_bars": [],
                "interval": "1d",
            }, "无本地A股K线"

        recent = []
        tail = df.tail(10)
        for _, row in tail.iterrows():
            recent.append({
                "time": str(row.get("date") or ""),
                "close": float(row.get("close") or 0),
                "volume": float(row.get("vol") or row.get("volume") or 0),
            })
        last = recent[-1]["close"] if recent else float(df["close"].iloc[-1])
        closes = [x["close"] for x in recent if x.get("close")]
        support = min(closes) if closes else last * 0.97
        resistance = max(closes) if closes else last * 1.03
        return {
            "symbol": code,
            "last_close": last,
            "interval": "1d",
            "metrics": {
                "last_close": last,
                "close": last,
                "support_hint": support,
                "resistance_hint": resistance,
                "supports": [{"price": support, "timeframe": "1d", "label": "S1"}],
                "resistances": [{"price": resistance, "timeframe": "1d", "label": "R1"}],
                "bars": int(len(df)),
            },
            "recent_bars": recent,
        }, ""
    except Exception as exc:
        return {
            "symbol": code,
            "last_close": None,
            "metrics": {},
            "recent_bars": [],
            "interval": "1d",
        }, str(exc)


def analyze(req: AnalyzeRequest) -> AnalyzeReport:
    req.market = Market.A_SHARE
    req.agent_id = AgentId.A_SHARE_ANALYST
    return run_analyst_pipeline(
        req,
        agent_id=AgentId.A_SHARE_ANALYST,
        market=Market.A_SHARE,
        system_prompt=A_SHARE_ANALYST_SYSTEM,
        persona_hint="资深A股投研分析师（基本面+政策新闻重于技术）",
        snapshot_fn=_snapshot,
    )
