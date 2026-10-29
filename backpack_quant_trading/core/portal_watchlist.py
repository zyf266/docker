"""标的观察库：币安加密 + Massive 美股；日线 MA 强弱 + 2h/4h 相对 WMA15 状态。

列表默认只读库（秒开）；指标默认读 30 分钟缓存（内存+磁盘），仅 force 时重拉 K 线。
变盘：2H/4H 收盘站上「日线 WMA15」；中强：日线收盘 > MA30。
任一状态变化推钉钉。加密 K 线优先 Hyperliquid。
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

PORTAL_WATCH_DINGTALK_WEBHOOK = (
    os.environ.get("PORTAL_WATCH_DINGTALK_WEBHOOK")
    or "https://oapi.dingtalk.com/robot/send?access_token=8b44c3949d211969cb4ec04ac605b605c39d87cc404a200a2b45a19694660b82"
).strip()
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
    """2h/4h 状态：该周期最新收盘 vs 日线 WMA15（15 日均线）。"""
    if not tf_closes:
        return "—"
    daily_wma = wma(daily_closes, 15)
    if daily_wma is None:
        return "—"
    return "站上" if float(tf_closes[-1]) >= float(daily_wma) else "未站上"


def _profile_gate_check(gates: Dict[str, Any], metrics: Dict[str, Any]) -> tuple:
    """返回 (used_gate_keys, missing_labels)。"""
    used = []
    missing = []
    if gates.get("require_2h"):
        used.append("2h")
        if str(metrics.get("signal_2h") or "") != "站上":
            missing.append("2h状态")
    if gates.get("require_4h"):
        used.append("4h")
        if str(metrics.get("signal_4h") or "") != "站上":
            missing.append("4h状态")
    if gates.get("require_mid"):
        used.append("mid")
        if not metrics.get("mid_on"):
            missing.append("中强(MA30)")
    if gates.get("require_long"):
        used.append("long")
        if not metrics.get("long_on"):
            missing.append("长强(MA200)")
    return used, missing


def eval_tradable(cfg: Optional[Dict[str, Any]], metrics: Dict[str, Any]) -> Dict[str, Any]:
    """三套状态配置：按 趋势>反弹>空头 优先级，先满足者显示该标签；都不满足为 —。"""
    if not cfg:
        return {
            "tradable": False,
            "gates": [],
            "missing": [],
            "configured": False,
            "status_label": "",
            "status_mode": "",
        }
    profiles = store.normalize_status_profiles(cfg.get("status_profiles"))
    if store.status_profiles_configured(profiles):
        configured = True
        last_missing = []
        last_gates = []
        for mode in store.WATCH_STATUS_MODES:  # 趋势 → 反弹 → 空头
            g = profiles.get(mode) or {}
            used, missing = _profile_gate_check(g, metrics)
            if not used:
                continue
            last_gates, last_missing = used, missing
            if not missing:
                return {
                    "tradable": True,
                    "gates": used,
                    "missing": [],
                    "configured": True,
                    "status_mode": mode,
                    "status_label": mode,
                }
        return {
            "tradable": False,
            "gates": last_gates,
            "missing": last_missing,
            "configured": configured,
            "status_mode": "",
            "status_label": "",
        }

    # 兼容旧版单配置
    used, missing = _profile_gate_check(cfg, metrics)
    configured = bool(used)
    ok = bool(configured and not missing)
    mode = store.normalize_status_mode(cfg.get("status_mode"))
    return {
        "tradable": ok,
        "gates": used,
        "missing": missing,
        "configured": configured,
        "status_mode": mode,
        "status_label": mode if ok else "",
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
        return
    try:
        from backpack_quant_trading.core.stock_news_alert import send_dingtalk_markdown

        ok, msg = send_dingtalk_markdown(wh, title=title, text=body)
        if not ok:
            logger.warning("portal watch dingtalk failed: %s", msg)
    except Exception as exc:
        logger.warning("portal watch dingtalk error: %s", exc)


def maybe_notify_status_changes(metrics: Dict[str, Any]) -> None:
    """变盘/趋势状态边沿触发钉钉（站上 WMA15 / 进入日线>MA30）。"""
    code = str(metrics.get("code") or metrics.get("symbol") or "").upper()
    if not code or metrics.get("error"):
        return
    market = "美股" if (metrics.get("market") or "") in ("us", "美股") else "加密"
    key = f"{metrics.get('market') or 'crypto'}:{metrics.get('symbol') or code}"
    cur_2h = str(metrics.get("signal_2h") or "—")
    cur_4h = str(metrics.get("signal_4h") or "—")
    cur_trend = bool(metrics.get("mid_on"))
    px = metrics.get("price")

    with _STATUS_STATE_LOCK:
        state = _load_status_state()
        prev = state.get(key) or {}
        prev_2h = str(prev.get("signal_2h") or "")
        prev_4h = str(prev.get("signal_4h") or "")
        prev_trend = prev.get("trend_on")
        alerts: List[str] = []

        # 任一变化即推（含站上↔未站上、中强真假切换）
        if prev_2h and cur_2h != prev_2h and cur_2h != "—":
            alerts.append(f"【2H状态】{code}（{market}）{prev_2h} → {cur_2h}（相对日线 WMA15）")
        if prev_4h and cur_4h != prev_4h and cur_4h != "—":
            alerts.append(f"【4H状态】{code}（{market}）{prev_4h} → {cur_4h}（相对日线 WMA15）")
        if prev_trend is not None and bool(prev_trend) != cur_trend:
            alerts.append(
                f"【中强/趋势】{code}（{market}）日线{'站上' if cur_trend else '跌破'} MA30"
            )

        state[key] = {
            "signal_2h": cur_2h,
            "signal_4h": cur_4h,
            "trend_on": cur_trend,
            "price": px,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        _save_status_state(state)

    for line in alerts:
        detail = f"{line}\n最新价: {px if px is not None else '—'}\n2H状态: {cur_2h} · 4H状态: {cur_4h} · 趋势(日>MA30): {'是' if cur_trend else '否'}"
        _send_watch_dingtalk("观察库状态提醒", detail)


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


def _fetch_crypto_klines(symbol: str, interval: str, limit: int = 250) -> Tuple[List[Dict[str, Any]], str]:
    """优先 Hyperliquid；失败再回退币安合约/现货。"""
    try:
        from backpack_quant_trading.core.hyperliquid_klines import (
            fetch_hl_klines_batch,
            hl_bars_to_ohlcv,
            to_hl_coin,
        )

        coin = to_hl_coin(symbol)
        raw = fetch_hl_klines_batch(coin, interval, total_limit=max(limit, 80)) or []
        if raw:
            bars = hl_bars_to_ohlcv(raw)
            # 统一 close 字段，兼容 _closes_from_bars
            for b in bars:
                if "close" not in b and "c" in b:
                    b["close"] = b["c"]
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
    """Massive →（日线）Yahoo。"""
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
    cache_key = f"{'us' if is_us else 'crypto'}:{normalize_pair(symbol, 'us' if is_us else 'crypto')}"
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
        # 日线必须；2h/4h 并行且少根数，失败可空
        with ThreadPoolExecutor(max_workers=3) as pool:
            f1 = pool.submit(_fetch_us_klines, ticker, "1d", 220)
            f2 = pool.submit(_fetch_us_klines, ticker, "2h", 80)
            f4 = pool.submit(_fetch_us_klines, ticker, "4h", 80)
            k1d, src1 = f1.result()
            k2, src2 = f2.result()
            k4, src4 = f4.result()
        closes_1d = _closes_from_bars(k1d)
        m1d = _daily_stand(closes_1d)
        # 2h/4h：收盘 vs 日线 WMA15（15日均线）
        sig2 = _vs_daily_wma15(_closes_from_bars(k2), closes_1d)
        sig4 = _vs_daily_wma15(_closes_from_bars(k4), closes_1d)
        sources = [s for s in (src1, src2, src4) if s]
        last_px = m1d.get("price")
        if last_px is None and k2:
            closes2 = _closes_from_bars(k2)
            last_px = closes2[-1] if closes2 else None
    else:
        pair = normalize_crypto_pair(symbol)
        base = _empty_metrics(pair, "crypto")
        if not pair:
            base["error"] = "无效交易对"
            return base
        with ThreadPoolExecutor(max_workers=3) as pool:
            f1 = pool.submit(_fetch_crypto_klines, pair, "1d", 220)
            f2 = pool.submit(_fetch_crypto_klines, pair, "2h", 80)
            f4 = pool.submit(_fetch_crypto_klines, pair, "4h", 80)
            k1d, src1 = f1.result()
            k2, src2 = f2.result()
            k4, src4 = f4.result()
        closes_1d = _closes_from_bars(k1d)
        m1d = _daily_stand(closes_1d)
        sig2 = _vs_daily_wma15(_closes_from_bars(k2), closes_1d)
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
    base.update({
        "price": last_px if last_px not in (None, 0) else None,
        "signal_2h": sig2,
        "signal_4h": sig4,
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
            cache_key = f"{'us' if (market or '').lower() in ('us', '美股') else 'crypto'}:" \
                        f"{normalize_pair(sym, market)}"
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
        "source": "hyperliquid→binance+massive→yahoo",
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
        if default and store.status_profiles_configured(profiles):
            store.upsert_watch_gates(
                user_id,
                [item["symbol"]],
                status_profiles=profiles,
            )
            item["config"] = {"status_profiles": profiles}
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
