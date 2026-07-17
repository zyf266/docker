"""美股分析师 Agent。"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from backpack_quant_trading.agents.analysts.base import run_analyst_pipeline
from backpack_quant_trading.agents.prompts import US_ANALYST_SYSTEM
from backpack_quant_trading.agents.types import AgentId, AnalyzeReport, AnalyzeRequest, Market


def _snapshot(symbol: str, req: AnalyzeRequest) -> Tuple[Dict[str, Any], str]:
    try:
        from backpack_quant_trading.core.us_stock_signal_scorer import build_us_stock_indicator_snapshot

        snap, err = build_us_stock_indicator_snapshot(symbol, interval=req.timeframe or None)
        if not snap:
            return {}, err or "无美股快照"
        metrics = dict(snap.get("metrics") or {})
        last = None
        bars = snap.get("recent_bars") or []
        if bars:
            last = bars[-1].get("close")
        out = {
            "symbol": snap.get("symbol") or symbol,
            "last_close": last,
            "metrics": metrics,
            "recent_bars": bars,
            "interval": snap.get("interval") or req.timeframe or "1d",
        }
        # 新闻上下文供钉钉消息面展示
        try:
            from backpack_quant_trading.core.us_stock_news import fetch_us_stock_news_context

            out["news_context"] = fetch_us_stock_news_context(symbol, max_items=8)
        except Exception:
            pass
        return out, ""
    except Exception as exc:
        return {}, str(exc)


def analyze(req: AnalyzeRequest) -> AnalyzeReport:
    req.market = Market.US_STOCK
    req.agent_id = AgentId.US_ANALYST
    return run_analyst_pipeline(
        req,
        agent_id=AgentId.US_ANALYST,
        market=Market.US_STOCK,
        system_prompt=US_ANALYST_SYSTEM,
        persona_hint="资深美股投研分析师（基本面+新闻重于技术）",
        snapshot_fn=_snapshot,
    )
