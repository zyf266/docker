"""Agent 侧钉钉 Markdown 推送（解析 webhook 后再发）。"""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def resolve_ops_dingtalk_webhook() -> str:
    """
    自动复盘 / 日巡检专用群。
    优先 AGENT_OPS_DINGTALK_WEBHOOK；未配则回退新闻监控 webhook。
    """
    wh = (os.getenv("AGENT_OPS_DINGTALK_WEBHOOK") or "").strip()
    if wh:
        return wh
    try:
        from backpack_quant_trading.core.stock_news_alert import (
            load_config,
            resolve_dingtalk_webhook,
        )

        return resolve_dingtalk_webhook(load_config()) or ""
    except Exception:
        return ""


def push_dingtalk_markdown(
    title: str,
    text: str,
    *,
    webhook_url: Optional[str] = None,
    use_ops_webhook: bool = False,
) -> Tuple[bool, str]:
    """推送 Markdown。use_ops_webhook=True 时走复盘/巡检专用群。"""
    try:
        from backpack_quant_trading.core.stock_news_alert import (
            load_config,
            resolve_dingtalk_webhook,
            send_dingtalk_markdown,
        )

        wh = (webhook_url or "").strip()
        if not wh and use_ops_webhook:
            wh = resolve_ops_dingtalk_webhook()
        if not wh:
            wh = resolve_dingtalk_webhook(load_config())
        if not wh:
            return False, "未配置钉钉 webhook"
        body = (text or "")[:3500]
        return send_dingtalk_markdown(wh, title or "通知", body)
    except Exception as exc:
        logger.warning("push_dingtalk_markdown failed: %s", exc)
        return False, str(exc)
