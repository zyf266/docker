"""分析师输出的支撑/压力贴价校准：保证最小有效距离，优先结构位。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _to_float(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _norm_tf(tf: str) -> str:
    t = (tf or "").strip().lower()
    if t.endswith("h") and t[:-1].isdigit():
        return f"{int(t[:-1])}h"
    if t in ("d", "1d", "day"):
        return "1d"
    if t.isdigit():
        # TradingView interval minutes
        m = int(t)
        if m >= 1440:
            return "1d"
        if m >= 240:
            return "4h"
        if m >= 120:
            return "2h"
        if m >= 60:
            return "1h"
        if m >= 30:
            return "30m"
        return "15m"
    return t or "4h"


def min_sr_dist_pct(interval: str, *, atr: Optional[float], close: float) -> float:
    """
    最小有效距离（百分比）：
    - 按周期抬地板（2h 至少约 2.5%）
    - 与 1.2×ATR% 取较大，避免波动大时仍贴价
    """
    tf = _norm_tf(interval)
    floor = {
        "15m": 1.8,
        "30m": 2.0,
        "1h": 2.2,
        "2h": 2.5,
        "4h": 3.0,
        "6h": 3.2,
        "12h": 3.5,
        "1d": 4.0,
        "1w": 6.0,
    }.get(tf, 2.5)
    atr_pct = 0.0
    if atr and close and close > 0:
        atr_pct = abs(float(atr)) / float(close) * 100.0
    return max(floor, 1.2 * atr_pct)


def _collect_candidates(metrics: Dict[str, Any], *, side: str) -> List[float]:
    out: List[float] = []
    key_list = "supports" if side == "support" else "resistances"
    for item in metrics.get(key_list) or []:
        if isinstance(item, dict):
            p = _to_float(item.get("price"))
        else:
            p = _to_float(item)
        if p is not None:
            out.append(p)
    for k in (
        "nearest_support" if side == "support" else "nearest_resistance",
        "nearest_resistance_same_tf" if side == "resistance" else "",
        "nearest_resistance_lower_tf" if side == "resistance" else "",
        "ema20",
        "ema50",
        "ema200",
    ):
        if not k:
            continue
        p = _to_float(metrics.get(k))
        if p is not None:
            out.append(p)
    return out


def _pick_level(
    close: float,
    *,
    side: str,
    min_pct: float,
    llm_val: Optional[float],
    candidates: List[float],
) -> Tuple[Optional[float], str]:
    """选距现价不少于 min_pct 的结构位；不够则回退到 close±min_pct。"""
    ratio = max(0.01, min_pct / 100.0)
    if side == "support":
        pool = [p for p in candidates if p < close * (1.0 - ratio * 0.98)]
        pool = sorted(set(round(p, 6) for p in pool), reverse=True)
        # 优先：刚好满足最小距离的最近结构位（不是无限远）
        if pool:
            # 在 [min_dist, ~2.2*min_dist] 窗口内优先
            band = [p for p in pool if (close - p) / close * 100 <= min_pct * 2.2]
            chosen = (band[0] if band else pool[0])
            return chosen, "structure"
        if llm_val is not None and llm_val < close * (1.0 - ratio):
            return float(llm_val), "llm"
        return round(close * (1.0 - ratio), 4), "floor"
    else:
        pool = [p for p in candidates if p > close * (1.0 + ratio * 0.98)]
        pool = sorted(set(round(p, 6) for p in pool))
        if pool:
            band = [p for p in pool if (p - close) / close * 100 <= min_pct * 2.2]
            chosen = (band[0] if band else pool[0])
            return chosen, "structure"
        if llm_val is not None and llm_val > close * (1.0 + ratio):
            return float(llm_val), "llm"
        return round(close * (1.0 + ratio), 4), "floor"


def calibrate_structured_sr(
    structured: Dict[str, Any],
    snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    """就地校准 structured 的 support/resistance/stop/target 文案。"""
    st = dict(structured or {})
    metrics = dict(snapshot.get("metrics") or {})
    close = _to_float(snapshot.get("last_close")) or _to_float(metrics.get("close"))
    if not close or close <= 0:
        return st

    interval = str(snapshot.get("interval") or metrics.get("sr_signal_timeframe") or "")
    atr = _to_float(metrics.get("atr14"))
    min_pct = min_sr_dist_pct(interval, atr=atr, close=close)

    llm_sup = _to_float(st.get("support"))
    llm_res = _to_float(st.get("resistance"))
    sup_cands = _collect_candidates(metrics, side="support")
    res_cands = _collect_candidates(metrics, side="resistance")
    if llm_sup is not None:
        sup_cands.append(llm_sup)
    if llm_res is not None:
        res_cands.append(llm_res)

    support, src_s = _pick_level(
        close, side="support", min_pct=min_pct, llm_val=llm_sup, candidates=sup_cands
    )
    resistance, src_r = _pick_level(
        close, side="resistance", min_pct=min_pct, llm_val=llm_res, candidates=res_cands
    )

    # 盈亏比过差时再拉开压力（至少 1.2× 支撑距离）
    if support is not None and resistance is not None:
        risk = close - support
        reward = resistance - close
        if risk > 0 and reward < risk * 1.2:
            resistance = round(close + risk * 1.5, 4)
            src_r = "rr_expand"

    st["support"] = support
    st["resistance"] = resistance
    st["sr_min_dist_pct"] = round(min_pct, 2)
    st["sr_calibrated"] = True
    st["sr_sources"] = {"support": src_s, "resistance": src_r}

    dist_s = (support - close) / close * 100 if support else 0
    dist_r = (resistance - close) / close * 100 if resistance else 0
    st["stop_hint"] = (
        f"止损参考：跌破结构支撑 {support}（距现价 {dist_s:+.2f}% / 最小有效距离≥{min_pct:.1f}%）下方。"
        if support is not None
        else st.get("stop_hint")
    )
    st["target_hint"] = (
        f"目标参考：第一目标结构压力 {resistance}（距现价 {dist_r:+.2f}%）；"
        f"若突破可看下一档更远结构位。"
        if resistance is not None
        else st.get("target_hint")
    )
    if support is not None and not str(st.get("invalidation") or "").strip():
        st["invalidation"] = f"收盘跌破 {support} 结构支撑则观点失效"
    return st


def format_sr_candidates_for_prompt(snapshot: Dict[str, Any]) -> str:
    metrics = dict(snapshot.get("metrics") or {})
    close = _to_float(snapshot.get("last_close")) or _to_float(metrics.get("close"))
    if not close:
        return ""
    interval = str(snapshot.get("interval") or "")
    atr = _to_float(metrics.get("atr14"))
    min_pct = min_sr_dist_pct(interval, atr=atr, close=close)
    lines = [
        f"## 结构位硬约束（必须遵守）",
        f"- last_close={close}，周期={interval or '—'}，ATR14={atr}",
        f"- support 距现价至少 -{min_pct:.1f}%；resistance 至少 +{min_pct:.1f}%",
        f"- 禁止把 ±1% 内的贴价噪声当作主支撑/压力；止损风险也不应显著小于该距离",
        f"- 优先使用下列候选（或同量级更远结构位）：",
    ]
    for p in _collect_candidates(metrics, side="support")[:5]:
        lines.append(f"  · 支撑候选 {p}（{(p - close) / close * 100:+.2f}%）")
    for p in _collect_candidates(metrics, side="resistance")[:5]:
        lines.append(f"  · 压力候选 {p}（{(p - close) / close * 100:+.2f}%）")
    return "\n".join(lines)
