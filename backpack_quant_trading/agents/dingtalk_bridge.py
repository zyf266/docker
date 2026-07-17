"""钉钉 ↔ Agent 编排桥接（与旧手动评分并存）。"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict

from backpack_quant_trading.agents.coordinator import extract_symbols, parse_route, strip_prefix
from backpack_quant_trading.agents.execution_agent import parse_confirm_command
from backpack_quant_trading.agents.memory import is_agent_preference_command

logger = logging.getLogger(__name__)

_AGENT_ROLE_RE = re.compile(
    r"(美股分析师|A股分析师|加密分析师|信息检索|风控|复盘|执行|协调)"
)


def agent_orch_enabled() -> bool:
    return os.getenv("AGENT_ORCH_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")


def mentions_agent_role(user_text: str) -> bool:
    """是否点名了多 Agent 角色（优先级高于旧「信号评分」）。"""
    return bool(_AGENT_ROLE_RE.search(user_text or ""))


def should_route_to_agent(user_text: str) -> bool:
    """判断是否走多 Agent 编排（优先于旧「评分」路径）。"""
    if not agent_orch_enabled():
        return False
    t = (user_text or "").strip()
    if not t:
        return False

    # 点名角色：一律走 Agent（即使同时写了「信号评分」）
    if mentions_agent_role(t):
        return True

    hit, _ = strip_prefix(t)
    if hit is not None:
        return True

    ok_confirm, _ = parse_confirm_command(t)
    if ok_confirm:
        return True

    if is_agent_preference_command(t):
        return True

    if t.startswith("复盘") or "复盘 " in t:
        return True

    syms = extract_symbols(t)
    if len(syms) >= 2:
        return True

    # 自然语言分析且带标的（无「评分」时走 Agent；带「评分/打分」留给旧路径）
    if any(k in t for k in ("看看", "分析一下", "帮我看", "怎么看")) and syms:
        if not any(k in t for k in ("评分", "打分", "score")):
            return True

    if t.startswith("信息检索") or t.startswith("风控") or t.startswith("执行"):
        return True

    return False


def handle_agent_text(user_text: str, *, staff_id: str = "") -> Dict[str, Any]:
    from backpack_quant_trading.agents.coordinator import handle

    try:
        return handle(user_text, staff_id=staff_id, propose_execution=True)
    except Exception as exc:
        logger.exception("agent handle failed: %s", exc)
        return {"ok": False, "markdown": f"Agent 处理失败：{exc}", "reports": []}


def usage_hint() -> str:
    return (
        "【Agent】@美股分析师 NVDA / @A股分析师 茅台 / @加密分析师 BTC\n"
        "拆单：看看茅台+BTC | 检索：@信息检索 NVDA | 复盘 NVDA\n"
        "纠正偏好：纠正偏好：更严止损 | 下单：确认\n"
        "【旧评分】评一下分 / 对 TSM 2h 买入 评分（不要点名「xx分析师」）"
    )
