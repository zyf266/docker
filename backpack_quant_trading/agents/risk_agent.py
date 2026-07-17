"""风控 Agent：一期启发式（mode=heuristic_v1）。"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from backpack_quant_trading.agents.types import AnalyzeReport, RiskDecision


def evaluate_risk(
    report: AnalyzeReport,
    *,
    account: Optional[Dict[str, Any]] = None,
    force_allow: bool = False,
) -> RiskDecision:
    if force_allow:
        return RiskDecision(decision="allow", reason="用户要求放行", mode="heuristic_v1")

    text = f"{report.rationale or ''} {report.action or ''} {report.raw}"
    reasons: list[str] = []

    # 过高杠杆暗示
    for m in re.finditer(r"(\d{2,})\s*[xX倍]", text):
        lev = int(m.group(1))
        if lev >= 50:
            reasons.append(f"杠杆暗示过高（{lev}x≥50）")
            break

    # 满仓 / 梭哈
    if any(k in text for k in ("满仓", "梭哈", "All-in", "all in", "全仓买入", "一把梭")):
        reasons.append("含满仓/梭哈类表述")

    # buy 但无止损/支撑
    if (report.action or "").lower() == "buy":
        if report.support is None and "止损" not in text:
            reasons.append("买入建议缺少支撑位/止损说明")
        # 支撑相对压力过近且无 rationale 保护 — 跳过

    # 与「更严止损」偏好冲突：建议追高且无支撑
    if "追高" in text and (report.action or "").lower() == "buy":
        reasons.append("建议疑似追高")

    # account 可选：单日次数等（占位）
    if account:
        daily = int(account.get("daily_orders") or 0)
        if daily >= int(account.get("daily_order_limit") or 20):
            reasons.append(f"当日下单次数已达上限（{daily}）")

    if reasons:
        return RiskDecision(
            decision="reject",
            reason="；".join(reasons),
            mode="heuristic_v1",
        )
    return RiskDecision(decision="allow", reason="启发式检查通过", mode="heuristic_v1")


def apply_risk(report: AnalyzeReport, **kwargs) -> AnalyzeReport:
    decision = evaluate_risk(report, **kwargs)
    report.risk = decision
    if decision.decision == "reject" and (report.action or "").lower() != "reject":
        report.raw = dict(report.raw or {})
        report.raw["action_before_risk"] = report.action
        report.action = "reject"
        report.rationale = (report.rationale or "") + f"\n【风控拒绝】{decision.reason}"
    return report
