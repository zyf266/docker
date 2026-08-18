"""A股 AI 自适应策略 Agent API。"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backpack_quant_trading.api.deps import require_user
from backpack_quant_trading.core.a_share_ai_agent import (
    INTERVALS_ALLOWED,
    AShareAIAdaptiveAgent,
    append_feedback_draft,
    confirm_style_prefs,
    decide_once,
    get_agent_instance,
    get_fundamentals,
    load_confirmed_prefs,
    load_style_draft,
    mark_agent_user_stopped,
    restore_agent_from_db_if_needed,
    run_backtest,
    set_agent_instance,
)
from backpack_quant_trading.core.a_share_ai_agent_dingtalk import push_signal_action_card, resolve_agent_webhook
from backpack_quant_trading.database.models import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter()


class StartRequest(BaseModel):
    tasks: List[Dict[str, Any]] = Field(default_factory=list)


class DecideRequest(BaseModel):
    code: str
    name: str = ""
    interval: str = "30"
    push: bool = False


class RemoveRequest(BaseModel):
    code: str
    interval: str


class FeedbackRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    code: Optional[str] = None
    interval: Optional[str] = None


class BacktestRequest(BaseModel):
    code: str
    name: str = ""
    interval: str = "D"
    start: str = ""
    end: str = ""
    max_llm_calls: int = 12


@router.get("/meta")
def meta(user: dict = Depends(require_user)) -> Dict[str, Any]:
    return {
        "intervals": [{"id": i, "label": {"30": "30分钟", "60": "60分钟", "D": "日线"}[i]} for i in INTERVALS_ALLOWED],
        "webhook_configured": bool(resolve_agent_webhook()),
        "push_cutoff": "15:00",
        "fundamentals_ttl_hours": 24,
    }


def _lookup_pair(q: str) -> Optional[Tuple[str, str]]:
    raw = str(q or "").strip()[:40]
    if not raw:
        return None
    from backpack_quant_trading.agents.a_share_resolve import resolve_a_share_token

    return resolve_a_share_token(raw)


def _normalize_code_name(code: str, name: str) -> Tuple[str, str]:
    code = str(code or "").strip()
    name = str(name or "").strip()
    if not re.fullmatch(r"\d{6}", code) and name:
        hit = _lookup_pair(name)
        if hit:
            code, name = str(hit[0]), (hit[1] or name)
    if re.fullmatch(r"\d{1,6}", code):
        code = code.zfill(6)
    else:
        code = ""
    if code and (not name or name == code):
        hit = _lookup_pair(code)
        if hit:
            name = hit[1] or name
    return code, name


@router.get("/lookup")
def lookup(q: str = Query("", max_length=40), user: dict = Depends(require_user)) -> Dict[str, Any]:
    """代码↔名称：输入 600519 或 贵州茅台 / 茅台。"""
    hit = _lookup_pair(q)
    if not hit:
        return {"ok": False, "error": "未找到匹配标的"}
    code, name = hit
    return {"ok": True, "code": str(code).zfill(6), "name": str(name or "")}


@router.get("/status")
def status(user: dict = Depends(require_user)) -> Dict[str, Any]:
    inst = get_agent_instance()
    if not inst or not inst.running:
        inst = restore_agent_from_db_if_needed()
    if not inst:
        return {"running": False, "tasks": [], "task_count": 0, "recent": []}
    return inst.status()


@router.post("/start")
def start(req: StartRequest, user: dict = Depends(require_user)) -> Dict[str, Any]:
    new_tasks = []
    for t in req.tasks or []:
        code, name = _normalize_code_name(t.get("code") or "", t.get("name") or "")
        interval = str(t.get("interval") or "30")
        if not code or interval not in INTERVALS_ALLOWED:
            continue
        new_tasks.append(
            {
                "code": code,
                "name": name,
                "interval": interval,
            }
        )
    if not new_tasks:
        raise HTTPException(status_code=400, detail="请至少配置一个有效任务（code + 30/60/D）")

    old = get_agent_instance()
    merged = list(new_tasks)
    if old and old.tasks:
        seen = {(x["code"], x["interval"]) for x in merged}
        for t in old.tasks:
            key = (str(t.get("code")), str(t.get("interval")))
            if key not in seen:
                merged.append(t)
                seen.add(key)
    if old and old.running:
        old.stop()
    mark_agent_user_stopped(False)
    svc = AShareAIAdaptiveAgent(tasks=merged)
    set_agent_instance(svc)
    svc.start()
    DatabaseManager().save_a_share_ai_agent_config(json.dumps({"tasks": merged}, ensure_ascii=False))
    # 预热基本面
    for t in merged:
        try:
            get_fundamentals(t["code"])
        except Exception:
            pass
    return {"message": "已启动", **svc.status()}


@router.post("/stop")
def stop(user: dict = Depends(require_user)) -> Dict[str, Any]:
    inst = get_agent_instance()
    if inst and inst.running:
        inst.stop()
    set_agent_instance(None)
    mark_agent_user_stopped(True)
    DatabaseManager().delete_a_share_ai_agent_config()
    return {"message": "ok", "running": False}


@router.post("/remove-task")
def remove_task(req: RemoveRequest, user: dict = Depends(require_user)) -> Dict[str, Any]:
    inst = get_agent_instance() or restore_agent_from_db_if_needed()
    if not inst:
        raise HTTPException(status_code=404, detail="Agent 未运行")
    ok = inst.remove_task(req.code, req.interval)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到任务")
    remaining = list(inst.tasks)
    if not remaining:
        if inst.running:
            inst.stop()
        set_agent_instance(None)
        mark_agent_user_stopped(True)
        DatabaseManager().delete_a_share_ai_agent_config()
        return {"message": "已删光并停止", "running": False, "tasks": []}
    DatabaseManager().save_a_share_ai_agent_config(json.dumps({"tasks": remaining}, ensure_ascii=False))
    return {"message": "已删除", **inst.status()}


@router.post("/decide")
def decide(req: DecideRequest, user: dict = Depends(require_user)) -> Dict[str, Any]:
    code, name = _normalize_code_name(req.code, req.name)
    try:
        return decide_once(code=code, name=name, interval=req.interval, push=bool(req.push))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/test-dingtalk")
def test_dingtalk(user: dict = Depends(require_user)) -> Dict[str, Any]:
    sample = {
        "code": "600519",
        "name": "贵州茅台",
        "interval": "D",
        "interval_label": "日线",
        "as_of": "测试",
        "decision": {
            "action": "hold",
            "valid": True,
            "confidence": 0.42,
            "thesis": "这是一条测试卡片：基本面稳健，但量能未给出进攻信号，观望。",
            "volume_structure": {"state": "shrink", "divergence": "none", "trap_risk": "none"},
            "market_vs_stock": {"alignment": "unclear", "note": "测试"},
            "risk_notes": ["测试消息"],
        },
    }
    ok, msg = push_signal_action_card(sample)
    if not ok:
        raise HTTPException(status_code=502, detail=msg)
    return {"message": "ok", "detail": msg}


@router.get("/prefs")
def prefs(user: dict = Depends(require_user)) -> Dict[str, Any]:
    return {
        "confirmed": load_confirmed_prefs(),
        "draft": load_style_draft(),
    }


@router.post("/feedback")
def feedback(req: FeedbackRequest, user: dict = Depends(require_user)) -> Dict[str, Any]:
    append_feedback_draft(
        req.text,
        meta={"code": req.code, "interval": req.interval, "source": "web"},
    )
    return {"message": "已写入偏好草稿，待人工确认"}


@router.post("/prefs/confirm")
def prefs_confirm(user: dict = Depends(require_user)) -> Dict[str, Any]:
    prefs_data = confirm_style_prefs()
    return {"message": "已确认并生效", "confirmed": prefs_data}


@router.post("/backtest")
def backtest(req: BacktestRequest, user: dict = Depends(require_user)) -> Dict[str, Any]:
    code, name = _normalize_code_name(req.code, req.name)
    try:
        return run_backtest(
            code=code,
            name=name,
            interval=req.interval,
            start=req.start,
            end=req.end,
            max_llm_calls=max(3, min(int(req.max_llm_calls or 12), 40)),
        )
    except Exception as e:
        logger.exception("backtest failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
