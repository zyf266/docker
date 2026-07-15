"""AI 信号评分：钉钉用户反馈学习（Chroma + hard_gates 阈值调整）。"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backpack_quant_trading.core.score_feedback_store import (
    chroma_enabled,
    count_feedbacks,
    query_similar,
    upsert_feedback,
)

logger = logging.getLogger(__name__)

_PREFERENCES_PATH = (
    __import__("pathlib").Path(__file__).resolve().parents[1] / "data" / "score_feedback_preferences.json"
)

_FEEDBACK_KEYWORDS = (
    "偏保守", "偏激进", "分低了", "分高了", "分太低", "分太高",
    "觉得", "应该", "纠正", "学习", "记住", "不太贴切", "不对",
    "轻仓", "试错", "太高了", "太低了", "不合理", "不同意",
    "评分有点", "评低了", "评高了",
)

_REC_MAP = {
    "execute": ("execute", "执行", "开仓", "买入", "做多"),
    "caution": ("caution", "观望", "谨慎", "轻仓", "试错", "试仓", "小仓"),
    "reject": ("reject", "拒绝", "不做", "不建议"),
}


def is_feedback_command(text: str) -> bool:
    plain = re.sub(r"@[^\s@　]+", " ", text or "", flags=re.IGNORECASE).strip()
    if len(plain) < 6:
        return False
    if not any(k in plain for k in _FEEDBACK_KEYWORDS):
        return False
    # 「评分有点偏保守」等是纠正，不是「重新评一下分」
    correction_hints = (
        "偏保守", "偏激进", "分低", "分高", "太低", "太高",
        "觉得", "应该", "轻仓", "试错", "纠正", "不合理", "不同意",
    )
    if any(h in plain for h in correction_hints):
        return True
    from backpack_quant_trading.core.dingtalk_manual_score import is_manual_score_command

    if is_manual_score_command(text):
        return False
    return True


def _f(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def parse_symbol_timeframe_from_text(text: str) -> Tuple[str, str]:
    plain = re.sub(r"@[^\s@　]+", " ", text or "", flags=re.IGNORECASE)
    sym = ""
    m = re.search(r"\b([A-Z]{1,5})\b(?:\s*(\d+[hHdDmMwW]))?", plain)
    if m:
        sym = m.group(1).upper()
        tf = (m.group(2) or "").strip()
        if tf:
            return sym, tf.lower()
    m2 = re.search(r"(\d+[hHdDmMwW])", plain)
    tf = m2.group(1).lower() if m2 else ""
    return sym, tf


def infer_desired_recommendation(text: str) -> str:
    plain = (text or "").lower()
    for rec, kws in _REC_MAP.items():
        if any(k in plain for k in kws):
            return rec
    if any(k in plain for k in ("偏保守", "分低", "评低", "太低")):
        return "caution"
    return "caution"


def infer_score_hint(text: str) -> Optional[int]:
    plain = text or ""
    for pat in (
        r"至少\s*(\d{2})\s*分",
        r"应该\s*(\d{2})\s*分",
        r"(\d{2})\s*分以上",
        r"给到\s*(\d{2})",
    ):
        m = re.search(pat, plain)
        if m:
            return int(m.group(1))
    return None


def build_gate_patch_from_feedback(text: str, metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """从用户自然语言反馈推导 hard_gates 补丁。"""
    plain = (text or "").lower()
    m = metrics or {}
    patch: Dict[str, Any] = {
        "clear_force_reject": False,
        "allow_trial_low_volume_rebound": False,
        "boost_execute_eligible": False,
        "min_vol_ratio_execute": None,
        "score_floor": None,
        "min_recommendation": infer_desired_recommendation(text),
    }
    score_hint = infer_score_hint(text)
    if score_hint is not None:
        patch["score_floor"] = score_hint

    if any(k in plain for k in ("偏保守", "分低", "评低", "太低", "不合理")):
        patch["clear_force_reject"] = True
        patch["score_floor"] = patch["score_floor"] or 50

    if any(k in plain for k in ("轻仓", "试错", "试仓", "小仓")):
        patch["allow_trial_low_volume_rebound"] = True
        patch["min_recommendation"] = "caution"
        patch["clear_force_reject"] = True
        patch["min_vol_ratio_execute"] = 0.30

    if "ema20" in plain or "站上" in plain:
        patch["pattern"] = patch.get("pattern") or {}
        patch["pattern"]["price_above_ema20"] = True
    if "macd" in plain and ("金叉" in plain or "gold" in plain):
        patch.setdefault("pattern", {})["macd_hist_rising"] = True
    if "量能" in plain and ("萎缩" in plain or "缩量" in plain):
        patch["allow_trial_low_volume_rebound"] = True
        patch.setdefault("pattern", {})["vol_ratio_max"] = 0.65
    if "反弹" in plain and ("强" in plain or "强劲" in plain):
        patch["allow_trial_low_volume_rebound"] = True
        patch["clear_force_reject"] = True

    if m:
        if m.get("price_above_ema20") and m.get("macd_hist_rising"):
            patch["allow_trial_low_volume_rebound"] = True
        if _f(m.get("vol_ratio"), 1.0) < 0.55 and (m.get("macd_hist_rising") or _f(m.get("macd_hist")) > 0):
            patch.setdefault("pattern", {})["vol_ratio_max"] = 0.60

    return patch


def _compact_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    m = metrics or {}
    keys = (
        "price_above_ema20", "price_above_ema50", "macd_hist", "macd_hist_rising",
        "rsi14", "adx14", "vol_ratio", "recent_change_pct", "trend_score",
        "uptrend_met", "strong_trend",
    )
    return {k: m.get(k) for k in keys if m.get(k) is not None}


def build_embedding_document(
    *,
    symbol: str,
    timeframe: str,
    action: str,
    user_text: str,
    original_score: Optional[int] = None,
    original_rec: str = "",
    metrics: Optional[Dict[str, Any]] = None,
) -> str:
    m = metrics or {}
    parts = [
        f"品种 {symbol} {timeframe} {action}",
        f"用户反馈：{user_text.strip()}",
    ]
    if original_score is not None:
        parts.append(f"原评分 {original_score} 建议 {original_rec}")
    feats = []
    if m.get("price_above_ema20"):
        feats.append("站上EMA20")
    if m.get("macd_hist_rising"):
        feats.append("MACD抬升/金叉")
    if m.get("rsi14") is not None:
        feats.append(f"RSI={_f(m.get('rsi14')):.0f}")
    if m.get("vol_ratio") is not None:
        feats.append(f"量比={_f(m.get('vol_ratio')):.2f}")
    if m.get("recent_change_pct") is not None:
        feats.append(f"近期涨跌={_f(m.get('recent_change_pct')):.1f}%")
    if feats:
        parts.append("技术特征：" + "，".join(feats))
    return "\n".join(parts)


def _patch_matches_metrics(pattern: Optional[Dict[str, Any]], metrics: Dict[str, Any]) -> bool:
    if not pattern:
        return True
    m = metrics or {}
    if "price_above_ema20" in pattern and bool(m.get("price_above_ema20")) != pattern["price_above_ema20"]:
        return False
    if "macd_hist_rising" in pattern and bool(m.get("macd_hist_rising")) != pattern["macd_hist_rising"]:
        return False
    if "vol_ratio_max" in pattern and _f(m.get("vol_ratio"), 1.0) > _f(pattern["vol_ratio_max"]):
        return False
    if "vol_ratio_min" in pattern and _f(m.get("vol_ratio"), 0.0) < _f(pattern["vol_ratio_min"]):
        return False
    if "rsi_min" in pattern and _f(m.get("rsi14"), 0) < _f(pattern["rsi_min"]):
        return False
    if "rsi_max" in pattern and _f(m.get("rsi14"), 100) > _f(pattern["rsi_max"]):
        return False
    return True


def apply_feedback_gate_overrides(
    gates: Dict[str, Any],
    metrics: Dict[str, Any],
    patches: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """将检索到的用户反馈补丁应用到 hard_gates。"""
    out = dict(gates or {})
    m = metrics or {}
    applied: List[str] = []
    above20 = bool(m.get("price_above_ema20"))
    macd_ok = bool(m.get("macd_hist_rising")) or _f(m.get("macd_hist")) > 0
    vol = _f(m.get("vol_ratio"), 1.0)

    for item in patches or []:
        gp = item if "clear_force_reject" in item else item.get("gate_patch") or item
        if not _patch_matches_metrics(gp.get("pattern"), m):
            continue

        if gp.get("clear_force_reject") and out.get("force_reject"):
            out["force_reject"] = False
            applied.append("clear_force_reject")

        if gp.get("allow_trial_low_volume_rebound"):
            rebound = (out.get("rebound_strength") or {}).get("strength_score", 0)
            if above20 and macd_ok and vol < 0.75 and rebound >= 45:
                out["force_reject"] = False
                out["trial_low_volume_rebound"] = True
                if gp.get("boost_execute_eligible") or gp.get("min_recommendation") == "caution":
                    out["execute_eligible"] = True
                applied.append("trial_low_volume_rebound")

        min_vol = gp.get("min_vol_ratio_execute")
        if min_vol is not None and above20 and macd_ok:
            if vol >= _f(min_vol) or gp.get("allow_trial_low_volume_rebound"):
                out["execute_eligible"] = True
                applied.append(f"vol_execute>={min_vol}")

    if applied:
        out["feedback_applied"] = applied
    return out


def retrieve_feedback_for_scoring(
    metrics: Dict[str, Any],
    *,
    symbol: str = "",
    timeframe: str = "",
    top_k: int = 5,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """返回 (gate_patches, prompt_items)。"""
    if not chroma_enabled():
        return [], []

    doc = build_embedding_document(
        symbol=symbol or "UNKNOWN",
        timeframe=timeframe or "",
        action="buy",
        user_text="当前信号技术形态检索",
        metrics=metrics,
    )
    hits = query_similar(doc, n_results=top_k, symbol=symbol)
    if not hits and symbol:
        hits = query_similar(doc, n_results=top_k)

    patches: List[Dict[str, Any]] = []
    prompt_items: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for h in hits:
        meta = h.get("metadata") or {}
        fid = str(h.get("id") or "")
        if fid in seen:
            continue
        seen.add(fid)

        gp_raw = meta.get("gate_patch")
        if isinstance(gp_raw, str):
            try:
                gp = json.loads(gp_raw)
            except Exception:
                gp = {}
        elif isinstance(gp_raw, dict):
            gp = gp_raw
        else:
            gp = build_gate_patch_from_feedback(str(meta.get("user_text") or h.get("document") or ""), metrics)

        if gp:
            patches.append(gp)

        prompt_items.append({
            "symbol": meta.get("symbol") or "",
            "timeframe": meta.get("timeframe") or "",
            "original_score": meta.get("original_score"),
            "original_recommendation": meta.get("original_recommendation") or "",
            "user_feedback": meta.get("user_text") or h.get("document") or "",
            "desired_recommendation": gp.get("min_recommendation") or "",
            "distance": h.get("distance"),
        })

    return patches, prompt_items


def format_feedback_prompt_section(prompt_items: List[Dict[str, Any]]) -> List[str]:
    if not prompt_items:
        return []
    lines = [
        "9) 用户历史纠正（相似形态，须参考但不得违背 safety hard_gates）：",
    ]
    for i, item in enumerate(prompt_items[:5], 1):
        orig = item.get("original_score")
        orig_s = f"原评{orig}分" if orig is not None else "原评未知"
        rec = item.get("original_recommendation") or "—"
        want = item.get("desired_recommendation") or "caution"
        fb = (item.get("user_feedback") or "")[:200]
        sym = item.get("symbol") or "?"
        lines.append(f"   - [{i}] {sym}: {orig_s}/{rec} → 用户认为应偏{want}；理由摘要：{fb}")
    return lines


def find_recent_score_for_signal(
    symbol: str,
    timeframe: str = "",
) -> Optional[Dict[str, Any]]:
    from backpack_quant_trading.core.crypto_signal_scorer import list_score_history

    sym = (symbol or "").upper().strip()
    tf = (timeframe or "").lower().strip()
    for row in list_score_history(30):
        if str(row.get("symbol") or "").upper() != sym:
            continue
        row_tf = str(row.get("timeframe") or "").lower()
        if tf and row_tf and tf not in row_tf and row_tf not in tf:
            continue
        return row
    return None


def save_feedback_from_dingtalk(
    *,
    user_text: str,
    symbol: str,
    timeframe: str = "",
    action: str = "buy",
    sender_id: str = "",
    original_score: Optional[int] = None,
    original_rec: str = "",
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    sym = (symbol or "").upper().strip()
    if not sym:
        return {"ok": False, "error": "未能识别品种，请写明如 TSM 2h"}

    gate_patch = build_gate_patch_from_feedback(user_text, metrics)
    doc = build_embedding_document(
        symbol=sym,
        timeframe=timeframe,
        action=action,
        user_text=user_text,
        original_score=original_score,
        original_rec=original_rec,
        metrics=metrics,
    )
    fid = f"fb_{sym}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    meta = {
        "symbol": sym,
        "timeframe": timeframe or "",
        "action": action,
        "user_text": user_text[:2000],
        "original_score": original_score if original_score is not None else -1,
        "original_recommendation": original_rec or "",
        "gate_patch": json.dumps(gate_patch, ensure_ascii=False),
        "metrics_compact": json.dumps(_compact_metrics(metrics or {}), ensure_ascii=False),
        "sender_id": sender_id or "",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    stored = upsert_feedback(fid, doc, meta)
    _append_preference_rule(sym, timeframe, user_text, gate_patch, fid)

    total = count_feedbacks()
    logger.info(
        "[评分反馈] 已保存 symbol=%s tf=%s patch=%s chroma=%s total=%s",
        sym, timeframe, gate_patch, stored, total,
    )
    return {
        "ok": True,
        "feedback_id": fid,
        "symbol": sym,
        "timeframe": timeframe,
        "gate_patch": gate_patch,
        "chroma_stored": stored,
        "total_feedbacks": total,
    }


def _append_preference_rule(
    symbol: str,
    timeframe: str,
    user_text: str,
    gate_patch: Dict[str, Any],
    fid: str,
) -> None:
    try:
        items: List[Dict[str, Any]] = []
        if _PREFERENCES_PATH.is_file():
            items = json.loads(_PREFERENCES_PATH.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            items = []
        items.insert(0, {
            "id": fid,
            "symbol": symbol,
            "timeframe": timeframe,
            "user_text": user_text[:500],
            "gate_patch": gate_patch,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        items = items[:200]
        _PREFERENCES_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PREFERENCES_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("写入 score_feedback_preferences 失败: %s", exc)


def apply_feedback_score_floor(
    final: int,
    rec: str,
    feedback_patches: List[Dict[str, Any]],
) -> Tuple[int, str]:
    for p in feedback_patches or []:
        floor = p.get("score_floor")
        if floor is not None:
            try:
                floor_i = int(floor)
            except (TypeError, ValueError):
                continue
            if final < floor_i:
                final = floor_i
        min_rec = p.get("min_recommendation")
        if min_rec == "caution" and rec == "reject":
            rec = "caution"
        elif min_rec == "execute" and rec in ("reject", "caution"):
            rec = "execute"
    return final, rec


def parse_score_card_from_reply(text: str) -> Tuple[str, str, Optional[int]]:
    """从 AI 评分卡 markdown 提取品种、周期、分数。"""
    clean = text or ""
    sym = ""
    m = re.search(r"\*\*([A-Z]{1,5})\*\*", clean)
    if m:
        sym = m.group(1).upper()
    if not sym:
        m2 = re.search(r"信号档案[\s\S]*?品种[:：]\s*([A-Z]{1,5})", clean, re.I)
        if m2:
            sym = m2.group(1).upper()
    tf = ""
    m3 = re.search(r"`(\d+[hHdDmMwW])`", clean)
    if m3:
        tf = m3.group(1).lower()
    score = None
    m4 = re.search(r"(\d{1,3})\s*/\s*100", clean)
    if m4:
        score = int(m4.group(1))
    return sym, tf, score


def handle_dingtalk_feedback(
    user_text: str,
    raw: Dict[str, Any],
    *,
    sender_id: str = "",
) -> Tuple[str, Dict[str, Any]]:
    """处理钉钉 @ 反馈消息，返回 (回复文案, result)。"""
    from backpack_quant_trading.core.dingtalk_manual_score import (
        resolve_signal_for_scoring,
        parse_dingtalk_signal_text,
        extract_user_text_from_raw,
    )

    sym_tf = parse_symbol_timeframe_from_text(user_text)
    symbol, timeframe = sym_tf[0], sym_tf[1]
    action = "buy"
    metrics: Dict[str, Any] = {}
    original_score: Optional[int] = None
    original_rec = ""

    parsed, _ = resolve_signal_for_scoring(user_text, raw)
    if parsed and parsed.get("symbol"):
        symbol = parsed.get("symbol") or symbol
        timeframe = parsed.get("timeframe") or timeframe
        action = parsed.get("action") or action

    from backpack_quant_trading.core.dingtalk_manual_score import _resolve_from_reply_body

    reply_parsed, _ = _resolve_from_reply_body(raw)
    if reply_parsed and reply_parsed.get("symbol"):
        symbol = reply_parsed.get("symbol") or symbol
        timeframe = reply_parsed.get("timeframe") or timeframe

    reply_text = ""
    text_block = raw.get("text")
    if isinstance(text_block, dict) and text_block.get("repliedMsg"):
        from backpack_quant_trading.core.dingtalk_manual_score import _summarize_replied_msg

        reply_text = _summarize_replied_msg(text_block["repliedMsg"]) or ""
    if reply_text:
        rsym, rtf, rscore = parse_score_card_from_reply(reply_text)
        symbol = symbol or rsym
        timeframe = timeframe or rtf
        if rscore is not None and original_score is None:
            original_score = rscore

    hist = find_recent_score_for_signal(symbol, timeframe) if symbol else None
    if hist:
        original_score = int(hist.get("score") or 0) if hist.get("score") is not None else None
        original_rec = str(hist.get("recommendation") or "")

    m_score = re.search(r"(\d{1,3})\s*/\s*100", user_text)
    if m_score:
        original_score = int(m_score.group(1))
    if "拒绝" in user_text or "reject" in user_text.lower():
        original_rec = original_rec or "reject"

    result = save_feedback_from_dingtalk(
        user_text=user_text,
        symbol=symbol,
        timeframe=timeframe,
        action=action,
        sender_id=sender_id,
        original_score=original_score,
        original_rec=original_rec,
        metrics=metrics,
    )
    if not result.get("ok"):
        return result.get("error") or "反馈保存失败", result

    patch = result.get("gate_patch") or {}
    want = patch.get("min_recommendation") or "caution"
    floor = patch.get("score_floor")
    lines = [
        f"✅ 已记住你对 **{symbol}** {timeframe or ''} 的评分纠正。",
        f"· 偏好建议：**{want}**" + (f"（分数底线约 {floor}）" if floor else ""),
    ]
    if patch.get("allow_trial_low_volume_rebound"):
        lines.append("· 已记录：**缩量反弹可轻仓试错**，后续相似形态会放宽 hard_gates。")
    if patch.get("clear_force_reject"):
        lines.append("· 已记录：同类形态**不再轻易 force_reject**。")
    lines.append(f"· 向量库累计 **{result.get('total_feedbacks', 0)}** 条反馈，下次评分自动检索参考。")
    return "\n".join(lines), result
