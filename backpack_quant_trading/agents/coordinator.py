"""协调 / 路由 Agent：前缀点名 + 自动识别拆单。"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backpack_quant_trading.agents.formatters import format_multi_reports, format_report_markdown
from backpack_quant_trading.agents.memory import (
    is_agent_preference_command,
    save_global_preference,
)
from backpack_quant_trading.agents.risk_agent import apply_risk
from backpack_quant_trading.agents.types import AgentId, AnalyzeReport, AnalyzeRequest, Market

logger = logging.getLogger(__name__)

# 前缀 → (意图, 默认 agent)
_PREFIX_MAP = [
    (r"^@?美股分析师\s*", "analyze", AgentId.US_ANALYST, Market.US_STOCK),
    (r"^@?A股分析师\s*", "analyze", AgentId.A_SHARE_ANALYST, Market.A_SHARE),
    (r"^@?加密分析师\s*", "analyze", AgentId.CRYPTO_ANALYST, Market.CRYPTO),
    (r"^@?信息检索\s*", "research", AgentId.RESEARCH, Market.UNKNOWN),
    (r"^@?风控\s*", "risk", AgentId.RISK, Market.UNKNOWN),
    (r"^@?复盘\s*", "review", AgentId.REVIEW, Market.UNKNOWN),
    (r"^@?执行\s*", "execution", AgentId.EXECUTION, Market.UNKNOWN),
    (r"^@?协调\s*", "coord", AgentId.COORDINATOR, Market.UNKNOWN),
]

# 别名 → (symbol, market)
_ALIASES = {
    "茅台": ("600519", Market.A_SHARE),
    "贵州茅台": ("600519", Market.A_SHARE),
    "宁德时代": ("300750", Market.A_SHARE),
    "BTC": ("BTC", Market.CRYPTO),
    "比特币": ("BTC", Market.CRYPTO),
    "ETH": ("ETH", Market.CRYPTO),
    "以太坊": ("ETH", Market.CRYPTO),
    "NVDA": ("NVDA", Market.US_STOCK),
    "英伟达": ("NVDA", Market.US_STOCK),
    "TSLA": ("TSLA", Market.US_STOCK),
    "特斯拉": ("TSLA", Market.US_STOCK),
    "AAPL": ("AAPL", Market.US_STOCK),
}


@dataclass
class RouteHit:
    intent: str
    agent_id: AgentId
    market: Market
    rest: str
    symbols: List[Tuple[str, Market]] = field(default_factory=list)


def strip_prefix(text: str) -> Tuple[Optional[RouteHit], str]:
    t = (text or "").strip()
    for pat, intent, aid, mkt in _PREFIX_MAP:
        m = re.match(pat, t, flags=re.I)
        if m:
            rest = t[m.end() :].strip()
            return RouteHit(intent=intent, agent_id=aid, market=mkt, rest=rest), rest
    return None, t


def extract_symbols(text: str) -> List[Tuple[str, Market]]:
    """从文本提取多个标的（支持 茅台+BTC）。"""
    found: List[Tuple[str, Market]] = []
    seen = set()
    t = text or ""

    # 别名（长词优先）
    for name in sorted(_ALIASES.keys(), key=len, reverse=True):
        if name in t or name.upper() in t.upper():
            sym, mkt = _ALIASES[name]
            key = (sym, mkt)
            if key not in seen:
                seen.add(key)
                found.append(key)

    # A股 6 位
    for m in re.finditer(r"\b(\d{6})\b", t):
        code = m.group(1)
        key = (code, Market.A_SHARE)
        if key not in seen:
            seen.add(key)
            found.append(key)

    # 美股 / 加密 ticker：仅匹配独立 token，并过滤常见英文词
    _STOP = {
        "USDT", "USD", "HTTP", "HTTPS", "JSON", "AI", "API", "CEO", "ETF",
        "THE", "AND", "FOR", "WITH", "FROM", "THIS", "THAT", "HAVE", "WILL",
    }
    for m in re.finditer(r"(?<![A-Za-z0-9])([A-Z]{2,5})(?![A-Za-z0-9])", t.upper()):
        tok = m.group(1)
        if tok in _STOP:
            continue
        if tok in ("BTC", "ETH", "SOL", "BNB", "DOGE", "XRP", "HYPE", "TAO"):
            key = (tok, Market.CRYPTO)
        elif tok in _ALIASES or len(tok) >= 2:
            # 仅当是已知别名，或文本里明确「分析/看看」语境才当美股 ticker
            if tok in {a.upper() for a in _ALIASES if a.isascii()} or any(
                k in t for k in ("分析", "看看", "怎么看", "评分", "分析师")
            ):
                if tok in ("BTC", "ETH", "SOL", "BNB", "DOGE", "XRP", "HYPE", "TAO"):
                    key = (tok, Market.CRYPTO)
                else:
                    key = (tok, Market.US_STOCK)
            else:
                continue
        else:
            continue
        if key not in seen:
            seen.add(key)
            found.append(key)

    # crypto xxxUSDT
    for m in re.finditer(r"\b([A-Z]{2,10})USDT\b", t.upper()):
        key = (m.group(1), Market.CRYPTO)
        if key not in seen:
            seen.add(key)
            found.append(key)

    return found


def parse_route(text: str) -> RouteHit:
    hit, rest = strip_prefix(text)
    if hit is None:
        hit = RouteHit(
            intent="coord",
            agent_id=AgentId.COORDINATOR,
            market=Market.UNKNOWN,
            rest=rest,
        )
    syms = extract_symbols(hit.rest or text)
    if hit.market != Market.UNKNOWN and not syms:
        # 前缀指定市场但未解析出标的：尝试 rest 整体当 symbol
        token = (hit.rest or "").split()[0] if (hit.rest or "").split() else ""
        if token:
            syms = [(token.upper().replace("USDT", ""), hit.market)]
    elif hit.market != Market.UNKNOWN and syms:
        # 强制市场覆盖（前缀优先）
        syms = [(s, hit.market) for s, _ in syms]
    hit.symbols = syms
    return hit


def _run_analyst(symbol: str, market: Market, user_text: str, staff_id: str = "") -> AnalyzeReport:
    req = AnalyzeRequest(
        symbol=symbol,
        market=market,
        user_text=user_text,
        staff_id=staff_id,
        include_research=True,
    )
    if market == Market.US_STOCK:
        from backpack_quant_trading.agents.analysts.us_analyst import analyze

        return analyze(req)
    if market == Market.A_SHARE:
        from backpack_quant_trading.agents.analysts.a_share_analyst import analyze

        return analyze(req)
    if market == Market.CRYPTO:
        from backpack_quant_trading.agents.analysts.crypto_analyst import analyze

        return analyze(req)
    from backpack_quant_trading.core.signal_asset_router import classify_signal_asset

    kind = str(classify_signal_asset(symbol) or "crypto").lower()
    if "us" in kind:
        from backpack_quant_trading.agents.analysts.us_analyst import analyze

        return analyze(req)
    from backpack_quant_trading.agents.analysts.crypto_analyst import analyze

    return analyze(req)


def handle(
    user_text: str,
    *,
    staff_id: str = "",
    propose_execution: bool = True,
) -> Dict[str, Any]:
    """主入口：返回 markdown + 结构化结果。"""
    text = (user_text or "").strip()
    if not text:
        return {"ok": False, "markdown": "请说明要分析的标的或 Agent。", "reports": []}

    # 确认下单
    from backpack_quant_trading.agents.execution_agent import confirm_order, parse_confirm_command

    is_confirm, pid = parse_confirm_command(text)
    if is_confirm:
        res = confirm_order(pid, staff_id=staff_id, dry_run=False)
        md = res.get("message") or res.get("error") or str(res)
        return {"ok": bool(res.get("ok")), "markdown": md, "execution": res, "reports": []}

    # 全局偏好纠正
    hit = parse_route(text)
    if is_agent_preference_command(text) or (
        hit.intent == "analyze" and is_agent_preference_command(hit.rest)
    ):
        pref_text = hit.rest if hit.intent == "analyze" else text
        aid = hit.agent_id if hit.intent == "analyze" else AgentId.COORDINATOR
        saved = save_global_preference(pref_text, agent_id=aid, staff_id=staff_id)
        return {
            "ok": bool(saved.get("ok")),
            "markdown": f"已记录全局风格偏好（{aid.value}）：{saved.get('document')}",
            "preference": saved,
            "reports": [],
        }

    # 复盘
    if hit.intent == "review" or text.startswith("复盘"):
        from backpack_quant_trading.agents.review_agent import format_review_markdown, review

        syms = hit.symbols or extract_symbols(hit.rest or text)
        if not syms:
            return {"ok": False, "markdown": "复盘请带上标的，例如：复盘 NVDA", "reports": []}
        parts = []
        reviews = []
        for sym, mkt in syms:
            r = review(sym, market=mkt.value)
            reviews.append(r)
            parts.append(format_review_markdown(r))
        return {"ok": True, "markdown": "\n\n".join(parts), "reviews": reviews, "reports": []}

    # 风控：审查过激表述，或对标的跑分析后只返回风控结论；「放行」可 force_allow
    if hit.intent == "risk":
        from backpack_quant_trading.agents.risk_agent import apply_risk, evaluate_risk
        from backpack_quant_trading.agents.formatters import format_report_markdown

        force = "放行" in (hit.rest or text)
        syms = hit.symbols or extract_symbols(hit.rest or text)
        if syms:
            reports = []
            for sym, mkt in syms:
                report = _run_analyst(sym, mkt, text, staff_id=staff_id)
                report = apply_risk(report, force_allow=force)
                reports.append(report)
            return {
                "ok": True,
                "markdown": format_multi_reports(reports, header="### 风控审查"),
                "reports": reports,
            }
        # 无标的：对用户文本做启发式审查
        probe = AnalyzeReport(
            agent_id=AgentId.RISK,
            symbol="TEXT",
            market=Market.UNKNOWN,
            action="buy",
            rationale=hit.rest or text,
            support=None,
        )
        rd = evaluate_risk(probe, force_allow=force)
        return {
            "ok": True,
            "markdown": (
                f"### 风控\n- **结论**: {'通过' if rd.decision == 'allow' else '拒绝'}\n"
                f"- **理由**: {rd.reason}\n- **模式**: {rd.mode}"
            ),
            "risk": rd.to_dict(),
            "reports": [],
        }

    # 信息检索
    if hit.intent == "research":
        from backpack_quant_trading.agents.research_agent import research
        from backpack_quant_trading.agents.types import Citation

        syms = hit.symbols or extract_symbols(hit.rest or text)
        if not syms:
            return {"ok": False, "markdown": "信息检索请带上标的，例如：@信息检索 NVDA", "reports": []}
        blocks = []
        for sym, mkt in syms:
            res = research(sym, mkt, limit=6)
            cites: List[Citation] = list(res.get("citations") or [])
            lines = [f"### 信息检索 · {sym}"]
            if res.get("degraded"):
                lines.append(f"- 降级: {res.get('error') or '无数据'}")
            for i, c in enumerate(cites[:6], 1):
                lines.append(f"{i}. [{c.source}] {c.title}")
            blocks.append("\n".join(lines))
        return {"ok": True, "markdown": "\n\n".join(blocks), "reports": []}

    # 分析（含拆单）
    syms = hit.symbols
    if not syms:
        return {
            "ok": False,
            "markdown": "未能识别标的。示例：`@美股分析师 NVDA` 或 `看看茅台+BTC`",
            "reports": [],
            "route": hit,
        }

    reports: List[AnalyzeReport] = []
    pending_notes: List[str] = []
    for sym, mkt in syms:
        try:
            report = _run_analyst(sym, mkt, text, staff_id=staff_id)
            report = apply_risk(report)
            if propose_execution and report.action in ("buy", "sell") and (
                not report.risk or report.risk.decision == "allow"
            ):
                from backpack_quant_trading.agents.execution_agent import propose_order

                prop = propose_order(report, staff_id=staff_id)
                if prop.get("ok"):
                    pending_notes.append(
                        format_report_markdown(report, pending_id=prop["pending_id"])
                    )
                reports.append(report)
                continue
            reports.append(report)
        except Exception as exc:
            logger.exception("analyst failed %s: %s", sym, exc)
            reports.append(
                AnalyzeReport(
                    agent_id=AgentId.COORDINATOR,
                    symbol=sym,
                    market=mkt,
                    action="hold",
                    rationale=f"分析异常: {exc}",
                    error=str(exc),
                    degraded=True,
                )
            )

    if pending_notes and not reports:
        md = "\n\n".join(pending_notes)
    elif pending_notes:
        md = format_multi_reports(reports) + "\n\n" + "\n\n".join(pending_notes)
    else:
        md = format_multi_reports(reports)

    return {
        "ok": True,
        "markdown": md,
        "reports": reports,
        "route": {
            "intent": hit.intent,
            "agent_id": hit.agent_id.value,
            "symbols": [(s, m.value) for s, m in syms],
        },
    }
