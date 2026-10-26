"""MA 5/30/200 标签看板。"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backpack_quant_trading.api.deps import require_admin, require_user
from backpack_quant_trading.core.ma_label_board import (
    add_board_symbol,
    ingest_webhook_payload,
    list_board_symbols,
    load_board,
    remove_board_symbol,
)

router = APIRouter()


class SymbolIn(BaseModel):
    symbol: str = Field(..., min_length=1, description="如 BTC 或 BTCUSDT")


@router.get("")
def get_board(
    symbols: str = Query("", description="逗号分隔；留空则返回看板币种列表"),
    user: dict = Depends(require_user),
) -> dict:
    parts: List[str] = [p.strip() for p in (symbols or "").split(",") if p.strip()]
    data = load_board(parts)
    return {"ok": True, **data}


@router.post("/tv-webhook")
async def ma_label_tv_webhook(request: Request) -> dict:
    """TradingView → 标签看板（无需登录，不走钉钉）。

    写入 ma_label_snapshots；同币种同周期只展示最新一条。
    """
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无效 JSON: {e}") from e
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体须为 JSON 对象")
    try:
        return ingest_webhook_payload(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"写入失败: {e}") from e


@router.get("/tv-webhook/hint")
def ma_label_tv_webhook_hint(user: dict = Depends(require_user)) -> dict:
    return {
        "ok": True,
        "path": "/api/ma-label-board/tv-webhook",
        "method": "POST",
        "example": {
            "symbol": "BTCUSDT",
            "interval": "30m",
            "close": 64880,
            "ma5": 64610,
            "ma30": 64120,
            "ma200": 61840,
            "score": 5,
            "pos_score": 3,
            "align_score": 2,
            "sug_pos": 100,
            "state": "strong_bull",
            "state_cn": "极强多头",
            "direction": "buy",
        },
    }


@router.get("/symbols")
def get_symbols(user: dict = Depends(require_user)) -> dict:
    return {"ok": True, "items": list_board_symbols()}


@router.post("/symbols")
def post_symbol(body: SymbolIn, user: dict = Depends(require_admin)) -> dict:
    try:
        sym = add_board_symbol(body.symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "symbol": sym, "items": list_board_symbols()}


@router.delete("/symbols/{symbol}")
def delete_symbol(symbol: str, user: dict = Depends(require_admin)) -> dict:
    ok = remove_board_symbol(symbol)
    if not ok:
        raise HTTPException(status_code=404, detail="币种不在看板中")
    return {"ok": True, "items": list_board_symbols()}
