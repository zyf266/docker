"""缓存最近推送的钉钉交易信号，供「回复 @ 评分」在钉钉未回传引用正文时兜底。"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

_CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "dingtalk_recent_signals.json"
_LOCK = threading.Lock()
_MAX_ITEMS = 40
_DEFAULT_TTL_SEC = 7200


def _parse_trigger_time_from_text(text: str) -> Optional[float]:
    clean = re.sub(r"\*+", "", text or "")
    m = re.search(r"触发时间[:：]\s*([0-9\-:\s]+)", clean)
    if not m:
        return None
    raw = m.group(1).strip()[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).timestamp()
        except ValueError:
            continue
    return None


def find_cached_signal_by_trigger_time(
    trigger_ts: float,
    *,
    window_sec: int = 180,
    max_age_sec: int = _DEFAULT_TTL_SEC,
) -> Optional[Dict[str, Any]]:
    """按卡片「触发时间」精确匹配（优于仅靠策略名）。"""
    if not trigger_ts:
        return None
    scored: list[tuple[float, Dict[str, Any]]] = []
    for row in list_recent_cached_signals(max_age_sec=max_age_sec):
        t = row.get("trigger_time")
        if t is None:
            t = _parse_trigger_time_from_text(str(row.get("raw_text") or ""))
        else:
            try:
                t = float(t)
            except (TypeError, ValueError):
                t = None
        if t is None:
            continue
        delta = abs(float(t) - float(trigger_ts))
        if delta > window_sec:
            continue
        scored.append((delta, row))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0])
    best_delta = scored[0][0]
    # 仅当多条信号触发时间几乎相同（≤0.5s）才视为歧义；相差 1s 取最近一条
    close = [row for d, row in scored if d <= best_delta + 0.5]
    symbols = {str(r.get("symbol") or "").upper() for r in close}
    if len(symbols) > 1:
        return None
    return dict(scored[0][1])


def _row_trigger_ts(row: Dict[str, Any]) -> Optional[float]:
    trig = row.get("trigger_time")
    if trig is None:
        return _parse_trigger_time_from_text(str(row.get("raw_text") or ""))
    try:
        return float(trig)
    except (TypeError, ValueError):
        return None


def _norm_action_hint(action: str) -> str:
    a = str(action or "").strip().lower()
    if a in ("buy", "sell"):
        return a
    if "买" in a or "多" in a:
        return "buy"
    if "卖" in a or "空" in a:
        return "sell"
    return a


def find_cached_signal_by_composite(
    *,
    trigger_ts: Optional[float] = None,
    replied_ts: Optional[float] = None,
    strategy_hint: str = "",
    action_hint: str = "",
    symbol_hint: str = "",
    max_age_sec: int = _DEFAULT_TTL_SEC,
) -> Optional[Dict[str, Any]]:
    """
    组合匹配：触发时间 + 被回复时间 + 策略名 + 方向 + 品种。
    用于钉钉话题/引用仅回传策略名、不带「交易品种」的场景。
    """
    sym_hint = str(symbol_hint or "").strip().upper().replace(".P", "")
    st_hint = _norm_hint_key(strategy_hint)
    act_hint = _norm_action_hint(action_hint)
    scored: list[tuple[float, Dict[str, Any]]] = []

    for row in list_recent_cached_signals(max_age_sec=max_age_sec):
        score = 0.0
        row_sym = str(row.get("symbol") or "").upper().replace(".P", "")
        if sym_hint and row_sym == sym_hint:
            score += 200.0

        row_trig = _row_trigger_ts(row)
        if trigger_ts and row_trig is not None:
            delta = abs(float(row_trig) - float(trigger_ts))
            if delta <= 2:
                score += 120.0 - delta * 10
            elif delta <= 90:
                score += max(0.0, 80.0 - delta)

        if replied_ts:
            refs: list[float] = []
            try:
                refs.append(float(row.get("at") or 0))
            except (TypeError, ValueError):
                pass
            if row_trig is not None:
                refs.append(float(row_trig))
            best = min((abs(r - replied_ts) for r in refs if r > 0), default=9999.0)
            if best <= 120:
                score += max(0.0, 90.0 - best)

        if st_hint:
            row_st = _norm_hint_key(str(row.get("strategy") or ""))
            if st_hint in row_st or row_st in st_hint:
                score += 55.0

        if act_hint:
            row_act = _norm_action_hint(str(row.get("action") or ""))
            if row_act == act_hint:
                score += 35.0

        if score >= 70.0:
            scored.append((score, row))

    if not scored:
        return None
    scored.sort(key=lambda x: (x[0], float(x[1].get("at") or 0)), reverse=True)
    best_score = scored[0][0]
    top = [row for s, row in scored if s >= best_score - 1.0]
    if len(top) >= 2:
        syms = {str(r.get("symbol") or "").upper() for r in top}
        if len(syms) > 1:
            # 分数接近时，用触发时间/推送时间与 replied_ts 的距离决胜
            if replied_ts or trigger_ts:
                def _time_dist(row: Dict[str, Any]) -> float:
                    refs: list[float] = []
                    rt = _row_trigger_ts(row)
                    if rt:
                        refs.append(float(rt))
                    try:
                        refs.append(float(row.get("at") or 0))
                    except (TypeError, ValueError):
                        pass
                    target = float(trigger_ts or replied_ts or 0)
                    return min((abs(r - target) for r in refs if r > 0), default=9999.0)

                top.sort(key=_time_dist)
                if len(top) >= 2 and abs(_time_dist(top[0]) - _time_dist(top[1])) < 0.5:
                    return None
                return dict(top[0])
            return None
    return dict(scored[0][1])


def _load() -> List[Dict[str, Any]]:
    if not _CACHE_PATH.is_file():
        return []
    try:
        data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        return list(data.get("items") or [])
    except Exception:
        return []


def _save(items: List[Dict[str, Any]]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(
        json.dumps({"items": items[-_MAX_ITEMS:]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def cache_dingtalk_signal(parsed: Dict[str, Any], *, source: str = "tradingview_bot") -> None:
    """推送钉钉成功后写入最近信号列表。"""
    symbol = str(parsed.get("symbol") or "").strip().upper().replace(".P", "")
    if not symbol or symbol == "未知品种":
        return
    action = str(parsed.get("signal") or parsed.get("action") or "").strip()
    entry = {
        "at": time.time(),
        "at_iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "symbol": symbol,
        "action": action,
        "timeframe": str(parsed.get("timeframe") or "").strip(),
        "strategy": str(parsed.get("strategy") or "").strip(),
        "price": parsed.get("price"),
        "raw_text": str(parsed.get("raw_message") or "")[:1500],
        "trigger_time": _parse_trigger_time_from_text(str(parsed.get("raw_message") or "")),
    }
    with _LOCK:
        items = _load()
        items.append(entry)
        _save(items)


def get_latest_cached_signal(*, max_age_sec: int = _DEFAULT_TTL_SEC) -> Optional[Dict[str, Any]]:
    now = time.time()
    with _LOCK:
        items = _load()
    for row in reversed(items):
        try:
            if now - float(row.get("at") or 0) <= max_age_sec:
                return dict(row)
        except (TypeError, ValueError):
            continue
    return None


def list_recent_cached_signals(*, max_age_sec: int = _DEFAULT_TTL_SEC) -> List[Dict[str, Any]]:
    now = time.time()
    with _LOCK:
        items = _load()
    out: List[Dict[str, Any]] = []
    for row in reversed(items):
        try:
            if now - float(row.get("at") or 0) <= max_age_sec:
                out.append(dict(row))
        except (TypeError, ValueError):
            continue
    return out


def find_cached_signal_by_symbol(
    symbol: str,
    *,
    max_age_sec: int = _DEFAULT_TTL_SEC,
) -> Optional[Dict[str, Any]]:
    sym = str(symbol or "").strip().upper().replace(".P", "")
    if not sym:
        return None
    if not sym.endswith(("USDT", "USDC")) and len(sym) <= 10:
        sym_usdt = f"{sym}USDT"
    else:
        sym_usdt = sym
    for row in list_recent_cached_signals(max_age_sec=max_age_sec):
        row_sym = str(row.get("symbol") or "").upper().replace(".P", "")
        if row_sym in (sym, sym_usdt):
            return row
    return None


def find_cached_signal_by_reply_time(
    replied_ts: float,
    *,
    window_sec: int = 900,
    max_age_sec: int = _DEFAULT_TTL_SEC,
) -> Optional[Dict[str, Any]]:
    """按被回复消息的发送时间，找时间最接近的一条缓存（优先 trigger_time；多品种同距则放弃）。"""
    if not replied_ts:
        return None
    scored: list[tuple[float, str, Dict[str, Any]]] = []
    for row in list_recent_cached_signals(max_age_sec=max_age_sec):
        candidates: list[float] = []
        try:
            candidates.append(float(row.get("at") or 0))
        except (TypeError, ValueError):
            pass
        trig = row.get("trigger_time")
        if trig is None:
            trig = _parse_trigger_time_from_text(str(row.get("raw_text") or ""))
        if trig is not None:
            try:
                candidates.append(float(trig))
            except (TypeError, ValueError):
                pass
        best_row_delta: Optional[float] = None
        for ref in candidates:
            if ref <= 0:
                continue
            delta = abs(ref - replied_ts)
            if delta > window_sec:
                continue
            if best_row_delta is None or delta < best_row_delta:
                best_row_delta = delta
        if best_row_delta is not None:
            sym = str(row.get("symbol") or "").upper()
            scored.append((best_row_delta, sym, row))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0])
    best_delta = scored[0][0]
    close = [(d, sym, row) for d, sym, row in scored if d <= best_delta + 30]
    symbols = {sym for _, sym, _ in close if sym}
    if len(symbols) > 1:
        return None
    return dict(close[0][2])


def _norm_hint_key(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").lower()).replace("信号", "")


def _score_hint_match(needle: str, row: Dict[str, Any]) -> int:
    needle_l = needle.lower()
    needle_core = re.sub(r"信号$", "", needle_l).strip()
    needle_norm = _norm_hint_key(needle_core)
    strategy = str(row.get("strategy") or "").lower()
    raw_text = str(row.get("raw_text") or "").lower()
    strategy_norm = _norm_hint_key(strategy)
    if needle_norm and (needle_norm in strategy_norm or strategy_norm in needle_norm):
        return 110 + len(needle_norm)
    if needle_core and needle_core in strategy:
        return 100 + len(needle_core)
    if needle_core and needle_core in raw_text:
        return 80 + len(needle_core)
    if needle_l in strategy or needle_l in raw_text:
        return 60
    return 0


def find_cached_signals_by_hint(
    hint: str,
    *,
    max_age_sec: int = _DEFAULT_TTL_SEC,
    min_score: int = 60,
) -> List[Dict[str, Any]]:
    """返回所有匹配该引用的缓存条目（按分数、时间倒序）。"""
    needle = (hint or "").strip()
    if not needle:
        return []
    scored: list[tuple[int, float, Dict[str, Any]]] = []
    for row in list_recent_cached_signals(max_age_sec=max_age_sec):
        score = _score_hint_match(needle, row)
        if score >= min_score:
            try:
                at = float(row.get("at") or 0)
            except (TypeError, ValueError):
                at = 0.0
            scored.append((score, at, row))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [row for _, _, row in scored]


def find_cached_signal_by_hint(
    hint: str,
    *,
    max_age_sec: int = _DEFAULT_TTL_SEC,
) -> Optional[Dict[str, Any]]:
    """按策略名/引用预览找唯一匹配；多品种同名策略时返回 None（由调用方提示歧义）。"""
    matches = find_cached_signals_by_hint(hint, max_age_sec=max_age_sec)
    if not matches:
        return None
    symbols = {str(m.get("symbol") or "").upper() for m in matches}
    if len(symbols) > 1:
        return None
    return dict(matches[0])


def cache_signal_count(*, max_age_sec: int = _DEFAULT_TTL_SEC) -> int:
    now = time.time()
    with _LOCK:
        items = _load()
    n = 0
    for row in items:
        try:
            if now - float(row.get("at") or 0) <= max_age_sec:
                n += 1
        except (TypeError, ValueError):
            continue
    return n
