"""A股 AI 自适应 Agent — 钉钉 Stream 自动收评。"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_A_SHARE_CARD_MARKERS = (
    "A股AI自适应",
    "A股自适应策略",
    "A股自适应买入",
    "A股自适应卖出",
    "A股自适应观望",
    "打开A股AI自适应",
)

_A_SHARE_FEEDBACK_HINTS = (
    "不应该",
    "不应出现",
    "不该买",
    "不该卖",
    "可以买",
    "可以买入",
    "应该买",
    "应该买入",
    "这时可以",
    "这个时候可以",
    "此时可以",
    "其实可以",
    "我认为可以",
    "我觉得可以",
    "警惕",
    "诱多",
    "诱空",
    "量能萎缩",
    "缩量",
    "假金叉",
    "滞涨",
    "大盘回调",
    "没有进攻",
    "没有买入",
    "没有卖出",
    "观望更合适",
    "记住",
    "纠正",
    "觉得",
    "不同意",
    "分析不对",
    "判断错",
)


def _replied_summary(raw: Dict[str, Any]) -> str:
    try:
        from backpack_quant_trading.core.dingtalk_manual_score import _summarize_replied_msg

        chunks = []
        text_block = raw.get("text")
        if isinstance(text_block, dict) and text_block.get("repliedMsg"):
            chunks.append(_summarize_replied_msg(text_block["repliedMsg"]) or "")
        for key in ("repliedMsg", "quoteMessage", "quotedMessage"):
            if isinstance(raw.get(key), dict):
                chunks.append(_summarize_replied_msg(raw[key]) or "")
        return "\n".join(x for x in chunks if x)
    except Exception:
        return ""


def parse_a_share_code_from_text(text: str) -> Tuple[str, str]:
    """从卡片/点评中解析 A 股代码与周期。返回 (code, interval)。"""
    plain = text or ""
    code = ""
    m = re.search(r"(?<!\d)([036]\d{5})(?!\d)", plain)
    if m:
        code = m.group(1)
    interval = ""
    if "30分钟" in plain or re.search(r"\b30m\b", plain, re.I):
        interval = "30"
    elif "60分钟" in plain or re.search(r"\b60m\b", plain, re.I):
        interval = "60"
    elif "日线" in plain or re.search(r"\b1d\b|\bD\b", plain):
        interval = "D"
    return code, interval


def is_a_share_ai_card_context(raw: Dict[str, Any], user_text: str = "") -> bool:
    replied = _replied_summary(raw)
    blob = f"{replied}\n{user_text or ''}"
    if any(m in blob for m in _A_SHARE_CARD_MARKERS):
        return True
    try:
        from backpack_quant_trading.core.score_feedback import load_last_signal_context

        ctx = load_last_signal_context()
        if str(ctx.get("source") or "") == "a_share_ai_agent":
            return True
    except Exception:
        pass
    return False


def is_a_share_ai_feedback_text(text: str) -> bool:
    plain = re.sub(r"@[^\s@　]+", " ", text or "", flags=re.IGNORECASE).strip()
    if len(plain) < 8:
        return False
    if any(h in plain for h in _A_SHARE_FEEDBACK_HINTS):
        return True
    try:
        from backpack_quant_trading.core.score_feedback import is_feedback_command

        return is_feedback_command(plain)
    except Exception:
        return False


def should_handle_a_share_ai_feedback(user_text: str, raw: Dict[str, Any]) -> bool:
    """回复 A股AI 卡片时：任意较完整点评都收录（含反驳观望、主张可买入）。"""
    if not is_a_share_ai_card_context(raw, user_text):
        return False
    plain = re.sub(r"@[^\s@　]+", " ", user_text or "", flags=re.IGNORECASE).strip()
    if len(plain) >= 15:
        return True
    return is_a_share_ai_feedback_text(user_text)


def handle_a_share_ai_dingtalk_feedback(
    user_text: str,
    raw: Dict[str, Any],
    *,
    sender_id: str = "",
) -> Tuple[str, Dict[str, Any]]:
    """把群点评写入 A股AI 偏好草稿（待人工确认后生效）。"""
    from backpack_quant_trading.core.a_share_ai_agent import append_feedback_draft, load_style_draft
    from backpack_quant_trading.core.score_feedback import load_last_signal_context

    replied = _replied_summary(raw)
    code, interval = parse_a_share_code_from_text(f"{replied}\n{user_text}")
    if not code:
        ctx = load_last_signal_context()
        if str(ctx.get("source") or "") == "a_share_ai_agent":
            code = str(ctx.get("symbol") or "").strip()
            interval = interval or str(ctx.get("timeframe") or "")
    # A 股代码保持 6 位数字，不 upper 成字母
    if code and code.isdigit():
        code = code.zfill(6)
    else:
        code = ""

    plain = re.sub(r"@[^\s@　]+", " ", user_text or "", flags=re.IGNORECASE).strip()
    # 同时写入偏好草稿 + Chroma/Agent 记忆（RAG），确认后才会并进 System 风格附言
    append_feedback_draft(
        plain,
        meta={
            "code": code or None,
            "interval": interval or None,
            "source": "dingtalk_stream",
            "sender_id": sender_id,
            "replied_excerpt": (replied or "")[:240],
            "agent_action_hint": str((load_last_signal_context() or {}).get("recommendation") or ""),
        },
    )
    try:
        from backpack_quant_trading.core.agent_memory_store import upsert_memory
        import time as _time

        upsert_memory(
            "a_share_ai_feedback",
            f"a_share_ai_fb_{code or 'na'}_{int(_time.time())}",
            f"[A股AI自适应纠偏] code={code or '?'} tf={interval or '?'} | {plain}",
            {
                "kind": "a_share_ai_agent_feedback",
                "code": code or "",
                "interval": interval or "",
                "source": "dingtalk_stream",
            },
        )
    except Exception as exc:
        logger.debug("upsert_memory a_share_ai feedback skip: %s", exc)

    draft = load_style_draft()
    pending_n = len(draft.get("pending") or [])
    code_s = code or "（未解析到代码，已按最近上下文入库）"
    lines = [
        f"✅ 已收录你对 **A股AI自适应** {code_s} {interval or ''} 的点评（已进 RAG/草稿）。",
        "· 无论本轮卡片是「买入」还是「不买入/观望」，你的纠偏理由都会保留。",
        "· 请在网页点 **「刷新并生效风格」** 后，下一轮扫描会把点评并入提示词。",
        f"· 草稿累计约 **{pending_n}** 条。",
    ]
    return "\n".join(lines), {"ok": True, "code": code, "interval": interval, "pending": pending_n}


def remember_a_share_ai_push(result: Dict[str, Any]) -> None:
    """推送 ActionCard 后记住上下文，便于用户只回复卡片正文时回落。"""
    try:
        from backpack_quant_trading.core.score_feedback import remember_last_signal_context

        code = str(result.get("code") or "").strip()
        if code.isdigit():
            code = code.zfill(6)
        d = result.get("decision") or {}
        remember_last_signal_context(
            symbol=code,
            timeframe=str(result.get("interval") or ""),
            score=None,
            recommendation=str(d.get("action") or ""),
            source="a_share_ai_agent",
        )
    except Exception as exc:
        logger.debug("remember_a_share_ai_push failed: %s", exc)
