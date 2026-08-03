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

    # A股中文名（利通电子 / 茅台 等）—— 已有加密/美股 ticker 且无中文时跳过，避免拉全表
    has_cn = bool(re.search(r"[\u4e00-\u9fff]{2,}", t))
    if has_cn and not any(m == Market.A_SHARE for _, m in found):
        try:
            from backpack_quant_trading.agents.a_share_resolve import extract_a_share_from_text

            hit_a = extract_a_share_from_text(t)
            if hit_a:
                code, _name = hit_a
                key = (code, Market.A_SHARE)
                if key not in seen:
                    seen.add(key)
                    found.append(key)
        except Exception:
            pass

    # 美股 / 加密 ticker：仅匹配独立 token，并过滤常见英文词
    _STOP = {
        "USDT", "USD", "HTTP", "HTTPS", "JSON", "AI", "API", "CEO", "ETF",
        "THE", "AND", "FOR", "WITH", "FROM", "THIS", "THAT", "HAVE", "WILL",
    }
    # Webhook/口语常见：INTC 30 做多 / MU 2h 买入 —— 无「分析」也认 ticker
    _SIGNAL_CTX = bool(
        re.search(
            r"(?<![A-Za-z0-9])([A-Z]{1,5})(?![A-Za-z0-9])\s*(\d{1,4}\s*[HhMmDdWw]|做多|做空|开仓|买入|卖出|评分)",
            t.upper(),
        )
        or any(k in t for k in ("分析", "看看", "怎么看", "评分", "分析师", "做多", "做空", "开仓"))
    )
    for m in re.finditer(r"(?<![A-Za-z0-9])([A-Z]{2,5})(?![A-Za-z0-9])", t.upper()):
        tok = m.group(1)
        if tok in _STOP:
            continue
        if tok in ("BTC", "ETH", "SOL", "BNB", "DOGE", "XRP", "HYPE", "TAO"):
            key = (tok, Market.CRYPTO)
        elif tok in _ALIASES or len(tok) >= 2:
            # 仅当是已知别名，或文本里明确分析/信号语境才当美股 ticker
            if tok in {a.upper() for a in _ALIASES if a.isascii()} or _SIGNAL_CTX:
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
    # 先解析 rest；空则回退全文（保留「@美股分析师」等关键词，避免 CRCL 等非别名 ticker 被丢弃）
    syms = extract_symbols(hit.rest or text)
    if not syms and hit.rest and hit.rest != text:
        syms = extract_symbols(text)
    if hit.market != Market.UNKNOWN and not syms:
        # 前缀指定市场但未解析出标的：清理「分析一下」后再解析 / 当代码
        from backpack_quant_trading.agents.a_share_resolve import (
            extract_a_share_from_text,
            strip_query_noise,
        )

        rest = hit.rest or ""
        if hit.market == Market.A_SHARE:
            hit_a = extract_a_share_from_text(rest) or extract_a_share_from_text(text)
            if hit_a:
                syms = [(hit_a[0], Market.A_SHARE)]
        if not syms:
            token = strip_query_noise(rest)
            # 仅接受 6 位代码或短 ticker，禁止整句中文当 symbol
            if re.fullmatch(r"\d{6}", token or ""):
                syms = [(token, hit.market)]
            elif re.fullmatch(r"[A-Za-z]{1,5}", token or ""):
                syms = [(token.upper(), hit.market)]
            else:
                # Webhook 新链路常见：CRCL 2h 做多开仓 —— 取首个独立 ticker
                m = re.search(r"(?<![A-Za-z0-9])([A-Za-z]{1,5})(?![A-Za-z0-9])", rest)
                if m:
                    tok = m.group(1).upper()
                    if tok not in {
                        "USDT", "USD", "HTTP", "HTTPS", "JSON", "AI", "API", "CEO", "ETF",
                        "BUY", "SELL", "LONG", "SHORT",
                    }:
                        syms = [(tok, hit.market)]
    elif hit.market != Market.UNKNOWN and syms:
        # 强制市场覆盖（前缀优先）
        syms = [(s, hit.market) for s, _ in syms]
    hit.symbols = syms
    return hit


def extract_timeframe(text: str) -> str:
    """从用户文案解析周期：2H / 2h / 4小时 / 15m / 日线 等。"""
    t = text or ""
    # 显式：2H、4h、15m、1d、1w
    m = re.search(r"(?<![A-Za-z0-9])(\d{1,4})\s*([HhDdWwMm]|小时|分钟|日|周)(?![A-Za-z])", t)
    if m:
        n, u = m.group(1), m.group(2)
        u_l = u.lower()
        if u in ("小时",) or u_l == "h":
            return f"{n}h"
        if u in ("分钟",) or u_l == "m":
            return f"{n}m"
        if u in ("日",) or u_l == "d":
            return f"{n}d" if n != "1" else "1d"
        if u in ("周",) or u_l == "w":
            return "1w"
    # 中文别名
    aliases = {
        "日线": "1d",
        "周线": "1w",
        "小时线": "1h",
        "两小时": "2h",
        "四小时": "4h",
        "十五分钟": "15m",
        "五分钟": "5m",
    }
    for k, v in aliases.items():
        if k in t:
            return v
    return ""


def _is_bubble_weekly_request(text: str) -> bool:
    """识别「这周美股/A股周报 / 泡沫阶段」类指令（无个股标的时走周报管线）。"""
    t = (text or "").strip()
    if not t:
        return False
    # 策略A个股报告优先，不走泡沫周报
    if re.search(r"策略\s*[Aa]", t) and ("报告" in t or "分析" in t):
        return False
    if "周报" in t or "泡沫阶段" in t or "泡沫监测" in t:
        return True
    if re.search(r"(这周|本周).{0,16}(美股|A股|市场|泡沫)", t):
        return True
    if re.search(r"(美股|A股).{0,16}(这周|本周)", t) and any(
        k in t for k in ("分析", "复盘", "怎么看", "点评")
    ):
        return True
    return False


def _parse_stock_strategy_request(text: str) -> Optional[tuple]:
    """识别「利通电子 策略A的报告」/「NVDA 策略B」→ (strategy_id, raw_symbol_hint)。"""
    t = (text or "").strip()
    if not t:
        return None
    sid = None
    m = re.search(r"策略\s*([A-Za-z])", t)
    if m:
        sid = m.group(1).upper()
    elif re.search(r"(供应链|个股深度|L\s*1\s*[-~到至]\s*L\s*7)", t, re.I) and (
        "报告" in t or "分析" in t
    ):
        sid = "A"
    elif ("报告" in t or "深度分析" in t) and re.search(
        r"(给我|帮我|来一|生成|出一).{0,12}(份|篇)?", t
    ):
        # 「给我一份利通电子的报告」或「给我一份 NVDA 的报告」
        from backpack_quant_trading.agents.a_share_resolve import extract_a_share_from_text

        if extract_a_share_from_text(t):
            sid = "A"
        elif re.search(r"(?<![A-Za-z0-9])([A-Z]{2,5})(?![A-Za-z0-9])", t.upper()) and (
            "美股" in t or "个股" in t or "分析" in t or "报告" in t
        ):
            sid = "A"
    if not sid:
        return None
    return sid, t


def _resolve_weekly_market(text: str, hit: RouteHit) -> Optional[str]:
    """返回 us / a_share；无法判断时 None。"""
    if hit.market == Market.A_SHARE:
        return "a_share"
    if hit.market == Market.US_STOCK:
        return "us"
    t = text or ""
    if "A股" in t or "沪深" in t or "上证" in t:
        return "a_share"
    if "美股" in t or "纳指" in t or "标普" in t:
        return "us"
    return None


def _run_analyst(symbol: str, market: Market, user_text: str, staff_id: str = "") -> AnalyzeReport:
    import os

    # 钉钉问答默认关掉 Jin10 研究（可 AGENT_INCLUDE_RESEARCH=1 打开），省约 10s
    research_on = os.getenv("AGENT_INCLUDE_RESEARCH", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    req = AnalyzeRequest(
        symbol=symbol,
        market=market,
        user_text=user_text,
        timeframe=extract_timeframe(user_text),
        staff_id=staff_id,
        include_research=research_on,
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

    # 确认 / 取消 / 待确认列表
    from backpack_quant_trading.agents.execution_agent import (
        cancel_order,
        confirm_order,
        format_pending_list_markdown,
        list_pending,
        parse_exec_command,
    )

    kind, pid = parse_exec_command(text)
    if kind == "confirm":
        res = confirm_order(pid, staff_id=staff_id, dry_run=False)
        md = res.get("message") or res.get("error") or str(res)
        return {"ok": bool(res.get("ok")), "markdown": md, "execution": res, "reports": []}
    if kind == "cancel":
        res = cancel_order(pid, staff_id=staff_id)
        md = res.get("message") or res.get("error") or str(res)
        return {"ok": bool(res.get("ok")), "markdown": md, "execution": res, "reports": []}
    if kind == "list":
        res = list_pending(staff_id=staff_id)
        return {
            "ok": True,
            "markdown": format_pending_list_markdown(res),
            "execution": res,
            "reports": [],
        }

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
        from backpack_quant_trading.agents.risk_agent import evaluate_risk

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

    # 策略A/B 个股深度报告：给我一份利通电子 策略A的报告 / NVDA 策略B
    strat_req = _parse_stock_strategy_request(text)
    if strat_req:
        sid, _hint = strat_req
        from backpack_quant_trading.agents.a_share_resolve import extract_a_share_from_text

        stock = extract_a_share_from_text(text)
        market_key = "a_share"
        if not stock and hit.symbols:
            for sym, mkt in hit.symbols:
                if mkt == Market.A_SHARE or re.fullmatch(r"\d{6}", sym or ""):
                    stock = (sym, sym)
                    market_key = "a_share"
                    break
                if mkt == Market.US_STOCK:
                    stock = (sym, sym)
                    market_key = "us"
                    break
        if not stock:
            # 再扫一遍独立美股 ticker（策略语境）
            m_us = re.search(r"(?<![A-Za-z0-9])([A-Za-z]{1,5})(?![A-Za-z0-9])", text or "")
            if m_us:
                tok = m_us.group(1).upper()
                if tok not in {"USDT", "USD", "HTTP", "JSON", "API", "CEO", "ETF", "THE", "AND", "FOR"}:
                    stock = (tok, tok)
                    market_key = "us"
        if not stock:
            return {
                "ok": False,
                "markdown": (
                    "请带上股票名称或代码。示例：\n"
                    "- `给我一份利通电子 策略A的报告`\n"
                    "- `@A股分析师 603629 策略A`\n"
                    "- `给我一份 NVDA 策略A的报告`\n"
                    "- `@美股分析师 TSLA 策略B`"
                ),
                "reports": [],
                "route": hit,
            }
        code, name = stock
        try:
            from backpack_quant_trading.api.routers.us_weekly_report import (
                run_stock_strategy_task,
                split_dingtalk_markdown,
                strip_disclaimer_markdown,
            )

            res = run_stock_strategy_task(
                symbol=code,
                strategy=sid,
                extra=f"钉钉指令：{(text or '')[:200]}",
                save=False,
                market=market_key,
            )
        except Exception as exc:
            logger.exception("stock strategy report failed: %s", exc)
            return {
                "ok": False,
                "markdown": f"策略{sid}个股报告生成失败：{exc}",
                "reports": [],
            }
        if not res.get("ok"):
            return {
                "ok": False,
                "markdown": f"策略{sid}个股报告生成失败：{res.get('error') or res}",
                "reports": [],
                "stock_report": res,
            }
        label = res.get("stock_name") or name or code
        code_show = res.get("symbol") or code
        head = (
            f"### 策略{sid} · {('百分配仓评分卡' if sid == 'B' else '供应链个股深度')}\n"
            f"- **标的**: {label}（{code_show}）\n"
            f"- **日期**: {res.get('report_date') or '—'}\n"
            f"- **摘要**: {res.get('one_liner') or '—'}\n\n"
            f"---\n\n"
        )
        raw_md = strip_disclaimer_markdown(res.get("markdown") or "")
        parts = split_dingtalk_markdown(head + raw_md, chunk_size=3500)
        if not parts:
            parts = [head + (raw_md or "（无正文）")]
        return {
            "ok": True,
            "markdown": parts[0],
            "markdown_parts": parts,
            "reports": [],
            "stock_report": {
                "strategy": sid,
                "symbol": code_show,
                "stock_name": label,
                "report_date": res.get("report_date"),
                "report_type": res.get("report_type"),
                "saved": False,
            },
        }

    # 泡沫阶段周报（无个股标的）：@美股分析师 这周美股周报 / @A股分析师 分析这周A股
    if _is_bubble_weekly_request(text) and not hit.symbols:
        market_key = _resolve_weekly_market(text, hit)
        if not market_key:
            return {
                "ok": False,
                "markdown": (
                    "请指定市场。示例：\n"
                    "- `@美股分析师 分析这周美股，给出这周美股周报`\n"
                    "- `@A股分析师 分析这周A股，给出这周A股周报`"
                ),
                "reports": [],
                "route": hit,
            }
        label = "美股" if market_key == "us" else "A股"
        try:
            from backpack_quant_trading.api.routers.us_weekly_report import run_weekly_analyze_task

            res = run_weekly_analyze_task(market_key)
        except Exception as exc:
            logger.exception("bubble weekly failed: %s", exc)
            return {
                "ok": False,
                "markdown": f"{label}泡沫周报生成失败：{exc}",
                "reports": [],
            }
        if not res.get("ok"):
            return {
                "ok": False,
                "markdown": f"{label}泡沫周报生成失败：{res.get('error') or res}",
                "reports": [],
                "weekly": res,
            }
        md_body = (res.get("markdown") or "").strip()
        head = (
            f"### {label}泡沫阶段周报 · {res.get('report_date') or ''}\n"
            f"- **市场状态**: {res.get('market_state') or '—'}\n"
            f"- **阶段**: {res.get('stage') or '—'}\n"
            f"- **总分**: {res.get('bubble_total_score')} / {res.get('bubble_total_max', 70)}\n"
            f"- **下周倾向**: {res.get('next_week_bias') or '—'}\n\n"
        )
        # 钉钉消息过长时截断正文，完整内容已落盘到后台「泡沫阶段监测」
        max_md = 3500
        if len(md_body) > max_md:
            md_body = md_body[:max_md] + "\n\n…（全文已写入后台「泡沫阶段监测」，此处截断）"
        return {
            "ok": True,
            "markdown": head + (md_body or "（无 Markdown 正文）"),
            "reports": [],
            "weekly": {
                "market": market_key,
                "report_date": res.get("report_date"),
                "bubble_total_score": res.get("bubble_total_score"),
                "stage": res.get("stage"),
            },
        }

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
