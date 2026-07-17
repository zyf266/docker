#!/usr/bin/env python3
"""Agent 一期验收烟雾测试（默认 MOCK LLM，不真下单）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("AGENT_E2E_MOCK_LLM", "1")
os.environ.setdefault("AGENT_MEMORY_CHROMA_ENABLED", "1")
os.environ.setdefault("AGENT_ORCH_ENABLED", "1")
# 使用独立测试目录，避免污染生产 Chroma
os.environ.setdefault(
    "SCORE_FEEDBACK_CHROMA_PATH",
    str(ROOT / "backpack_quant_trading" / "data" / "chroma_agent_e2e"),
)


def _pass(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        raise SystemExit(1)


def main() -> None:
    from backpack_quant_trading.agents.types import AgentId, AnalyzeRequest, AnalyzeReport, Market
    from backpack_quant_trading.agents.analysts import analyze_a_share, analyze_crypto, analyze_us
    from backpack_quant_trading.agents.coordinator import extract_symbols, handle, parse_route
    from backpack_quant_trading.agents.dingtalk_bridge import should_route_to_agent
    from backpack_quant_trading.agents.execution_agent import confirm_order, propose_order
    from backpack_quant_trading.agents.memory import retrieve_global_preferences, save_global_preference
    from backpack_quant_trading.agents.research_agent import research
    from backpack_quant_trading.agents.risk_agent import apply_risk, evaluate_risk
    from backpack_quant_trading.agents.scheduler_hooks import run_agent_signal_hook

    # 1) 三市场报告字段
    ru = analyze_us(AnalyzeRequest(symbol="NVDA", include_research=False))
    ra = analyze_a_share(AnalyzeRequest(symbol="600519", include_research=False))
    rc = analyze_crypto(AnalyzeRequest(symbol="BTC", include_research=False))
    _pass(
        "三市场分析报告",
        all(x.action and (x.support is not None) and (x.resistance is not None) for x in (ru, ra, rc)),
        f"us={ru.action}/{ru.support} a={ra.action}/{ra.support} c={rc.action}/{rc.support}",
    )

    # 2) 检索结构（允许降级）
    res = research("NVDA", Market.US_STOCK, limit=3, persist=False)
    _pass(
        "信息检索结构",
        "citations" in res and isinstance(res["citations"], list),
        f"degraded={res.get('degraded')} n={len(res.get('citations') or [])}",
    )

    # 3) 全局偏好可迁移到其它标的检索
    save_global_preference("纠正偏好：更严止损，少追高", agent_id=AgentId.US_ANALYST, staff_id="e2e")
    hits = retrieve_global_preferences(AgentId.US_ANALYST, query="AAPL 怎么看", n=5)
    _pass(
        "全局偏好可迁移",
        any("更严止损" in (h.get("document") or "") for h in hits),
        f"hits={len(hits)}",
    )

    # 4) 茅台+BTC 拆单
    syms = extract_symbols("看看茅台+BTC")
    route = parse_route("看看茅台+BTC")
    _pass(
        "协调拆单茅台+BTC",
        len(syms) >= 2 and len(route.symbols) >= 2,
        str([(s, m.value) for s, m in route.symbols]),
    )

    # 5) 风控拒单
    bad = AnalyzeReport(
        agent_id=AgentId.CRYPTO_ANALYST,
        symbol="BTC",
        market=Market.CRYPTO,
        action="buy",
        rationale="建议 100x 满仓梭哈",
        support=None,
    )
    rd = evaluate_risk(bad)
    _pass("风控拒绝过激信号", rd.decision == "reject", rd.reason)

    # 6) propose pending + staff 隔离 + payload 含 signal
    good = apply_risk(
        AnalyzeReport(
            agent_id=AgentId.US_ANALYST,
            symbol="NVDA",
            market=Market.US_STOCK,
            action="buy",
            rationale="稳健建仓，止损看支撑",
            support=100.0,
            resistance=120.0,
        )
    )
    prop = propose_order(good, staff_id="e2e")
    hijack = confirm_order(prop.get("pending_id") or "", staff_id="other", dry_run=True)
    conf = confirm_order(prop.get("pending_id") or "", staff_id="e2e", dry_run=True)
    payload = conf.get("payload") or {}
    _pass(
        "执行待确认订单",
        bool(prop.get("ok")) and bool(conf.get("ok")) and conf.get("dry_run") is True,
        prop.get("pending_id"),
    )
    _pass("确认订单防劫持", hijack.get("ok") is False, str(hijack.get("error") or "")[:60])
    _pass(
        "webhook payload 含 signal",
        payload.get("signal") in ("buy", "sell") and payload.get("agent_execution") is True,
        str(payload.get("signal")),
    )

    # TradingViewSignal 校验
    from backpack_quant_trading.engine.webhook_trading import TradingViewSignal

    try:
        TradingViewSignal(
            signal=payload["signal"],
            symbol=payload["symbol"],
            action=payload.get("action"),
            ticker=payload.get("ticker"),
            strategy_name=payload.get("strategy_name"),
            indicator=payload.get("indicator"),
            instance_id=payload.get("instance_id") or "test_inst",
        )
        tv_ok = True
    except Exception as exc:
        tv_ok = False
        print("TV validate err", exc)
    _pass("TradingViewSignal 可解析", tv_ok)

    # 偏好命令收紧：分析句不应被当成偏好
    from backpack_quant_trading.agents.memory import is_agent_preference_command

    _pass(
        "偏好识别不误伤分析",
        not is_agent_preference_command("@美股分析师 NVDA 风格偏保守"),
    )
    _pass(
        "偏好识别纠正前缀",
        is_agent_preference_command("纠正偏好：更严止损"),
    )

    # 钉钉路由桥
    _pass("钉钉路由识别Agent", should_route_to_agent("@美股分析师 NVDA"))
    _pass("钉钉路由不误伤空串", not should_route_to_agent(""))

    # 定时钩子 dry-run
    hook = run_agent_signal_hook("NVDA", market="us_stock", dry_run=True)
    _pass("信号钩子dry-run", "markdown" in hook, f"ok={hook.get('ok')}")

    # 轻量 handle 拆单（mock，可能较慢）
    out = handle("看看茅台+BTC", propose_execution=False)
    _pass(
        "handle拆单产出",
        bool(out.get("ok")) and len(out.get("reports") or []) >= 2,
        f"reports={len(out.get('reports') or [])}",
    )

    print("\n全部验收项 PASS")


if __name__ == "__main__":
    main()
