"""A股 AI 自适应策略 Agent：扫描、硬规则、基本面缓存、LLM 决策、回测采样。"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backpack_quant_trading.core.a_share_ai_agent_prompts import (
    BACKTEST_SYSTEM_ADDENDUM,
    BACKTEST_USER_HINT,
    SYSTEM_PROMPT,
)
from backpack_quant_trading.core.a_share_monitor import (
    BJ,
    INDEX_META,
    INTERVAL_LABEL,
    _a_share_symbol_prefix,
    _direct_session,
    _in_a_share_session,
    drop_forming_bar,
    fetch_index_klines,
    fetch_klines_for_interval,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
FUND_CACHE_PATH = DATA_DIR / "a_share_ai_fundamentals_cache.json"
PREFS_PATH = DATA_DIR / "a_share_ai_agent_prefs.json"
SIGNALS_PATH = DATA_DIR / "a_share_ai_agent_signals.json"
STYLE_DRAFT_PATH = DATA_DIR / "a_share_ai_agent_style_draft.json"
STYLE_ADDENDUM_PATH = DATA_DIR / "a_share_ai_agent_style_addendum.txt"

INTERVALS_ALLOWED = ("30", "60", "D")
FUND_TTL_SEC = 24 * 3600
FUND_PARTIAL_TTL_SEC = 20 * 60
FUND_EMPTY_TTL_SEC = 10 * 60

_instance_lock = threading.Lock()
_instance: Optional["AShareAIAdaptiveAgent"] = None
_user_stopped = False


def get_agent_instance() -> Optional["AShareAIAdaptiveAgent"]:
    return _instance


def set_agent_instance(svc: Optional["AShareAIAdaptiveAgent"]) -> None:
    global _instance
    with _instance_lock:
        _instance = svc


def mark_agent_user_stopped(v: bool) -> None:
    global _user_stopped
    _user_stopped = bool(v)


def agent_user_stopped() -> bool:
    return _user_stopped


def _now_bj() -> datetime:
    return datetime.now(tz=BJ)


def can_push_now(now: Optional[datetime] = None) -> bool:
    """交易时段内且未超过 15:00 才允许推送。"""
    dt = now or _now_bj()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    else:
        dt = dt.astimezone(BJ)
    if not _in_a_share_session(dt):
        return False
    # 超过 15:00 一律不推（含收盘宽限）
    close = dt.replace(hour=15, minute=0, second=0, microsecond=0)
    return dt < close


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save_json(path: Path, data: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_fundamentals_cache() -> Dict[str, Any]:
    return _load_json(FUND_CACHE_PATH, {})


def save_fundamentals_cache(cache: Dict[str, Any]) -> None:
    _save_json(FUND_CACHE_PATH, cache)


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        s = str(v).strip().replace(",", "").replace("%", "")
        if s in ("", "-", "--", "None", "nan", "NaN"):
            return None
        return float(s)
    except Exception:
        return None


_PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


def _akshare_call(fn):
    """
    国内东财/新浪接口：若本机代理不可达会失败。
    先按当前环境请求，失败则临时去掉代理重试一次。
    """
    try:
        return fn()
    except Exception as first:
        cleared = {}
        try:
            for k in _PROXY_ENV_KEYS:
                if k in os.environ:
                    cleared[k] = os.environ.pop(k)
            if not cleared:
                raise first
            return fn()
        except Exception:
            raise first
        finally:
            os.environ.update(cleared)


def _fundamentals_from_value_em(code: str) -> Dict[str, Any]:
    """东财估值序列 stock_value_em：PE(TTM)/市净率/PEG/市值（取最新一行）。"""
    out: Dict[str, Any] = {}
    try:
        import akshare as ak

        df = _akshare_call(lambda: ak.stock_value_em(symbol=code))
        if df is None or getattr(df, "empty", True):
            return out
        row = df.iloc[-1]
        cols = {str(c): c for c in df.columns}

        def _col(*names: str):
            for n in names:
                if n in cols:
                    return row[cols[n]]
            for c in df.columns:
                cs = str(c)
                if any(n in cs for n in names):
                    return row[c]
            return None

        out["pe"] = _to_float(_col("PE(TTM)", "PE（TTM）", "市盈率"))
        out["pe_static"] = _to_float(_col("PE(静)", "PE（静）"))
        out["pb"] = _to_float(_col("市净率", "PB"))
        out["peg"] = _to_float(_col("PEG值", "PEG"))
        out["ps"] = _to_float(_col("市销率"))
        mkt = _to_float(_col("总市值"))
        if mkt is not None:
            out["market_cap"] = mkt
            out["market_cap_yi"] = round(mkt / 1e8, 2)
        out["close"] = _to_float(_col("当日收盘价"))
        d = _col("数据日期")
        if d is not None:
            out["value_asof"] = str(d)[:10]
        out["_source_value_em"] = True
    except Exception as e:
        logger.debug("stock_value_em %s: %s", code, e)
    return out


def _fundamentals_from_individual_info(code: str) -> Dict[str, Any]:
    """东财个股资料 stock_individual_info_em：行业/ROE/增速等。"""
    out: Dict[str, Any] = {}
    try:
        import akshare as ak

        df = _akshare_call(lambda: ak.stock_individual_info_em(symbol=code))
        if df is None or getattr(df, "empty", True) or len(df.columns) < 2:
            return out
        key_col = "item" if "item" in df.columns else df.columns[0]
        val_col = "value" if "value" in df.columns else df.columns[1]
        kv = {str(k).strip(): v for k, v in zip(df[key_col].tolist(), df[val_col].tolist())}

        def _find(*keys: str):
            for k in keys:
                if k in kv:
                    return kv[k]
            for name, val in kv.items():
                if any(sub in name for sub in keys):
                    return val
            return None

        industry = _find("行业", "所属行业")
        if industry is not None:
            out["industry"] = str(industry).strip()[:40]
        pe = _to_float(_find("市盈率", "市盈率(TTM)", "市盈率-动态"))
        if pe is not None:
            out["pe"] = pe
        pb = _to_float(_find("市净率"))
        if pb is not None:
            out["pb"] = pb
        roe = _to_float(_find("ROE", "净资产收益率"))
        if roe is not None:
            out["roe"] = roe
        growth = _to_float(_find("净利润同比", "净利润增长率", "营收同比", "营业收入同比"))
        if growth is not None:
            out["revenue_growth"] = growth
        name = _find("股票简称", "简称")
        if name is not None:
            out["name"] = str(name).strip()
        out["_source_individual_info"] = True
    except Exception as e:
        logger.debug("stock_individual_info_em %s: %s", code, e)
    return out


def _fundamentals_from_tencent_quote(code: str) -> Dict[str, Any]:
    """腾讯行情：PE/PB/市值/简称（东财 push2 在部分网络会断连）。"""
    out: Dict[str, Any] = {}
    sym = _a_share_symbol_prefix(code)
    if not sym:
        return out
    try:
        r = _direct_session().get(
            f"https://qt.gtimg.cn/q={sym}",
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.qq.com/"},
            timeout=10,
            proxies={"http": None, "https": None},
        )
        r.raise_for_status()
        text = r.text or ""
        i = text.find('"')
        j = text.rfind('"')
        if i < 0 or j <= i:
            return out
        p = text[i + 1 : j].split("~")
        if len(p) < 47:
            return out
        name = str(p[1] or "").strip()
        if name:
            out["name"] = name
        out["pe"] = _to_float(p[39])
        out["pb"] = _to_float(p[46])
        yi = _to_float(p[45])
        if yi is not None:
            out["market_cap_yi"] = yi
            out["market_cap"] = yi * 1e8
        out["_source_tencent"] = True
    except Exception as e:
        logger.debug("tencent quote %s: %s", code, e)
    return out


def _fundamentals_from_eastmoney_f10(code: str) -> Dict[str, Any]:
    """东财 F10 主要指标：ROE、营收同比、报告期。"""
    out: Dict[str, Any] = {}
    c = str(code or "").strip().zfill(6)
    try:
        r = _direct_session().get(
            "https://datacenter-web.eastmoney.com/api/data/v1/get",
            params={
                "reportName": "RPT_F10_FINANCE_MAINFINADATA",
                "columns": "ALL",
                "filter": f'(SECURITY_CODE="{c}")',
                "pageNumber": "1",
                "pageSize": "1",
                "sortTypes": "-1",
                "sortColumns": "REPORT_DATE",
                "source": "F10",
                "client": "WEB",
            },
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"},
            timeout=15,
            proxies={"http": None, "https": None},
        )
        r.raise_for_status()
        rows = (((r.json() or {}).get("result") or {}).get("data") or [])
        if not rows or not isinstance(rows[0], dict):
            return out
        row = rows[0]
        out["roe"] = _to_float(row.get("ROEJQ") or row.get("WEIGHTAVGROE"))
        out["revenue_growth"] = _to_float(row.get("TOTALOPERATEREVETZ") or row.get("OI_YOYRATIO_PK"))
        rd = str(row.get("REPORT_DATE") or "")[:10]
        if rd:
            out["report_date"] = rd
        profit = _to_float(row.get("PARENTNETPROFIT"))
        reve = _to_float(row.get("TOTALOPERATEREVE"))
        if profit is not None:
            out["net_profit_yi"] = round(profit / 1e8, 2)
        if reve is not None:
            out["revenue_yi"] = round(reve / 1e8, 2)
        out["_source_f10"] = True
    except Exception as e:
        logger.debug("eastmoney f10 %s: %s", code, e)
    return out


def get_fundamentals(code: str, force: bool = False) -> Dict[str, Any]:
    """
    拉取 A 股关键基本面（多源）：
    1) stock_value_em —— PE(TTM)/PB/PEG/市值（较稳）
    2) stock_individual_info_em —— 行业/ROE/增速（东财，偶发代理失败）
    3) 新浪财报摘要 —— 营收/净利文本兜底
    结果缓存 24h（FUND_TTL_SEC）。
    """
    code = str(code or "").strip().zfill(6)
    cache = load_fundamentals_cache()
    hit = cache.get(code) or {}
    ts = float(hit.get("_ts") or 0)
    age = time.time() - ts
    core_ok = hit.get("pe") is not None or hit.get("pb") is not None
    extra_ok = hit.get("roe") is not None and hit.get("revenue_growth") is not None
    if not force and hit and ts:
        if core_ok and extra_ok and age < FUND_TTL_SEC:
            return hit
        if core_ok and not extra_ok and age < FUND_PARTIAL_TTL_SEC:
            return hit
        if not core_ok and age < FUND_EMPTY_TTL_SEC:
            return hit

    out: Dict[str, Any] = {
        "code": code,
        "name": None,
        "pe": None,
        "pe_static": None,
        "pb": None,
        "peg": None,
        "ps": None,
        "roe": None,
        "revenue_growth": None,
        "market_cap": None,
        "market_cap_yi": None,
        "industry": None,
        "report_date": None,
        "value_asof": None,
        "raw_text": "",
        "missing": [],
        "sources": [],
        "_ts": time.time(),
        "_fresh": True,
    }

    # 1) 估值序列（优先，不依赖 push2 个股详情）
    v1 = _fundamentals_from_value_em(code)
    for k, v in v1.items():
        if k.startswith("_"):
            continue
        if v is not None and (out.get(k) is None or out.get(k) == ""):
            out[k] = v
    if v1.get("_source_value_em"):
        out["sources"].append("eastmoney_value_em")

    # 2) 个股资料
    v2 = _fundamentals_from_individual_info(code)
    for k, v in v2.items():
        if k.startswith("_"):
            continue
        if v is not None and (out.get(k) is None or out.get(k) == ""):
            out[k] = v
    if v2.get("_source_individual_info"):
        out["sources"].append("eastmoney_individual_info")

    # 3) 腾讯估值（补 PE/PB）
    v3 = _fundamentals_from_tencent_quote(code)
    for k, v in v3.items():
        if k.startswith("_"):
            continue
        if v is not None and (out.get(k) is None or out.get(k) == ""):
            out[k] = v
    if v3.get("_source_tencent"):
        out["sources"].append("tencent_quote")

    # 4) F10 财务（ROE / 营收同比 / 报告期）
    v4 = _fundamentals_from_eastmoney_f10(code)
    for k, v in v4.items():
        if k.startswith("_"):
            continue
        if v is not None and (out.get(k) is None or out.get(k) == ""):
            out[k] = v
    if v4.get("_source_f10"):
        out["sources"].append("eastmoney_f10")

    # 5) 文本摘要 + 新浪财报（补行业/报告期）
    try:
        from backpack_quant_trading.core.stock_ai import _get_basic_info_summary, _get_sina_financial_snippet

        basic = _get_basic_info_summary(code) or ""
        fina = _get_sina_financial_snippet(code) or ""
        out["raw_text"] = f"{basic}\n{fina}".strip()[:4000]
        if fina:
            out["sources"].append("sina_financial")
        import re

        text = out["raw_text"]
        if out.get("pe") is None:
            m = re.search(r"市盈率[^\d\-]*([\d\.\-]+)", text)
            if m:
                out["pe"] = _to_float(m.group(1))
        if out.get("pb") is None:
            m = re.search(r"市净率[^\d\-]*([\d\.\-]+)", text)
            if m:
                out["pb"] = _to_float(m.group(1))
        if out.get("roe") is None:
            m = re.search(r"ROE[^\d\-]*([\d\.\-]+)", text, re.I)
            if m:
                out["roe"] = _to_float(m.group(1))
        if out.get("industry") is None:
            m = re.search(r"行业[:：]\s*([^\n|；;]+)", text)
            if m:
                out["industry"] = m.group(1).strip()[:40]
        if out.get("report_date") is None:
            m = re.search(r"最近报告期[:：]?\s*(20\d{2}[-/年]\d{1,2}([-/月]\d{1,2})?)", text)
            if m:
                out["report_date"] = m.group(1)
        if out.get("revenue_growth") is None:
            m = re.search(r"(?:营收|净利)[^\n]{0,12}?([\-\d\.]+)\s*%", text)
            if m:
                out["revenue_growth"] = _to_float(m.group(1))
    except Exception as e:
        logger.warning("fundamentals text fallback failed %s: %s", code, e)
        if not out.get("raw_text"):
            out["raw_text"] = f"基本面文本拉取失败: {e}"

    for key in ("pe", "pb", "roe", "revenue_growth", "industry"):
        if out.get(key) is None or out.get(key) == "":
            out["missing"].append(key)

    out["_fresh"] = bool(out.get("pe") is not None or out.get("pb") is not None or out.get("raw_text"))
    if not out["sources"]:
        out["sources"] = ["none"]
        out["_fresh"] = False

    present = []
    if out.get("name"):
        present.append(f"简称:{out['name']}")
    if out.get("industry"):
        present.append(f"行业:{out['industry']}")
    if out.get("pe") is not None:
        present.append(f"PE(TTM):{out['pe']}")
    if out.get("pb") is not None:
        present.append(f"PB:{out['pb']}")
    if out.get("peg") is not None:
        present.append(f"PEG:{out['peg']}")
    if out.get("roe") is not None:
        present.append(f"ROE:{out['roe']}%")
    if out.get("revenue_growth") is not None:
        present.append(f"营收同比%:{out['revenue_growth']}")
    if out.get("net_profit_yi") is not None:
        present.append(f"净利:{out['net_profit_yi']}亿")
    if out.get("revenue_yi") is not None:
        present.append(f"营收:{out['revenue_yi']}亿")
    if out.get("market_cap_yi") is not None:
        present.append(f"总市值:{out['market_cap_yi']}亿")
    if out.get("value_asof"):
        present.append(f"估值日期:{out['value_asof']}")
    if out.get("report_date"):
        present.append(f"报告期:{out['report_date']}")
    summary = "；".join(present)
    miss = out.get("missing") or []
    rules = []
    if summary:
        rules.append("已提供：" + summary)
    if miss:
        rules.append("仅以下字段未取到（禁止把已提供字段说成缺失）：" + ",".join(miss))
    else:
        rules.append("关键估值字段已齐，禁止写「PE/PB缺失」。")
    out["raw_text"] = ("\n".join(rules) + "\n" + (out.get("raw_text") or "")).strip()[:4000]

    cache[code] = out
    save_fundamentals_cache(cache)
    return out


def _bar_limit_status(bars: List[Dict[str, Any]], code: str) -> str:
    if not bars:
        return "unknown"
    last = bars[-1]
    try:
        o = float(last.get("open") or 0)
        c = float(last.get("close") or 0)
        if o <= 0:
            return "unknown"
        chg = (c - o) / o * 100.0
    except Exception:
        return "unknown"
    # 简易涨跌停判定（创业板/科创板 20%，主板约 10%）
    limit = 19.5 if code.startswith(("3", "68")) else 9.5
    if chg >= limit:
        return "limit_up"
    if chg <= -limit:
        return "limit_down"
    if chg >= limit * 0.85:
        return "near_limit_up"
    if chg <= -limit * 0.85:
        return "near_limit_down"
    return "normal"


def normalize_action(raw: Any) -> str:
    """把模型可能输出的中英文 action 归一到 buy/sell/hold。"""
    s = str(raw or "").strip().lower()
    if not s:
        return "hold"
    if s in ("buy", "sell", "hold"):
        return s
    # 常见中文 / 混写
    if any(k in s for k in ("买入", "建仓", "开多", "加仓", "buy")) and "不买" not in s and "别买" not in s:
        return "buy"
    if any(k in s for k in ("卖出", "减仓", "平仓", "开空", "sell")) and "不卖" not in s:
        return "sell"
    if any(k in s for k in ("观望", "持有", "不买", "空仓", "等待", "hold")):
        return "hold"
    return "hold"


def default_position_for_interval(interval: str) -> Dict[str, Any]:
    """
    未显式传入持仓时的默认假设。
    30 分钟：默认已有底仓且可卖，支持当日 buy/sell（卖的是底仓，不是今日刚买的仓）。
    60 分钟 / 日线：默认空仓观望，偏波段，不假设可日内冲进冲出。
    """
    iv = str(interval or "30")
    if iv == "30":
        return {
            "holding": True,
            "has_base_position": True,
            "sellable": True,
            "bought_today": False,
            "intraday_ok": True,
            "note": "默认有底仓且可卖；30分钟支持日内加减仓（当日可买可卖底仓）",
        }
    return {
        "holding": False,
        "has_base_position": False,
        "sellable": False,
        "bought_today": False,
        "intraday_ok": False,
        "note": "默认空仓；60分钟/日线偏波段，禁止当日买当日卖思维",
    }


def apply_hard_rules(
    decision: Dict[str, Any],
    *,
    limit_status: str,
    position: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    d = dict(decision or {})
    action = normalize_action(d.get("action"))
    d["action"] = action
    d["limit_status"] = limit_status
    d.setdefault("valid", True)
    d.setdefault("t1_blocked", False)

    if action == "buy" and limit_status in ("limit_up", "near_limit_up"):
        d["action"] = "hold"
        d["valid"] = False
        d["invalid_reason"] = "涨停/接近涨停，禁止买入信号"
    if action == "sell" and limit_status in ("limit_down", "near_limit_down"):
        d["action"] = "hold"
        d["valid"] = False
        d["invalid_reason"] = "跌停/接近跌停，禁止卖出信号"

    pos = position or {}
    # 仅当「今日买入且明确不可卖」时拦 sell；底仓 sellable=true 时允许当日卖出
    if action == "sell" and pos.get("bought_today") and not pos.get("sellable"):
        d["action"] = "hold"
        d["valid"] = False
        d["t1_blocked"] = True
        d["invalid_reason"] = "T+1：今日买入尚不可卖"
    if action == "sell" and not pos.get("holding") and not pos.get("sellable") and not pos.get("has_base_position"):
        d["action"] = "hold"
        d["valid"] = False
        d["invalid_reason"] = "无持仓/无可卖底仓，禁止卖出信号"

    ensure_decision_thesis(d)
    return d


def ensure_decision_thesis(d: Dict[str, Any], *, fallback: str = "") -> Dict[str, Any]:
    """每轮推送都必须有可复核分析理由（买入/不买入/卖出均同）。"""
    thesis = str(d.get("thesis") or "").strip()
    if thesis:
        return d
    action = str(d.get("action") or "hold").lower()
    inv = str(d.get("invalid_reason") or "").strip()
    risks = d.get("risk_notes") or []
    risk0 = ""
    if isinstance(risks, list) and risks:
        risk0 = str(risks[0])
    elif isinstance(risks, str):
        risk0 = risks
    if fallback:
        d["thesis"] = fallback[:400]
    elif inv:
        d["thesis"] = f"本轮结论为不买入/观望：{inv}"[:400]
    elif action == "buy":
        d["thesis"] = "本轮建议买入，但模型未返回详细 thesis；请结合量能与技术结构自行复核。"
    elif action == "sell":
        d["thesis"] = "本轮建议卖出，但模型未返回详细 thesis；请结合持仓与风控自行复核。"
    else:
        base = "本轮建议不买入/观望：未见满足赔率的技术买点，或量能不足以支持进攻。"
        d["thesis"] = (f"{base} {risk0}".strip())[:400]
    return d


def load_confirmed_prefs() -> Dict[str, Any]:
    return _load_json(PREFS_PATH, {"style_notes": [], "confirmed_at": None})


def load_style_draft() -> Dict[str, Any]:
    return _load_json(STYLE_DRAFT_PATH, {"pending": [], "updated_at": None})


def append_feedback_draft(text: str, meta: Optional[Dict[str, Any]] = None) -> None:
    draft = load_style_draft()
    pending = list(draft.get("pending") or [])
    pending.append(
        {
            "text": str(text or "").strip()[:2000],
            "meta": meta or {},
            "ts": _now_bj().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    draft["pending"] = pending[-200:]
    draft["updated_at"] = _now_bj().strftime("%Y-%m-%d %H:%M:%S")
    _save_json(STYLE_DRAFT_PATH, draft)

    try:
        from backpack_quant_trading.agents.memory import save_global_preference

        save_global_preference(
            f"[A股AI自适应点评] {text}",
            agent_id="a_share_ai_agent",
            staff_id=str((meta or {}).get("sender_id") or "dingtalk"),
        )
    except Exception as e:
        logger.debug("save_global_preference skip: %s", e)


def _rebuild_style_addendum(prefs: Dict[str, Any]) -> str:
    notes = prefs.get("style_notes") or []
    lines = [
        "# 人类纠偏风格（已确认生效，必须遵守，但仍不得违反硬规则）",
        "以下来自交易员对历史扫描结论的点评。若与「本轮只看技术金叉」冲突，以本附言与硬规则为准。",
    ]
    for n in notes[-30:]:
        t = str(n.get("text") or "").strip()
        if not t:
            continue
        meta = n.get("meta") or {}
        tag = ""
        if meta.get("code"):
            tag = f"[{meta.get('code')}/{meta.get('interval') or '?'}] "
        lines.append(f"- {tag}{t}")
    body = "\n".join(lines)
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        STYLE_ADDENDUM_PATH.write_text(body, encoding="utf-8")
    except Exception:
        pass
    return body


def load_style_addendum() -> str:
    try:
        if STYLE_ADDENDUM_PATH.is_file():
            return STYLE_ADDENDUM_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    prefs = load_confirmed_prefs()
    if prefs.get("style_notes"):
        return _rebuild_style_addendum(prefs)
    return ""


def confirm_style_prefs() -> Dict[str, Any]:
    """人工确认/刷新：把 draft pending 合并进正式 prefs，并重写提示词附言。"""
    draft = load_style_draft()
    prefs = load_confirmed_prefs()
    notes = list(prefs.get("style_notes") or [])
    for p in draft.get("pending") or []:
        t = str(p.get("text") or "").strip()
        if t:
            notes.append({"text": t, "ts": p.get("ts"), "meta": p.get("meta")})
    prefs["style_notes"] = notes[-100:]
    prefs["confirmed_at"] = _now_bj().strftime("%Y-%m-%d %H:%M:%S")
    _save_json(PREFS_PATH, prefs)
    _save_json(STYLE_DRAFT_PATH, {"pending": [], "updated_at": prefs["confirmed_at"]})
    _rebuild_style_addendum(prefs)
    return prefs


def _prefs_block() -> str:
    parts = []
    addendum = load_style_addendum()
    if addendum:
        parts.append(addendum)
    prefs = load_confirmed_prefs()
    notes = prefs.get("style_notes") or []
    if notes and not addendum:
        lines = ["# 已确认偏好"]
        for n in notes[-12:]:
            lines.append(f"- {n.get('text')}")
        parts.append("\n".join(lines))
    try:
        from backpack_quant_trading.core.agent_memory_store import query_memory

        hits = query_memory(
            "a_share_ai_feedback",
            "A股 买入 观望 量能 纠偏",
            n_results=5,
        )
        if hits:
            lines = ["# RAG 检索到的近期纠偏"]
            for h in hits:
                doc = (h.get("document") or h.get("text") or "")[:240]
                if doc:
                    lines.append(f"- {doc}")
            parts.append("\n".join(lines))
    except Exception:
        pass
    return "\n\n".join(parts) if parts else "（暂无已确认偏好）"


_index_bar_cache: Dict[str, Tuple[float, List[Dict[str, Any]], str]] = {}
_index_bar_lock = threading.Lock()
INDEX_BAR_TTL_SEC = 90.0


def index_keys_for_code(code: str) -> List[str]:
    """板块对应指数 + 沪深300 宽基。"""
    c = str(code or "").strip().zfill(6)
    if c.startswith("688"):
        keys = ["star50", "csi300"]
    elif c.startswith("300") or c.startswith("301"):
        keys = ["chinext", "csi300"]
    elif c.startswith(("6", "9")):
        keys = ["sh_composite", "csi300"]
    else:
        keys = ["sz_component", "csi300"]
    out: List[str] = []
    for k in keys:
        if k not in out and k in INDEX_META:
            out.append(k)
    return out


def _close_pct(bars: List[Dict[str, Any]], n: int) -> Optional[float]:
    if n < 1 or len(bars) < n + 1:
        return None
    try:
        a = float(bars[-(n + 1)].get("close") or 0)
        b = float(bars[-1].get("close") or 0)
    except (TypeError, ValueError):
        return None
    if a == 0:
        return None
    return round((b - a) / a * 100.0, 3)


def _session_pct(bars: List[Dict[str, Any]]) -> Optional[float]:
    if len(bars) < 2:
        return None
    last = bars[-1]
    try:
        last_ts = int(last.get("open_time") or 0)
        last_c = float(last.get("close") or 0)
        day = datetime.fromtimestamp(last_ts / 1000.0, tz=BJ).strftime("%Y-%m-%d")
    except Exception:
        return None
    first_open = None
    for b in bars:
        try:
            ts = int(b.get("open_time") or 0)
            d = datetime.fromtimestamp(ts / 1000.0, tz=BJ).strftime("%Y-%m-%d")
        except Exception:
            continue
        if d == day:
            first_open = float(b.get("open") or 0)
            break
    if not first_open or last_c == 0:
        return None
    return round((last_c - first_open) / first_open * 100.0, 3)


def _rs_threshold(interval: str) -> float:
    if interval == "D":
        return 1.2
    if interval == "60":
        return 0.5
    return 0.35


def _alignment_from_rs(rs: Optional[float], interval: str) -> str:
    if rs is None:
        return "unclear"
    if abs(rs) < _rs_threshold(interval):
        return "sync"
    return "lead" if rs > 0 else "lag"


def _bars_upto(bars: List[Dict[str, Any]], tms: Optional[int]) -> List[Dict[str, Any]]:
    if tms is None:
        return list(bars)
    return [b for b in bars if int(b.get("open_time") or 0) <= int(tms)]


def _fetch_index_bars_cached(index_key: str, interval: str, limit: int, *, use_cache: bool) -> Tuple[List[Dict[str, Any]], str]:
    cache_key = f"{index_key}|{interval}|{limit}"
    now = time.time()
    if use_cache:
        with _index_bar_lock:
            hit = _index_bar_cache.get(cache_key)
            if hit and now - hit[0] < INDEX_BAR_TTL_SEC:
                return hit[1], hit[2]
    bars, src = fetch_index_klines(index_key, interval, limit=limit)
    bars = drop_forming_bar(bars, interval)
    if use_cache and bars:
        with _index_bar_lock:
            _index_bar_cache[cache_key] = (now, bars, src)
    return bars, src


def _index_pack(index_key: str, bars: List[Dict[str, Any]], src: str) -> Dict[str, Any]:
    meta = INDEX_META.get(index_key) or {}
    last = bars[-1] if bars else {}
    return {
        "key": index_key,
        "name": meta.get("name") or index_key,
        "code": meta.get("code") or "",
        "source": src,
        "last_close": last.get("close"),
        "last_time": last.get("time_label") or last.get("open_time"),
        "ret_1": _close_pct(bars, 1),
        "ret_5": _close_pct(bars, 5),
        "ret_20": _close_pct(bars, 20),
        "session_ret": _session_pct(bars),
        "bars": _summarize_bars(bars, 12),
    }


def build_market_context(
    code: str,
    interval: str,
    stock_bars: List[Dict[str, Any]],
    *,
    as_of_ms: Optional[int] = None,
    use_cache: bool = True,
    index_bars_by_key: Optional[Dict[str, Tuple[List[Dict[str, Any]], str]]] = None,
) -> Dict[str, Any]:
    """个股相对板块指数 + 沪深300 的涨跌与超额收益。"""
    keys = index_keys_for_code(code)
    indexes: List[Dict[str, Any]] = []
    for k in keys:
        if index_bars_by_key is not None:
            raw, src = index_bars_by_key.get(k) or ([], "none")
        else:
            raw, src = _fetch_index_bars_cached(k, interval, 80, use_cache=use_cache)
        sliced = _bars_upto(raw, as_of_ms)
        if len(sliced) < 8:
            continue
        indexes.append(_index_pack(k, sliced, src))
    if not indexes:
        return {
            "ok": False,
            "error": "指数K线不足，无法计算相对强弱",
            "alignment_hint": "unclear",
            "note": "大盘指数拉取失败或K线不足，相对强弱暂无法计算。",
        }
    primary = indexes[0]
    stock_ret_1 = _close_pct(stock_bars, 1)
    stock_ret_5 = _close_pct(stock_bars, 5)
    stock_ret_20 = _close_pct(stock_bars, 20)
    stock_session = _session_pct(stock_bars)

    def _sub(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        return round(a - b, 3)

    rs_1 = _sub(stock_ret_1, primary.get("ret_1"))
    rs_5 = _sub(stock_ret_5, primary.get("ret_5"))
    rs_20 = _sub(stock_ret_20, primary.get("ret_20"))
    rs_session = _sub(stock_session, primary.get("session_ret"))
    rs_main = rs_5 if rs_5 is not None else rs_1
    alignment = _alignment_from_rs(rs_main, interval)
    pname = primary.get("name") or "指数"
    note = (
        f"对照{pname}：近1根个股{stock_ret_1}% / 指数{primary.get('ret_1')}%，超额{rs_1}pct；"
        f"近5根超额{rs_5}pct（lead=强于大盘，lag=弱于大盘，sync=同步）。"
    )
    return {
        "ok": True,
        "primary": primary.get("name"),
        "primary_code": primary.get("code"),
        "indexes": indexes,
        "stock": {
            "ret_1": stock_ret_1,
            "ret_5": stock_ret_5,
            "ret_20": stock_ret_20,
            "session_ret": stock_session,
        },
        "vs_primary": {
            "rs_1": rs_1,
            "rs_5": rs_5,
            "rs_20": rs_20,
            "rs_session": rs_session,
        },
        "alignment_hint": alignment,
        "note": note,
    }


def apply_market_vs_stock(decision: Dict[str, Any], market: Dict[str, Any]) -> Dict[str, Any]:
    """有大盘数据时禁止卡片再写「无大盘数据」。"""
    d = dict(decision or {})
    mvs = d.get("market_vs_stock")
    if not isinstance(mvs, dict):
        mvs = {}
        d["market_vs_stock"] = mvs
    else:
        mvs = dict(mvs)
        d["market_vs_stock"] = mvs
    if not market or not market.get("ok"):
        if not str(mvs.get("alignment") or "").strip():
            mvs["alignment"] = "unclear"
        if not str(mvs.get("note") or "").strip():
            mvs["note"] = str(market.get("note") or "无大盘数据，无法判断个股相对强弱")
        return d
    hint = str(market.get("alignment_hint") or "").strip()
    computed = str(market.get("note") or "").strip()
    note = str(mvs.get("note") or "")
    alignment = str(mvs.get("alignment") or "").strip().lower()
    missing_claim = any(x in note for x in ("无大盘", "没有大盘", "缺少大盘", "无法判断个股相对强弱"))
    if hint in ("lead", "lag", "sync") and (alignment not in ("lead", "lag", "sync") or missing_claim):
        mvs["alignment"] = hint
    if computed and (missing_claim or not note.strip() or alignment in ("", "unclear")):
        mvs["note"] = computed
    return d


def _market_for_llm(market: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(market, dict):
        return {"ok": False}
    if not market.get("ok"):
        return {"ok": False, "error": market.get("error"), "note": market.get("note")}
    slim_indexes = []
    for idx in market.get("indexes") or []:
        item = {k: v for k, v in idx.items() if k != "bars"}
        bars = idx.get("bars") or []
        item["recent"] = [{"t": b.get("t"), "c": b.get("c")} for b in bars[-8:]]
        slim_indexes.append(item)
    return {
        "ok": True,
        "primary": market.get("primary"),
        "primary_code": market.get("primary_code"),
        "indexes": slim_indexes,
        "stock": market.get("stock"),
        "vs_primary": market.get("vs_primary"),
        "alignment_hint": market.get("alignment_hint"),
        "note": market.get("note"),
        "instruction": "必须填写 market_vs_stock；禁止声称无大盘数据。",
    }


VOLUME_STATE_CN = {
    "expand": "放量",
    "shrink": "缩量",
    "neutral": "平量",
    "climax": "天量",
    "unclear": "量能不明",
}
VOLUME_DIV_CN = {
    "none": "无背离",
    "price_up_vol_down": "价涨量缩",
    "price_down_vol_up": "价跌量增",
    "other": "其它背离",
}
VOLUME_TRAP_CN = {
    "none": "低",
    "bull_trap": "诱多",
    "bear_trap": "诱空",
    "possible": "可能有",
}
MARKET_ALIGN_CN = {
    "lead": "强于大盘",
    "lag": "弱于大盘",
    "sync": "同步",
    "unclear": "不明",
}


def compute_volume_structure(bars: List[Dict[str, Any]]) -> Dict[str, Any]:
    """用成交量均量比 + 近几根价量方向，避免模型输出 expand 同时又写价涨量缩。"""
    if len(bars) < 10:
        return {
            "state": "unclear",
            "divergence": "other",
            "trap_risk": "possible",
            "vol_ratio": None,
            "note": "成交量样本不足",
        }
    vols = [float(b.get("volume") or 0) for b in bars]
    closes = [float(b.get("close") or 0) for b in bars]
    window = vols[-21:-1] if len(vols) >= 21 else vols[:-1]
    ma = sum(window) / max(len(window), 1)
    last = vols[-1]
    ratio = (last / ma) if ma > 0 else 1.0
    if ratio >= 2.0:
        state = "climax"
    elif ratio >= 1.25:
        state = "expand"
    elif ratio <= 0.7:
        state = "shrink"
    else:
        state = "neutral"

    div = "none"
    trap = "none"
    if len(closes) >= 4:
        px_chg = closes[-1] - closes[-4]
        v_prev = sum(vols[-4:-1]) / 3.0
        if px_chg > 0 and last < v_prev * 0.85:
            div = "price_up_vol_down"
            trap = "bull_trap" if ratio < 1.15 else "possible"
        elif px_chg < 0 and last > v_prev * 1.15:
            div = "price_down_vol_up"
            trap = "possible"

    note = f"近1根成交量是近20均量的 {ratio:.2f} 倍（{VOLUME_STATE_CN.get(state, state)}）"
    if div == "price_up_vol_down":
        note += "；近几根上涨时量能未同步放大，属价涨量缩，需防诱多"
    elif div == "price_down_vol_up":
        note += "；下跌放量，抛压较重"
    return {
        "state": state,
        "divergence": div,
        "trap_risk": trap,
        "vol_ratio": round(ratio, 3),
        "note": note,
    }


def apply_volume_structure(decision: Dict[str, Any], computed: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(decision or {})
    vs = dict(computed or {})
    d["volume_structure"] = {
        "state": vs.get("state") or "unclear",
        "divergence": vs.get("divergence") or "other",
        "trap_risk": vs.get("trap_risk") or "possible",
        "note": vs.get("note") or "",
        "vol_ratio": vs.get("vol_ratio"),
    }
    return d


def format_volume_cn(vol: Dict[str, Any]) -> str:
    if not isinstance(vol, dict):
        return "—"
    st = VOLUME_STATE_CN.get(str(vol.get("state") or ""), str(vol.get("state") or "—"))
    dv = VOLUME_DIV_CN.get(str(vol.get("divergence") or ""), str(vol.get("divergence") or "—"))
    tr = VOLUME_TRAP_CN.get(str(vol.get("trap_risk") or ""), str(vol.get("trap_risk") or "—"))
    note = str(vol.get("note") or "").strip()
    base = f"{st} · 背离：{dv} · 诱多/诱空：{tr}"
    return f"{base}（{note}）" if note else base


def fundamentals_brief(fund: Dict[str, Any]) -> str:
    if not isinstance(fund, dict):
        return "基本面暂不可用"
    parts = []

    def _n(key: str, label: str, suffix: str = "", nd: int = 2) -> None:
        v = fund.get(key)
        if v is None or v == "":
            return
        try:
            parts.append(f"{label} {float(v):.{nd}f}{suffix}")
        except (TypeError, ValueError):
            parts.append(f"{label} {v}{suffix}")

    if fund.get("industry"):
        parts.append(str(fund.get("industry")))
    _n("pe", "PE(TTM)", nd=1)
    _n("pb", "PB", nd=2)
    _n("roe", "ROE", "%", nd=2)
    _n("revenue_growth", "营收同比", "%", nd=1)
    _n("market_cap_yi", "市值", "亿", nd=1)
    if fund.get("report_date"):
        parts.append(f"报告期 {fund.get('report_date')}")
    miss = [x for x in (fund.get("missing") or []) if fund.get(x) is None]
    if miss and not parts:
        return "基本面暂不可用（" + ",".join(miss) + "）"
    if miss:
        parts.append("未覆盖:" + ",".join(miss))
    return " · ".join(parts) if parts else "基本面暂不可用"


def scrub_false_missing_fundamentals(decision: Dict[str, Any], fund: Dict[str, Any]) -> Dict[str, Any]:
    """有 PE/PB 时禁止卡片/理由再写「估值关键数据缺失」。"""
    d = dict(decision or {})
    pe, pb = fund.get("pe"), fund.get("pb")
    if pe is None and pb is None:
        return d
    bits = []
    try:
        if pe is not None:
            bits.append(f"PE(TTM) {float(pe):.1f}")
        if pb is not None:
            bits.append(f"PB {float(pb):.2f}")
        if fund.get("roe") is not None:
            bits.append(f"ROE {float(fund['roe']):.1f}%")
        if fund.get("revenue_growth") is not None:
            bits.append(f"营收同比 {float(fund['revenue_growth']):.1f}%")
    except (TypeError, ValueError):
        pass
    fact = "、".join(bits) or "估值字段已取到"

    def _fix(text: str) -> str:
        t = str(text or "")
        t = re.sub(r"PE/?PB[^。；\n]{0,24}缺失", f"估值可用（{fact}）", t)
        t = re.sub(r"(PE|市盈率|市净率)[、/]?(PB)?等?关键(数据|指标)缺失", f"估值可用（{fact}）", t)
        t = re.sub(r"基本面关键(数据|指标)缺失[^。；\n]{0,20}", f"估值可用（{fact}）", t)
        t = t.replace("无法进行有效估值", f"估值可用（{fact}）")
        t = t.replace("无法评估估值和成长性", f"估值可用（{fact}）")
        t = t.replace("无法评估估值。", f"估值可用（{fact}）。")
        t = t.replace("，无法评估。", "。")
        t = t.replace("无法评估。", f"估值可用（{fact}）。")
        return t

    d["thesis"] = _fix(d.get("thesis") or "")
    risks = d.get("risk_notes")
    if isinstance(risks, list):
        d["risk_notes"] = [_fix(x) for x in risks if str(x).strip()]
    elif isinstance(risks, str):
        d["risk_notes"] = [_fix(risks)]
    return d


def _summarize_bars(bars: List[Dict[str, Any]], n: int = 40) -> List[Dict[str, Any]]:
    out = []
    for b in bars[-n:]:
        out.append(
            {
                "t": b.get("open_time"),
                "o": b.get("open"),
                "h": b.get("high"),
                "l": b.get("low"),
                "c": b.get("close"),
                "v": b.get("volume"),
            }
        )
    return out


def decide_once(
    *,
    code: str,
    name: str = "",
    interval: str = "30",
    position: Optional[Dict[str, Any]] = None,
    push: bool = False,
) -> Dict[str, Any]:
    code = str(code or "").strip().zfill(6)
    interval = str(interval or "30")
    if interval not in INTERVALS_ALLOWED:
        raise ValueError(f"不支持的周期: {interval}")

    as_of = _now_bj().strftime("%Y-%m-%d %H:%M:%S")
    bars, src = fetch_klines_for_interval(code, interval, limit=120)
    bars = drop_forming_bar(bars, interval)
    if len(bars) < 30:
        result = {
            "ok": False,
            "error": f"K线不足({len(bars)})",
            "code": code,
            "name": name or code,
            "interval": interval,
            "interval_label": INTERVAL_LABEL.get(interval, interval),
            "as_of": as_of,
            "data_source": src,
            "decision": ensure_decision_thesis(
                {
                    "action": "hold",
                    "valid": False,
                    "invalid_reason": f"K线不足({len(bars)})，本轮无法给出买点",
                    "confidence": 0.0,
                    "thesis": "",
                    "risk_notes": ["数据不足，仅作扫描占位推送"],
                },
                fallback=f"本轮扫描完成但数据不足（K线仅{len(bars)}根），结论：不买入/观望。",
            ),
        }
        _maybe_push_scan_result(result, push=push)
        return result

    fund = get_fundamentals(code)
    limit_status = _bar_limit_status(bars, code)
    last_ms = int(bars[-1].get("open_time") or 0) if bars else None
    market = build_market_context(code, interval, bars, as_of_ms=last_ms, use_cache=True)
    vol_hint = compute_volume_structure(bars)
    pos = position if position is not None else default_position_for_interval(interval)

    user_payload = {
        "universe": {"code": code, "name": name or code, "market": "A"},
        "timeframe": interval,
        "as_of": as_of,
        "bars": _summarize_bars(bars),
        "market": _market_for_llm(market),
        "volume_hint": vol_hint,
        "fundamentals": {k: v for k, v in fund.items() if not str(k).startswith("_")},
        "fundamentals_raw": (fund.get("raw_text") or "")[:2500],
        "position": pos,
        "rag_prefs": _prefs_block(),
        "limit_hint": limit_status,
        "data_source": src,
    }
    tf_hint = ""
    if interval == "30":
        tf_hint = (
            "本轮为 30 分钟周期：默认已有底仓且 sellable=true，支持日内加减仓；"
            "当日可 buy 也可 sell（卖的是底仓）。不要机械几天才给一次买卖信号。\n"
        )
    user_prompt = (
        "请根据以下输入给出决策 JSON。"
        "无论 action 是 buy/sell/hold，都必须填写可复核的 thesis。\n"
        "决策以技术面（量能→其它技术）为主；基本面仅参考。"
        "监控标的默认基本面无重大问题：不得用 PE/PB/增速「一般或偏高」否决技术买点；"
        "仅当有重大利空（新闻/财报暴雷/监管等）才可因基本面否决 buy。\n"
        + tf_hint
        + "若 market.ok=true，必须根据相对强弱填写 market_vs_stock（lead/lag/sync），禁止写「无大盘数据」。\n"
        "fundamentals 里已有数值的字段（如 PE/PB）禁止写成缺失。"
        "volume_structure 必须与 volume_hint 一致，thesis 里用中文解释量能（放量/缩量/价涨量缩），不要堆英文枚举。\n"
        + json.dumps(user_payload, ensure_ascii=False)[:14000]
    )

    from backpack_quant_trading.agents.analysts.base import call_analyst_llm

    llm = call_analyst_llm(SYSTEM_PROMPT, user_prompt)
    if not llm.get("ok"):
        err = str(llm.get("error") or "LLM失败")
        result = {
            "ok": False,
            "error": err,
            "code": code,
            "name": name or code,
            "interval": interval,
            "interval_label": INTERVAL_LABEL.get(interval, interval),
            "as_of": as_of,
            "data_source": src,
            "decision": ensure_decision_thesis(
                {
                    "action": "hold",
                    "valid": False,
                    "invalid_reason": err,
                    "confidence": 0.0,
                    "thesis": "",
                    "risk_notes": ["模型调用失败，本轮不买入"],
                },
                fallback=f"本轮扫描完成但模型分析失败（{err}），结论：不买入/观望。",
            ),
        }
        _maybe_push_scan_result(result, push=push)
        return result

    structured = apply_hard_rules(llm.get("structured") or {}, limit_status=limit_status, position=pos)
    structured = apply_market_vs_stock(structured, market)
    structured = apply_volume_structure(structured, vol_hint)
    structured = scrub_false_missing_fundamentals(structured, fund)
    fund_snap = {
        "pe": fund.get("pe"),
        "pb": fund.get("pb"),
        "roe": fund.get("roe"),
        "revenue_growth": fund.get("revenue_growth"),
        "market_cap_yi": fund.get("market_cap_yi"),
        "industry": fund.get("industry"),
        "report_date": fund.get("report_date"),
        "missing": fund.get("missing") or [],
        "brief": fundamentals_brief(fund),
    }
    result = {
        "ok": True,
        "code": code,
        "name": name or fund.get("name") or code,
        "interval": interval,
        "interval_label": INTERVAL_LABEL.get(interval, interval),
        "as_of": as_of,
        "data_source": src,
        "fundamentals": fund_snap,
        "market": {
            "ok": bool(market.get("ok")),
            "primary": market.get("primary"),
            "alignment_hint": market.get("alignment_hint"),
            "vs_primary": market.get("vs_primary"),
            "note": market.get("note"),
        },
        "decision": structured,
        "model": llm.get("model"),
    }

    # 落盘信号
    try:
        hist = _load_json(SIGNALS_PATH, {"items": []})
        items = list(hist.get("items") or [])
        items.insert(0, result)
        hist["items"] = items[:200]
        _save_json(SIGNALS_PATH, hist)
    except Exception:
        pass

    # 每轮扫描（买入/不买入/卖出）都必须推钉钉，且带分析理由
    _maybe_push_scan_result(result, push=push)
    return result


def _maybe_push_scan_result(result: Dict[str, Any], *, push: bool) -> None:
    if not push:
        return
    d = result.get("decision")
    if not isinstance(d, dict):
        result["decision"] = ensure_decision_thesis({"action": "hold", "thesis": ""})
    else:
        ensure_decision_thesis(d)
    if can_push_now():
        try:
            from backpack_quant_trading.core.a_share_ai_agent_dingtalk import push_signal_action_card

            ok, msg = push_signal_action_card(result)
            result["dingtalk_ok"] = ok
            result["dingtalk_msg"] = msg
        except Exception as e:
            result["dingtalk_ok"] = False
            result["dingtalk_msg"] = str(e)
    else:
        result["dingtalk_ok"] = False
        result["dingtalk_msg"] = "非推送窗口（休市或已过15:00）"


def compute_tape_stats(bars: List[Dict[str, Any]]) -> Dict[str, Any]:
    """回测用盘面摘要：回撤/涨跌，避免模型只盯着未来估值。"""
    closes = []
    for b in bars:
        try:
            closes.append(float(b.get("close") or 0))
        except (TypeError, ValueError):
            continue
    if len(closes) < 5:
        return {"ok": False, "buy_bias": False}
    last = closes[-1]
    high = max(closes)
    low = min(c for c in closes if c > 0) if any(c > 0 for c in closes) else last
    dd = ((last / high) - 1.0) * 100.0 if high > 0 else 0.0
    ret5 = ((last / closes[-6]) - 1.0) * 100.0 if len(closes) > 6 and closes[-6] else None
    ret20 = ((last / closes[-21]) - 1.0) * 100.0 if len(closes) > 21 and closes[-21] else None
    down = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] < closes[i - 1]:
            down += 1
        else:
            break
    buy_bias = bool(dd <= -18.0 or (ret20 is not None and ret20 <= -12.0) or down >= 4)
    return {
        "ok": True,
        "last": round(last, 4),
        "window_high": round(high, 4),
        "window_low": round(low, 4),
        "drawdown_from_high_pct": round(dd, 2),
        "ret_5_pct": None if ret5 is None else round(ret5, 2),
        "ret_20_pct": None if ret20 is None else round(ret20, 2),
        "consecutive_down": down,
        "buy_bias": buy_bias,
        "note": (
            f"相对窗口高点回撤 {dd:.1f}%"
            + ("；空仓应评估低吸，禁止用当前估值当 hold 理由" if buy_bias else "")
        ),
    }


def backtest_fundamentals_payload(fund: Dict[str, Any]) -> Dict[str, Any]:
    """回测不得把今日 PE/PB 当成历史估值。"""
    fund = fund or {}
    return {
        "mode": "backtest_no_lookahead",
        "name": fund.get("name"),
        "industry": fund.get("industry"),
        "note": "PE/PB/ROE/市值为今日快照，属于前视数据，禁止用来否决本时点买点。请只根据 bars/tape/volume_hint 决策。",
    }


def run_backtest(
    *,
    code: str,
    name: str = "",
    interval: str = "D",
    start: str = "",
    end: str = "",
    max_llm_calls: int = 60,
) -> Dict[str, Any]:
    """
    LLM 回测（采样 + 仓位状态机）：
    - 空仓只能开买；持仓后评估卖出；买卖成对，计算收益率。
    - 期末若仍持仓则按最后一根 K 线强平，保证可统计收益。
    """
    code = str(code or "").strip().zfill(6)
    interval = str(interval or "D")
    if interval not in INTERVALS_ALLOWED:
        raise ValueError(f"不支持的周期: {interval}")

    bars, src = fetch_klines_for_interval(code, interval, limit=320)
    bars = drop_forming_bar(bars, interval)

    def _ts(b: Dict[str, Any]) -> int:
        return int(b.get("open_time") or 0)

    def _px(b: Dict[str, Any]) -> float:
        return float(b.get("close") or 0)

    def _day_key(ms: int) -> str:
        try:
            return datetime.fromtimestamp(ms / 1000, tz=BJ).strftime("%Y-%m-%d")
        except Exception:
            return ""

    if start:
        try:
            st = datetime.strptime(start[:10], "%Y-%m-%d").replace(tzinfo=BJ)
            st_ms = int(st.timestamp() * 1000)
            bars = [b for b in bars if _ts(b) >= st_ms]
        except Exception:
            pass
    if end:
        try:
            ed = datetime.strptime(end[:10], "%Y-%m-%d").replace(tzinfo=BJ) + timedelta(days=1)
            ed_ms = int(ed.timestamp() * 1000)
            bars = [b for b in bars if _ts(b) < ed_ms]
        except Exception:
            pass

    if len(bars) > 260:
        bars = bars[-260:]

    if len(bars) < 40:
        return {"ok": False, "error": "区间 K 线不足（请放宽日期或换日线）", "bars": [], "markers": [], "trades": []}

    max_calls = max(3, min(int(max_llm_calls or 12), 40))
    usable = max(1, len(bars) - 35)
    step = max(1, (usable + max_calls - 1) // max_calls)
    markers: List[Dict[str, Any]] = []
    decisions: List[Dict[str, Any]] = []
    trades: List[Dict[str, Any]] = []
    fund = get_fundamentals(code)
    index_bars_by_key: Dict[str, Tuple[List[Dict[str, Any]], str]] = {}
    for k in index_keys_for_code(code):
        ib, isrc = fetch_index_klines(k, interval, limit=320)
        ib = drop_forming_bar(ib, interval)
        index_bars_by_key[k] = (ib, isrc)

    from backpack_quant_trading.agents.analysts.base import call_analyst_llm

    calls = 0
    llm_fail = 0
    action_counts = {"buy": 0, "sell": 0, "hold": 0}
    open_pos: Optional[Dict[str, Any]] = None

    sample_indices = list(range(35, len(bars), step))[:max_calls]
    # 保证最后一根也参与一次，便于评估是否卖出/强平
    last_i = len(bars) - 1
    if sample_indices and sample_indices[-1] != last_i:
        sample_indices.append(last_i)

    for i in sample_indices:
        if calls >= max_calls + 1:
            break
        window = bars[: i + 1]
        bar = window[-1]
        px = _px(bar)
        tms = _ts(bar)
        limit_status = _bar_limit_status(window, code)

        holding = open_pos is not None
        entry_px = float(open_pos["entry_price"]) if holding else None
        entry_t = int(open_pos["entry_time"]) if holding else None
        pnl_pct = None
        if holding and entry_px and entry_px > 0:
            pnl_pct = round((px - entry_px) / entry_px * 100.0, 3)
        # 日线：买入日与决策日不同即可卖；分钟线：同自然日不可卖（T+1 简化）
        bought_today = bool(holding and entry_t and _day_key(entry_t) == _day_key(tms))
        sellable = bool(holding and not bought_today)

        position = {
            "holding": holding,
            "entry_price": entry_px,
            "entry_time": datetime.fromtimestamp(entry_t / 1000, tz=BJ).strftime("%Y-%m-%d %H:%M:%S")
            if entry_t
            else None,
            "unrealized_pnl_pct": pnl_pct,
            "bought_today": bought_today,
            "sellable": sellable,
        }

        market = build_market_context(
            code,
            interval,
            window,
            as_of_ms=tms,
            use_cache=False,
            index_bars_by_key=index_bars_by_key,
        )
        tape = compute_tape_stats(window)
        vol_hint = compute_volume_structure(window)
        payload = {
            "universe": {"code": code, "name": name or code},
            "timeframe": interval,
            "as_of": datetime.fromtimestamp(tms / 1000, tz=BJ).strftime("%Y-%m-%d %H:%M:%S"),
            "bars": _summarize_bars(window, 40),
            "tape": tape,
            "market": _market_for_llm(market),
            "volume_hint": vol_hint,
            "fundamentals": backtest_fundamentals_payload(fund),
            "limit_hint": limit_status,
            "position": position,
            "backtest": True,
        }
        extra = ""
        if tape.get("buy_bias") and not holding:
            extra = "本时点 tape.buy_bias=true（深回撤或连跌），空仓应给出 buy，除非涨停买不进。\n"
        user_prompt = (
            f"{BACKTEST_USER_HINT}\n{extra}请根据以下输入给出决策 JSON。"
            "禁止写「无大盘数据」；禁止用当前 PE/PB 当 hold 理由。\n"
            + json.dumps(payload, ensure_ascii=False)[:12000]
        )
        llm = call_analyst_llm(SYSTEM_PROMPT + "\n" + BACKTEST_SYSTEM_ADDENDUM, user_prompt)
        calls += 1
        if not llm.get("ok"):
            llm_fail += 1
            continue

        raw_action = (llm.get("structured") or {}).get("action")
        d = apply_hard_rules(
            llm.get("structured") or {},
            limit_status=limit_status,
            position={"bought_today": bought_today, "sellable": sellable},
        )
        d = apply_market_vs_stock(d, market)
        action = str(d.get("action") or "hold")
        valid = bool(d.get("valid", True))

        # 仓位状态机：空仓只允许 buy；持仓只允许 sell/hold
        exec_action = "hold"
        if not holding:
            if action == "buy" and valid:
                exec_action = "buy"
            # 空仓 sell 无意义
        else:
            if action == "sell" and valid and sellable:
                exec_action = "sell"
            elif action == "buy":
                exec_action = "hold"  # 已持仓不再买

        action_counts[exec_action] = int(action_counts.get(exec_action) or 0) + 1
        decisions.append(
            {
                "i": i,
                "action": exec_action,
                "llm_action": action,
                "raw_action": raw_action,
                "valid": valid,
                "holding_before": holding,
                "thesis": (d.get("thesis") or "")[:200],
                "t": tms,
                "price": px,
                "unrealized_pnl_pct": pnl_pct,
            }
        )

        if exec_action == "buy":
            open_pos = {
                "entry_price": px,
                "entry_time": tms,
                "entry_index": i,
                "thesis": d.get("thesis") or "",
            }
            markers.append(
                {
                    "time": tms,
                    "price": px,
                    "side": "buy",
                    "thesis": d.get("thesis") or "",
                    "confidence": d.get("confidence"),
                }
            )
        elif exec_action == "sell" and open_pos:
            ep = float(open_pos["entry_price"])
            ret = ((px - ep) / ep * 100.0) if ep > 0 else 0.0
            trade = {
                "entry_time": open_pos["entry_time"],
                "exit_time": tms,
                "entry_price": ep,
                "exit_price": px,
                "return_pct": round(ret, 3),
                "bars_held": i - int(open_pos["entry_index"]),
                "entry_thesis": (open_pos.get("thesis") or "")[:160],
                "exit_thesis": (d.get("thesis") or "")[:160],
                "exit_reason": "signal",
            }
            trades.append(trade)
            markers.append(
                {
                    "time": tms,
                    "price": px,
                    "side": "sell",
                    "thesis": d.get("thesis") or "",
                    "confidence": d.get("confidence"),
                    "return_pct": trade["return_pct"],
                }
            )
            open_pos = None

    # 期末强平：保证买入有对应卖出，可算收益
    if open_pos is not None and bars:
        last = bars[-1]
        px = _px(last)
        tms = _ts(last)
        ep = float(open_pos["entry_price"])
        ret = ((px - ep) / ep * 100.0) if ep > 0 else 0.0
        trade = {
            "entry_time": open_pos["entry_time"],
            "exit_time": tms,
            "entry_price": ep,
            "exit_price": px,
            "return_pct": round(ret, 3),
            "bars_held": (len(bars) - 1) - int(open_pos["entry_index"]),
            "entry_thesis": (open_pos.get("thesis") or "")[:160],
            "exit_thesis": "回测区间结束，按收盘价强平",
            "exit_reason": "force_close",
        }
        trades.append(trade)
        markers.append(
            {
                "time": tms,
                "price": px,
                "side": "sell",
                "thesis": trade["exit_thesis"],
                "return_pct": trade["return_pct"],
                "force_close": True,
            }
        )
        action_counts["sell"] = int(action_counts.get("sell") or 0) + 1
        open_pos = None

    rets = [float(t["return_pct"]) for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    # 简单复利：连乘 (1+r)
    equity = 1.0
    for r in rets:
        equity *= 1.0 + r / 100.0
    summary = {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100.0, 2) if trades else 0.0,
        "avg_return_pct": round(sum(rets) / len(rets), 3) if rets else 0.0,
        "total_return_pct": round((equity - 1.0) * 100.0, 3),
        "max_win_pct": round(max(rets), 3) if rets else 0.0,
        "max_loss_pct": round(min(rets), 3) if rets else 0.0,
        "open_position": False,
    }

    return {
        "ok": True,
        "code": code,
        "name": name or code,
        "interval": interval,
        "data_source": src,
        "llm_calls": calls,
        "llm_fail": llm_fail,
        "sample_step": step,
        "action_counts": action_counts,
        "summary": summary,
        "trades": trades,
        "bars": [
            {
                "time": _ts(b),
                "open": float(b.get("open") or 0),
                "high": float(b.get("high") or 0),
                "low": float(b.get("low") or 0),
                "close": float(b.get("close") or 0),
                "volume": float(b.get("volume") or 0),
            }
            for b in bars
        ],
        "markers": markers,
        "decisions": decisions[-80:],
    }


class AShareAIAdaptiveAgent:
    """多任务扫描服务。"""

    def __init__(self, tasks: Optional[List[Dict[str, Any]]] = None):
        self.tasks: List[Dict[str, Any]] = list(tasks or [])
        self.running = False
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_fire: Dict[str, str] = {}  # key -> date-hour bucket
        self.last_error = ""
        self.last_scan_at = ""
        self.recent: List[Dict[str, Any]] = []

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self.running,
                "tasks": list(self.tasks),
                "task_count": len(self.tasks),
                "last_error": self.last_error,
                "last_scan_at": self.last_scan_at,
                "recent": list(self.recent)[:30],
            }

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="a-share-ai-agent", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.running = False
        self._stop.set()
        th = self._thread
        if th and th.is_alive() and th is not threading.current_thread():
            th.join(timeout=3.0)
        self._thread = None

    def remove_task(self, code: str, interval: str) -> bool:
        code = str(code).strip().zfill(6)
        interval = str(interval).strip()
        with self._lock:
            before = len(self.tasks)
            self.tasks = [
                t
                for t in self.tasks
                if not (str(t.get("code")) == code and str(t.get("interval")) == interval)
            ]
            return len(self.tasks) < before

    def _bucket(self, interval: str, now: datetime) -> str:
        if interval == "D":
            return now.strftime("%Y-%m-%d")
        # 30/60：按整点桶
        h = now.hour
        m = 0 if interval == "60" else (0 if now.minute < 30 else 30)
        if interval == "30":
            return now.strftime(f"%Y-%m-%d {h:02d}:{m:02d}")
        return now.strftime(f"%Y-%m-%d {h:02d}:00")

    def _loop(self) -> None:
        while not self._stop.is_set():
            now = _now_bj()
            if not _in_a_share_session(now):
                self._stop.wait(60)
                continue
            try:
                self._scan_tick(now)
            except Exception as e:
                self.last_error = str(e)
                logger.exception("a-share ai agent scan: %s", e)
            self._stop.wait(45)

    def _scan_tick(self, now: datetime) -> None:
        with self._lock:
            tasks = list(self.tasks)
        if not tasks:
            return
        self.last_scan_at = now.strftime("%Y-%m-%d %H:%M:%S")
        for t in tasks:
            code = str(t.get("code") or "").zfill(6)
            interval = str(t.get("interval") or "30")
            name = str(t.get("name") or "")
            key = f"{code}|{interval}"
            bucket = self._bucket(interval, now)
            # 日线：仅 14:50 后扫一次；分钟线：接近收盘桶末尾
            if interval == "D":
                if now.hour < 14 or (now.hour == 14 and now.minute < 50):
                    continue
            else:
                # 30m: :28-:29 / :58-:59；60m: :55-:59
                if interval == "30" and now.minute not in (28, 29, 58, 59):
                    continue
                if interval == "60" and now.minute < 55:
                    continue
            if self._last_fire.get(key) == bucket:
                continue
            # 过 15:00 不扫推
            if not can_push_now(now) and now.hour >= 15:
                continue
            try:
                res = decide_once(
                    code=code,
                    name=name,
                    interval=interval,
                    position=default_position_for_interval(interval),
                    push=True,
                )
                self._last_fire[key] = bucket
                with self._lock:
                    self.recent.insert(0, res)
                    self.recent = self.recent[:40]
                if not res.get("ok"):
                    self.last_error = str(res.get("error") or "")
            except Exception as e:
                self.last_error = str(e)
                logger.warning("decide_once %s: %s", key, e)


def restore_agent_from_db_if_needed() -> Optional[AShareAIAdaptiveAgent]:
    if agent_user_stopped():
        return None
    if get_agent_instance() and get_agent_instance().running:
        return get_agent_instance()
    try:
        from backpack_quant_trading.database.models import DatabaseManager

        row = DatabaseManager().get_a_share_ai_agent_config()
        if not row:
            return None
        cfg = json.loads(row)
        tasks = cfg.get("tasks") or []
        if not tasks:
            return None
        svc = AShareAIAdaptiveAgent(tasks=tasks)
        set_agent_instance(svc)
        svc.start()
        return svc
    except Exception as e:
        logger.warning("restore a_share_ai_agent failed: %s", e)
        return None
