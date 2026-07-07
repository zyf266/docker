"""Massive（原 Polygon.io）美股 K 线 / 报价。"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# 官方仍可用 api.polygon.io；Massive 文档亦指向同一套 REST
MASSIVE_API_BASE = os.getenv("MASSIVE_API_BASE", "https://api.polygon.io")

_INTERVAL_MS: Dict[str, int] = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
    "1w": 604_800_000,
}


def get_massive_api_key() -> str:
    from backpack_quant_trading.core.env_loader import load_project_env

    load_project_env()
    return (
        os.getenv("MASSIVE_API_KEY")
        or os.getenv("POLYGON_API_KEY")
        or ""
    ).strip()


def normalize_us_ticker(symbol: str) -> str:
    """NVDA / NVDAUSDT / AAPL -> NVDA"""
    s = (symbol or "").upper().strip()
    for suffix in ("USDT", "USD", ".US", ".O", ".P"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    if ":" in s:
        s = s.split(":")[-1]
    return s.strip()


def normalize_massive_interval(interval: str) -> Tuple[int, str]:
    """
    返回 (multiplier, timespan) 供 Polygon aggs API 使用。
    timespan: minute | hour | day | week
    """
    iv = (interval or "1d").strip().upper()
    mapping = {
        "1": ("1", "minute"), "1M": ("1", "minute"), "1m": ("1", "minute"),
        "5": ("5", "minute"), "5M": ("5", "minute"), "5m": ("5", "minute"),
        "15": ("15", "minute"), "15M": ("15", "minute"), "15m": ("15", "minute"),
        "30": ("30", "minute"), "30M": ("30", "minute"), "30m": ("30", "minute"),
        "60": ("1", "hour"), "1H": ("1", "hour"), "1h": ("1", "hour"),
        "120": ("2", "hour"), "2H": ("2", "hour"), "2h": ("2", "hour"),
        "240": ("4", "hour"), "4H": ("4", "hour"), "4h": ("4", "hour"),
        "D": ("1", "day"), "1D": ("1", "day"), "1d": ("1", "day"),
        "W": ("1", "week"), "1W": ("1", "week"), "1w": ("1", "week"),
    }
    if iv in mapping:
        m, t = mapping[iv]
        return int(m), t
    iv_low = iv.lower()
    if iv_low in mapping:
        m, t = mapping[iv_low]
        return int(m), t
    if iv_low.endswith("h") and iv_low[:-1].isdigit():
        return int(iv_low[:-1]), "hour"
    if iv_low.endswith("m") and iv_low[:-1].isdigit():
        return int(iv_low[:-1]), "minute"
    return 1, "day"


def interval_label(interval: str) -> str:
    """统一展示用周期标签，如 1h / 4h / 1d"""
    mult, span = normalize_massive_interval(interval)
    if span == "minute":
        return f"{mult}m"
    if span == "hour":
        return f"{mult}h"
    if span == "week":
        return "1w"
    return "1d"


def _max_lookback_days(span: str) -> int:
    """Polygon 低档套餐小时/分钟线通常只有近 1～2 年，避免无意义远古请求。"""
    default = {"minute": 60, "hour": 400, "day": 730, "week": 1825}.get(span, 400)
    try:
        return max(30, int(os.getenv("MASSIVE_MAX_LOOKBACK_DAYS", str(default))))
    except (TypeError, ValueError):
        return default


def _lookback_days_for_us_bars(mult: int, span: str, limit: int) -> int:
    """美股非 24h 交易，分钟/小时周期需更长日历回看。"""
    lim = max(int(limit or 200), 30)
    if span == "week":
        raw = max(52, lim * 7 + 14)
    elif span == "day":
        raw = max(30, int(lim * 1.8) + 10)
    elif span == "hour":
        bars_per_trading_day = max(6.5 / max(mult, 1), 0.5)
        trading_days = lim / bars_per_trading_day
        raw = int(trading_days * (7 / 5) * 1.45) + 20
        raw = max(raw, 90)
    else:
        bars_per_trading_day = max(390 / max(mult, 1), 1.0)
        trading_days = lim / bars_per_trading_day
        raw = int(trading_days * (7 / 5) * 1.45) + 20
        raw = max(raw, 120)
    return min(raw, _max_lookback_days(span))


# Polygon aggs 单窗口 limit；分批拉取时按日期窗口切片，避免一次请求过大触发限流
_POLYGON_AGG_REQUEST_LIMIT = 50_000
_DEFAULT_BATCH_PAUSE_SEC = 0.35
_DEFAULT_RATE_LIMIT_RETRIES = 5


def _batch_pause_sec() -> float:
    try:
        return max(0.0, float(os.getenv("MASSIVE_BATCH_PAUSE_SEC", str(_DEFAULT_BATCH_PAUSE_SEC))))
    except (TypeError, ValueError):
        return _DEFAULT_BATCH_PAUSE_SEC


def _chunk_days_for_span(mult: int, span: str) -> int:
    """按周期估算每批日历天数，控制单次 aggs 返回量。"""
    if span == "week":
        return 365 * 2
    if span == "day":
        return 120
    if span == "hour":
        return 35 if mult >= 2 else 28
    return 10


def _massive_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    key = get_massive_api_key()
    if not key:
        raise ValueError("未配置 MASSIVE_API_KEY（或 POLYGON_API_KEY）")
    p = dict(params or {})
    p["apiKey"] = key
    url = f"{MASSIVE_API_BASE.rstrip('/')}{path}"
    for attempt in range(_DEFAULT_RATE_LIMIT_RETRIES):
        r = requests.get(url, params=p, timeout=30)
        if r.status_code == 429:
            wait = min(2.0 ** attempt, 16.0)
            logger.warning("Massive 限流 429，%ss 后重试 (%s/%s)", wait, attempt + 1, _DEFAULT_RATE_LIMIT_RETRIES)
            time.sleep(wait)
            continue
        if r.status_code == 403:
            try:
                detail = r.json()
            except Exception:
                detail = r.text[:300]
            raise RuntimeError(f"Massive API 403: {detail}")
        if r.status_code != 200:
            try:
                detail = r.json()
            except Exception:
                detail = r.text[:300]
            raise RuntimeError(f"Massive API {r.status_code}: {detail}")
        return r.json()
    raise RuntimeError("Massive API 429: 限流重试次数已用尽")


def _parse_agg_rows(data: Any, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """解析 aggs 结果。"""
    rows: List[Dict[str, Any]] = []
    for item in (data.get("results") or []):
        try:
            rows.append({
                "time": int(item["t"]),
                "open": float(item["o"]),
                "high": float(item["h"]),
                "low": float(item["l"]),
                "close": float(item["c"]),
                "volume": float(item.get("v") or 0),
            })
        except (KeyError, TypeError, ValueError):
            continue
    if limit is not None and len(rows) > limit:
        rows = rows[:limit]
    return rows


def _fetch_agg_range(
    ticker: str,
    mult: int,
    span: str,
    from_s: str,
    to_s: str,
    *,
    client_limit: int,
    sort: str = "desc",
) -> List[Dict[str, Any]]:
    """
    Polygon aggs 单窗口拉取。
    - sort=desc：取窗口内最近 N 根（兼容旧逻辑）
    - sort=asc：分批回填历史时使用
    """
    path = f"/v2/aggs/ticker/{ticker}/range/{mult}/{span}/{from_s}/{to_s}"
    data = _massive_get(
        path,
        {
            "adjusted": "true",
            "sort": sort,
            "limit": _POLYGON_AGG_REQUEST_LIMIT,
        },
    )
    rows = _parse_agg_rows(data)
    if sort == "desc" and len(rows) > client_limit:
        rows = rows[:client_limit]
    if sort == "desc":
        rows.reverse()
    return rows


def _fetch_massive_bars_batched(
    ticker: str,
    mult: int,
    span: str,
    start: datetime,
    end: datetime,
    *,
    total_limit: int,
) -> List[Dict[str, Any]]:
    """按日期窗口分批拉取，合并去重后返回升序列表。"""
    chunk_days = _chunk_days_for_span(mult, span)
    pause = _batch_pause_sec()
    merged: Dict[int, Dict[str, Any]] = {}
    cursor = start.date()
    end_date = end.date()
    batches = 0

    while cursor <= end_date:
        window_end = min(cursor + timedelta(days=chunk_days - 1), end_date)
        from_s = cursor.strftime("%Y-%m-%d")
        to_s = window_end.strftime("%Y-%m-%d")
        try:
            batch = _fetch_agg_range(
                ticker,
                mult,
                span,
                from_s,
                to_s,
                client_limit=total_limit,
                sort="asc",
            )
            for row in batch:
                merged[int(row["time"])] = row
            batches += 1
        except Exception as exc:
            msg = str(exc)
            if "403" in msg or "NOT_AUTHORIZED" in msg:
                logger.debug("Massive 无权限窗口 %s %s~%s，跳过", ticker, from_s, to_s)
            else:
                logger.warning("Massive 分批 K线失败 %s %s~%s: %s", ticker, from_s, to_s, exc)
        cursor = window_end + timedelta(days=1)
        if cursor <= end_date and pause > 0:
            time.sleep(pause)

    rows = [merged[k] for k in sorted(merged)]
    if len(rows) > total_limit:
        rows = rows[-total_limit:]
    logger.info(
        "Massive 分批 K线 %s %s%s: %s 批, 共 %s 根",
        ticker,
        mult,
        span,
        batches,
        len(rows),
    )
    return rows


def fetch_massive_bars(
    symbol: str,
    interval: str = "1d",
    limit: int = 200,
    start: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    拉取 OHLCV，返回与 HL/crypto 一致的升序列表：
    [{"time": ms, "open", "high", "low", "close", "volume"}, ...]
    start: 可选起始时间（策略同步时传首笔交易前 warmup，避免拉到套餐不支持的远古数据）
    """
    ticker = normalize_us_ticker(symbol)
    if not ticker:
        return []
    mult, span = normalize_massive_interval(interval)
    end = datetime.now(timezone.utc)
    lim = int(limit)
    if start is not None:
        start_dt = start.astimezone(timezone.utc) if start.tzinfo else start.replace(tzinfo=timezone.utc)
    else:
        lookback_days = _lookback_days_for_us_bars(mult, span, lim)
        start_dt = end - timedelta(days=lookback_days)
    # 不早于套餐允许的最大回看
    floor = end - timedelta(days=_max_lookback_days(span))
    if start_dt < floor:
        start_dt = floor
    from_s = start_dt.strftime("%Y-%m-%d")
    to_s = end.strftime("%Y-%m-%d")
    rows: List[Dict[str, Any]] = []

    if span in ("minute", "hour"):
        try:
            return _fetch_massive_bars_batched(
                ticker, mult, span, start_dt, end, total_limit=lim,
            )
        except Exception as e:
            logger.warning("Massive 分批 K线失败 %s %s: %s", ticker, interval, e)
            rows = []

    if not rows:
        try:
            rows = _fetch_agg_range(
                ticker, mult, span, from_s, to_s, client_limit=lim,
            )
        except Exception as e:
            logger.warning("Massive K线失败 %s %s: %s", ticker, interval, e)
            rows = []

    return rows


def fetch_massive_last_price(symbol: str) -> Optional[float]:
    """优先 prev 收盘；失败则取最近一根 K 线收盘价。"""
    ticker = normalize_us_ticker(symbol)
    if not ticker:
        return None
    try:
        data = _massive_get(f"/v2/aggs/ticker/{ticker}/prev", {})
        results = data.get("results") or []
        if results:
            return float(results[0]["c"])
    except Exception as e:
        logger.debug("Massive prev %s: %s", ticker, e)
    bars = fetch_massive_bars(ticker, "1d", limit=2)
    if bars:
        return float(bars[-1]["close"])
    return None


def fetch_klines_us(symbol: str, interval: str, total_limit: int = 200) -> Optional[List[Dict[str, Any]]]:
    """与 fetch_klines_crypto 同签名，供评分模块切换数据源。"""
    bars = fetch_massive_bars(symbol, interval, limit=total_limit)
    return bars if len(bars) >= 30 else None


def fetch_massive_news(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Polygon/Massive 个股新闻（需 MASSIVE_API_KEY）。"""
    ticker = normalize_us_ticker(symbol)
    if not ticker or not get_massive_api_key():
        return []
    try:
        data = _massive_get(
            "/v2/reference/news",
            {"ticker": ticker, "limit": min(int(limit or 10), 50), "order": "desc"},
        )
    except Exception as e:
        logger.debug("Massive news %s: %s", ticker, e)
        return []

    out: List[Dict[str, Any]] = []
    for item in (data.get("results") or []):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        pub = str(item.get("published_utc") or item.get("published") or "")
        try:
            if pub.endswith("Z"):
                pub = datetime.fromisoformat(pub.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            pass
        publisher = ""
        pubs = item.get("publisher")
        if isinstance(pubs, dict):
            publisher = str(pubs.get("name") or "")
        desc = str(item.get("description") or "")[:280]
        out.append({
            "time": pub,
            "source": publisher or "Massive",
            "title": title,
            "text": f"{title} — {desc}".strip(" —"),
            "url": str(item.get("article_url") or item.get("url") or ""),
            "feed_key": "massive",
        })
    return out


def is_us_stock_ticker(symbol: str) -> bool:
    """委托 signal_asset_router 统一判定（兼容旧调用）。"""
    from backpack_quant_trading.core.signal_asset_router import is_us_stock_signal

    return is_us_stock_signal(symbol)
