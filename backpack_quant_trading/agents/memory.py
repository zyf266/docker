"""全局风格偏好：写入 agent_prefs，检索不按 symbol 过滤。"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Any, Dict, List, Optional

from backpack_quant_trading.core.agent_memory_store import query_memory, upsert_memory
from backpack_quant_trading.agents.types import AgentId

logger = logging.getLogger(__name__)

# 仅明确「纠正偏好」前缀，或「@分析师 + 纠正句式」才写入全局偏好（避免误抢分析）
_PREF_PREFIX = re.compile(r"^纠正偏好\s*[:：]?\s*", re.I)
_CORRECTION_HINTS = (
    "偏保守",
    "偏激进",
    "太保守",
    "太激进",
    "更严止损",
    "少追高",
    "多看基本面",
    "以后都",
)


def is_agent_preference_command(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if _PREF_PREFIX.match(t):
        return True
    # @美股分析师 你太保守了 / 纠正：更严止损
    plain = re.sub(r"^@?(美股|A股|加密)分析师\s*", "", t).strip()
    if plain.startswith("纠正") or plain.startswith("纠正："):
        return True
    if any(h in plain for h in ("你太保守", "你太激进", "太偏保守", "太偏激进")):
        return True
    # 必须同时有「纠正/觉得应该」类词 + 风格提示，避免「NVDA 风格」误判
    if any(h in plain for h in _CORRECTION_HINTS) and any(
        k in plain for k in ("纠正", "以后", "偏好", "请记住", "记住")
    ):
        return True
    return False


def _pref_id(agent_id: str, staff_id: str, text: str) -> str:
    raw = f"{agent_id}|{staff_id}|{text.strip()}|{int(time.time())}"
    return "pref_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def save_global_preference(
    text: str,
    *,
    agent_id: str | AgentId = AgentId.COORDINATOR,
    staff_id: str = "",
) -> Dict[str, Any]:
    aid = agent_id.value if isinstance(agent_id, AgentId) else str(agent_id or "coordinator")
    body = (text or "").strip()
    body = _PREF_PREFIX.sub("", body).strip() or body
    body = re.sub(r"^纠正\s*[:：]?\s*", "", body).strip() or body
    if not body:
        return {"ok": False, "error": "空偏好文本"}

    mid = _pref_id(aid, staff_id, body)
    doc = f"[全局风格偏好] agent={aid} | {body}"
    meta = {
        "scope": "global",
        "agent_id": aid,
        "staff_id": staff_id or "",
        "kind": "preference",
        "ts": int(time.time()),
    }
    ok = upsert_memory("agent_prefs", mid, doc, meta)
    return {"ok": ok, "id": mid, "agent_id": aid, "document": doc}


def retrieve_global_preferences(
    agent_id: str | AgentId = "",
    query: str = "交易风格 止损 仓位 偏好",
    *,
    n: int = 5,
) -> List[Dict[str, Any]]:
    """全局检索：可用 agent_id 过滤，但绝不按 symbol 过滤。"""
    aid = agent_id.value if isinstance(agent_id, AgentId) else str(agent_id or "")
    filters: Optional[Dict[str, Any]] = {"scope": "global"}
    if aid:
        filters = {"scope": "global", "agent_id": aid}
    rows = query_memory("agent_prefs", query or "风格偏好", n_results=n, filters=filters)
    if not rows and aid:
        rows = query_memory(
            "agent_prefs",
            query or "风格偏好",
            n_results=n,
            filters={"scope": "global"},
        )
    return rows


def format_preferences_for_prompt(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return ""
    lines = ["## 用户全局风格偏好（必须遵守）"]
    for r in rows:
        lines.append(f"- {r.get('document') or ''}")
    return "\n".join(lines)
