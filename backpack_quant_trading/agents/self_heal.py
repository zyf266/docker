"""轻量自愈：监视空跑恢复 + 主机告警。"""
from __future__ import annotations

import logging
import os
import socket
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def check_and_heal_monitors() -> Dict[str, Any]:
    """监视空跑但 DB 有配置 → restore；返回已自愈 / 需人工条目。"""
    healed: List[str] = []
    needs_human: List[str] = []
    notes: List[str] = []

    try:
        from backpack_quant_trading.core.binance_monitor import (
            get_currency_monitor_user_stopped,
            restore_currency_monitor_from_db_if_needed,
            get_monitor_instance,
        )

        if get_currency_monitor_user_stopped():
            notes.append("币种监视：用户曾主动停止，跳过自愈")
        else:
            before = None
            try:
                svc = get_monitor_instance()
                before = bool(svc) and bool(getattr(svc, "pairs", None) or getattr(svc, "_thread", None))
            except Exception:
                before = False
            restored = restore_currency_monitor_from_db_if_needed()
            after = False
            try:
                svc2 = get_monitor_instance()
                after = bool(svc2)
            except Exception:
                after = bool(restored)
            if restored and (not before) and after:
                healed.append("币种监视：已从 DB 恢复运行")
            elif restored:
                notes.append("币种监视：restore 已调用")
            elif not after:
                # DB 可能无配置
                notes.append("币种监视：当前未运行（可能无 DB 配置）")
    except Exception as exc:
        needs_human.append(f"币种监视自愈异常：{exc}")
        logger.warning("heal currency monitor: %s", exc)

    try:
        from backpack_quant_trading.core.stock_news_alert import (
            try_restore_from_disk,
            get_stock_news_alert_user_stopped,
        )

        if get_stock_news_alert_user_stopped():
            notes.append("新闻监控：用户曾主动停止，跳过自愈")
        else:
            try_restore_from_disk()
            notes.append("新闻监控：已尝试磁盘恢复")
    except Exception as exc:
        needs_human.append(f"新闻监控恢复异常：{exc}")

    expected = (os.getenv("AGENT_EXPECTED_HOST") or "").strip()
    if expected:
        host = socket.gethostname()
        if host != expected and expected not in host:
            needs_human.append(
                f"主机名 `{host}` 与 AGENT_EXPECTED_HOST=`{expected}` 不一致（可能多机抢 Stream）"
            )

    return {
        "ok": True,
        "healed": healed,
        "needs_human": needs_human,
        "notes": notes,
    }
