"""A股 AI 自适应 Agent — 钉钉 ActionCard 推送。"""
from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from backpack_quant_trading.core.stock_news_alert import _dingtalk_post


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


def _rsi_line(result: Dict[str, Any], decision: Dict[str, Any]) -> str:
    ind = result.get("indicators") if isinstance(result.get("indicators"), dict) else {}
    r14 = ind.get("rsi14")
    r6 = ind.get("rsi6")
    zone = ind.get("zone") or ""
    note = str(decision.get("rsi_note") or "").strip()
    zone_cn = {"oversold": "超卖", "overbought": "超买", "neutral": "中性"}.get(str(zone), str(zone) or "—")
    parts = []
    if r14 is not None:
        parts.append(f"RSI14 {r14}")
    if r6 is not None:
        parts.append(f"RSI6 {r6}")
    parts.append(zone_cn)
    base = " · ".join(parts) if parts else "—"
    return f"{base}（{note}）" if note else base


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
    risks = d.get("risk_notes") or []
    if isinstance(risks, list):
        risk_s = "；".join(str(x) for x in risks[:3]) or ""
    else:
        risk_s = str(risks or "")
    pos_note = str(result.get("position_note") or "").strip()

    title = f"A股做T{action_cn} · {name}({code})"
    lines = [
        f"### A股AI日内做T · **{action_cn}**",
        f"- **标的**：{name} `{code}`",
        f"- **周期**：{result.get('interval_label') or result.get('interval')}",
        f"- **置信度**：{conf_s}",
        f"- **时间**：{result.get('as_of') or ''}",
        f"- **RSI**：{_rsi_line(result, d)}",
        f"- **分析理由**：{d.get('thesis') or '—'}",
    ]
    if pos_note:
        lines.append(f"- **仓位提示**：{pos_note}")
    if risk_s:
        lines.append(f"- **风险**：{risk_s}")
    return title, "\n".join(lines)


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
