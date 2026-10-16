"""MA 5/30/200 标签看板。"""
from typing import List

from fastapi import APIRouter, Depends, Query

from backpack_quant_trading.api.deps import require_user
from backpack_quant_trading.core.ma_label_board import load_board

router = APIRouter()


@router.get("")
def get_board(
    symbols: str = Query("", description="逗号分隔；留空则返回库里全部币种"),
    user: dict = Depends(require_user),
) -> dict:
    parts: List[str] = [p.strip() for p in (symbols or "").split(",") if p.strip()]
    data = load_board(parts)
    return {"ok": True, **data}
