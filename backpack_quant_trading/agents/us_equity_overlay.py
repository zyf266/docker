"""美股常规交易时段检测 + 供加密分析引用的美股快照。"""
from __future__ import annotations

import logging
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_NY = ZoneInfo("America/New_York")
_CN = ZoneInfo("Asia/Shanghai")

# 常规交易：美东 09:30–16:00（已含夏令时由 zoneinfo 处理）
_OPEN = time(9, 30)
_CLOSE = time(16, 0)
# 开盘前后缓冲：开盘前 30 分钟～收盘后 15 分钟也视为「联动敏感窗」
_PRE = time(9, 0)
_POST = time(16, 15)


def is_us_regular_session(now: Optional[datetime] = None) -> bool:
    dt = now or datetime.now(_NY)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_NY)
    else:
        dt = dt.astimezone(_NY)
    if dt.weekday() >= 5:
        return False
    t = dt.time()
    return _OPEN <= t <= _CLOSE


def is_us_session_overlay_window(now: Optional[datetime] = None) -> bool:
    """开盘前后缓冲窗：加密应参考美股。"""
    dt = now or datetime.now(_NY)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_NY)
    else:
        dt = dt.astimezone(_NY)
    if dt.weekday() >= 5:
        return False
    t = dt.time()
    return _PRE <= t <= _POST


def _bar_change_pct(klines: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if not klines or len(klines) < 2:
        if klines:
            c = float(klines[-1].get("close") or 0)
            return c, None, None
        return None, None, None
    last = float(klines[-1].get("close") or 0)
    prev = float(klines[-2].get("close") or 0)
    day_open = float(klines[0].get("open") or klines[0].get("close") or 0)
    chg = ((last - prev) / prev * 100.0) if prev else None
    day_chg = ((last - day_open) / day_open * 100.0) if day_open else None
    return last, chg, day_chg


def fetch_us_equity_overlay_snapshot(
    *,
    tickers: Optional[List[str]] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """
    拉取 QQQ/SPY/NVDA 等日线末两根，用于加密分析美股联动。
    force=False 时：非美股敏感窗只返回 session 元数据，不拉行情。
    """
    now_ny = datetime.now(_NY)
    now_cn = datetime.now(_CN)
    in_session = is_us_regular_session(now_ny)
    in_window = is_us_session_overlay_window(now_ny)
    meta = {
        "in_us_regular_session": in_session,
        "in_overlay_window": in_window,
        "now_ny": now_ny.strftime("%Y-%m-%d %H:%M %Z"),
        "now_cn": now_cn.strftime("%Y-%m-%d %H:%M %Z"),
        "symbols": {},
        "summary_text": "",
        "available": False,
    }
    if not force and not in_window:
        meta["summary_text"] = "当前非美股开盘敏感窗，美股联动参考降权。"
        return meta

    syms = tickers or ["QQQ", "SPY", "NVDA"]
    rows: Dict[str, Any] = {}
    try:
        from backpack_quant_trading.core.massive_klines import fetch_klines_us
    except Exception as exc:
        meta["summary_text"] = f"美股快照模块不可用: {exc}"
        return meta

    for sym in syms:
        try:
            kl = fetch_klines_us(sym, "1d", total_limit=5) or []
            last, chg, day_chg = _bar_change_pct(kl)
            rows[sym] = {
                "last": last,
                "chg_pct_bar": chg,
                "day_chg_pct_approx": day_chg,
                "bars": len(kl),
            }
        except Exception as exc:
            logger.debug("us overlay fetch %s failed: %s", sym, exc)
            rows[sym] = {"error": str(exc)}

    meta["symbols"] = rows
    meta["available"] = any(isinstance(v, dict) and v.get("last") for v in rows.values())

    bits = []
    for sym, info in rows.items():
        if not isinstance(info, dict) or info.get("last") is None:
            continue
        chg = info.get("chg_pct_bar")
        chg_s = f"{chg:+.2f}%" if isinstance(chg, (int, float)) else "n/a"
        bits.append(f"{sym} {info['last']:.2f} ({chg_s})")
    session_s = "美股常规交易中" if in_session else "美股开盘敏感窗（非严格盘中）"
    if bits:
        meta["summary_text"] = f"{session_s}｜" + "；".join(bits)
    else:
        meta["summary_text"] = f"{session_s}｜美股行情拉取失败，请标注 us_equity_overlay=n_a 或 insufficient"

    # 粗略风险偏好：以 QQQ 日变动为主
    q = rows.get("QQQ") or {}
    chg = q.get("chg_pct_bar")
    if isinstance(chg, (int, float)):
        if chg <= -1.0:
            meta["risk_bias_hint"] = "bearish"
        elif chg >= 1.0:
            meta["risk_bias_hint"] = "bullish"
        else:
            meta["risk_bias_hint"] = "neutral"
    else:
        meta["risk_bias_hint"] = "n_a"
    return meta
