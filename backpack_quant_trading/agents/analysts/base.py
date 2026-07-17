"""分析师共用：RAG 偏好注入、DeepSeek JSON、mock、报告落库。"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from backpack_quant_trading.agents.memory import (
    format_preferences_for_prompt,
    retrieve_global_preferences,
)
from backpack_quant_trading.agents.research_agent import research as run_research
from backpack_quant_trading.agents.types import (
    AgentId,
    AnalyzeReport,
    AnalyzeRequest,
    Citation,
    Market,
)
from backpack_quant_trading.core.agent_memory_store import upsert_memory

logger = logging.getLogger(__name__)


def mock_llm_enabled() -> bool:
    return os.getenv("AGENT_E2E_MOCK_LLM", "").strip().lower() in ("1", "true", "yes")


def _extract_json_object(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


def call_analyst_llm(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    if mock_llm_enabled():
        nums = [float(x) for x in re.findall(r"last_close[=:]\s*([0-9.]+)", user_prompt)]
        px = nums[0] if nums else 100.0
        has_us = "美股联动快照" in user_prompt
        return {
            "ok": True,
            "structured": {
                "action": "buy",
                "support": round(px * 0.97, 4),
                "resistance": round(px * 1.03, 4),
                "rationale": "（mock）结合技术位、消息面与用户偏好的模拟分析",
                "summary": "（mock）结构偏多，建议轻仓试错，严格止损。",
                "score": 72,
                "grade": "B",
                "recommendation": "caution",
                "fundamentals_bias": "neutral",
                "news_bias": "insufficient",
                "news_comment": "（mock）新闻证据有限",
                "technical_bias": "bullish",
                "us_equity_overlay": "neutral" if has_us else "n_a",
                "us_equity_notes": "（mock）已注入美股快照" if has_us else "非联动窗",
                "strengths": ["结构未破坏", "贴近支撑"],
                "risks": ["波动加大", "消息面不确定"],
                "invalidation": f"跌破 {round(px * 0.97, 4)}",
                "stop_hint": f"跌破 {round(px * 0.97, 4)} 止损",
                "target_hint": f"反弹至 {round(px * 1.03, 4)} 减仓",
            },
            "model": "mock",
        }
    try:
        from backpack_quant_trading.core.crypto_signal_scorer import call_deepseek_json_score

        ds = call_deepseek_json_score(system_prompt, user_prompt, temperature=0.2)
        if not ds.get("ok"):
            return {"ok": False, "error": ds.get("error") or "DeepSeek 失败"}
        structured = ds.get("structured") or _extract_json_object(str(ds.get("markdown") or ""))
        return {
            "ok": True,
            "structured": structured if isinstance(structured, dict) else {},
            "raw": ds.get("markdown"),
            "model": ds.get("model"),
        }
    except Exception as exc:
        logger.exception("analyst llm failed: %s", exc)
        return {"ok": False, "error": str(exc)}


def build_user_prompt(
    *,
    symbol: str,
    market: Market,
    persona_hint: str,
    snapshot: Dict[str, Any],
    prefs_block: str,
    citations: List[Citation],
    user_text: str,
) -> str:
    cite_lines = []
    for i, c in enumerate(citations[:8], 1):
        cite_lines.append(f"{i}. [{c.source}] {c.title} | {c.snippet[:120]}")
    cites = "\n".join(cite_lines) if cite_lines else "（无检索新闻，请主要依据行情与基本面框架）"
    metrics = snapshot.get("metrics") or {}
    last_close = snapshot.get("last_close") or metrics.get("close") or metrics.get("last_close")
    us_overlay = snapshot.get("us_equity_overlay")
    us_block = ""
    if isinstance(us_overlay, dict):
        us_block = (
            "\n## 美股联动快照（加密分析必须参考）\n"
            f"{json.dumps(us_overlay, ensure_ascii=False)[:1800]}\n"
            f"摘要: {us_overlay.get('summary_text') or ''}\n"
        )

    return f"""请严格按 system 角色完成分析，只输出一个 JSON 对象。
你是{persona_hint}。

标的: {symbol}
市场: {market.value}
周期: {snapshot.get('interval') or ''}
用户问题: {user_text or "请给出买卖建议与支撑压力位"}
last_close: {last_close}
指标摘要: {json.dumps(metrics, ensure_ascii=False)[:2500]}
近期K线: {json.dumps(snapshot.get("recent_bars") or [], ensure_ascii=False)[:1500]}
{us_block}
{prefs_block}

## 检索新闻（可引用，勿编造）
{cites}
"""


def persist_report(report: AnalyzeReport) -> None:
    def _job() -> None:
        try:
            mid = "rpt_" + hashlib.sha1(
                f"{report.agent_id.value}|{report.symbol}|{int(time.time())}".encode()
            ).hexdigest()[:16]
            doc = (
                f"[{report.market.value}] {report.symbol} action={report.action} "
                f"support={report.support} resistance={report.resistance} | {report.rationale[:500]}"
            )
            upsert_memory(
                "agent_reports",
                mid,
                doc,
                {
                    "symbol": report.symbol.upper(),
                    "market": report.market.value,
                    "agent_id": report.agent_id.value,
                    "action": report.action,
                    "scope": "report",
                    "ts": int(time.time()),
                },
            )
        except Exception as exc:
            logger.debug("persist report failed: %s", exc)

    # 异步落库，避免首次 Chroma/onnx 下载阻塞钉钉回复
    threading.Thread(target=_job, daemon=True, name="agent-persist-report").start()


def _derive_grade_rec(action: str, score: Optional[float], structured: Dict[str, Any]) -> Tuple[str, str]:
    grade = str(structured.get("grade") or "").upper().strip()
    rec = str(structured.get("recommendation") or "").lower().strip()
    if grade not in ("A", "B", "C", "D", "F"):
        s = float(score or 0)
        if s >= 80:
            grade = "A"
        elif s >= 65:
            grade = "B"
        elif s >= 50:
            grade = "C"
        elif s >= 35:
            grade = "D"
        else:
            grade = "F"
    if rec not in ("execute", "caution", "reject"):
        a = (action or "").lower()
        if a == "reject":
            rec = "reject"
        elif a in ("buy", "sell"):
            rec = "execute" if (score or 0) >= 60 else "caution"
        else:
            rec = "caution"
    return grade, rec


def run_analyst_pipeline(
    req: AnalyzeRequest,
    *,
    agent_id: AgentId,
    market: Market,
    system_prompt: str,
    persona_hint: str,
    snapshot_fn,
) -> AnalyzeReport:
    symbol = (req.symbol or "").strip()
    citations: List[Citation] = []
    degraded = False
    research_err = ""

    if req.include_research:
        res = run_research(symbol, market, limit=6, persist=True)
        citations = list(res.get("citations") or [])
        if res.get("degraded"):
            degraded = True
            research_err = str(res.get("error") or "")

    prefs = retrieve_global_preferences(agent_id, query=req.user_text or f"{symbol} 风格", n=5)
    prefs_block = format_preferences_for_prompt(prefs)

    snapshot: Dict[str, Any] = {}
    snap_err = ""
    try:
        snapshot, snap_err = snapshot_fn(symbol, req)
    except Exception as exc:
        snap_err = str(exc)
        snapshot = {}

    if not snapshot:
        degraded = True
        snapshot = {"symbol": symbol, "last_close": None, "metrics": {}, "recent_bars": []}

    user_prompt = build_user_prompt(
        symbol=symbol,
        market=market,
        persona_hint=persona_hint,
        snapshot=snapshot,
        prefs_block=prefs_block,
        citations=citations,
        user_text=req.user_text,
    )
    llm = call_analyst_llm(system_prompt, user_prompt)
    if not llm.get("ok"):
        return AnalyzeReport(
            agent_id=agent_id,
            symbol=symbol,
            market=market,
            action="hold",
            rationale=f"分析失败: {llm.get('error') or snap_err or research_err}",
            citations=citations,
            error=str(llm.get("error") or ""),
            degraded=True,
            raw={"snapshot": snapshot},
        )

    st = dict(llm.get("structured") or {})
    action = str(st.get("action") or "hold").lower()
    if action not in ("buy", "sell", "hold", "reject"):
        action = "hold"

    def _f(key: str) -> Optional[float]:
        v = st.get(key)
        try:
            return float(v) if v is not None and v != "" else None
        except Exception:
            return None

    score = _f("score")
    grade, rec = _derive_grade_rec(action, score, st)
    st["grade"] = grade
    st["recommendation"] = rec
    if not st.get("summary"):
        st["summary"] = str(st.get("rationale") or "")[:280]

    rationale = str(st.get("rationale") or st.get("summary") or "")
    if research_err and degraded:
        rationale = (rationale + f"\n（检索降级: {research_err}）").strip()
    if snap_err and not snapshot.get("metrics"):
        rationale = (rationale + f"\n（行情降级: {snap_err}）").strip()

    report = AnalyzeReport(
        agent_id=agent_id,
        symbol=symbol,
        market=market,
        action=action,
        support=_f("support"),
        resistance=_f("resistance"),
        rationale=rationale,
        citations=citations,
        score=score,
        raw={
            "model": llm.get("model"),
            "structured": st,
            "snapshot": snapshot,
            "timeframe": snapshot.get("interval") or req.timeframe or "",
        },
        degraded=degraded,
        error=research_err if degraded and not citations else "",
    )
    persist_report(report)
    return report
