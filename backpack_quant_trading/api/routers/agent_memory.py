"""跨 Agent 记忆只读面板 API。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from backpack_quant_trading.api.deps import require_user
from backpack_quant_trading.core.agent_memory_store import (
    KIND_TO_COLLECTION,
    count_memory,
    query_memory,
)
from backpack_quant_trading.core.score_feedback_store import count_feedbacks, query_similar

router = APIRouter()


@router.get("/stats")
def memory_stats(user: dict = Depends(require_user)) -> Dict[str, Any]:
    kinds = sorted(set(KIND_TO_COLLECTION.values()))
    counts = {k: count_memory(k) for k in kinds}
    counts["score_feedback"] = count_feedbacks()
    return {"ok": True, "counts": counts, "kinds": kinds + ["score_feedback"]}


@router.get("/query")
def memory_query(
    user: dict = Depends(require_user),
    kind: str = Query("agent_reports", description="memory kind 或 score_feedback"),
    q: str = Query(..., min_length=1),
    symbol: Optional[str] = Query(""),
    n: int = Query(8, ge=1, le=20),
) -> Dict[str, Any]:
    k = (kind or "").strip()
    sym = (symbol or "").strip().upper()
    if k in ("score_feedback", "feedback"):
        rows = query_similar(q, n_results=n, symbol=sym)
        return {"ok": True, "kind": "score_feedback", "items": rows}
    filters = {"symbol": sym} if sym else None
    rows = query_memory(k, q, n_results=n, filters=filters)
    return {"ok": True, "kind": k, "items": rows}
