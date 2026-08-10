"""
美股周报（免费数据源快照）

数据来源（均为免费、无需密钥；请遵守各站服务条款与访问频率）：
- Yahoo Finance v8 chart API（非官方）：指数/ETF/个股日线收盘价
- FRED 公开 CSV 导出：美债收益率 DGS10/DGS2、部分信用利差系列（若可用）

口径说明：
- 「近一周涨跌」：取最近一段日 K 中，**最后一根完整日 K 收盘价**相对 **往前第 5 个交易日** 收盘价的百分比变化（约等于一周交易日，非自然周）。
- 若历史不足 6 根有效收盘，则退化为首根至末根，并在字段中标注。
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backpack_quant_trading.api.deps import require_user, get_current_user, require_login_unless
from backpack_quant_trading.config.settings import config as _app_config

logger = logging.getLogger(__name__)

router = APIRouter()

YAHOO_CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
FRED_GRAPH_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"

UA = "Mozilla/5.0 (compatible; ApexAI-UsWeeklyReport/1.0; +https://example.local)"

# 简单的进程内 TTL 缓存：按市场分槽（snap:us / snap:a_share）
_CACHE_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {}
_CACHE_TTL_SEC = 300  # 5 分钟

# 历史分析结果持久化（JSON 文件，按市场分文件）
_HISTORY_LOCK = threading.Lock()
_HISTORY_PATH = Path(_app_config.data_dir) / "us_bubble_history.json"
_A_SHARE_HISTORY_PATH = Path(_app_config.data_dir) / "a_share_bubble_history.json"

# 泡沫阶段标签（与提示词一致）
from backpack_quant_trading.core.bubble_weekly_prompts import (
    BUBBLE_STAGES,
    build_stock_focus_block,
    build_stock_strategy_user_prompt,
    build_ui_report,
    get_output_format,
    get_report_type,
    get_strategy_meta,
    get_system_prompt,
    is_stock_focus_report,
    is_stock_strategy,
    list_a_share_strategies,
    normalize_market,
    normalize_strategy,
)


def _resolve_proxies() -> Optional[Dict[str, str]]:
    """
    代理解析顺序（优先级从高到低）：
    1) 环境变量 US_REPORT_PROXY（仅此模块生效，如 http://127.0.0.1:7890）
    2) 系统 HTTPS_PROXY / HTTP_PROXY（requests 默认行为）
    3) 显式禁用代理：US_REPORT_NO_PROXY=1
    """
    if os.getenv("US_REPORT_NO_PROXY") in ("1", "true", "True"):
        return {"http": None, "https": None}
    explicit = os.getenv("US_REPORT_PROXY")
    if explicit:
        return {"http": explicit, "https": explicit}
    # 返回 None 表示「让 requests 自行用系统代理」
    return None


def _http_get_domestic(url: str, params: Optional[dict] = None, retries: int = 1) -> requests.Response:
    """东财/国内源：强制直连，不走容器 HTTP_PROXY（避免 ProxyError）。"""
    from backpack_quant_trading.core.a_share_strategy_import import _direct_get

    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            return _direct_get(
                url,
                params=params or {},
                headers={"User-Agent": UA, "Accept": "application/json,*/*", "Referer": "https://quote.eastmoney.com/"},
                timeout=20,
            )
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("_http_get_domestic unknown error")


def _http_get(url: str, params: Optional[dict] = None, retries: int = 1) -> requests.Response:
    """
    对外部行情站请求：
    - 默认尊重系统代理（Clash 等），可通过 US_REPORT_PROXY 单独指定，或 US_REPORT_NO_PROXY=1 强制直连。
    - timeout 拉宽到 (8, 25)，失败重试 retries 次。
    """
    proxies = _resolve_proxies()
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            return requests.get(
                url,
                params=params or {},
                timeout=(8, 25),
                headers={"User-Agent": UA, "Accept": "application/json,text/csv,*/*"},
                proxies=proxies,
            )
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
                continue
            raise
    # 理论不会到这里
    if last_exc:
        raise last_exc
    raise RuntimeError("_http_get unknown error")


def _yahoo_series(symbol: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    返回 [{date, close, ts}, ...] 按时间升序；错误时第二项为错误说明。
    """
    enc = urllib.parse.quote(symbol, safe="")
    url = f"{YAHOO_CHART_BASE}/{enc}"
    try:
        r = _http_get(url, params={"range": "2mo", "interval": "1d"})
        r.raise_for_status()
        js = r.json()
    except Exception as e:
        return [], f"Yahoo 请求失败 {symbol}: {e}"

    try:
        res = js["chart"]["result"][0]
        ts_list = res.get("timestamp") or []
        _ind = res.get("indicators") or {}
        _qkey = "quote"
        _qrows = _ind.get(_qkey) or [{}]
        closes = (_qrows[0] or {}).get("close") or []
    except (KeyError, IndexError, TypeError) as e:
        return [], f"Yahoo 解析失败 {symbol}: {e}"

    out: List[Dict[str, Any]] = []
    for ts, c in zip(ts_list, closes):
        if c is None or ts is None:
            continue
        dt_utc = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        out.append({
            "ts": int(ts),
            "date": dt_utc.strftime("%Y-%m-%d"),
            "close": float(c),
        })
    if not out:
        return [], f"Yahoo 无有效收盘 {symbol}"
    return out, None


def _week_like_return(closes_asc: List[Dict[str, Any]]) -> Dict[str, Any]:
    """最后一根相对往前第 5 根交易日的涨跌幅。"""
    n = len(closes_asc)
    if n < 2:
        return {"pct": None, "note": "数据不足", "from_date": None, "to_date": None, "from_close": None, "to_close": None}
    end = closes_asc[-1]
    start_idx = max(0, n - 6)
    start = closes_asc[start_idx]
    pct = (end["close"] - start["close"]) / start["close"] * 100.0 if start["close"] else None
    note = "近约5个交易日收盘到收盘" if n >= 6 else f"仅{n}根K线，为首末根涨跌"
    return {
        "pct": round(pct, 4) if pct is not None else None,
        "note": note,
        "from_date": start["date"],
        "to_date": end["date"],
        "from_close": start["close"],
        "to_close": end["close"],
    }


def _fred_latest_two(series_id: str) -> Dict[str, Any]:
    """拉取 FRED graph CSV 最近两行（用于展示最新值与上一日）。"""
    url = f"{FRED_GRAPH_CSV}?id={series_id}"
    try:
        r = _http_get(url)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
    except Exception as e:
        return {"series": series_id, "error": str(e), "source": url}

    # 列名可能是 observation_date 或 DATE，值列多为 series_id
    cols = list(df.columns)
    if len(cols) < 2:
        return {"series": series_id, "error": "CSV列异常", "source": url, "columns": cols}

    date_col = "observation_date" if "observation_date" in cols else cols[0]
    val_col = series_id if series_id in cols else cols[-1]
    df = df[[date_col, val_col]].dropna()
    df = df[df[val_col] != "."]
    if df.empty:
        return {"series": series_id, "error": "无有效观测", "source": url}

    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
    df = df.dropna(subset=[val_col])
    if len(df) < 1:
        return {"series": series_id, "error": "无数值", "source": url}

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else None
    out: Dict[str, Any] = {
        "series": series_id,
        "source": url,
        "data_vendor": "FRED (St. Louis Fed) graph CSV export",
        "as_of_date": str(last[date_col]),
        "value_pct": float(last[val_col]),
        "field": "percent per annum" if series_id.startswith("DGS") else "index level / spread (see FRED definition)",
    }
    if prev is not None:
        out["prev_date"] = str(prev[date_col])
        out["prev_value_pct"] = float(prev[val_col])
        out["dod_bp"] = round((float(last[val_col]) - float(prev[val_col])) * 100.0, 2)  # 百分点→bp 显示用（对收益率序列）
    return out


def _build_index_row(label: str, yahoo_symbol: str) -> Dict[str, Any]:
    series, err = _yahoo_series(yahoo_symbol)
    if err:
        return {
            "label": label,
            "yahoo_symbol": yahoo_symbol,
            "error": err,
            "source": f"{YAHOO_CHART_BASE}/{urllib.parse.quote(yahoo_symbol, safe='')}?range=2mo&interval=1d",
            "data_vendor": "Yahoo Finance chart API (unofficial)",
        }
    ch = _week_like_return(series)
    last = series[-1]
    return {
        "label": label,
        "yahoo_symbol": yahoo_symbol,
        "last_date": last["date"],
        "last_close": last["close"],
        "week_change_pct": ch["pct"],
        "week_note": ch["note"],
        "week_from_date": ch["from_date"],
        "week_to_date": ch["to_date"],
        "source": f"{YAHOO_CHART_BASE}/{urllib.parse.quote(yahoo_symbol, safe='')}?range=2mo&interval=1d",
        "data_vendor": "Yahoo Finance chart API (unofficial)",
    }


def _build_snapshot_payload() -> Dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    index_specs: List[Tuple[str, str]] = [
        ("标普500", "^GSPC"),
        ("纳斯达克综合", "^IXIC"),
        ("纳斯达克100", "^NDX"),
        ("QQQ", "QQQ"),
        ("罗素2000 ETF", "IWM"),
        ("费城半导体指数", "^SOX"),
        ("半导体 ETF SMH", "SMH"),
    ]
    vol_specs: List[Tuple[str, str]] = [
        ("VIX", "^VIX"),
        ("VVIX", "^VVIX"),
    ]
    watch_symbols = [
        "NVDA", "AMD", "AVGO", "TSM", "ASML", "ANET", "DELL", "SMCI",
        "ORCL", "MSFT", "GOOGL", "AMZN", "META", "PLTR", "TSLA",
    ]
    dxy_spec = ("美元指数期货连续", "DX-Y.NYB")
    fred_rates = [("DGS10", "rates"), ("DGS2", "rates")]
    fred_credit = [
        ("BAMLH0A0HYM2", "ICE BofA US High Yield OAS"),
        ("BAMLC0A4CBBB", "ICE BofA BBB US Corporate OAS（近似投资级端，非全 IG 指数）"),
    ]

    # 全部抓取任务并发执行（IO 密集，线程池足够）
    yahoo_jobs: List[Tuple[str, Tuple[str, str]]] = []
    for label, sym in index_specs:
        yahoo_jobs.append((f"idx::{sym}", (label, sym)))
    for label, sym in vol_specs:
        yahoo_jobs.append((f"vol::{sym}", (label, sym)))
    for sym in watch_symbols:
        yahoo_jobs.append((f"wl::{sym}", (sym, sym)))
    yahoo_jobs.append((f"dxy::{dxy_spec[1]}", dxy_spec))

    fred_jobs: List[str] = [sid for sid, _ in fred_rates] + [sid for sid, _ in fred_credit]

    results: Dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        fut_map: Dict[Any, str] = {}
        for key, (label, sym) in yahoo_jobs:
            fut = ex.submit(_build_index_row, label, sym)
            fut_map[fut] = key
        for sid in fred_jobs:
            fut = ex.submit(_fred_latest_two, sid)
            fut_map[fut] = f"fred::{sid}"
        for fut, key in fut_map.items():
            try:
                results[key] = fut.result(timeout=25)
            except Exception as e:
                results[key] = {"error": f"任务异常: {e!r}", "key": key}

    indices = [results[f"idx::{sym}"] for _, sym in index_specs]
    vol_block = {
        "vix": results[f"vol::^VIX"],
        "vvix": results[f"vol::^VVIX"],
        "note": "VIX/VVIX 为 Yahoo 日线收盘推导的「近约5交易日」变化，非 CBOE 官方实时推送。",
    }
    rates = {
        "dgs10": results.get("fred::DGS10", {"error": "未取到"}),
        "dgs2": results.get("fred::DGS2", {"error": "未取到"}),
        "note": "DGS10/DGS2 为 FRED 日频「市场预期」口径美债收益率（%），非拍卖中标利率。",
    }
    credit: Dict[str, Any] = {}
    for sid, name in fred_credit:
        row = results.get(f"fred::{sid}", {"series": sid, "error": "未取到"})
        if isinstance(row, dict):
            row["label"] = name
        credit[sid] = row
    tickers = [results[f"wl::{s}"] for s in watch_symbols]
    dxy = results[f"dxy::{dxy_spec[1]}"]

    disclaimer = (
        "本页为免费数据源自动聚合，仅供内部研究备忘，不构成投资建议。"
        "未覆盖部分（期权结构、宽度、私募融资、GPU 租价等）标注为未提供。"
        "若某字段抓取失败，以 error 为准，请勿用记忆补数。"
    )

    return {
        "generated_at_utc": generated_at_utc,
        "disclaimer": disclaimer,
        "sections_included": [
            "主要指数与半导体相关（Yahoo）",
            "波动率 VIX / VVIX（Yahoo）",
            "美债 10Y/2Y（FRED CSV）",
            "部分信用利差 HY/IG OAS（FRED CSV，若系列可用）",
            "观察清单大票日线快照（Yahoo）",
            "美元指数相关（Yahoo DX-Y.NYB）",
        ],
        "sections_excluded": [
            "休市日历（需交易所官方日历逐周核对，此处不自动推断）",
            "Put/Call、期权成交、CDX、市场宽度、Mag7 贡献分解",
            "Hyperscaler capex 细项、GPU 租赁价、AI 私募估值",
        ],
        "indices": indices,
        "volatility": vol_block,
        "rates": rates,
        "credit": credit,
        "dxy": dxy,
        "watchlist_equities": tickers,
    }


@router.get("/snapshot")
def us_weekly_snapshot(
    user: dict = Depends(require_user),
    force_refresh: bool = Query(False, description="忽略缓存，强制重新抓取"),
    market: str = Query("us", description="us | a_share"),
) -> Dict[str, Any]:
    """
    周报快照：美股为 Yahoo/FRED 半套；A股为东财指数 K 线。
    内存级 TTL 缓存（默认 5 分钟），按 market 分槽。
    """
    m = normalize_market(market)
    cache_key = f"snap:{m}"
    now = time.time()
    if not force_refresh:
        with _CACHE_LOCK:
            slot = _CACHE.get(cache_key) or {}
            if slot.get("data") is not None and (now - (slot.get("ts") or 0)) < _CACHE_TTL_SEC:
                cached = dict(slot["data"])
                cached["_cache_age_sec"] = round(now - slot["ts"], 1)
                cached["_cache_ttl_sec"] = _CACHE_TTL_SEC
                return cached

    try:
        payload = (
            _build_a_share_snapshot_payload()
            if m == "a_share"
            else _build_snapshot_payload()
        )
        with _CACHE_LOCK:
            _CACHE[cache_key] = {"data": payload, "ts": time.time()}
        payload["_cache_age_sec"] = 0.0
        payload["_cache_ttl_sec"] = _CACHE_TTL_SEC
        return payload
    except Exception as e:
        logger.exception("us_weekly_snapshot(%s) 聚合失败: %s", m, e)
        return {
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "market": m,
            "fatal_error": repr(e),
            "disclaimer": "聚合过程发生异常，以下为占位；请查看 fatal_error 并重试或检查网络/代理。",
            "sections_included": [],
            "sections_excluded": [],
            "indices": [],
            "volatility": {"vix": {}, "vvix": {}, "note": ""},
            "rates": {},
            "credit": {},
            "dxy": {},
            "watchlist_equities": [],
        }


# ─────────────────────────────────────────────────────────
# 历史分析存储（JSON 文件，按 market 分文件）
# ─────────────────────────────────────────────────────────
def _history_file(market: str = "us") -> Path:
    m = normalize_market(market)
    return _A_SHARE_HISTORY_PATH if m == "a_share" else _HISTORY_PATH


def _history_load(market: str = "us") -> List[Dict[str, Any]]:
    path = _history_file(market)
    try:
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("读取历史分析失败(%s): %s", market, e)
        return []


def _history_save(items: List[Dict[str, Any]], market: str = "us") -> None:
    path = _history_file(market)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("写入历史分析失败(%s): %s", market, e)


def _history_append(item: Dict[str, Any], market: str = "us") -> None:
    with _HISTORY_LOCK:
        items = _history_load(market)
        item = dict(item)
        item["market"] = normalize_market(market)
        items.append(item)
        if len(items) > 200:
            items = items[-200:]
        _history_save(items, market)


# ─────────────────────────────────────────────────────────
# DeepSeek 分析（提示词见 core/bubble_weekly_prompts.py）
# ─────────────────────────────────────────────────────────

def _build_a_share_snapshot_payload() -> Dict[str, Any]:
    """A股周报轻量快照：东财主要指数近约 30 根日K。"""
    indices_map = [
        ("1.000001", "上证指数"),
        ("0.399001", "深证成指"),
        ("0.399006", "创业板指"),
        ("1.000688", "科创50"),
        ("1.000300", "沪深300"),
        ("1.000852", "中证1000"),
    ]
    out: List[Dict[str, Any]] = []
    for secid, name in indices_map:
        try:
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            r = _http_get_domestic(
                url,
                params={
                    "secid": secid,
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                    "klt": "101",
                    "fqt": "1",
                    "end": "20500101",
                    "lmt": "30",
                },
            )
            r.raise_for_status()
            kl = ((r.json() or {}).get("data") or {}).get("klines") or []
            closes = []
            for row in kl:
                parts = str(row).split(",")
                if len(parts) >= 3:
                    try:
                        closes.append({"date": parts[0], "close": float(parts[2])})
                    except Exception:
                        pass
            chg = None
            if len(closes) >= 6:
                a, b = closes[-6]["close"], closes[-1]["close"]
                if a:
                    chg = (b / a - 1.0) * 100.0
            out.append({
                "name": name,
                "secid": secid,
                "last_close": closes[-1]["close"] if closes else None,
                "week_chg_pct_approx": chg,
                "bars": len(closes),
            })
        except Exception as exc:
            out.append({"name": name, "secid": secid, "error": repr(exc)})
    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "market": "a_share",
        "indices": out,
        "disclaimer": "A股快照来自东财公开K线接口，非官方；仅供周报上下文。",
    }


def _fetch_a_share_stock_bars(code: str, limit: int = 60) -> Dict[str, Any]:
    """个股近 N 根日K摘要（东财直连）。"""
    from datetime import timedelta

    from backpack_quant_trading.core.a_share_strategy_import import (
        _eastmoney_secid,
        fetch_eastmoney_klines_daily,
    )

    start = datetime.now() - timedelta(days=max(120, limit * 3))
    bars, err = fetch_eastmoney_klines_daily(code, start)
    if err:
        return {"code": code, "error": err, "secid": _eastmoney_secid(code)}
    closes = []
    for b in (bars or [])[-limit:]:
        ts = b.get("timestamp")
        closes.append({
            "date": ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10],
            "open": b.get("open"),
            "close": b.get("close"),
            "high": b.get("high"),
            "low": b.get("low"),
            "volume": b.get("volume"),
        })
    chg_5d = chg_20d = chg_60d = None
    try:
        if len(closes) >= 6 and closes[-6].get("close"):
            chg_5d = (float(closes[-1]["close"]) / float(closes[-6]["close"]) - 1.0) * 100.0
        if len(closes) >= 21 and closes[-21].get("close"):
            chg_20d = (float(closes[-1]["close"]) / float(closes[-21]["close"]) - 1.0) * 100.0
        if len(closes) >= 2 and closes[0].get("close"):
            chg_60d = (float(closes[-1]["close"]) / float(closes[0]["close"]) - 1.0) * 100.0
    except Exception:
        pass
    return {
        "code": code,
        "secid": _eastmoney_secid(code),
        "last_close": closes[-1]["close"] if closes else None,
        "chg_5d_pct": chg_5d,
        "chg_20d_pct": chg_20d,
        "chg_60d_pct": chg_60d,
        "bars": len(closes),
        "recent_klines": closes[-30:],
    }


def _fetch_eastmoney_quote_snapshot(code: str) -> Dict[str, Any]:
    """东财实时估值字段（直连）。"""
    from backpack_quant_trading.core.a_share_strategy_import import _eastmoney_secid

    secid = _eastmoney_secid(code)
    if not secid:
        return {"error": "invalid_code"}
    try:
        r = _http_get_domestic(
            "https://push2.eastmoney.com/api/qt/stock/get",
            params={
                "secid": secid,
                "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f169,f170,f162,f163,f167,f116,f117,f46",
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            },
            retries=1,
        )
        r.raise_for_status()
        data = ((r.json() or {}).get("data") or {})
        def _div(v, n=100.0):
            try:
                return None if v in (None, "-", "") else float(v) / n
            except Exception:
                return None
        return {
            "source": "eastmoney_push2",
            "name": data.get("f58"),
            "price": _div(data.get("f43")),
            "pct_chg": _div(data.get("f170")),
            "pe_ttm": _div(data.get("f162"), 100.0) if data.get("f162") not in (None, "-") else None,
            "pb": _div(data.get("f167"), 100.0) if data.get("f167") not in (None, "-") else None,
            "total_mv": data.get("f116"),  # 元
            "circ_mv": data.get("f117"),
        }
    except Exception as exc:
        return {"source": "eastmoney_push2", "error": repr(exc)}


def _fetch_eastmoney_finance_rows(code: str) -> Dict[str, Any]:
    """东财业绩快报/主要指标（近几期）。"""
    c = str(code or "").strip()
    if not re.fullmatch(r"\d{6}", c):
        return {"error": "invalid_code"}
    try:
        # RPT_F10_FINANCE_MAINFINADATA 常见字段
        r = _http_get_domestic(
            "https://datacenter-web.eastmoney.com/api/data/v1/get",
            params={
                "reportName": "RPT_F10_FINANCE_MAINFINADATA",
                "columns": "ALL",
                "filter": f'(SECURITY_CODE="{c}")',
                "pageNumber": "1",
                "pageSize": "6",
                "sortTypes": "-1",
                "sortColumns": "REPORT_DATE",
                "source": "F10",
                "client": "WEB",
            },
            retries=1,
        )
        r.raise_for_status()
        rows = ((r.json() or {}).get("result") or {}).get("data") or []
        slim = []
        for row in rows[:6]:
            if not isinstance(row, dict):
                continue
            slim.append({
                "report_date": str(row.get("REPORT_DATE") or "")[:10],
                "revenue": row.get("TOTALOPERATEREVE") or row.get("OPERATE_INCOME"),
                "net_profit": row.get("PARENTNETPROFIT") or row.get("NETPROFIT"),
                "eps": row.get("BASIC_EPS") or row.get("EPSJB"),
                "roe": row.get("ROEJQ") or row.get("WEIGHTAVGROE"),
                "gross_margin": row.get("XSMLL") or row.get("GROSSPROFITMARGIN"),
            })
        return {"source": "eastmoney_f10_main", "rows": slim}
    except Exception as exc:
        return {"source": "eastmoney_f10_main", "error": repr(exc)}


def _fetch_ths_quote_fallback(code: str) -> Dict[str, Any]:
    """同花顺简况页兜底（解析失败则返回错误，不阻断主流程）。"""
    c = str(code or "").strip()
    if not re.fullmatch(r"\d{6}", c):
        return {"error": "invalid_code"}
    try:
        from backpack_quant_trading.core.a_share_strategy_import import _direct_get

        # 10=上证 33=深证近似：6开头上证
        market = "10" if c.startswith("6") else "33"
        url = f"https://d.10jqka.com.cn/v2/realhead/{market}_{c}/last.js"
        r = _direct_get(
            url,
            headers={
                "User-Agent": UA,
                "Referer": f"https://stockpage.10jqka.com.cn/{c}/",
            },
            timeout=12,
        )
        r.raise_for_status()
        text = r.text or ""
        # last.js 形如 quotebridge_v2_realhead_...({...});
        m = re.search(r"\((\{[\s\S]*\})\)\s*;?\s*$", text.strip())
        if not m:
            return {"source": "ths_realhead", "error": "parse_failed", "raw_head": text[:120]}
        payload = json.loads(m.group(1))
        items = payload.get("items") or payload
        if not isinstance(items, dict):
            return {"source": "ths_realhead", "error": "no_items"}
        return {
            "source": "ths_realhead",
            "price": items.get("10") or items.get("price"),
            "pct_chg": items.get("199112") or items.get("percent"),
            "pe": items.get("2034120") or items.get("pe"),
            "pb": items.get("2034122") or items.get("pb"),
            "name": items.get("name") or items.get("5"),
        }
    except Exception as exc:
        return {"source": "ths_realhead", "error": repr(exc)}


def _fetch_akshare_fundamentals(code: str) -> Dict[str, Any]:
    """复用 stock_ai 的东财资料+新浪财报摘要（若环境有 akshare）。"""
    out: Dict[str, Any] = {"source": "akshare_em_sina"}
    try:
        from backpack_quant_trading.core.stock_ai import (
            _get_basic_info_summary,
            _get_news_summary,
            _get_sina_financial_snippet,
        )

        basic = _get_basic_info_summary(code) or ""
        sina = _get_sina_financial_snippet(code) or ""
        news = _get_news_summary(code, max_items=6) or ""
        out["basic_summary"] = basic
        out["sina_finance"] = sina
        out["news_headlines"] = news
        if not basic and not sina:
            out["error"] = "empty"
    except Exception as exc:
        out["error"] = repr(exc)
    return out


def _build_stock_analysis_snapshot(code: str, name: str) -> Dict[str, Any]:
    """策略A/B · A股个股：多源行情+财务快照（东财/同花顺/新浪）。"""
    as_of = datetime.now().strftime("%Y-%m-%d")
    quote = _fetch_a_share_stock_bars(code)
    live_px, px_src = None, ""
    try:
        from backpack_quant_trading.core.research_card_prices import fetch_a_share_price

        live_px, px_src = fetch_a_share_price(code)
    except Exception as exc:
        px_src = f"live_price_error:{exc!r}"

    em_quote = _fetch_eastmoney_quote_snapshot(code)
    em_fin = _fetch_eastmoney_finance_rows(code)
    ths = _fetch_ths_quote_fallback(code)
    ak = _fetch_akshare_fundamentals(code)

    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of_date": as_of,
        "calendar_year": 2026,
        "market": "a_share",
        "symbol": code,
        "name": name,
        "currency": "CNY",
        "live_price": live_px,
        "live_price_source": px_src,
        "quote_klines": quote,
        "sources": {
            "eastmoney_quote": em_quote,
            "eastmoney_finance": em_fin,
            "ths_quote": ths,
            "akshare_em_sina": ak,
        },
        "note": (
            "多源快照：东财行情/财务主表、同花顺 realhead、新浪/东财基本面摘要。"
            "分析须优先引用 sources.*.report_date / 最新一期财务；当前年为 2026。"
        ),
    }


def _build_us_stock_analysis_snapshot(ticker: str, name: str) -> Dict[str, Any]:
    """策略A/B · 美股个股：Yahoo 日线 + 现价快照。"""
    as_of = datetime.now().strftime("%Y-%m-%d")
    series, yerr = _yahoo_series(ticker)
    bars = series[-40:] if series else []
    week = _week_like_return(series) if series else {}
    live_px, px_src, currency = None, "", "USD"
    try:
        from backpack_quant_trading.core.research_card_prices import fetch_yahoo_quote

        live_px, currency = fetch_yahoo_quote(ticker)
        px_src = "yahoo"
        currency = currency or "USD"
    except Exception as exc:
        px_src = f"yahoo_quote_error:{exc!r}"
        if bars:
            live_px = bars[-1].get("close")
            px_src = "yahoo_chart_last_close"
    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of_date": as_of,
        "calendar_year": 2026,
        "market": "us",
        "symbol": ticker,
        "name": name or ticker,
        "currency": currency or "USD",
        "live_price": live_px,
        "live_price_source": px_src,
        "quote_klines": {
            "bars": bars,
            "week_like_return": week,
            "error": yerr,
            "source": "yahoo_chart",
        },
        "sources": {
            "yahoo_chart": {
                "ticker": ticker,
                "bars_n": len(bars),
                "last": bars[-1] if bars else None,
                "error": yerr,
            },
        },
        "note": (
            "美股快照：Yahoo Finance 日线收盘与现价；财务/指引请结合 SEC 10-K/Q 与公司 IR。"
            "当前年为 2026；勿套用 A 股涨跌停/北向机制。"
        ),
    }


def _resolve_a_share_symbol(token: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """返回 (code, name, error)。"""
    raw = (token or "").strip()
    if not raw:
        return None, None, "请输入股票名称或6位代码"
    try:
        from backpack_quant_trading.agents.a_share_resolve import resolve_a_share_token

        hit = resolve_a_share_token(raw)
    except Exception as exc:
        return None, None, f"解析股票失败: {exc!r}"
    if not hit:
        return None, None, f"未识别股票「{raw}」，请换用6位代码或更完整名称"
    code, name = hit
    return code, name or code, None


_US_TICKER_ALIASES = {
    "英伟达": "NVDA",
    "苹果": "AAPL",
    "特斯拉": "TSLA",
    "微软": "MSFT",
    "谷歌": "GOOGL",
    "亚马逊": "AMZN",
    "META": "META",
    "博通": "AVGO",
    "台积电": "TSM",
}


def _resolve_us_stock_symbol(token: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """返回 (ticker, name, error)。Yahoo 不可达时仍接受合法 ticker，由快照标注数据缺失。"""
    raw = (token or "").strip()
    if not raw:
        return None, None, "请输入美股代码，如 NVDA"
    alias = _US_TICKER_ALIASES.get(raw) or _US_TICKER_ALIASES.get(raw.upper())
    ticker = (alias or raw).upper().lstrip("$")
    if not re.fullmatch(r"[A-Z]{1,5}(\.[A-Z])?", ticker):
        return None, None, f"美股代码格式无效「{raw}」"
    series, yerr = _yahoo_series(ticker)
    if not series and yerr and "解析失败" in (yerr or ""):
        return None, None, f"未识别美股「{ticker}」：{yerr}"
    # 网络失败时仍放行合法 ticker，分析阶段快照会带 error
    return ticker, ticker, None


def _resolve_stock_symbol(
    token: str,
    preferred_market: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """返回 (code, name, market, error)。自动识别 A股 / 美股。"""
    raw = (token or "").strip()
    if not raw:
        return None, None, None, "请输入股票名称或代码（A股如贵州茅台/600519，美股如 NVDA）"
    pref = normalize_market(preferred_market) if preferred_market else None

    # 已知美股中文别名优先
    if raw in _US_TICKER_ALIASES or raw.upper() in {k.upper() for k in _US_TICKER_ALIASES}:
        code, name, err = _resolve_us_stock_symbol(raw)
        if not err:
            return code, name, "us", None

    # 纯 ticker / 显式美股：不再回落 A股
    if pref == "us" or re.fullmatch(r"\$?[A-Za-z]{1,5}", raw):
        code, name, err = _resolve_us_stock_symbol(raw)
        if err:
            return None, None, None, err
        return code, name, "us", None

    # 6 位代码 / 中文名 / 显式 A股
    if pref == "a_share" or re.fullmatch(r"\d{6}", raw) or re.search(r"[\u4e00-\u9fff]", raw):
        code, name, err = _resolve_a_share_symbol(raw)
        if not err:
            return code, name, "a_share", None
        if pref == "a_share" or re.fullmatch(r"\d{6}", raw):
            return None, None, None, err

    code, name, err = _resolve_a_share_symbol(raw)
    if not err:
        return code, name, "a_share", None
    code, name, err2 = _resolve_us_stock_symbol(raw)
    if not err2:
        return code, name, "us", None
    return None, None, None, err or err2 or f"未识别标的「{raw}」"


def _build_user_prompt(
    snapshot: Dict[str, Any],
    holdings: Optional[List[Dict[str, Any]]] = None,
    extra: str = "",
    market: str = "us",
    strategy: str = "us",
    focus_code: Optional[str] = None,
    focus_name: Optional[str] = None,
) -> str:
    m = normalize_market(market)
    sid = normalize_strategy(strategy, m)
    rtype = get_report_type(sid, m)

    if is_stock_focus_report(rtype) and focus_code:
        return build_stock_strategy_user_prompt(
            focus_code,
            focus_name or focus_code,
            snapshot,
            extra,
            strategy=sid,
            market=m,
        )

    # 无个股时（周六全市场周报）强制泡沫周报输出格式，避免策略A的 L1-L7 模板串进来
    from backpack_quant_trading.core.bubble_weekly_prompts import A_SHARE_OUTPUT, US_OUTPUT

    holdings = holdings or []
    holdings_lines: List[str] = []
    if holdings:
        for h in holdings:
            holdings_lines.append(
                f"- {h.get('symbol','?')} | 方向={h.get('side','?')} | 仓位比例={h.get('weight','?')} | "
                f"成本={h.get('cost','?')} | 止损={h.get('stop','?')} | 目标={h.get('target','?')}"
            )
    else:
        holdings_lines.append("- 持仓未填写（仅给出宏观判断与三种情景计划）")

    if m == "a_share":
        if focus_code:
            label = f"{focus_name or focus_code}（{focus_code}）"
            watchlist = f"{label}；同主题对照股；上证/创业板/科创50作背景"
        else:
            watchlist = (
                "上证、深成、创业板、科创50、沪深300、中证1000、半导体、机器人、光模块、算力租赁相关龙头"
            )
        out_fmt = A_SHARE_OUTPUT if not focus_code else get_output_format(m, sid)
    else:
        watchlist = (
            "QQQ、SPY、IWM、SOXX、SMH、NVDA、AMD、AVGO、TSM、ASML、ANET、DELL、SMCI、"
            "ORCL、MSFT、GOOGL、AMZN、META、PLTR、SNOW、DDOG、MDB、NOW、CRM、TSLA"
        )
        out_fmt = US_OUTPUT

    snapshot_text = json.dumps(snapshot, ensure_ascii=False)
    if len(snapshot_text) > 28000:
        snapshot_text = snapshot_text[:28000] + "...(truncated)"

    focus_block = ""
    if m == "a_share" and focus_code:
        focus_block = build_stock_focus_block(focus_code, focus_name or focus_code) + "\n"

    strat_line = f"## 策略模板\n{sid}\n\n" if m == "a_share" and focus_code else ""

    return (
        f"## 市场\n{m}\n\n"
        f"{strat_line}"
        f"{focus_block}"
        f"## 用户持仓\n" + "\n".join(holdings_lines) + "\n\n"
        f"## 观察清单\n{watchlist}\n\n"
        f"## 额外说明\n{extra or '无'}\n\n"
        f"## 本周市场数据快照（JSON）\n"
        f"```json\n{snapshot_text}\n```\n\n"
        f"{out_fmt}"
    )


def _extract_balanced_object(text: str, start: int) -> Optional[str]:
    """从 text[start]=='{' 起截取括号平衡的 JSON 对象子串。"""
    if start < 0 or start >= len(text) or text[start] != "{":
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _extract_json_block(markdown: str) -> Dict[str, Any]:
    """从模型输出中提取结构化 JSON（优先含 report 字段的完整对象）。"""
    if not markdown:
        return {}
    candidates: List[str] = []
    # 1) 所有 ```json ... ``` 围栏
    for m in re.finditer(r"```(?:json)?\s*(\{)", markdown, flags=re.IGNORECASE):
        blob = _extract_balanced_object(markdown, m.start(1))
        if blob:
            candidates.append(blob)
    # 2) 全文从每个 '{' 尝试（取较长者优先）
    if not candidates:
        for i, ch in enumerate(markdown):
            if ch == "{":
                blob = _extract_balanced_object(markdown, i)
                if blob and len(blob) > 80:
                    candidates.append(blob)

    parsed: List[Dict[str, Any]] = []
    for blob in candidates:
        try:
            obj = json.loads(blob)
        except Exception:
            # 常见截断：尝试补全尾部括号（尽力而为）
            try:
                fixed = blob.rstrip()
                if not fixed.endswith("}"):
                    # 粗略补全
                    open_n = fixed.count("{") - fixed.count("}")
                    if open_n > 0:
                        fixed = fixed + ("}" * open_n)
                obj = json.loads(fixed)
            except Exception:
                continue
        if isinstance(obj, dict):
            parsed.append(obj)

    if not parsed:
        return {}
    # 优先带 report.top5_events / report.synthesis 的
    def _score(o: Dict[str, Any]) -> tuple:
        rep = o.get("report") if isinstance(o.get("report"), dict) else {}
        return (
            1 if rep.get("top5_events") else 0,
            1 if rep.get("synthesis") else 0,
            1 if rep.get("score_short") else 0,
            1 if "bubble_total_score" in o else 0,
            len(json.dumps(o, ensure_ascii=False)),
        )

    parsed.sort(key=_score, reverse=True)
    return parsed[0]

def _call_deepseek(
    snapshot: Dict[str, Any],
    holdings: Optional[List[Dict[str, Any]]] = None,
    extra: str = "",
    market: str = "us",
    strategy: str = "us",
    focus_code: Optional[str] = None,
    focus_name: Optional[str] = None,
) -> Dict[str, Any]:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return {"ok": False, "error": "未配置 DEEPSEEK_API_KEY"}

    m = normalize_market(market)
    sid = normalize_strategy(strategy, m)
    rtype = get_report_type(sid, m)
    is_stock = is_stock_focus_report(rtype) and bool(focus_code)

    user_prompt = _build_user_prompt(
        snapshot,
        holdings,
        extra,
        market=m,
        strategy=sid,
        focus_code=focus_code,
        focus_name=focus_name,
    )
    if is_stock:
        system_content = get_system_prompt(m, sid)
    elif m == "a_share" and not focus_code:
        from backpack_quant_trading.core.bubble_weekly_prompts import A_SHARE_SYSTEM
        system_content = A_SHARE_SYSTEM
    else:
        system_content = get_system_prompt(m, sid)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": os.getenv("DEEPSEEK_WEEKLY_MODEL", "deepseek-chat"),
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.25 if is_stock else 0.2,
        # 周报 JSON 卡片很大；4096 易截断 → 只有旧版 Markdown、无结构化卡片
        "max_tokens": 8192 if is_stock else int(os.getenv("DEEPSEEK_WEEKLY_MAX_TOKENS", "8192")),
    }
    try:
        r = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=300 if is_stock else 240,
            proxies=_resolve_proxies(),
        )
    except Exception as e:
        return {"ok": False, "error": f"DeepSeek 网络错误: {e!r}"}

    try:
        data = r.json()
    except Exception:
        return {"ok": False, "error": f"DeepSeek 返回非 JSON, status={r.status_code}"}

    if r.status_code != 200 or not data.get("choices"):
        err = data.get("error", {})
        if isinstance(err, dict):
            err = err.get("message", str(data))
        return {"ok": False, "error": f"DeepSeek 调用失败: {err}"}

    markdown = data["choices"][0]["message"]["content"] or ""
    if is_stock:
        return {
            "ok": True,
            "markdown": markdown,
            "structured": {},
            "report_type": rtype,
        }

    structured = _extract_json_block(markdown)
    report = structured.get("report") if isinstance(structured.get("report"), dict) else {}
    has_cards = bool(report.get("top5_events") or report.get("synthesis") or report.get("score_short"))
    if not has_cards:
        retry_user = (
            "上一次输出缺少可用的 report 结构化 JSON（前端无法渲染三层次判断/5件事/评分卡片）。\n"
            "请**只**输出一个完整 ```json ... ``` 代码块，必须含 report.top5_events（恰好5条）、"
            "report.synthesis（4条）、report.score_short/mid/long、report.scenarios（3条）、"
            "report.actions、report.watch_points、bubble_total_score 等。不要写长篇 Markdown。\n\n"
            f"参考上下文（可压缩使用）：\n{user_prompt[-6000:]}"
        )
        payload2 = {
            "model": payload["model"],
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": retry_user},
            ],
            "temperature": 0.1,
            "max_tokens": int(os.getenv("DEEPSEEK_WEEKLY_MAX_TOKENS", "8192")),
        }
        try:
            r2 = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload2,
                timeout=240,
                proxies=_resolve_proxies(),
            )
            data2 = r2.json()
            if r2.status_code == 200 and data2.get("choices"):
                md2 = data2["choices"][0]["message"]["content"] or ""
                st2 = _extract_json_block(md2)
                rep2 = st2.get("report") if isinstance(st2.get("report"), dict) else {}
                if rep2.get("top5_events") or rep2.get("synthesis") or rep2.get("score_short"):
                    markdown = md2
                    structured = st2
                    logger.info("[美股周报] DeepSeek 重试后已拿到结构化 report")
                else:
                    logger.warning("[美股周报] DeepSeek 重试仍无卡片字段 md_len=%s", len(md2))
        except Exception as e:
            logger.warning("[美股周报] DeepSeek 结构化重试失败: %s", e)

    return {
        "ok": True,
        "markdown": markdown,
        "structured": structured,
        "report_type": "bubble_weekly",
    }


# ─────────────────────────────────────────────────────────
# 分析接口 + 历史接口
# ─────────────────────────────────────────────────────────
class HoldingItem(BaseModel):
    symbol: str
    side: Optional[str] = "long"
    weight: Optional[float] = None
    cost: Optional[float] = None
    stop: Optional[float] = None
    target: Optional[float] = None


class AnalyzeRequest(BaseModel):
    holdings: Optional[List[HoldingItem]] = None
    extra: Optional[str] = ""
    force_refresh: Optional[bool] = False
    save: Optional[bool] = True
    market: Optional[str] = "us"  # us | a_share（个股分析时可由后端按代码重写）
    mode: Optional[str] = None  # weekly | stock；stock 时走策略A/B
    # 股票名称或代码（A股名称/6位；美股 ticker）；策略模板 id（A/B…）
    symbol: Optional[str] = None
    strategy: Optional[str] = "A"


def _stock_report_one_liner(md: str, name: Optional[str], code: Optional[str]) -> str:
    for line in (md or "").splitlines():
        t = line.strip().lstrip("#").strip()
        if t and len(t) > 6 and not t.startswith("```") and "L1" not in t[:20]:
            return t[:160]
    label = f"{name}（{code}）" if name and code else (name or code or "标的")
    return f"{label} · 供应链瓶颈深度报告"


def _do_analyze(
    holdings: Optional[List[Dict[str, Any]]],
    extra: str,
    force_refresh: bool,
    save: bool,
    market: str = "us",
    symbol: Optional[str] = None,
    strategy: Optional[str] = None,
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    m = normalize_market(market)
    mode_l = (mode or "").strip().lower()
    sym_raw = (symbol or "").strip()
    # 个股模式：显式 mode=stock，或传入策略A/B+标的
    want_stock = mode_l == "stock" or (bool(sym_raw) and is_stock_strategy(strategy or "A"))
    if mode_l == "stock" and not is_stock_strategy(strategy):
        strategy = strategy or "A"
    sid = normalize_strategy(strategy, m)
    focus_code: Optional[str] = None
    focus_name: Optional[str] = None

    if want_stock:
        if not is_stock_strategy(sid):
            sid = "A"
        meta = get_strategy_meta(sid, m)
        if not meta.get("enabled"):
            return {
                "ok": False,
                "error": f"策略 {sid} 尚未开放，请选用策略 A",
                "market": m,
                "strategy": sid,
            }
        if not sym_raw:
            return {
                "ok": False,
                "error": "请输入股票名称或代码（A股如贵州茅台/600519，美股如 NVDA）",
                "market": m,
                "strategy": sid,
            }
        code, name, resolved_m, resolve_err = _resolve_stock_symbol(
            sym_raw,
            preferred_market=m if mode_l != "stock" else None,
        )
        if resolve_err:
            return {
                "ok": False,
                "error": resolve_err,
                "market": m,
                "strategy": sid,
            }
        focus_code, focus_name = code, name
        m = resolved_m or m
    elif m == "a_share" and sym_raw:
        # 兼容旧路径：A股+symbol 但未标 stock mode
        code, name, resolve_err = _resolve_a_share_symbol(sym_raw)
        if resolve_err:
            return {
                "ok": False,
                "error": resolve_err,
                "market": m,
                "strategy": sid,
            }
        focus_code, focus_name = code, name
        if is_stock_strategy(sid):
            want_stock = True

    rtype = get_report_type(sid, m)
    is_stock_report = want_stock and is_stock_focus_report(rtype) and bool(focus_code)

    if is_stock_report:
        if m == "us":
            snapshot = _build_us_stock_analysis_snapshot(focus_code, focus_name or focus_code)
        else:
            snapshot = _build_stock_analysis_snapshot(focus_code, focus_name or focus_code)
    else:
        cache_key = f"snap:{m}"

        if m == "a_share":
            builder = _build_a_share_snapshot_payload
        else:
            builder = _build_snapshot_payload

        if force_refresh:
            snapshot = builder()
            with _CACHE_LOCK:
                _CACHE[cache_key] = {"data": snapshot, "ts": time.time()}
        else:
            with _CACHE_LOCK:
                slot = _CACHE.get(cache_key) or {}
                cached = slot.get("data")
                cached_age = time.time() - (slot.get("ts") or 0)
            if cached and cached_age < _CACHE_TTL_SEC:
                snapshot = cached
            else:
                snapshot = builder()
                with _CACHE_LOCK:
                    _CACHE[cache_key] = {"data": snapshot, "ts": time.time()}

        if m == "a_share" and focus_code:
            snapshot = dict(snapshot or {})
            snapshot["focus_stock"] = {
                "code": focus_code,
                "name": focus_name,
                "quote": _fetch_a_share_stock_bars(focus_code),
            }
            snapshot["strategy"] = sid

    ds = _call_deepseek(
        snapshot,
        holdings,
        extra,
        market=m,
        strategy=sid,
        focus_code=focus_code,
        focus_name=focus_name,
    )
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record: Dict[str, Any] = {
        "generated_at_utc": now_utc,
        "ok": ds.get("ok", False),
        "market": m,
        "strategy": sid,
        "symbol": focus_code,
        "stock_name": focus_name,
    }

    if not ds.get("ok"):
        record["error"] = ds.get("error")
        return record

    md = ds.get("markdown", "") or ""
    out_report_type = ds.get("report_type") or (rtype if is_stock_report else "bubble_weekly")

    if is_stock_focus_report(out_report_type):
        md = strip_disclaimer_markdown(md)
        one_liner = _stock_report_one_liner(md, focus_name, focus_code)
        strat_name = get_strategy_meta(sid, m).get("name") or f"策略{sid}"
        record.update({
            "report_type": out_report_type,
            "markdown": md,
            "one_liner": one_liner,
            "report_date": now_utc[:10],
            "report_label": f"{strat_name}·{focus_name or focus_code}（{focus_code}）",
        })
        if save:
            _history_append({
                "generated_at_utc": now_utc,
                "market": m,
                "strategy": sid,
                "report_type": out_report_type,
                "symbol": focus_code,
                "stock_name": focus_name,
                "report_date": record["report_date"],
                "report_label": record["report_label"],
                "one_liner": one_liner,
                "markdown": md,
            }, market=m)
        return record

    structured = ds.get("structured") or {}

    def _num(x: Any) -> Optional[float]:
        try:
            return float(x) if x is not None else None
        except Exception:
            return None

    score_f = _num(structured.get("bubble_total_score"))
    short_f = _num(structured.get("short_term_score"))
    mid_f = _num(structured.get("mid_term_score"))
    long_f = _num(structured.get("long_term_score"))
    if score_f is None and (short_f is not None or mid_f is not None or long_f is not None):
        score_f = sum(v for v in [short_f, mid_f, long_f] if v is not None)

    md = ds.get("markdown", "") or ""
    one_liner = (structured.get("one_liner") or "").strip() or (
        f"状态={structured.get('market_state') or '—'}；"
        f"阶段={structured.get('stage') or '—'}；"
        f"下周={structured.get('next_week_bias') or '—'}"
    )
    # 组装前端卡片 report（与历史 seed 周报同结构）
    report_obj = build_ui_report(structured, fallback_summary=one_liner)

    # 若顶层分数缺失，用 report 分段总分回填
    if short_f is None and report_obj.get("score_short_total") is not None:
        short_f = _num(report_obj.get("score_short_total"))
    if mid_f is None and report_obj.get("score_mid_total") is not None:
        mid_f = _num(report_obj.get("score_mid_total"))
    if long_f is None and report_obj.get("score_long_total") is not None:
        long_f = _num(report_obj.get("score_long_total"))
    if score_f is None and (short_f is not None or mid_f is not None or long_f is not None):
        score_f = sum(v for v in [short_f, mid_f, long_f] if v is not None)

    record.update({
        "report_type": "bubble_weekly",
        "markdown": md,
        "structured": structured,
        "report": report_obj,
        "one_liner": one_liner,
        "key_invalidation": structured.get("key_invalidation") or "",
        "bubble_total_score": score_f,
        "bubble_total_max": structured.get("bubble_total_max", 70),
        "short_term_score": short_f,
        "short_term_max": structured.get("short_term_max", 20),
        "mid_term_score": mid_f,
        "mid_term_max": structured.get("mid_term_max", 25),
        "long_term_score": long_f,
        "long_term_max": structured.get("long_term_max", 25),
        "stage": structured.get("stage"),
        "stage_probabilities": structured.get("stage_probabilities") or {},
        "market_state": structured.get("market_state"),
        "next_week_bias": structured.get("next_week_bias"),
        "short_term_bias": structured.get("short_term_bias"),
        "mid_term_bias": structured.get("mid_term_bias"),
        "analog_year": structured.get("analog_year"),
        "report_date": now_utc[:10],
        "report_label": (
            "美股周报"
            if m == "us"
            else (
                f"A股·策略{sid}·{focus_name or focus_code}"
                if focus_code
                else f"A股·策略{sid}"
            )
        ),
        "strategy": sid,
        "symbol": focus_code,
        "stock_name": focus_name,
    })

    if save:
        _history_append({
            "generated_at_utc": now_utc,
            "market": m,
            "strategy": sid,
            "report_type": "bubble_weekly",
            "symbol": focus_code,
            "stock_name": focus_name,
            "report_date": record["report_date"],
            "report_label": record["report_label"],
            "bubble_total_score": score_f,
            "bubble_total_max": record["bubble_total_max"],
            "short_term_score": short_f,
            "short_term_max": record["short_term_max"],
            "mid_term_score": mid_f,
            "mid_term_max": record["mid_term_max"],
            "long_term_score": long_f,
            "long_term_max": record["long_term_max"],
            "stage": record["stage"],
            "market_state": record["market_state"],
            "next_week_bias": record["next_week_bias"],
            "short_term_bias": record["short_term_bias"],
            "mid_term_bias": record["mid_term_bias"],
            "analog_year": record["analog_year"],
            "stage_probabilities": record["stage_probabilities"],
            "one_liner": one_liner,
            "key_invalidation": record.get("key_invalidation") or "",
            "markdown": record["markdown"],
            "report": report_obj,
        }, market=m)
    return record


@router.get("/strategies")
def list_strategies(
    user: Optional[dict] = Depends(get_current_user),
    market: str = Query("a_share", description="us | a_share"),
    mode: Optional[str] = Query(None, description="weekly | stock"),
) -> Dict[str, Any]:
    """策略模板：个股分析返回 A/B；市场周报返回对应周报模板。"""
    m = normalize_market(market)
    mode_l = (mode or "").strip().lower()
    # 游客仅可拉个股策略列表（mode=stock）
    require_login_unless(mode_l == "stock", user)
    if mode_l == "stock" or m == "a_share":
        return {"market": m, "mode": "stock", "items": list_a_share_strategies()}
    return {
        "market": m,
        "mode": "weekly",
        "items": [{"id": "us", "name": "美股周报", "enabled": True, "description": "美股泡沫阶段周报"}],
    }


@router.post("/analyze")
def analyze_now(
    req: AnalyzeRequest,
    user: Optional[dict] = Depends(get_current_user),
) -> Dict[str, Any]:
    """手动触发一次分析（调用 DeepSeek）。游客仅允许个股分析。"""
    mode_l = (req.mode or "").strip().lower()
    sym_raw = (req.symbol or "").strip()
    strategy = (req.strategy or "").strip()
    want_stock = mode_l == "stock" or (bool(sym_raw) and is_stock_strategy(strategy or "A"))
    require_login_unless(want_stock, user)
    holdings = [h.model_dump() if hasattr(h, "model_dump") else h.dict() for h in (req.holdings or [])]
    return _do_analyze(
        holdings,
        req.extra or "",
        bool(req.force_refresh),
        bool(req.save),
        market=req.market or "us",
        symbol=req.symbol,
        strategy=req.strategy,
        mode=req.mode,
    )


@router.get("/history")
def list_history(
    user: Optional[dict] = Depends(get_current_user),
    limit: int = Query(80, ge=1, le=200),
    market: str = Query("us", description="us | a_share"),
    strategy: Optional[str] = Query(None, description="A股策略模板 id，如 A"),
    symbol: Optional[str] = Query(None, description="过滤个股代码或名称"),
) -> Dict[str, Any]:
    m = normalize_market(market)
    sid_req = (strategy or "").strip()
    allow_guest = bool(sid_req and is_stock_strategy(sid_req))
    require_login_unless(allow_guest, user)
    items = _history_load(m)
    if sid_req and is_stock_strategy(sid_req):
        sid = normalize_strategy(sid_req, m)
        items = [
            x for x in items
            if is_stock_strategy(x.get("strategy") or "")
            and normalize_strategy(x.get("strategy") or "A", m) == sid
        ]
        sym_q = (symbol or "").strip()
        if sym_q:
            code, _, rm, err = _resolve_stock_symbol(sym_q, preferred_market=m)
            if not err and code:
                items = [x for x in items if (x.get("symbol") or "") == code]
            else:
                items = [
                    x for x in items
                    if sym_q in (x.get("symbol") or "")
                    or sym_q in (x.get("stock_name") or "")
                    or sym_q in (x.get("report_label") or "")
                ]
    elif m == "a_share":
        sid = normalize_strategy(strategy or "A", m)
        # 旧记录无 strategy 字段时视为策略 A
        items = [
            x for x in items
            if normalize_strategy(x.get("strategy") or "A", m) == sid
        ]
        sym_q = (symbol or "").strip()
        if sym_q:
            code, _, err = _resolve_a_share_symbol(sym_q)
            if not err and code:
                items = [x for x in items if (x.get("symbol") or "") == code]
            else:
                # 解析失败则按原文模糊匹配历史标签
                items = [
                    x for x in items
                    if sym_q in (x.get("symbol") or "")
                    or sym_q in (x.get("stock_name") or "")
                    or sym_q in (x.get("report_label") or "")
                ]
    else:
        # 市场周报：排除个股策略记录，避免与美股个股混槽
        items = [
            x for x in items
            if not is_stock_focus_report(x.get("report_type"))
            and not (x.get("symbol") and is_stock_strategy(x.get("strategy")))
        ]
    items = items[-limit:]
    series = [
        {
            "generated_at_utc": x.get("generated_at_utc"),
            "market": x.get("market") or m,
            "report_type": x.get("report_type") or (
                "stock_scorecard"
                if x.get("symbol") and normalize_strategy(x.get("strategy") or "A", m) == "B"
                else (
                    "stock_supply_chain"
                    if x.get("symbol") and normalize_strategy(x.get("strategy") or "A", m) == "A"
                    else "bubble_weekly"
                )
            ),
            "strategy": x.get("strategy") or ("A" if m == "a_share" else "us"),
            "symbol": x.get("symbol"),
            "stock_name": x.get("stock_name"),
            "report_date": x.get("report_date"),
            "report_label": x.get("report_label"),
            "bubble_total_score": x.get("bubble_total_score"),
            "bubble_total_max": x.get("bubble_total_max", 70),
            "short_term_score": x.get("short_term_score"),
            "short_term_max": x.get("short_term_max", 20),
            "mid_term_score": x.get("mid_term_score"),
            "mid_term_max": x.get("mid_term_max", 25),
            "long_term_score": x.get("long_term_score"),
            "long_term_max": x.get("long_term_max", 25),
            "stage": x.get("stage"),
            "market_state": x.get("market_state"),
            "next_week_bias": x.get("next_week_bias"),
            "short_term_bias": x.get("short_term_bias"),
            "mid_term_bias": x.get("mid_term_bias"),
            "analog_year": x.get("analog_year"),
            "one_liner": x.get("one_liner"),
            "is_seed": x.get("is_seed", False),
            "has_report": bool(x.get("report")) or len(x.get("markdown") or "") > 400,
        }
        for x in items
    ]
    return {
        "market": m,
        "strategy": normalize_strategy(strategy or "A", m) if m == "a_share" else "us",
        "stages": BUBBLE_STAGES,
        "count": len(series),
        "items": series,
    }


@router.get("/latest")
def latest_analysis(
    user: Optional[dict] = Depends(get_current_user),
    market: str = Query("us", description="us | a_share"),
    strategy: Optional[str] = Query(None, description="策略模板 id（个股 A/B）"),
    symbol: Optional[str] = Query(None, description="个股代码或名称"),
) -> Dict[str, Any]:
    m = normalize_market(market)
    sid_req = (strategy or "").strip()
    allow_guest = bool(sid_req and is_stock_strategy(sid_req))
    require_login_unless(allow_guest, user)
    items = _history_load(m)
    if strategy and is_stock_strategy(strategy):
        sid = normalize_strategy(strategy, m)
        items = [
            x for x in items
            if is_stock_strategy(x.get("strategy") or "")
            and normalize_strategy(x.get("strategy") or "A", m) == sid
        ]
        sym_q = (symbol or "").strip()
        if sym_q:
            code, _, _, err = _resolve_stock_symbol(sym_q, preferred_market=m)
            if not err and code:
                items = [x for x in items if (x.get("symbol") or "") == code]
    elif m == "a_share":
        sid = normalize_strategy(strategy or "A", m)
        items = [
            x for x in items
            if normalize_strategy(x.get("strategy") or "A", m) == sid
        ]
        sym_q = (symbol or "").strip()
        if sym_q:
            code, _, err = _resolve_a_share_symbol(sym_q)
            if not err and code:
                items = [x for x in items if (x.get("symbol") or "") == code]
    else:
        items = [
            x for x in items
            if not is_stock_focus_report(x.get("report_type"))
            and not (x.get("symbol") and is_stock_strategy(x.get("strategy")))
        ]
    if not items:
        return {"empty": True, "market": m}
    return items[-1]


@router.get("/report")
def get_report_by_id(
    user: Optional[dict] = Depends(get_current_user),
    id: str = Query(..., description="generated_at_utc 作为报告 ID"),
    market: str = Query("us", description="us | a_share"),
) -> Dict[str, Any]:
    """按 ID 取某一份完整周报。游客仅可读取个股报告。"""
    items = _history_load(market)
    for x in items:
        if (x.get("generated_at_utc") or "") == id:
            is_stock = is_stock_focus_report(x.get("report_type")) or (
                bool(x.get("symbol")) and is_stock_strategy(x.get("strategy") or "")
            )
            require_login_unless(is_stock, user)
            return x
    return {"empty": True, "error": "report not found"}


def run_weekly_analyze_task(market: str = "us") -> Dict[str, Any]:
    """由调度器 / 钉钉 Agent 调用：无 require_user 依赖，直接生成并落盘。"""
    m = normalize_market(market)
    label = "美股" if m == "us" else "A股"
    try:
        # 全市场周报：不走策略A个股模板（无 symbol 时强制泡沫周报提示词）
        return _do_analyze(
            holdings=None,
            extra=f"自动/指令生成（{label}泡沫阶段周报）",
            force_refresh=True,
            save=True,
            market=m,
            strategy=None,
            symbol=None,
        )
    except Exception as e:
        logger.exception("run_weekly_analyze_task(%s) 失败: %s", m, e)
        return {"ok": False, "error": repr(e), "market": m}


def run_stock_strategy_task(
    symbol: str,
    strategy: str = "A",
    extra: str = "",
    save: bool = False,
    market: Optional[str] = None,
) -> Dict[str, Any]:
    """钉钉 / 调度：生成个股策略报告（A股或美股）。钉钉默认 save=False。"""
    try:
        return _do_analyze(
            holdings=None,
            extra=extra or "钉钉指令生成（个股策略报告）",
            force_refresh=True,
            save=bool(save),
            market=market or "a_share",
            strategy=strategy or "A",
            symbol=symbol,
            mode="stock",
        )
    except Exception as e:
        logger.exception("run_stock_strategy_task(%s) 失败: %s", symbol, e)
        return {"ok": False, "error": repr(e), "market": market or "a_share", "symbol": symbol}


def strip_disclaimer_markdown(md: str) -> str:
    """去掉附注/免责声明章节。"""
    text = (md or "").strip()
    if not text:
        return ""
    lines = text.splitlines()
    out: List[str] = []
    skip = False
    for line in lines:
        t = line.strip()
        if re.search(r"(附注|数据溯源|免责声明)", t) and (
            t.startswith("#") or t.startswith("【") or re.match(r"^#{0,3}\s*【?附注", t)
            or "免责声明" == t or t.startswith("免责声明")
        ):
            skip = True
            continue
        if skip:
            if re.match(r"^#{1,3}\s+", t) or re.match(r"^【L?\d", t) or re.match(
                r"^[一二三四五六七八九十]+[、.]", t
            ):
                skip = False
            else:
                continue
        if skip:
            continue
        out.append(line)
    # 再滤掉独立「免责声明」短段
    cleaned = "\n".join(out)
    cleaned = re.sub(
        r"(?ms)^#{0,3}\s*免责声明\s*\n.*?(?=^#{1,3}\s|\Z)",
        "",
        cleaned,
    )
    return cleaned.strip()


def markdown_for_dingtalk(md: str, max_len: Optional[int] = None) -> str:
    """钉钉 Markdown 不支持表格：把 | 表 转成列表。默认不截断（完整报告）。"""
    text = strip_disclaimer_markdown(md)
    if not text:
        return ""
    lines = text.splitlines()
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("|") and "|" in stripped[1:]:
            rows: List[List[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if cells and all(re.fullmatch(r":?-{3,}:?", c or "") for c in cells):
                    i += 1
                    continue
                rows.append(cells)
                i += 1
            if rows:
                headers = rows[0]
                body = rows[1:] if len(rows) > 1 else []
                for r in body or rows:
                    parts = []
                    for j, cell in enumerate(r):
                        if not cell:
                            continue
                        label = headers[j] if j < len(headers) else f"列{j+1}"
                        if body:
                            parts.append(f"{label}：{cell}")
                        else:
                            parts.append(cell)
                    if parts:
                        out.append("- " + " ｜ ".join(parts))
                out.append("")
            continue
        out.append(line)
        i += 1
    result = "\n".join(out).strip()
    if max_len is not None and max_len > 0 and len(result) > max_len:
        result = result[:max_len] + "\n\n…（内容过长已截断）"
    return result


def split_dingtalk_markdown(md: str, chunk_size: int = 3500) -> List[str]:
    """按章节边界拆成多条钉钉消息，保证完整送达。"""
    text = markdown_for_dingtalk(md, max_len=None)
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    parts: List[str] = []
    buf: List[str] = []
    buf_len = 0
    for line in text.splitlines(keepends=True):
        is_heading = bool(re.match(r"^#{1,3}\s+", line.strip()) or re.match(r"^【", line.strip()))
        if buf and is_heading and buf_len + len(line) > chunk_size * 0.85:
            parts.append("".join(buf).strip())
            buf = [line]
            buf_len = len(line)
            continue
        if buf_len + len(line) > chunk_size and buf:
            parts.append("".join(buf).strip())
            buf = [line]
            buf_len = len(line)
        else:
            buf.append(line)
            buf_len += len(line)
    if buf:
        parts.append("".join(buf).strip())
    # 加分页脚注
    n = len(parts)
    if n > 1:
        parts = [f"{p}\n\n（第 {i}/{n} 段）" for i, p in enumerate(parts, 1) if p]
    return [p for p in parts if p]
