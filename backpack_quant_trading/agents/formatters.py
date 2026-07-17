"""钉钉 Markdown：对齐「AI 信号评分」海报式排版。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from backpack_quant_trading.agents.types import AgentId, AnalyzeReport

_AGENT_TITLE = {
    AgentId.US_ANALYST: "美股分析师",
    AgentId.A_SHARE_ANALYST: "A股分析师",
    AgentId.CRYPTO_ANALYST: "加密分析师",
    AgentId.RESEARCH: "信息检索",
    AgentId.RISK: "风控",
    AgentId.EXECUTION: "执行",
    AgentId.REVIEW: "复盘",
    AgentId.COORDINATOR: "协调",
}

_ACTION_CN = {
    "buy": "买入",
    "sell": "卖出",
    "hold": "观望",
    "reject": "拒绝",
}


def agent_title(agent_id: AgentId | str) -> str:
    if isinstance(agent_id, AgentId):
        return _AGENT_TITLE.get(agent_id, agent_id.value)
    try:
        return _AGENT_TITLE.get(AgentId(agent_id), str(agent_id))
    except Exception:
        return str(agent_id)


def _score_bar(score_val: int) -> str:
    n = max(0, min(100, int(score_val)))
    filled = n // 10
    return "█" * filled + "░" * (10 - filled) + f"  {n}%"


def _grade_badge(grade: str) -> str:
    g = str(grade or "—").upper().strip()
    icons = {"A": "🏆", "B": "🥈", "C": "🥉", "D": "📉", "F": "🚫"}
    return f"{icons.get(g, '📊')} {g}"


def _rec_label(rec: str, action: str) -> tuple[str, str]:
    r = (rec or "").lower().strip()
    if r == "execute":
        return "✅", "建议执行"
    if r == "caution":
        return "⚠️", "谨慎观望"
    if r == "reject":
        return "⛔", "建议拒绝"
    a = (action or "").lower()
    if a == "reject":
        return "⛔", "建议拒绝"
    if a in ("buy", "sell"):
        return "✅", "建议执行"
    return "⚠️", "谨慎观望"


def _fmt_num(v: Any, digits: int = 2) -> str:
    try:
        if v is None or v == "":
            return "—"
        return f"{float(v):,.{digits}f}"
    except Exception:
        return str(v)


def _dir_icon(action: str) -> str:
    a = (action or "").lower()
    if a == "buy":
        return "🟢"
    if a == "sell":
        return "🔴"
    if a == "reject":
        return "🚫"
    return "🔔"


def format_report_markdown(
    report: AnalyzeReport,
    *,
    pending_id: str = "",
    max_citations: int = 6,
) -> str:
    title = agent_title(report.agent_id)
    raw = report.raw or {}
    st: Dict[str, Any] = dict(raw.get("structured") or {})
    snap: Dict[str, Any] = dict(raw.get("snapshot") or {})
    metrics: Dict[str, Any] = dict(snap.get("metrics") or {})
    tf = str(raw.get("timeframe") or snap.get("interval") or "—")

    try:
        score_val = int(float(report.score if report.score is not None else st.get("score") or 0))
    except Exception:
        score_val = 0

    grade = str(st.get("grade") or "—")
    rec = str(st.get("recommendation") or "")
    rec_ico, rec_cn = _rec_label(rec, report.action)
    action_cn = _ACTION_CN.get((report.action or "").lower(), report.action or "—")
    dir_ico = _dir_icon(report.action or "")
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    summary = (st.get("summary") or report.rationale or "").strip()
    if len(summary) > 320:
        summary = summary[:317] + "…"

    sep = "━━━━━━━━━━━━━━━━━━━━━━"
    sep_thin = "──────────────────────"
    market = report.market.value if hasattr(report.market, "value") else str(report.market)

    lines: List[str] = [
        f"## 提醒 · {title}",
        "",
        "#### 🎯 信号档案",
        sep_thin,
        f"- **品种** {report.symbol}",
        f"- **方向** {dir_ico} {action_cn}",
        f"- **市场** {market}",
        f"- **周期** {tf}",
        f"- **时间** {now_utc}",
        "",
        "#### ⭐ 综合评分",
        sep,
        "",
        f"## {score_val} / 100",
        "",
        f"> {_score_bar(score_val)}",
        "",
        f"- **等级** {_grade_badge(grade)}",
        f"- **结论** {rec_ico} {rec_cn}",
        "",
    ]

    if summary:
        lines += ["#### 💬 研判摘要", sep_thin, f"> {summary}", ""]

    # 消息面
    news_comment = str(st.get("news_comment") or "").strip()
    cites = list(report.citations or [])[:max_citations]
    news_ctx = snap.get("news_context")
    news_lines: List[str] = []
    if news_ctx or news_comment:
        try:
            from backpack_quant_trading.core.us_stock_news import format_news_for_dingtalk

            news_lines = format_news_for_dingtalk(
                news_ctx if isinstance(news_ctx, dict) else None,
                ticker=report.symbol,
                news_comment=news_comment,
                max_items=6,
            )
        except Exception:
            news_lines = []
    if not news_lines and (cites or news_comment):
        if news_comment:
            news_lines.append(f"> **AI 解读** {news_comment[:220]}")
        for c in cites:
            bit = f"- [{c.source}] {c.title}"
            if len(bit) > 120:
                bit = bit[:117] + "…"
            news_lines.append(bit)
    if news_lines:
        lines += ["#### 📰 消息面", sep_thin, *news_lines, ""]

    # 美股联动（加密）
    us_overlay = snap.get("us_equity_overlay") if isinstance(snap.get("us_equity_overlay"), dict) else {}
    us_notes = str(st.get("us_equity_notes") or us_overlay.get("summary_text") or "").strip()
    us_bias = str(st.get("us_equity_overlay") or us_overlay.get("risk_bias_hint") or "").strip()
    if us_notes or us_bias:
        lines += [
            "#### 🇺🇸 美股联动",
            sep_thin,
            f"- **偏好** {us_bias or 'n/a'}",
            f"- **快照** {us_notes[:280] or '—'}",
            "",
        ]

    # 支撑压力
    support = report.support
    resistance = report.resistance
    last = snap.get("last_close") or metrics.get("close") or metrics.get("last_close")
    lines += ["#### 📐 支撑 / 压力位", sep_thin, f"- **信号周期** `{tf}`"]
    if support is not None:
        dist = ""
        try:
            if last:
                dist = f"　距现价 {(float(support) - float(last)) / float(last) * 100:+.2f}%"
        except Exception:
            pass
        lines.append(f"- **支撑** {_fmt_num(support)}{dist}")
    if resistance is not None:
        dist = ""
        try:
            if last:
                dist = f"　距现价 {(float(resistance) - float(last)) / float(last) * 100:+.2f}%"
        except Exception:
            pass
        lines.append(f"- **压力** {_fmt_num(resistance)}{dist}")
    stop_hint = str(st.get("stop_hint") or "").strip()
    target_hint = str(st.get("target_hint") or "").strip()
    invalidation = str(st.get("invalidation") or "").strip()
    if stop_hint:
        lines.append(f"- **止损参考** {stop_hint}")
    elif support is not None:
        lines.append(f"- **止损参考** 若跌破 {_fmt_num(support)} 支撑，建议止损/降级观点。")
    if target_hint:
        lines.append(f"- **目标参考** {target_hint}")
    elif resistance is not None:
        lines.append(f"- **目标参考** 若反弹至 {_fmt_num(resistance)} 压力附近，可考虑减仓或止盈。")
    if invalidation:
        lines.append(f"- **失效条件** {invalidation}")
    lines.append("")

    # 技术快照
    rsi = metrics.get("rsi14")
    macd = metrics.get("macd_hist")
    adx = metrics.get("adx14")
    volr = metrics.get("vol_ratio")
    close = last or metrics.get("close")
    lines += [
        "#### 📊 技术快照",
        sep_thin,
        f"- **现价** {_fmt_num(close)}",
        f"- **RSI** {_fmt_num(rsi)}　**MACD** {_fmt_num(macd, 4)}　**ADX** {_fmt_num(adx)}",
        f"- **量比** {_fmt_num(volr, 3)}",
    ]
    tech_bias = st.get("technical_bias") or ""
    fund_bias = st.get("fundamentals_bias") or ""
    if tech_bias or fund_bias:
        lines.append(f"- **偏向** 技术={tech_bias or '—'}　基本面={fund_bias or '—'}")
    deriv = str(st.get("derivatives_notes") or "").strip()
    if deriv:
        lines.append(f"- **衍生品** {deriv[:180]}")
    a_notes = str(st.get("a_share_notes") or "").strip()
    if a_notes:
        lines.append(f"- **A股提示** {a_notes[:180]}")
    lines.append("")

    strengths = [str(x).strip() for x in (st.get("strengths") or []) if str(x).strip()][:4]
    risks = [str(x).strip() for x in (st.get("risks") or st.get("key_risks") or []) if str(x).strip()][:4]
    if strengths:
        lines += ["#### ✅ 亮点", sep_thin, *[f"- {x}" for x in strengths], ""]
    if risks:
        lines += ["#### ⚠ 风险", sep_thin, *[f"- {x}" for x in risks], ""]

    if report.risk:
        risk_cn = "通过" if report.risk.decision == "allow" else "拒绝"
        lines += [
            "#### 🛡 风控",
            sep_thin,
            f"- **结论** {risk_cn}（{report.risk.mode}）",
            f"- **理由** {report.risk.reason}",
            "",
        ]

    if pending_id:
        lines += [
            "#### ✅ 待确认下单",
            sep_thin,
            f"- 订单 `{pending_id}` — 回复「确认」或「确认 {pending_id}」提交",
            "",
        ]

    lines += [sep, f"沐龙量化 · {title} · {report.symbol} · {tf}"]
    text = "\n".join(lines)
    if len(text) > 4500:
        text = text[:4497] + "…"
    return text


def format_multi_reports(
    reports: Iterable[AnalyzeReport],
    *,
    header: str = "## 提醒 · 协调结果",
) -> str:
    parts = [header, ""]
    for r in reports:
        parts.append(format_report_markdown(r))
        parts.append("")
    return "\n".join(parts).strip()
