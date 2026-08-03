"""定时/信号旁路：Webhook 实盘信号走 Agent 评分卡（统一钉钉群，不再回退旧链路）。"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def agent_orch_enabled() -> bool:
    return os.getenv("AGENT_ORCH_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")


def agent_replace_legacy_push() -> bool:
    """为 1 时：Webhook 信号只推 Agent 报告到信号评分钉钉群，不走旧 DeepSeek 海报链路。"""
    raw = os.getenv("AGENT_REPLACE_LEGACY_PUSH", "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return agent_orch_enabled()


def agent_signal_push_enabled() -> bool:
    """是否在旧评分之外额外推送 Agent 报告（二者并存；默认关闭）。"""
    return os.getenv("AGENT_SIGNAL_PUSH_ENABLED", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _action_cn(action: str) -> str:
    a = (action or "").lower().strip()
    if a in ("buy", "long") or "买" in a or "多" in a:
        return "做多开仓"
    if a in ("sell", "short") or "卖" in a or "空" in a:
        return "做空开仓"
    return action or "分析"


def _normalize_hook_symbol(symbol: str, market: str = "") -> str:
    """TradingView 常见写法：ETHUSDT.P / BTCUSDT → 分析师用的 ticker。"""
    raw = str(symbol or "").strip().upper()
    if not raw:
        return ""
    m = (market or "").strip().lower()
    s = raw.replace("-", "").replace("/", "")
    if s.endswith(".P"):
        s = s[:-2]
    if "USDT" in s:
        s = s.split("USDT", 1)[0] or s
    if m in ("crypto",) or raw.endswith("USDT") or raw.endswith("USDT.P"):
        return s or raw
    # 美股：去掉交易所前缀 NASDAQ:NVDA
    if ":" in s:
        s = s.split(":")[-1]
    return s or raw


def build_agent_signal_text(
    symbol: str,
    *,
    market: str = "",
    timeframe: str = "",
    action: str = "",
) -> str:
    m = (market or "").strip().lower()
    prefix = {
        "us_stock": "@美股分析师 ",
        "us": "@美股分析师 ",
        "a_share": "@A股分析师 ",
        "crypto": "@加密分析师 ",
    }.get(m, "@美股分析师 " if not m else "")
    # 带「分析」关键词，避免非别名 ticker 被 extract_symbols 丢掉
    sym = _normalize_hook_symbol(symbol, market)
    parts = [prefix.strip(), "分析一下", sym]
    tf = (timeframe or "").strip()
    if tf:
        # 纯数字周期补单位，便于解析且不影响标的提取
        if tf.isdigit():
            n = int(tf)
            tf = f"{n}h" if n >= 60 else f"{n}m"
        parts.append(tf)
    if action:
        parts.append(_action_cn(action))
    return " ".join(p for p in parts if p)


def _push_agent_markdown_to_score_group(title: str, markdown: str) -> tuple[bool, str]:
    """推送到信号评分钉钉群（crypto_signal_scorer_config.dingtalk_webhook）。"""
    from backpack_quant_trading.core.crypto_signal_scorer import (
        resolve_signal_score_dingtalk_webhook,
    )
    from backpack_quant_trading.core.stock_news_alert import send_dingtalk_markdown

    url = resolve_signal_score_dingtalk_webhook()
    if not url:
        return False, "未配置信号评分钉钉 Webhook"
    body = (markdown or "")[:3500]
    return send_dingtalk_markdown(url, title or "信号评分", body)


def run_agent_signal_hook(
    symbol: str,
    *,
    market: str = "",
    timeframe: str = "",
    action: str = "",
    dry_run: bool = True,
    user_text: str = "",
) -> Dict[str, Any]:
    """
    对单个标的跑分析师+风控，返回 markdown。
    dry_run=True 时只打日志不推钉钉。
    """
    from backpack_quant_trading.agents.coordinator import handle

    sym = _normalize_hook_symbol(symbol, market)
    text = (user_text or "").strip() or build_agent_signal_text(
        sym or symbol, market=market, timeframe=timeframe, action=action
    )
    result = handle(text, propose_execution=False)
    md = str(result.get("markdown") or "")
    # 解析失败时强制带标的重试一次，避免往评分群刷「未能识别标的」
    if (not result.get("ok")) and sym and ("未能识别" in md or not (result.get("reports") or [])):
        retry = build_agent_signal_text(
            sym, market=market or "us_stock", timeframe=timeframe or "2h", action=action or "buy"
        )
        if retry != text:
            logger.warning("[AgentHook] 标的解析失败，重试 text=%s → %s", text[:80], retry[:80])
            result = handle(retry, propose_execution=False)
            md = str(result.get("markdown") or "")
            text = retry
    logger.info(
        "[AgentHook] symbol=%s→%s market=%s tf=%s action=%s ok=%s dry_run=%s md_len=%s text=%s",
        symbol,
        sym,
        market,
        timeframe,
        action,
        result.get("ok"),
        dry_run,
        len(md),
        text[:100],
    )
    # 仍失败则不推「未能识别」，避免钉钉刷屏
    if not result.get("ok") and "未能识别" in md:
        logger.warning("[AgentHook] 跳过推送未能识别 symbol=%s text=%s", symbol, text[:120])
        return {**result, "pushed": False, "dry_run": dry_run, "skipped_unrecognized": True}
    if dry_run or not md:
        return {**result, "pushed": False, "dry_run": dry_run}

    mkt = (market or "").strip().lower()
    if "crypto" in mkt:
        title = f"加密分析师 · {symbol}"
    elif "a_share" in mkt:
        title = f"A股分析师 · {symbol}"
    elif "us" in mkt:
        title = f"美股分析师 · {symbol}"
    else:
        title = f"Agent · {symbol}"

    try:
        ok, err = _push_agent_markdown_to_score_group(title, md)
        if not ok:
            logger.warning("[AgentHook] 信号评分群推送失败: %s", err)
        try:
            from backpack_quant_trading.core.score_feedback import (
                parse_score_card_from_reply,
                remember_last_signal_context,
            )

            reports = result.get("reports") or []
            if reports:
                r0 = reports[0]
                raw0 = getattr(r0, "raw", None) or {}
                tf = timeframe
                if isinstance(raw0, dict):
                    tf = str(raw0.get("timeframe") or tf or "")
                score = getattr(r0, "score", None)
                remember_last_signal_context(
                    symbol=str(getattr(r0, "symbol", None) or symbol),
                    timeframe=tf,
                    score=int(score) if score is not None else None,
                    recommendation=str(
                        ((raw0.get("structured") or {}) if isinstance(raw0, dict) else {}).get(
                            "recommendation"
                        )
                        or ""
                    ),
                    source="webhook_agent",
                )
            else:
                sym, tf, sc = parse_score_card_from_reply(md)
                if sym or symbol:
                    remember_last_signal_context(
                        symbol=sym or symbol,
                        timeframe=tf or timeframe,
                        score=sc,
                        source="webhook_agent_md",
                    )
        except Exception:
            pass
        return {**result, "pushed": ok, "dry_run": False, "push_error": err if not ok else None}
    except Exception as exc:
        logger.warning("Agent hook 钉钉推送失败: %s", exc)
        return {**result, "pushed": False, "push_error": str(exc)}


def schedule_agent_signal_push(
    symbol: str,
    action: str = "buy",
    *,
    timeframe: str = "",
    market: str = "us_stock",
    webhook_raw: Optional[Dict[str, Any]] = None,
) -> None:
    """后台线程跑 Agent 并推送到信号评分钉钉群。"""

    def _job() -> None:
        try:
            run_agent_signal_hook(
                symbol,
                market=market,
                timeframe=timeframe,
                action=action,
                dry_run=False,
            )
        except Exception as exc:
            logger.exception(
                "Webhook Agent 推送失败 %s %s: %s", symbol, action, exc
            )

    threading.Thread(
        target=_job,
        daemon=True,
        name=f"agent-signal-{symbol}",
    ).start()
    logger.info(
        "[AgentHook] 已调度 Agent 推送 symbol=%s tf=%s action=%s market=%s",
        symbol,
        timeframe,
        action,
        market,
    )
