"""小管家 API：钉钉 Agent 转发自然语言 → 后台监视配置。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backpack_quant_trading.api.deps import require_steward

router = APIRouter()


class StewardCommandBody(BaseModel):
    text: str = Field(..., min_length=1, description="用户原话，可含 @小管家")
    staff_id: Optional[str] = ""


@router.post("/command")
def steward_command(body: StewardCommandBody, user: dict = Depends(require_steward)) -> Dict[str, Any]:
    from backpack_quant_trading.agents.steward_agent import handle_steward

    result = handle_steward(body.text, staff_id=body.staff_id or "")
    return {
        "ok": bool(result.get("ok")),
        "markdown": result.get("markdown") or "",
        "steward": user.get("username"),
    }
