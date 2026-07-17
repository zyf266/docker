"""定时/信号旁路：可选用 Agent 格式推送（默认关闭，不替换旧评分推送）。"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def agent_replace_legacy_push() -> bool:
    return os.getenv("AGENT_REPLACE_LEGACY_PUSH", "0").strip().lower() in ("1", "true", "yes")


def agent_signal_push_enabled() -> bool:
    """是否在信号旁路额外推送 Agent 报告（可与旧推送并存）。"""
    return os.getenv("AGENT_SIGNAL_PUSH_ENABLED", "0").strip().lower() in ("1", "true", "yes")


def run_agent_signal_hook(
    symbol: str,
    *,
    market: str = "",
    dry_run: bool = True,
    user_text: str = "",
) -> Dict[str, Any]:
    """
    对单个标的跑分析师+风控，返回 markdown。
    dry_run=True 时只打日志不推钉钉。
    """
    from backpack_quant_trading.agents.coordinator import handle
    from backpack_quant_trading.agents.types import Market

    m = (market or "").strip().lower()
    prefix = {
        "us_stock": "@美股分析师 ",
        "a_share": "@A股分析师 ",
        "crypto": "@加密分析师 ",
    }.get(m, "")
    text = user_text or f"{prefix}{symbol}".strip()
    result = handle(text, propose_execution=False)
    md = str(result.get("markdown") or "")
    logger.info(
        "[AgentHook] symbol=%s market=%s ok=%s dry_run=%s md_len=%s",
        symbol,
        market,
        result.get("ok"),
        dry_run,
        len(md),
    )
    if dry_run or not md:
        return {**result, "pushed": False, "dry_run": dry_run}

    if agent_replace_legacy_push() or agent_signal_push_enabled():
        try:
            from backpack_quant_trading.core.stock_news_alert import send_dingtalk_markdown

            send_dingtalk_markdown(title=f"Agent · {symbol}", text=md)
            return {**result, "pushed": True, "dry_run": False}
        except Exception as exc:
            logger.warning("Agent hook 钉钉推送失败: %s", exc)
            return {**result, "pushed": False, "push_error": str(exc)}
    return {**result, "pushed": False, "dry_run": dry_run}
