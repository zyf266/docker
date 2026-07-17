"""加密货币分析师 Agent。"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from backpack_quant_trading.agents.analysts.base import run_analyst_pipeline
from backpack_quant_trading.agents.prompts import CRYPTO_ANALYST_SYSTEM
from backpack_quant_trading.agents.types import AgentId, AnalyzeReport, AnalyzeRequest, Market


def _normalize_coin(symbol: str) -> str:
    s = (symbol or "").upper().replace("-", "").replace("/", "")
    for suf in ("USDT", "USD", "PERP"):
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
    return s or symbol


def _snapshot(symbol: str, req: AnalyzeRequest) -> Tuple[Dict[str, Any], str]:
    try:
        from backpack_quant_trading.core.crypto_signal_scorer import build_indicator_snapshot
        from backpack_quant_trading.agents.us_equity_overlay import fetch_us_equity_overlay_snapshot

        coin = _normalize_coin(symbol)
        snap, err = build_indicator_snapshot(coin, interval=req.timeframe or None)
        if not snap:
            # 即使加密 K 线失败，仍附带美股快照供模型降级判断
            us_overlay = fetch_us_equity_overlay_snapshot()
            return {
                "symbol": coin,
                "last_close": None,
                "metrics": {},
                "recent_bars": [],
                "us_equity_overlay": us_overlay,
                "interval": req.timeframe or "4h",
            }, err or "无加密快照"

        metrics = dict(snap.get("metrics") or {})
        bars = snap.get("recent_bars") or []
        last = bars[-1].get("close") if bars else metrics.get("close")
        us_overlay = fetch_us_equity_overlay_snapshot()
        return {
            "symbol": snap.get("symbol") or coin,
            "last_close": last,
            "metrics": metrics,
            "recent_bars": bars,
            "interval": snap.get("interval") or req.timeframe or "4h",
            "us_equity_overlay": us_overlay,
        }, ""
    except Exception as exc:
        return {}, str(exc)


def analyze(req: AnalyzeRequest) -> AnalyzeReport:
    req.market = Market.CRYPTO
    req.agent_id = AgentId.CRYPTO_ANALYST
    return run_analyst_pipeline(
        req,
        agent_id=AgentId.CRYPTO_ANALYST,
        market=Market.CRYPTO,
        system_prompt=CRYPTO_ANALYST_SYSTEM,
        persona_hint="资深加密交易分析师（技术面为主，美股开盘参考美股）",
        snapshot_fn=_snapshot,
    )
