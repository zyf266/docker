"""StockAPI.com.cn 客户端（Token 鉴权）。

标的池：/v1/base/all（缓存 24h）
日线：/v1/base/day
分钟线：优先 /v1/base/kline、/v1/base/minkLine；套餐无权限时由调用方东财兜底。
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

STOCKAPI_BASE = "https://www.stockapi.com.cn"
_CACHE_TTL_SEC = 24 * 3600
_cache_lock = threading.Lock()
_pool_cache: Dict[str, Any] = {"ts": 0.0, "items": []}


def get_stockapi_token() -> str:
    return (os.getenv("STOCKAPI_TOKEN") or "").strip()


def _headers() -> Dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.stockapi.com.cn/",
        "Accept": "application/json,text/plain,*/*",
    }


class StockApiError(Exception):
    def __init__(self, message: str, code: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message


def stockapi_get(path: str, params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Any:
    token = get_stockapi_token()
    if not token:
        raise StockApiError("未配置 STOCKAPI_TOKEN")
    q = dict(params or {})
    q["token"] = token
    url = f"{STOCKAPI_BASE}{path}"
    try:
        # 国内源直连，避免本机坏代理导致连接失败
        sess = requests.Session()
        sess.trust_env = False
        r = sess.get(url, params=q, headers=_headers(), timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise StockApiError(f"StockAPI 网络错误: {type(e).__name__}") from e
    code = data.get("code") if isinstance(data, dict) else None
    if code not in (20000, 200, "20000", "200", None):
        raise StockApiError(str(data.get("msg") or data), code=code)
    return data.get("data") if isinstance(data, dict) and "data" in data else data


def fetch_a_share_pool(force: bool = False) -> List[Dict[str, str]]:
    """全 A 列表；本地内存 + 磁盘缓存 24h。"""
    from backpack_quant_trading.config.settings import config

    cache_path = Path(config.data_dir) / "a_share_pool_cache.json"
    now = time.time()
    with _cache_lock:
        if not force and _pool_cache["items"] and now - float(_pool_cache["ts"]) < _CACHE_TTL_SEC:
            return list(_pool_cache["items"])
        if not force and cache_path.exists():
            try:
                obj = json.loads(cache_path.read_text(encoding="utf-8"))
                ts = float(obj.get("ts") or 0)
                items = obj.get("items") or []
                if items and now - ts < _CACHE_TTL_SEC:
                    _pool_cache["ts"] = ts
                    _pool_cache["items"] = items
                    return list(items)
            except Exception:
                pass

    raw = stockapi_get("/v1/base/all", timeout=90)
    if not isinstance(raw, list):
        raise StockApiError("A股列表返回格式异常")
    items: List[Dict[str, str]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        code = str(row.get("api_code") or row.get("code") or "").strip()
        if not code:
            continue
        name = str(row.get("name") or "").strip()
        jys = str(row.get("jys") or "").strip().upper()
        items.append({
            "code": code,
            "name": name,
            "market": jys,
            "label": f"{code} {name}".strip(),
        })
    items.sort(key=lambda x: x["code"])
    with _cache_lock:
        _pool_cache["ts"] = now
        _pool_cache["items"] = items
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps({"ts": now, "items": items}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning("写入 A股池缓存失败: %s", e)
    return list(items)


def fetch_day_klines(code: str, days: int = 180) -> List[Dict[str, Any]]:
    end = datetime.now().date()
    start = end - timedelta(days=max(days, 60))
    raw = stockapi_get(
        "/v1/base/day",
        {
            "code": code,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "calculationCycle": "100",
        },
    )
    bars: List[Dict[str, Any]] = []
    if not isinstance(raw, list):
        return bars
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            t = str(row.get("time") or row.get("date") or "")[:10]
            dt = datetime.strptime(t, "%Y-%m-%d")
            close = float(row["close"])
            open_ = float(row.get("open") or close)
            high = float(row.get("high") or close)
            low = float(row.get("low") or close)
            bars.append({
                "open_time": int(dt.timestamp() * 1000),
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": float(row.get("volume") or 0),
                "close_time": int(dt.timestamp() * 1000),
                "time_label": t,
            })
        except Exception:
            continue
    bars.sort(key=lambda b: b["open_time"])
    return bars


def try_fetch_stockapi_minute_klines(code: str, interval: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """尝试 stockapi 分钟 K；失败返回 ([], err)。interval: 1/5/15/30/60/120。"""
    iv = str(interval)
    try:
        if iv == "1":
            raw = stockapi_get("/v1/base/minkLine", {"code": code, "all": 1}, timeout=40)
            return _normalize_stockapi_minute_payload(raw, 1), None
        if iv in ("5", "15", "30", "60", "120"):
            raw = stockapi_get("/v1/base/kline", {"code": code, "type": iv}, timeout=40)
            return _normalize_stockapi_minute_payload(raw, int(iv)), None
        return [], f"不支持的 stockapi interval={iv}"
    except StockApiError as e:
        return [], f"{e.message} (code={e.code})"


def _normalize_stockapi_minute_payload(raw: Any, minutes: int) -> List[Dict[str, Any]]:
    """兼容 data 为列数组对象或行数组。"""
    bars: List[Dict[str, Any]] = []
    if isinstance(raw, dict) and ("close" in raw or "date" in raw or "time" in raw):
        closes = raw.get("close") or []
        opens = raw.get("open") or closes
        highs = raw.get("high") or closes
        lows = raw.get("low") or closes
        vols = raw.get("volume") or raw.get("vol") or [0] * len(closes)
        times = raw.get("date") or raw.get("time") or []
        n = min(len(closes), len(times)) if times else len(closes)
        for i in range(n):
            try:
                label = str(times[i]) if i < len(times) else ""
                ts = _parse_bar_ts(label)
                c = float(closes[i])
                bars.append({
                    "open_time": ts,
                    "open": float(opens[i]) if i < len(opens) else c,
                    "high": float(highs[i]) if i < len(highs) else c,
                    "low": float(lows[i]) if i < len(lows) else c,
                    "close": c,
                    "volume": float(vols[i]) if i < len(vols) else 0,
                    "close_time": ts + minutes * 60 * 1000 - 1,
                    "time_label": label,
                })
            except Exception:
                continue
    elif isinstance(raw, list):
        for row in raw:
            if not isinstance(row, dict):
                continue
            try:
                label = str(row.get("time") or row.get("date") or "")
                ts = _parse_bar_ts(label)
                c = float(row["close"])
                bars.append({
                    "open_time": ts,
                    "open": float(row.get("open") or c),
                    "high": float(row.get("high") or c),
                    "low": float(row.get("low") or c),
                    "close": c,
                    "volume": float(row.get("volume") or row.get("vol") or 0),
                    "close_time": ts + minutes * 60 * 1000 - 1,
                    "time_label": label,
                })
            except Exception:
                continue
    bars.sort(key=lambda b: b["open_time"])
    return bars


def _parse_bar_ts(label: str) -> int:
    """按北京时间解析 K 线时间戳（毫秒）。"""
    from datetime import timezone, timedelta

    bj = timezone(timedelta(hours=8))
    s = (label or "").strip()
    for fmt, n in (
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d %H:%M", 16),
        ("%Y/%m/%d %H:%M:%S", 19),
        ("%Y-%m-%d", 10),
    ):
        try:
            dt = datetime.strptime(s[:n], fmt).replace(tzinfo=bj)
            return int(dt.timestamp() * 1000)
        except Exception:
            continue
    raise ValueError(f"无法解析时间: {label}")
