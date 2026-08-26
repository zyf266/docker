"""A股 AI 自适应 Agent — 钉钉 ActionCard 推送。"""
from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from backpack_quant_trading.core.stock_news_alert import _dingtalk_post

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


def _volume_line(vol: Dict[str, Any]) -> str:
    if not isinstance(vol, dict):
        return "—"
    st = VOLUME_STATE_CN.get(str(vol.get("state") or ""), str(vol.get("state") or "—"))
    dv = VOLUME_DIV_CN.get(str(vol.get("divergence") or ""), str(vol.get("divergence") or "—"))
    tr = VOLUME_TRAP_CN.get(str(vol.get("trap_risk") or ""), str(vol.get("trap_risk") or "—"))
    note = str(vol.get("note") or "").strip()
    base = f"{st} · 背离：{dv} · 诱多/诱空：{tr}"
    return f"{base}（{note}）" if note else base


def resolve_agent_webhook() -> str:
    """仅本功能专用群；不回退到 A 股监控 Webhook，避免误发到旧群。"""
    return (os.getenv("A_SHARE_AI_AGENT_DINGTALK_WEBHOOK") or "").strip()


def resolve_agent_keyword() -> str:
    return (
        os.getenv("A_SHARE_AI_AGENT_DINGTALK_KEYWORD", "").strip()
        or os.getenv("A_SHARE_MONITOR_DINGTALK_KEYWORD", "").strip()
        or "信号"
    )


def _inject_keyword(text: str) -> str:
    kw = resolve_agent_keyword()
    body = text or ""
    if kw and kw not in body:
        body = f"【{kw}】\n{body}"
    return body


def build_action_card_markdown(result: Dict[str, Any]) -> Tuple[str, str]:
    d = result.get("decision") or {}
    action = str(d.get("action") or "hold").upper()
    action_cn = {"BUY": "买入", "SELL": "卖出", "HOLD": "不买入/观望"}.get(action, action)
    code = result.get("code") or ""
    name = result.get("name") or code
    conf = d.get("confidence")
    try:
        conf_s = f"{float(conf) * 100:.0f}%" if conf is not None else "—"
    except Exception:
        conf_s = "—"
    vol = (d.get("volume_structure") or {}) if isinstance(d.get("volume_structure"), dict) else {}
    mvs = (d.get("market_vs_stock") or {}) if isinstance(d.get("market_vs_stock"), dict) else {}
    risks = d.get("risk_notes") or []
    if isinstance(risks, list):
        risk_s = "；".join(str(x) for x in risks[:3]) or "—"
    else:
        risk_s = str(risks)
    valid = d.get("valid", True)
    inv = d.get("invalid_reason") or ""
    align = str(mvs.get("alignment") or "")
    align_cn = MARKET_ALIGN_CN.get(align, align or "—")
    fund = result.get("fundamentals") or {}
    fund_s = str(fund.get("brief") or "").strip() or "（本轮未附带估值快照）"

    title = f"A股自适应{action_cn} · {name}({code})"
    lines = [
        f"### A股AI自适应策略 · **{action_cn}**",
        f"- **标的**：{name} `{code}`",
        f"- **周期**：{result.get('interval_label') or result.get('interval')}",
        f"- **置信度**：{conf_s}",
        f"- **时间**：{result.get('as_of') or ''}",
        f"- **基本面**：{fund_s}",
        f"- **分析理由**：{d.get('thesis') or '—'}",
        f"- **量能**：{_volume_line(vol)}",
        f"- **大盘vs个股**：{align_cn} · {mvs.get('note') or ''}",
        f"- **风险**：{risk_s}",
        f"- **硬规则**：{'通过' if valid else f'拦截 · {inv}'}",
        "",
        "> 纠偏：引用本条回复理由。机器人回「已收录」= 草稿成功；网页点「刷新并生效风格」后群里会再推「已生效」。",
    ]
    return title, "\n".join(lines)


def push_style_confirmed_notice(prefs: Dict[str, Any]) -> Tuple[bool, str]:
    """网页确认风格后，群内回执：纠偏已生效。"""
    newly = prefs.get("newly_confirmed") or []
    n = int(prefs.get("newly_count") or len(newly) or 0)
    if n <= 0:
        return False, "无新增生效条目"
    total = len(prefs.get("style_notes") or [])
    at = prefs.get("confirmed_at") or ""
    lines = [
        "### A股AI自适应 · 纠偏风格已生效",
        f"- **本次生效**：{n} 条",
        f"- **累计已生效**：{total} 条",
        f"- **时间**：{at}",
        "",
        "**本次内容：**",
    ]
    for item in newly[-8]:
        t = str((item or {}).get("text") or "").strip()
        if not t:
            continue
        meta = (item or {}).get("meta") or {}
        tag = ""
        if meta.get("code"):
            tag = f"`{meta.get('code')}` "
        lines.append(f"- {tag}{t[:120]}{'…' if len(t) > 120 else ''}")
    lines.extend(
        [
            "",
            "> 下一轮扫描会把以上纠偏并入提示词。若未看到本条，请检查 Webhook 或网页「已生效」列表。",
        ]
    )
    body = "\n".join(lines)
    return send_dingtalk_action_card(
        title="A股自适应纠偏已生效",
        text=body,
        single_title="打开A股AI自适应",
        single_url=(
            f"{os.getenv('PUBLIC_WEB_BASE', '').strip().rstrip('/')}/strategies/a-share-ai-agent"
            if os.getenv("PUBLIC_WEB_BASE", "").strip()
            else "https://www.dingtalk.com"
        ),
    )


def send_dingtalk_action_card(
    *,
    title: str,
    text: str,
    single_title: str = "打开策略页",
    single_url: str = "",
    webhook: str = "",
) -> Tuple[bool, str]:
    url = (webhook or resolve_agent_webhook()).strip()
    if not url:
        return False, "未配置 A_SHARE_AI_AGENT_DINGTALK_WEBHOOK"
    kw = resolve_agent_keyword()
    body = _inject_keyword(text)
    card_title = title if (not kw or kw in title) else f"【{kw}】{title}"
    jump = (single_url or "").strip() or "https://www.dingtalk.com"
    payload = {
        "msgtype": "actionCard",
        "actionCard": {
            "title": card_title[:128],
            "text": body[:18000],
            "btnOrientation": "0",
            "singleTitle": single_title or "打开策略页",
            "singleURL": jump,
        },
    }
    return _dingtalk_post(url, payload, timeout=12.0)


def push_signal_action_card(result: Dict[str, Any]) -> Tuple[bool, str]:
    title, md = build_action_card_markdown(result)
    base = os.getenv("PUBLIC_WEB_BASE", "").strip().rstrip("/")
    link = f"{base}/strategies/a-share-ai-agent" if base else "https://www.dingtalk.com"
    ok, msg = send_dingtalk_action_card(
        title=title,
        text=md,
        single_title="打开A股AI自适应",
        single_url=link if base else "https://www.dingtalk.com",
    )
    if ok:
        try:
            from backpack_quant_trading.core.a_share_ai_agent_feedback import remember_a_share_ai_push

            remember_a_share_ai_push(result)
        except Exception:
            pass
    return ok, msg
