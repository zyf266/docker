"""实盘策略报错 → 钉钉（运维群 AGENT_OPS_DINGTALK_WEBHOOK）。

覆盖：
1. API 启动/初始化失败显式调用 notify_live_trade_error
2. 策略 logger ERROR+ 自动旁路推送（去重限流）
"""
from __future__ import annotations

import logging
import os
import threading
import time
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_STRATEGY_LOGGERS = (
    "adaptive_long",
    "adaptive_short",
    "auto_close",
    "eth_trend_short",
    "backpack_quant_trading.strategy.hype_adaptive_short",
    "backpack_quant_trading.api.routers.trading",
)

# fingerprint -> last_sent_ts
_recent: Dict[str, float] = {}
_lock = threading.Lock()
_handler_installed = False

_COOLDOWN_SEC = float(os.environ.get("LIVE_TRADE_ALERT_COOLDOWN_SEC") or "90")
_MAX_BODY = 2800


def resolve_live_trade_webhook() -> str:
    """实盘报错推送目标。

    优先级：
    1. LIVE_TRADE_DINGTALK_WEBHOOK（专用）
    2. 信号评分群 crypto_signal_scorer_config.json
    3. 新闻群 stock_news_alert_config（关键词「提醒」可用）
    4. AGENT_OPS（可能关键词不同，作最后备选）
    """
    wh = (os.getenv("LIVE_TRADE_DINGTALK_WEBHOOK") or "").strip()
    if wh:
        return wh

    # 信号评分群
    try:
        from pathlib import Path
        import json

        p = Path(__file__).resolve().parents[1] / "data" / "crypto_signal_scorer_config.json"
        if p.is_file():
            cfg = json.loads(p.read_text(encoding="utf-8"))
            wh = str(cfg.get("dingtalk_webhook") or "").strip()
            if wh:
                return wh
    except Exception:
        pass
    try:
        from backpack_quant_trading.core.crypto_signal_scorer import load_config as _score_cfg

        wh = str((_score_cfg() or {}).get("dingtalk_webhook") or "").strip()
        if wh:
            return wh
    except Exception:
        pass

    # 新闻群（确认支持「提醒」关键词）
    try:
        from backpack_quant_trading.core.stock_news_alert import (
            load_config,
            resolve_dingtalk_webhook,
        )

        wh = (resolve_dingtalk_webhook(load_config()) or "").strip()
        if wh:
            return wh
    except Exception:
        pass

    wh = (os.getenv("AGENT_OPS_DINGTALK_WEBHOOK") or "").strip()
    if wh:
        return wh
    return ""


def _fingerprint(title: str, detail: str) -> str:
    raw = f"{title}|{(detail or '')[:240]}"
    return raw


def _should_send(fp: str) -> bool:
    now = time.time()
    with _lock:
        last = _recent.get(fp) or 0.0
        if now - last < _COOLDOWN_SEC:
            return False
        _recent[fp] = now
        # 清理过期
        if len(_recent) > 200:
            cutoff = now - max(_COOLDOWN_SEC * 3, 300)
            for k in list(_recent.keys()):
                if _recent[k] < cutoff:
                    del _recent[k]
        return True


def _sanitize(text: str) -> str:
    s = str(text or "")
    # 避免把密钥刷到钉钉
    for bad in ("api_secret", "private_key", "secret_key", "SECRET", "PRIVATE_KEY"):
        if bad.lower() in s.lower() and len(s) > 80:
            s = s[:200] + "\n...(含敏感字段，已截断)"
            break
    if len(s) > _MAX_BODY:
        s = s[: _MAX_BODY - 20] + "\n...(截断)"
    return s


def notify_live_trade_error(
    title: str,
    detail: str = "",
    *,
    instance_id: str = "",
    exchange: str = "",
    symbol: str = "",
    strategy: str = "",
    exc: Optional[BaseException] = None,
) -> Tuple[bool, str]:
    """推送一条实盘策略报错（异步线程，不阻塞交易主路径）。"""
    wh = resolve_live_trade_webhook()
    if not wh:
        return False, "未配置 LIVE_TRADE/AGENT_OPS 钉钉 webhook"

    lines = [
        f"### 【提醒】实盘策略报错",
        f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 标题: **{(title or '错误')[:120]}**",
    ]
    if instance_id:
        lines.append(f"- 实例: `{instance_id}`")
    if strategy:
        lines.append(f"- 策略: {strategy}")
    if exchange:
        lines.append(f"- 交易所: {exchange}")
    if symbol:
        lines.append(f"- 标的: {symbol}")
    body_detail = detail or ""
    if exc is not None:
        body_detail = (body_detail + "\n" if body_detail else "") + f"{type(exc).__name__}: {exc}"
        try:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            if tb and len(tb) < 1200:
                body_detail += f"\n```\n{tb[-1000:]}\n```"
        except Exception:
            pass
    if body_detail:
        lines.append("")
        lines.append(_sanitize(body_detail))

    text = "\n".join(lines)
    fp = _fingerprint(title, body_detail)
    if not _should_send(fp):
        return False, "cooldown"

    def _job() -> None:
        try:
            from backpack_quant_trading.core.stock_news_alert import send_dingtalk_markdown

            ok, msg = send_dingtalk_markdown(wh, f"提醒·实盘报错·{(title or '')[:40]}", text)
            if not ok:
                logger.warning("live_trade dingtalk push failed: %s", msg)
        except Exception as e:
            logger.warning("live_trade dingtalk push exc: %s", e)

    threading.Thread(target=_job, name="live-trade-dingtalk", daemon=True).start()
    return True, "queued"


class _LiveTradeErrorHandler(logging.Handler):
    """策略 ERROR+ 日志旁路推钉钉。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if record.levelno < logging.ERROR:
                return
            # 避免推送链路自身报错再递归
            if record.name.startswith("backpack_quant_trading.core.live_trade_dingtalk"):
                return
            if record.name.startswith("backpack_quant_trading.core.stock_news_alert"):
                return
            msg = record.getMessage()
            if "live_trade dingtalk" in msg:
                return
            detail = msg
            if record.exc_info:
                try:
                    detail += "\n" + "".join(traceback.format_exception(*record.exc_info))[-800:]
                except Exception:
                    pass
            notify_live_trade_error(
                f"[{record.name}] {msg[:80]}",
                detail=detail,
                strategy=record.name,
            )
        except Exception:
            self.handleError(record)


def install_live_trade_error_handlers() -> bool:
    """给实盘策略相关 logger 挂 ERROR 旁路（幂等）。"""
    global _handler_installed
    with _lock:
        if _handler_installed:
            return True
        handler = _LiveTradeErrorHandler(level=logging.ERROR)
        handler.setFormatter(logging.Formatter("%(message)s"))
        for name in _STRATEGY_LOGGERS:
            lg = logging.getLogger(name)
            # 避免重复挂载
            if any(isinstance(h, _LiveTradeErrorHandler) for h in lg.handlers):
                continue
            lg.addHandler(handler)
            if lg.level == logging.NOTSET or lg.level > logging.ERROR:
                # 不强制抬高级别；若父级已收 ERROR 即可
                pass
        _handler_installed = True
    logger.info(
        "live_trade dingtalk handlers installed loggers=%s webhook=%s",
        _STRATEGY_LOGGERS,
        "yes" if resolve_live_trade_webhook() else "no",
    )
    return True
