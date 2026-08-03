"""A股分析师 Agent。"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from backpack_quant_trading.agents.analysts.base import run_analyst_pipeline
from backpack_quant_trading.agents.prompts import A_SHARE_ANALYST_SYSTEM
from backpack_quant_trading.agents.types import AgentId, AnalyzeReport, AnalyzeRequest, Market


def _normalize_code(symbol: str) -> str:
    code = (symbol or "").strip().upper()
    code = code.replace(".SH", "").replace(".SZ", "").replace("SH", "").replace("SZ", "")
    # 若误传入中文名，尝试解析
    if not code.isdigit():
        try:
            from backpack_quant_trading.agents.a_share_resolve import resolve_a_share_token

            hit = resolve_a_share_token(symbol)
            if hit:
                return hit[0]
        except Exception:
            pass
    return code


def _bars_from_eastmoney(code: str, lookback_days: int = 120) -> Tuple[List[Dict[str, Any]], str]:
    try:
        from backpack_quant_trading.core.a_share_strategy_import import fetch_eastmoney_klines_daily

        start = datetime.now() - timedelta(days=max(lookback_days + 30, 150))
        last_err = ""
        for _ in range(3):
            bars, err = fetch_eastmoney_klines_daily(code, start)
            if bars:
                recent = []
                for b in bars[-10:]:
                    recent.append({
                        "time": str(b.get("timestamp") or "")[:10],
                        "close": float(b.get("close") or 0),
                        "volume": float(b.get("volume") or 0),
                    })
                return recent if recent else [], ""
            last_err = err or "东方财富无日K"
        return [], last_err
    except Exception as exc:
        return [], str(exc)


def _bars_from_tencent(code: str, lookback_days: int = 120) -> Tuple[List[Dict[str, Any]], str]:
    """腾讯财经前复权日K（ECS 上东方财富常被断开时的兜底）。"""
    c = str(code or "").strip()
    if not c.isdigit() or len(c) != 6:
        return [], "无效代码"
    sym = f"sh{c}" if c.startswith("6") else f"sz{c}"
    try:
        import requests

        sess = requests.Session()
        sess.trust_env = False
        r = sess.get(
            "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
            params={"param": f"{sym},day,,,{int(lookback_days)},qfq"},
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.qq.com/"},
        )
        r.raise_for_status()
        data = ((r.json() or {}).get("data") or {}).get(sym) or {}
        rows = data.get("qfqday") or data.get("day") or []
        if not rows:
            return [], "腾讯无日K"
        recent = []
        for row in rows[-10:]:
            # [date, open, close, high, low, volume]
            if not isinstance(row, (list, tuple)) or len(row) < 6:
                continue
            recent.append({
                "time": str(row[0])[:10],
                "close": float(row[2]),
                "volume": float(row[5] or 0),
            })
        return recent, ""
    except Exception as exc:
        return [], str(exc)


def _bars_from_akshare(code: str, lookback_days: int = 120) -> Tuple[List[Dict[str, Any]], str]:
    try:
        import akshare as ak

        end = datetime.now()
        start = end - timedelta(days=max(lookback_days + 40, 180))
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )
        if df is None or getattr(df, "empty", True):
            return [], "akshare 无日K"
        col_map = {str(c): c for c in df.columns}
        date_c = col_map.get("日期") or col_map.get("date") or df.columns[0]
        close_c = col_map.get("收盘") or col_map.get("close")
        vol_c = col_map.get("成交量") or col_map.get("volume") or col_map.get("vol")
        if close_c is None:
            return [], "akshare 列缺失"
        recent = []
        for _, row in df.tail(10).iterrows():
            recent.append({
                "time": str(row.get(date_c) or "")[:10],
                "close": float(row.get(close_c) or 0),
                "volume": float(row.get(vol_c) or 0) if vol_c is not None else 0.0,
            })
        return recent, ""
    except Exception as exc:
        return [], str(exc)


def _snapshot(symbol: str, req: AnalyzeRequest) -> Tuple[Dict[str, Any], str]:
    code = _normalize_code(symbol)
    display = code
    try:
        from backpack_quant_trading.agents.a_share_resolve import resolve_a_share_token

        hit = resolve_a_share_token(symbol) or resolve_a_share_token(code)
        if hit:
            code, display = hit[0], f"{hit[1]}({hit[0]})"
    except Exception:
        pass

    recent: List[Dict[str, Any]] = []
    err = ""
    try:
        from backpack_quant_trading.core.stock_kline_cache import get_daily_klines_from_cache

        df = get_daily_klines_from_cache(code, lookback_days=120)
        if df is not None and not getattr(df, "empty", True):
            tail = df.tail(10)
            for _, row in tail.iterrows():
                recent.append({
                    "time": str(row.get("date") or "")[:10],
                    "close": float(row.get("close") or 0),
                    "volume": float(row.get("vol") or row.get("volume") or 0),
                })
    except Exception as exc:
        err = str(exc)

    if not recent:
        for fetcher in (_bars_from_tencent, _bars_from_eastmoney, _bars_from_akshare):
            bars, ferr = fetcher(code)
            if bars:
                recent = bars
                err = ""
                break
            err = err or ferr

    if not recent:
        return {
            "symbol": display,
            "code": code,
            "last_close": None,
            "metrics": {"note": err or "无A股K线，降级分析"},
            "recent_bars": [],
            "interval": "1d",
        }, err or "无A股K线"

    last = recent[-1]["close"]
    closes = [x["close"] for x in recent if x.get("close")]
    support = min(closes) if closes else last * 0.97
    resistance = max(closes) if closes else last * 1.03
    return {
        "symbol": display,
        "code": code,
        "last_close": last,
        "interval": "1d",
        "metrics": {
            "last_close": last,
            "close": last,
            "support_hint": support,
            "resistance_hint": resistance,
            "supports": [{"price": support, "timeframe": "1d", "label": "S1"}],
            "resistances": [{"price": resistance, "timeframe": "1d", "label": "R1"}],
            "bars": len(recent),
        },
        "recent_bars": recent,
    }, ""


def analyze(req: AnalyzeRequest) -> AnalyzeReport:
    req.market = Market.A_SHARE
    req.agent_id = AgentId.A_SHARE_ANALYST
    # 规范化 symbol 为 6 位代码，报告展示名由 snapshot.symbol 带回
    code = _normalize_code(req.symbol)
    if code and code != req.symbol:
        req.symbol = code
    return run_analyst_pipeline(
        req,
        agent_id=AgentId.A_SHARE_ANALYST,
        market=Market.A_SHARE,
        system_prompt=A_SHARE_ANALYST_SYSTEM,
        persona_hint="资深A股投研分析师（基本面+政策新闻重于技术）",
        snapshot_fn=_snapshot,
    )
