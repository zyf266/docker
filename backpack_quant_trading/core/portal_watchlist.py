"""标的观察库：币安加密 + Massive 美股；日线 MA 强弱 + 三状态（对齐 TV Pine）。

列表默认只读库（秒开）；指标默认读 30 分钟缓存（内存+磁盘），仅 force 时重拉 K 线。
三状态（固定级别）：熊市空头 / 趋势 / 反弹 / 牛市空头。
- 加密：2h SMA(ma2hLen 默认 180)；日线 MACD「水上金叉」(DIF>0 且 DIF>DEA)
- 美股：2h SMA(ma2hLen 默认 30)；日线 MACD「水上」(DIF>0 且 DEA>0)
Pine 四态变化 → 钉钉（关键词含「信号」）+ 站内信。加密 K 线优先 Hyperliquid。

钉钉 Webhook 只读环境变量 PORTAL_WATCH_DINGTALK_WEBHOOK（勿把 token 写进仓库）。
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from backpack_quant_trading.core.binance_monitor import (
    fetch_binance_klines,
    fetch_binance_symbols_usdt,
)
from backpack_quant_trading.core.ma_label_board import sma
from backpack_quant_trading.core import portal_store as store

logger = logging.getLogger(__name__)

# 对齐 Pine：ma2hLen（加密默认 180；美股脚本默认 30）
MA2H_LEN_CRYPTO = int(os.environ.get("PORTAL_WATCH_MA2H_LEN") or "180")
MA2H_LEN_US = int(os.environ.get("PORTAL_WATCH_MA2H_LEN_US") or "30")
# 兼容旧名
MA2H_LEN = MA2H_LEN_CRYPTO
# 缓存版本：改均线/美股 MACD/美股改 HL K 线后旧缓存失效
_METRICS_CACHE_VER = f"ma2h{MA2H_LEN_CRYPTO}_us{MA2H_LEN_US}_hlus1"

PORTAL_WATCH_DINGTALK_WEBHOOK = (os.environ.get("PORTAL_WATCH_DINGTALK_WEBHOOK") or "").strip()
_STATUS_STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "portal_watch_status_state.json"
_STATUS_STATE_LOCK = threading.Lock()

_CRYPTO_HINTS = {
    "BTCUSDT": "比特币",
    "ETHUSDT": "以太坊",
    "SOLUSDT": "Solana",
    "BNBUSDT": "BNB",
    "XRPUSDT": "XRP",
    "DOGEUSDT": "Dogecoin",
}

_US_HINTS = {
    "NVDA": "英伟达",
    "TSLA": "特斯拉",
    "AAPL": "苹果",
    "MSFT": "微软",
    "AMZN": "亚马逊",
    "GOOGL": "谷歌",
    "META": "Meta",
    "AMD": "AMD",
    "INTC": "英特尔",
    "MU": "美光",
    "SNDK": "SanDisk",
    "COIN": "Coinbase",
    "MSTR": "MicroStrategy",
    "PLTR": "Palantir",
    "NFLX": "奈飞",
    "BABA": "阿里巴巴",
    "PDD": "拼多多",
    "NIO": "蔚来",
    "XPEV": "小鹏",
    "LI": "理想",
}

# 指标缓存：默认 30 分钟；落盘避免 API 重启后每次进页都重拉 K 线
_METRICS_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_METRICS_TTL_SEC = 1800.0
_CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "portal_watchlist_metrics_cache.json"
_CACHE_LOCK = threading.Lock()
_CACHE_LOADED = False


def _load_disk_cache() -> None:
    global _CACHE_LOADED
    if _CACHE_LOADED:
        return
    with _CACHE_LOCK:
        if _CACHE_LOADED:
            return
        _CACHE_LOADED = True
        try:
            if not _CACHE_PATH.is_file():
                return
            raw = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            now = time.time()
            for key, row in (raw or {}).items():
                ts = float(row.get("ts") or 0)
                data = row.get("data")
                if not key or not isinstance(data, dict):
                    continue
                if now - ts > _METRICS_TTL_SEC * 2:
                    continue  # 太旧直接丢
                _METRICS_CACHE[key] = (ts, data)
            logger.info("portal_watchlist: 已加载指标缓存 %s 条", len(_METRICS_CACHE))
        except Exception as exc:
            logger.warning("portal_watchlist: 读磁盘缓存失败: %s", exc)


def _persist_disk_cache() -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            key: {"ts": ts, "data": data}
            for key, (ts, data) in _METRICS_CACHE.items()
        }
        tmp = _CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_CACHE_PATH)
    except Exception as exc:
        logger.warning("portal_watchlist: 写磁盘缓存失败: %s", exc)


def _cache_get(cache_key: str) -> Optional[Tuple[float, Dict[str, Any]]]:
    _load_disk_cache()
    hit = _METRICS_CACHE.get(cache_key)
    if not hit:
        return None
    ts, data = hit
    if (time.time() - ts) >= _METRICS_TTL_SEC:
        return None
    return ts, data


def _cache_put(cache_key: str, data: Dict[str, Any]) -> None:
    _load_disk_cache()
    clean = {k: v for k, v in data.items() if not str(k).startswith("_")}
    with _CACHE_LOCK:
        _METRICS_CACHE[cache_key] = (time.time(), clean)
        _persist_disk_cache()


def normalize_crypto_pair(symbol: str) -> str:
    raw = (symbol or "").strip().upper().replace("/", "").replace("-", "")
    if not raw:
        return ""
    if raw.endswith("USDT"):
        return raw
    return f"{raw}USDT"


def normalize_us_symbol(symbol: str) -> str:
    from backpack_quant_trading.core.massive_klines import normalize_us_ticker

    return normalize_us_ticker(symbol or "")


def normalize_pair(symbol: str, market: str = "crypto") -> str:
    if (market or "").lower() in ("us", "美股"):
        return normalize_us_symbol(symbol)
    return normalize_crypto_pair(symbol)


def display_code(symbol: str, market: str = "crypto") -> str:
    if (market or "").lower() in ("us", "美股"):
        return normalize_us_symbol(symbol) or (symbol or "").upper()
    sym = normalize_crypto_pair(symbol)
    return sym[:-4] if sym.endswith("USDT") else sym


def wma(values: List[float], length: int) -> Optional[float]:
    """加权移动平均（最近一根权重最大）。"""
    if length <= 0 or len(values) < length:
        return None
    window = values[-length:]
    weights = list(range(1, length + 1))
    den = float(sum(weights))
    if den <= 0:
        return None
    return sum(float(v) * w for v, w in zip(window, weights)) / den


def _vs_daily_wma15(tf_closes: List[float], daily_closes: List[float]) -> str:
    """2h/4h 状态（旧）：该周期最新收盘 vs 日线 WMA15。"""
    if not tf_closes:
        return "—"
    daily_wma = wma(daily_closes, 15)
    if daily_wma is None:
        return "—"
    return "站上" if float(tf_closes[-1]) >= float(daily_wma) else "未站上"


def _vs_own_sma(tf_closes: List[float], length: int = MA2H_LEN_CRYPTO) -> str:
    """周期收盘 vs 本周期 SMA（对齐 Pine：h2Close > ma2h）。"""
    if not tf_closes or length <= 0:
        return "—"
    ma = sma(tf_closes, length)
    if ma is None:
        return "—"
    return "站上" if float(tf_closes[-1]) >= float(ma) else "未站上"


def _macd_last(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[Optional[float], Optional[float]]:
    """日线 MACD 最新一根：(DIF/macd, DEA/signal)。不足数据返回 (None, None)。"""
    if len(closes) < slow + signal + 2:
        return None, None
    ema_fast = _ema_series(closes, fast)
    ema_slow = _ema_series(closes, slow)
    macd_line: List[Optional[float]] = [None] * len(closes)
    for i in range(len(closes)):
        if ema_fast[i] is None or ema_slow[i] is None:
            continue
        macd_line[i] = float(ema_fast[i]) - float(ema_slow[i])
    filled: List[float] = []
    for x in macd_line:
        filled.append(float(x) if x is not None else (filled[-1] if filled else 0.0))
    sig_series = _ema_series(filled, signal)
    i = len(closes) - 1
    m = macd_line[i]
    s = sig_series[i] if i < len(sig_series) else None
    if m is None or s is None:
        return None, None
    return float(m), float(s)


def _ema_series(values: List[float], length: int) -> List[Optional[float]]:
    if length <= 0 or not values:
        return []
    k = 2.0 / (length + 1)
    out: List[Optional[float]] = [None] * len(values)
    seed = sma(values[:length], length) if len(values) >= length else None
    if seed is None:
        return out
    start = length - 1
    out[start] = float(seed)
    prev = float(seed)
    for i in range(start + 1, len(values)):
        prev = float(values[i]) * k + prev * (1 - k)
        out[i] = prev
    return out


def _macd_water_golden(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> bool:
    """加密 Pine：日线 MACD 水上金叉（DIF>0 且 DIF>DEA）。"""
    m, s = _macd_last(closes, fast, slow, signal)
    if m is None or s is None:
        return False
    return m > 0 and m > s


def _macd_above_water(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> bool:
    """美股 Pine：日线 MACD 水上（DIF>0 且 DEA>0）；否则水下。"""
    m, s = _macd_last(closes, fast, slow, signal)
    if m is None or s is None:
        return False
    return m > 0 and s > 0


def eval_tradable(cfg: Optional[Dict[str, Any]], metrics: Dict[str, Any]) -> Dict[str, Any]:
    """对齐 TV 三状态 Pine。

    - 加密：水上金叉 (macd_water_golden)
    - 美股：水上/水下 (macd_above_water = DIF>0 且 DEA>0)
    """
    _ = cfg
    if metrics.get("ma200") is None:
        return {
            "tradable": False,
            "gates": [],
            "missing": ["日线数据不足"],
            "configured": False,
            "status_label": "",
            "status_mode": "",
        }
    is_us = (metrics.get("market") or "") in ("us", "美股")
    above200 = bool(metrics.get("long_on"))
    above30 = bool(metrics.get("mid_on"))
    above2h = bool(metrics.get("above_2h_ma")) or str(metrics.get("signal_2h") or "") == "站上"
    # 美股用 aboveWater；加密用水上金叉
    if is_us:
        water = bool(metrics.get("macd_above_water"))
        gate_tag = "pine_us_macd_water"
    else:
        water = bool(metrics.get("macd_water_golden"))
        gate_tag = "pine_crypto_macd_golden"

    if not above200:
        label = "熊市空头"
    elif above2h and (not above30) and (not water):
        label = "反弹"
    elif above2h or above30 or water:
        label = "趋势"
    else:
        label = "牛市空头"

    return {
        "tradable": label in ("趋势", "反弹"),
        "gates": [gate_tag],
        "missing": [],
        "configured": True,
        "status_mode": label,
        "status_label": label,
    }


def _load_status_state() -> Dict[str, Any]:
    try:
        if _STATUS_STATE_PATH.is_file():
            return json.loads(_STATUS_STATE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("read watch status state failed: %s", exc)
    return {}


def _save_status_state(state: Dict[str, Any]) -> None:
    try:
        _STATUS_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STATUS_STATE_PATH.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("write watch status state failed: %s", exc)


def _send_watch_dingtalk(title: str, body: str) -> None:
    wh = (PORTAL_WATCH_DINGTALK_WEBHOOK or "").strip()
    if not wh:
        logger.debug("PORTAL_WATCH_DINGTALK_WEBHOOK 未配置，跳过钉钉推送")
        return
    try:
        from backpack_quant_trading.core.stock_news_alert import send_dingtalk_markdown

        ok, msg = send_dingtalk_markdown(wh, title=title, text=body)
        if not ok:
            logger.warning("portal watch dingtalk failed: %s", msg)
    except Exception as exc:
        logger.warning("portal watch dingtalk error: %s", exc)


def _push_status_inbox(title: str, body: str) -> None:
    """站内信广播：观察库可见用户都能在 💡 里看到。"""
    try:
        n = store.broadcast_inbox(title, body)
        logger.info("portal watch inbox broadcast n=%s title=%s", n, title)
    except Exception as exc:
        logger.warning("portal watch inbox failed: %s", exc)


def maybe_notify_status_changes(metrics: Dict[str, Any]) -> None:
    """Pine 四态（status_label）边沿变化 → 钉钉（含关键词「信号」）+ 站内信。"""
    code = str(metrics.get("code") or metrics.get("symbol") or "").upper()
    if not code or metrics.get("error"):
        return
    # 确保有四态标签
    label = str(metrics.get("status_label") or "").strip()
    if not label:
        gate = eval_tradable(None, metrics)
        label = str(gate.get("status_label") or "").strip()
        metrics["status_label"] = label
    if not label:
        return

    market = "美股" if (metrics.get("market") or "") in ("us", "美股") else "加密"
    key = f"{metrics.get('market') or 'crypto'}:{metrics.get('symbol') or code}"
    cur_2h = str(metrics.get("signal_2h") or "—")
    cur_4h = str(metrics.get("signal_4h") or "—")
    px = metrics.get("price")
    ts = time.strftime("%Y-%m-%d %H:%M:%S")

    with _STATUS_STATE_LOCK:
        state = _load_status_state()
        prev = state.get(key) or {}
        prev_label = str(prev.get("status_label") or "").strip()
        changed = bool(prev_label) and prev_label != label
        state[key] = {
            "status_label": label,
            "signal_2h": cur_2h,
            "signal_4h": cur_4h,
            "price": px,
            "updated_at": ts,
        }
        _save_status_state(state)

    if not changed:
        return

    # 钉钉自定义机器人关键词：信号
    title = f"信号 · {code} 状态变更"
    detail = (
        f"【信号】观察库状态变更\n"
        f"{code}（{market}）{prev_label} → {label}\n"
        f"最新价: {px if px is not None else '—'}\n"
        f"2H(SMA{MA2H_LEN}): {cur_2h} · 4H: {cur_4h}\n"
        f"时间: {ts}"
    )
    _send_watch_dingtalk(title, detail)
    _push_status_inbox(title, detail)


def _daily_stand(closes: List[float]) -> Dict[str, Any]:
    """日线短中长强需要 MA200。"""
    if len(closes) < 200:
        return {
            "ok": False,
            "error": f"日线不足({len(closes)}/200)",
            "price": float(closes[-1]) if closes else None,
            "short_on": False,
            "mid_on": False,
            "long_on": False,
            "ma5": None,
            "ma30": None,
            "ma200": None,
        }
    price = float(closes[-1])
    ma5 = sma(closes, 5)
    ma30 = sma(closes, 30)
    ma200 = sma(closes, 200)
    assert ma5 is not None and ma30 is not None and ma200 is not None
    return {
        "ok": True,
        "error": "",
        "price": price,
        "short_on": price >= ma5,
        "mid_on": price >= ma30,
        "long_on": price >= ma200,
        "ma5": round(ma5, 6),
        "ma30": round(ma30, 6),
        "ma200": round(ma200, 6),
    }


def _closes_from_bars(bars: Optional[List[Dict[str, Any]]]) -> List[float]:
    if not bars:
        return []
    out = []
    for b in bars:
        try:
            out.append(float(b["close"]))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _normalize_ohlcv_bars(bars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """兼容 HL batch（已含 close）与原始 t/o/h/l/c。"""
    out: List[Dict[str, Any]] = []
    for b in bars or []:
        if not isinstance(b, dict):
            continue
        close = b.get("close", b.get("c"))
        if close is None:
            continue
        item = dict(b)
        item["close"] = float(close)
        if "open" not in item and b.get("o") is not None:
            item["open"] = float(b["o"])
        if "high" not in item and b.get("h") is not None:
            item["high"] = float(b["h"])
        if "low" not in item and b.get("l") is not None:
            item["low"] = float(b["l"])
        out.append(item)
    return out


def _fetch_crypto_klines(symbol: str, interval: str, limit: int = 250) -> Tuple[List[Dict[str, Any]], str]:
    """优先 Hyperliquid；失败再回退币安合约/现货。"""
    try:
        from backpack_quant_trading.core.hyperliquid_klines import (
            fetch_hl_klines_batch,
            to_hl_coin,
        )

        coin = to_hl_coin(symbol)
        raw = fetch_hl_klines_batch(coin, interval, total_limit=max(limit, 80)) or []
        bars = _normalize_ohlcv_bars(raw)
        if bars:
            return bars, "hyperliquid"
    except Exception as exc:
        logger.debug("hyperliquid %s %s: %s", symbol, interval, exc)
    try:
        bars = fetch_binance_klines(symbol, interval, limit=limit, market="futures") or []
        if bars:
            return bars, "binance_futures"
    except Exception as exc:
        logger.debug("binance futures %s %s: %s", symbol, interval, exc)
    try:
        bars = fetch_binance_klines(symbol, interval, limit=limit, market="spot") or []
        if bars:
            return bars, "binance_spot"
    except Exception as exc:
        logger.debug("binance spot %s %s: %s", symbol, interval, exc)
    return [], ""


def _fetch_yahoo_daily_closes(ticker: str, limit: int = 250) -> List[float]:
    """Yahoo chart 日线备选（仅日线）。"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval": "1d", "range": "2y"}
    try:
        resp = requests.get(
            url,
            params=params,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if resp.status_code != 200:
            return []
        result = (resp.json().get("chart") or {}).get("result") or []
        if not result:
            return []
        quotes = ((result[0].get("indicators") or {}).get("quote") or [{}])[0]
        closes = quotes.get("close") or []
        out = [float(x) for x in closes if x is not None]
        return out[-limit:] if out else []
    except Exception as exc:
        logger.debug("yahoo daily %s: %s", ticker, exc)
        return []


def _fetch_us_klines(symbol: str, interval: str, limit: int = 250) -> Tuple[List[Dict[str, Any]], str]:
    """优先 Hyperliquid（xyz:TICKER）→ Massive →（日线）Yahoo。"""
    try:
        from backpack_quant_trading.core.hyperliquid_klines import fetch_hl_klines_batch

        raw = fetch_hl_klines_batch(
            symbol, interval, total_limit=max(limit, 80), us_equity=True
        ) or []
        bars = _normalize_ohlcv_bars(raw)
        if bars:
            return bars, "hyperliquid"
    except Exception as exc:
        logger.debug("hyperliquid us %s %s: %s", symbol, interval, exc)
    try:
        from backpack_quant_trading.core.massive_klines import fetch_klines_us

        bars = fetch_klines_us(symbol, interval, total_limit=limit) or []
        if bars:
            return bars, "massive"
    except Exception as exc:
        logger.debug("massive %s %s: %s", symbol, interval, exc)
    if interval in ("1d", "d", "1day"):
        closes = _fetch_yahoo_daily_closes(symbol, limit=limit)
        if closes:
            return [{"close": c} for c in closes], "yahoo"
    return [], ""


def _empty_metrics(symbol: str, market: str, name: str = "") -> Dict[str, Any]:
    is_us = (market or "").lower() in ("us", "美股")
    code = display_code(symbol, "us" if is_us else "crypto")
    return {
        "symbol": normalize_pair(symbol, "us" if is_us else "crypto"),
        "code": code,
        "name": name or (_US_HINTS.get(code, code) if is_us else _CRYPTO_HINTS.get(
            normalize_crypto_pair(symbol), code
        )),
        "market": "us" if is_us else "crypto",
        "price": None,
        "signal_2h": "—",
        "signal_4h": "—",
        "above_2h_ma": False,
        "macd_water_golden": False,
        "macd_above_water": False,
        "short_on": False,
        "mid_on": False,
        "long_on": False,
        "ma5": None,
        "ma30": None,
        "ma200": None,
        "ma_timeframe": "1d",
        "error": "",
        "data_source": "",
    }


def compute_symbol_metrics(
    symbol: str,
    market: str = "crypto",
    *,
    force: bool = False,
) -> Dict[str, Any]:
    from concurrent.futures import ThreadPoolExecutor

    is_us = (market or "").lower() in ("us", "美股")
    cache_key = (
        f"{_METRICS_CACHE_VER}:{'us' if is_us else 'crypto'}:"
        f"{normalize_pair(symbol, 'us' if is_us else 'crypto')}"
    )
    if not force:
        hit = _cache_get(cache_key)
        if hit:
            ts, data = hit
            out = dict(data)
            out["_from_cache"] = True
            out["_cache_age_sec"] = round(time.time() - ts, 1)
            return out

    if is_us:
        ticker = normalize_us_symbol(symbol)
        base = _empty_metrics(ticker, "us")
        if not ticker:
            base["error"] = "无效美股代码"
            return base
        ma2h_len = MA2H_LEN_US
        # 日线必须；2h/4h 并行；美股 Pine ma2hLen 默认 30
        with ThreadPoolExecutor(max_workers=3) as pool:
            f1 = pool.submit(_fetch_us_klines, ticker, "1d", 220)
            f2 = pool.submit(_fetch_us_klines, ticker, "2h", max(220, ma2h_len + 40))
            f4 = pool.submit(_fetch_us_klines, ticker, "4h", 80)
            k1d, src1 = f1.result()
            k2, src2 = f2.result()
            k4, src4 = f4.result()
        closes_1d = _closes_from_bars(k1d)
        closes_2h = _closes_from_bars(k2)
        m1d = _daily_stand(closes_1d)
        sig2 = _vs_own_sma(closes_2h, ma2h_len)
        sig4 = _vs_daily_wma15(_closes_from_bars(k4), closes_1d)
        sources = [s for s in (src1, src2, src4) if s]
        last_px = m1d.get("price")
        if last_px is None and k2:
            last_px = closes_2h[-1] if closes_2h else None
    else:
        pair = normalize_crypto_pair(symbol)
        base = _empty_metrics(pair, "crypto")
        if not pair:
            base["error"] = "无效交易对"
            return base
        ma2h_len = MA2H_LEN_CRYPTO
        with ThreadPoolExecutor(max_workers=3) as pool:
            f1 = pool.submit(_fetch_crypto_klines, pair, "1d", 220)
            f2 = pool.submit(_fetch_crypto_klines, pair, "2h", max(220, ma2h_len + 40))
            f4 = pool.submit(_fetch_crypto_klines, pair, "4h", 80)
            k1d, src1 = f1.result()
            k2, src2 = f2.result()
            k4, src4 = f4.result()
        closes_1d = _closes_from_bars(k1d)
        closes_2h = _closes_from_bars(k2)
        m1d = _daily_stand(closes_1d)
        sig2 = _vs_own_sma(closes_2h, ma2h_len)
        sig4 = _vs_daily_wma15(_closes_from_bars(k4), closes_1d)
        sources = [s for s in (src1, src2, src4) if s]
        last_px = m1d.get("price")
        if last_px is None:
            for bars in (k2, k4):
                closes = _closes_from_bars(bars)
                if closes:
                    last_px = closes[-1]
                    break

    daily_wma15 = wma(closes_1d, 15) if closes_1d else None
    above_2h = sig2 == "站上"
    water_golden = _macd_water_golden(closes_1d) if closes_1d else False
    above_water = _macd_above_water(closes_1d) if closes_1d else False
    base.update({
        "price": last_px if last_px not in (None, 0) else None,
        "signal_2h": sig2,
        "signal_4h": sig4,
        "above_2h_ma": above_2h,
        "macd_water_golden": water_golden,
        "macd_above_water": above_water,
        "short_on": bool(m1d.get("short_on")),
        "mid_on": bool(m1d.get("mid_on")),
        "long_on": bool(m1d.get("long_on")),
        "ma5": m1d.get("ma5"),
        "ma30": m1d.get("ma30"),
        "ma200": m1d.get("ma200"),
        "wma15_daily": round(daily_wma15, 6) if daily_wma15 is not None else None,
        "error": m1d.get("error") or "",
        "data_source": "+".join(dict.fromkeys(sources)) if sources else "",
    })
    gate0 = eval_tradable(None, base)
    base["status_label"] = gate0.get("status_label") or ""
    base["status_mode"] = gate0.get("status_mode") or ""
    base["ma2h_len"] = ma2h_len
    _cache_put(cache_key, base)
    base["_from_cache"] = False
    base["_cache_age_sec"] = 0
    try:
        maybe_notify_status_changes(base)
    except Exception as exc:
        logger.debug("watch status notify skip: %s", exc)
    return base


def search_binance_pairs(q: str = "", limit: int = 40) -> List[Dict[str, str]]:
    return search_watch_symbols(q, market="crypto", limit=limit)


def search_us_symbols(q: str = "", limit: int = 40) -> List[Dict[str, str]]:
    key = (q or "").strip().upper()
    hits: List[Dict[str, str]] = []
    for sym, name in _US_HINTS.items():
        if not key or key in sym or key in name.upper():
            hits.append({"symbol": sym, "code": sym, "name": name, "market": "us"})
        if len(hits) >= limit:
            break
    if key and re.fullmatch(r"[A-Z]{1,5}", key) and not any(h["symbol"] == key for h in hits):
        hits.insert(0, {"symbol": key, "code": key, "name": key, "market": "us"})
    return hits[:limit]


def search_watch_symbols(q: str = "", market: str = "all", limit: int = 40) -> List[Dict[str, str]]:
    mkt = (market or "all").lower()
    if mkt in ("us", "美股"):
        return search_us_symbols(q, limit=limit)
    if mkt in ("crypto", "加密"):
        key = (q or "").strip().upper().replace("/", "")
        try:
            symbols = fetch_binance_symbols_usdt()
        except Exception:
            symbols = list(_CRYPTO_HINTS.keys())
        hits: List[str] = []
        for sym in symbols:
            if not key or key in sym:
                hits.append(sym)
            if len(hits) >= limit:
                break
        return [
            {
                "symbol": s,
                "code": display_code(s, "crypto"),
                "name": _CRYPTO_HINTS.get(s, display_code(s, "crypto")),
                "market": "crypto",
            }
            for s in hits
        ]
    half = max(limit // 2, 8)
    crypto = search_watch_symbols(q, "crypto", limit=half)
    us = search_us_symbols(q, limit=limit - len(crypto))
    return crypto + us


def list_watchlist_board(
    user_id: int,
    *,
    with_metrics: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    from concurrent.futures import ThreadPoolExecutor

    favs = store.list_favorites(user_id)
    try:
        configs = store.list_watch_configs(user_id)
    except Exception:
        configs = []
    cfg_map = {c["symbol"]: c for c in configs}

    def _one(fav: Dict[str, Any]) -> Dict[str, Any]:
        market = fav.get("market") or "crypto"
        sym = fav["symbol"]
        if with_metrics:
            try:
                metrics = compute_symbol_metrics(sym, market, force=force)
            except Exception as exc:
                metrics = _empty_metrics(sym, market, fav.get("name") or "")
                metrics["error"] = str(exc)[:200]
                metrics["_from_cache"] = False
        else:
            # 无 metrics 请求时仍尽量回填未过期缓存，避免进页全是「—」
            cache_key = (
                f"{_METRICS_CACHE_VER}:"
                f"{'us' if (market or '').lower() in ('us', '美股') else 'crypto'}:"
                f"{normalize_pair(sym, market)}"
            )
            hit = _cache_get(cache_key)
            if hit:
                ts, data = hit
                metrics = dict(data)
                metrics["_from_cache"] = True
                metrics["_cache_age_sec"] = round(time.time() - ts, 1)
            else:
                metrics = _empty_metrics(sym, market, fav.get("name") or "")
                metrics["_from_cache"] = False
        metrics["id"] = fav["id"]
        if fav.get("name") and fav["name"] != fav["symbol"]:
            metrics["name"] = fav["name"]
        cfg = cfg_map.get(normalize_pair(sym, market))
        metrics["config"] = cfg
        gate = eval_tradable(cfg, metrics)
        metrics["tradable"] = gate["tradable"]
        metrics["tradable_missing"] = gate["missing"]
        metrics["gates_configured"] = gate["configured"]
        metrics["status_mode"] = gate.get("status_mode") or ""
        metrics["status_label"] = gate.get("status_label") or ""
        return metrics

    if with_metrics and len(favs) > 1:
        with ThreadPoolExecutor(max_workers=min(4, len(favs))) as pool:
            items = list(pool.map(_one, favs))
    else:
        items = [_one(fav) for fav in favs]

    short_n = sum(1 for i in items if i.get("short_on"))
    mid_n = sum(1 for i in items if i.get("mid_on"))
    long_n = sum(1 for i in items if i.get("long_on"))
    ages = [float(i.get("_cache_age_sec") or 0) for i in items if i.get("_from_cache")]
    from_cache = bool(with_metrics) and bool(items) and all(i.get("_from_cache") for i in items)
    oldest = max(ages) if ages else None
    return {
        "items": items,
        "summary": {"short": short_n, "mid": mid_n, "long": long_n},
        "with_metrics": bool(with_metrics),
        "from_cache": from_cache,
        "force": bool(force),
        "cache_ttl_sec": int(_METRICS_TTL_SEC),
        "oldest_cache_age_sec": oldest,
        "source": "crypto:HL→binance; us:HL(xyz:)→massive→yahoo",
    }


def add_watch_symbol(
    user_id: int,
    symbol: str,
    name: str = "",
    market: str = "crypto",
) -> Dict[str, Any]:
    """只落库，不算 K 线，保证添加瞬间有反馈。"""
    is_us = (market or "").lower() in ("us", "美股")
    if is_us:
        ticker = normalize_us_symbol(symbol)
        if not ticker:
            raise ValueError("请输入美股代码，例如 NVDA")
        display_name = (name or "").strip() or _US_HINTS.get(ticker, ticker)
        fav = store.add_favorite(user_id, ticker, "us", display_name)
        item = _empty_metrics(ticker, "us", display_name)
    else:
        pair = normalize_crypto_pair(symbol)
        if not pair:
            raise ValueError("请输入币安交易对，例如 BTC 或 BTCUSDT")
        # 不强依赖 exchangeInfo（代理挂了也能加常用币）
        try:
            known = set(fetch_binance_symbols_usdt())
        except Exception:
            known = set()
        if known and pair not in known and pair not in _CRYPTO_HINTS:
            raise ValueError(f"{pair} 不在币安 USDT 永续列表中")
        display_name = (name or "").strip() or _CRYPTO_HINTS.get(pair, display_code(pair, "crypto"))
        fav = store.add_favorite(user_id, pair, "crypto", display_name)
        item = _empty_metrics(pair, "crypto", display_name)
    item["id"] = fav["id"]
    item["name"] = display_name
    item["saved"] = True
    # 新标的继承该市场已保存的默认状态（及可选交易）配置
    try:
        mkt = "us" if is_us else "crypto"
        default = store.get_watch_market_default(user_id, mkt)
        profiles = store.normalize_status_profiles(default.get("status_profiles") if default else None)
        allowed = store.normalize_allowed_statuses(
            (default or {}).get("allowed_statuses")
            or (default or {}).get("status_profiles")
        )
        profiles_blob = {**profiles, "allowed_statuses": allowed} if allowed else profiles
        if default and (store.status_profiles_configured(profiles) or allowed):
            store.upsert_watch_gates(
                user_id,
                [item["symbol"]],
                status_profiles=profiles_blob,
            )
            item["config"] = {
                "status_profiles": profiles,
                "allowed_statuses": allowed,
            }
        elif default and (
            default.get("require_2h")
            or default.get("require_4h")
            or default.get("require_mid")
            or default.get("require_long")
        ):
            store.upsert_watch_gates(
                user_id,
                [item["symbol"]],
                require_short=False,
                require_mid=bool(default.get("require_mid")),
                require_long=bool(default.get("require_long")),
                require_2h=bool(default.get("require_2h")),
                require_4h=bool(default.get("require_4h")),
                status_mode=default.get("status_mode") or "趋势",
            )
            item["config"] = {
                "require_mid": bool(default.get("require_mid")),
                "require_long": bool(default.get("require_long")),
                "require_2h": bool(default.get("require_2h")),
                "require_4h": bool(default.get("require_4h")),
                "status_mode": store.normalize_status_mode(default.get("status_mode")),
            }
    except Exception as exc:
        logger.debug("apply market default skip: %s", exc)
    return item
