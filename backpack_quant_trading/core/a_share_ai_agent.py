"""A股 AI 自适应策略 Agent：扫描、硬规则、基本面缓存、LLM 决策、回测采样。"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backpack_quant_trading.core.a_share_ai_agent_prompts import SYSTEM_PROMPT, BACKTEST_USER_HINT
from backpack_quant_trading.core.a_share_monitor import (
    BJ,
    INTERVAL_LABEL,
    _in_a_share_session,
    drop_forming_bar,
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


def get_fundamentals(code: str, force: bool = False) -> Dict[str, Any]:
    code = str(code or "").strip().zfill(6)
    cache = load_fundamentals_cache()
    hit = cache.get(code) or {}
    ts = float(hit.get("_ts") or 0)
    if not force and hit and (time.time() - ts) < FUND_TTL_SEC:
        return hit

    out: Dict[str, Any] = {
        "code": code,
        "pe": None,
        "pb": None,
        "revenue_growth": None,
        "roe": None,
        "industry": None,
        "report_date": None,
        "raw_text": "",
        "_ts": time.time(),
        "_fresh": True,
    }
    try:
        from backpack_quant_trading.core.stock_ai import _get_basic_info_summary, _get_sina_financial_snippet

        basic = _get_basic_info_summary(code) or ""
        fina = _get_sina_financial_snippet(code) or ""
        out["raw_text"] = f"{basic}\n{fina}".strip()[:4000]
        # 粗解析常见字段（容错）
        import re

        text = out["raw_text"]
        m = re.search(r"市盈率[^\d\-]*([\d\.\-]+)", text)
        if m:
            try:
                out["pe"] = float(m.group(1))
            except Exception:
                pass
        m = re.search(r"市净率[^\d\-]*([\d\.\-]+)", text)
        if m:
            try:
                out["pb"] = float(m.group(1))
            except Exception:
                pass
        m = re.search(r"ROE[^\d\-]*([\d\.\-]+)", text, re.I)
        if m:
            try:
                out["roe"] = float(m.group(1))
            except Exception:
                pass
        m = re.search(r"行业[:：]\s*([^\n|]+)", text)
        if m:
            out["industry"] = m.group(1).strip()[:40]
        m = re.search(r"(20\d{2}[-/年]\d{1,2}([-/月]\d{1,2})?)", text)
        if m:
            out["report_date"] = m.group(1)
        m = re.search(r"营收[^\n]{0,12}?([\-\d\.]+)\s*%", text)
        if m:
            try:
                out["revenue_growth"] = float(m.group(1))
            except Exception:
                pass
    except Exception as e:
        logger.warning("fundamentals fetch failed %s: %s", code, e)
        out["raw_text"] = f"基本面拉取失败: {e}"
        out["_fresh"] = False

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
    if action == "sell" and pos.get("bought_today") and not pos.get("sellable"):
        d["action"] = "hold"
        d["valid"] = False
        d["t1_blocked"] = True
        d["invalid_reason"] = "T+1：今日买入尚不可卖"

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
        d["thesis"] = "本轮建议买入，但模型未返回详细 thesis；请结合基本面与量能自行复核。"
    elif action == "sell":
        d["thesis"] = "本轮建议卖出，但模型未返回详细 thesis；请结合持仓与风控自行复核。"
    else:
        base = "本轮建议不买入/观望：未见满足赔率的买点，或量能/基本面不足以支持进攻。"
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

    user_payload = {
        "universe": {"code": code, "name": name or code, "market": "A"},
        "timeframe": interval,
        "as_of": as_of,
        "bars": _summarize_bars(bars),
        "fundamentals": {k: v for k, v in fund.items() if not str(k).startswith("_")},
        "fundamentals_raw": (fund.get("raw_text") or "")[:2500],
        "position": position or {"holding": False},
        "rag_prefs": _prefs_block(),
        "limit_hint": limit_status,
        "data_source": src,
    }
    user_prompt = (
        "请根据以下输入给出决策 JSON。"
        "无论 action 是 buy/sell/hold，都必须填写可复核的 thesis（不买入也要写清为什么）。\n"
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

    structured = apply_hard_rules(llm.get("structured") or {}, limit_status=limit_status, position=position)
    result = {
        "ok": True,
        "code": code,
        "name": name or code,
        "interval": interval,
        "interval_label": INTERVAL_LABEL.get(interval, interval),
        "as_of": as_of,
        "data_source": src,
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
    LLM 回测（采样）：在区间内对收盘 bar 采样调用 LLM，返回 K 线与买卖标注。
    最长建议 1 年；max_llm_calls 控制费用。
    """
    code = str(code or "").strip().zfill(6)
    interval = str(interval or "D")
    if interval not in INTERVALS_ALLOWED:
        raise ValueError(f"不支持的周期: {interval}")

    bars, src = fetch_klines_for_interval(code, interval, limit=320)
    bars = drop_forming_bar(bars, interval)

    def _ts(b: Dict[str, Any]) -> int:
        return int(b.get("open_time") or 0)

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

    # 最长约 1 年日线 ~250；分钟线截断
    if len(bars) > 260:
        bars = bars[-260:]

    if len(bars) < 40:
        return {"ok": False, "error": "区间 K 线不足（请放宽日期或换日线）", "bars": [], "markers": []}

    max_calls = max(3, min(int(max_llm_calls or 12), 40))
    # 采样：保证调用次数可控，避免一次回测卡死整站
    usable = max(1, len(bars) - 35)
    step = max(1, (usable + max_calls - 1) // max_calls)
    markers: List[Dict[str, Any]] = []
    decisions: List[Dict[str, Any]] = []
    fund = get_fundamentals(code)
    # 偏好只取一次：循环内反复查 RAG 会把回测拖成数十分钟
    prefs_once = _prefs_block()

    from backpack_quant_trading.agents.analysts.base import call_analyst_llm

    calls = 0
    llm_fail = 0
    action_counts = {"buy": 0, "sell": 0, "hold": 0}
    for i in range(35, len(bars), step):
        if calls >= max_calls:
            break
        window = bars[: i + 1]
        limit_status = _bar_limit_status(window, code)
        payload = {
            "universe": {"code": code, "name": name or code},
            "timeframe": interval,
            "as_of": datetime.fromtimestamp(_ts(window[-1]) / 1000, tz=BJ).strftime("%Y-%m-%d %H:%M:%S"),
            "bars": _summarize_bars(window, 40),
            "fundamentals": {k: v for k, v in fund.items() if not str(k).startswith("_")},
            "rag_prefs": prefs_once,
            "limit_hint": limit_status,
            "backtest": True,
        }
        user_prompt = (
            f"{BACKTEST_USER_HINT}\n请根据以下输入给出决策 JSON。\n"
            + json.dumps(payload, ensure_ascii=False)[:12000]
        )
        llm = call_analyst_llm(SYSTEM_PROMPT, user_prompt)
        calls += 1
        if not llm.get("ok"):
            llm_fail += 1
            continue
        raw_action = (llm.get("structured") or {}).get("action")
        d = apply_hard_rules(llm.get("structured") or {}, limit_status=limit_status)
        action = str(d.get("action") or "hold")
        action_counts[action] = int(action_counts.get(action) or 0) + 1
        decisions.append(
            {
                "i": i,
                "action": action,
                "raw_action": raw_action,
                "valid": d.get("valid", True),
                "thesis": (d.get("thesis") or "")[:200],
                "t": _ts(window[-1]),
                "price": float(window[-1].get("close") or 0),
            }
        )
        if action in ("buy", "sell") and d.get("valid", True):
            markers.append(
                {
                    "time": _ts(window[-1]),
                    "price": float(window[-1].get("close") or 0),
                    "side": action,
                    "thesis": d.get("thesis") or "",
                    "confidence": d.get("confidence"),
                }
            )

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
                res = decide_once(code=code, name=name, interval=interval, push=True)
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
