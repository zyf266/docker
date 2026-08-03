"""小管家：钉钉操作实盘实例（按 AGENT_STEWARD_TRADE_USER_ID 隔离）。"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def resolve_steward_trade_user_id() -> Optional[int]:
    raw = (os.getenv("AGENT_STEWARD_TRADE_USER_ID") or "").strip()
    if raw.isdigit():
        return int(raw)
    try:
        from backpack_quant_trading.database.models import db_manager

        # 取第一个 admin；否则第一个用户
        users = []
        try:
            users = list(db_manager.list_users() or [])
        except Exception:
            try:
                # 兼容无 list_users
                session = db_manager.get_session()
                from backpack_quant_trading.database.models import User

                users = session.query(User).order_by(User.id.asc()).limit(20).all()
                session.close()
            except Exception as exc:
                logger.warning("resolve steward trade user failed: %s", exc)
                return None
        for u in users:
            role = getattr(u, "role", "") or ""
            if str(role).lower() in ("admin", "administrator"):
                return int(u.id)
        if users:
            return int(users[0].id)
    except Exception as exc:
        logger.warning("resolve steward trade user: %s", exc)
    return None


def _user_dict() -> Dict[str, Any]:
    uid = resolve_steward_trade_user_id()
    if uid is None:
        raise RuntimeError("未配置 AGENT_STEWARD_TRADE_USER_ID，且无法解析默认用户")
    return {"id": uid, "username": "小管家", "role": "steward"}


def list_instances_brief() -> Dict[str, Any]:
    user = _user_dict()
    from backpack_quant_trading.api.routers.trading import list_instances

    # FastAPI Depends 绕过：直接调内部逻辑会失败，改为复制 list 核心
    from backpack_quant_trading.database.models import DatabaseManager

    db = DatabaseManager()
    my_ids = set(db.get_user_instance_ids(user["id"], "live") or [])
    configs = {iid: cfg for iid, cfg in db.get_user_instance_configs(user["id"], "live")}
    rows: List[Dict[str, Any]] = []
    for iid in sorted(my_ids):
        import json

        obj = {}
        try:
            obj = json.loads(configs.get(iid) or "{}")
        except Exception:
            pass
        status = str(obj.get("status") or obj.get("run_status") or "unknown")
        rows.append(
            {
                "id": iid,
                "strategy": obj.get("strategy_name") or obj.get("strategy") or "",
                "symbol": obj.get("symbol") or "",
                "margin_type": obj.get("margin_type") or "",
                "status": status,
                "exchange": obj.get("exchange") or obj.get("platform") or "",
            }
        )
    return {"ok": True, "user_id": user["id"], "instances": rows}


def instance_brief(instance_id: str) -> Dict[str, Any]:
    data = list_instances_brief()
    iid = (instance_id or "").strip()
    for row in data.get("instances") or []:
        if str(row.get("id")) == iid:
            return {"ok": True, "instance": row, "user_id": data.get("user_id")}
    return {"ok": False, "error": f"未找到实例 {iid}（或不属于小管家绑定用户）"}


def start_instance(instance_id: str) -> Dict[str, Any]:
    user = _user_dict()
    from backpack_quant_trading.api.routers import trading as trading_mod

    # 直接调用路由函数会触发 Depends；改为复制调用内部实现
    return trading_mod.start_instance_from_saved_config(instance_id, user=user)


def stop_instance(instance_id: str, *, keep_card: bool = True) -> Dict[str, Any]:
    user = _user_dict()
    from backpack_quant_trading.api.routers import trading as trading_mod

    if keep_card:
        return trading_mod.stop_instance_keep_card(instance_id, user=user)
    return trading_mod.stop_instance(instance_id, user=user)


def set_margin(instance_id: str, margin_type: str) -> Dict[str, Any]:
    user = _user_dict()
    from backpack_quant_trading.api.routers.trading import (
        InstanceUpdateRequest,
        update_instance_config,
    )

    req = InstanceUpdateRequest(margin_type=margin_type)
    return update_instance_config(instance_id, req, user=user)


def recent_logs_markdown(limit: int = 40) -> str:
    user = _user_dict()
    from backpack_quant_trading.api.routers import trading as trading_mod

    data = trading_mod.get_logs(user=user)
    raw = data.get("logs") or data.get("lines") or ""
    if isinstance(raw, list):
        text = "\n".join(str(x) for x in raw[-limit:])
    else:
        # get_logs 返回整段字符串（已按时间倒序截断）
        chunk = str(raw)
        parts = chunk.splitlines()
        text = "\n".join(parts[:limit]) if parts else chunk
    if not text.strip():
        return "### 实例日志\n（暂无）"
    return f"### 实例日志（最近 {limit} 行）\n```\n{text[-3500:]}\n```"


def instance_brief_api(instance_id: str) -> Dict[str, Any]:
    """供 GET /api/trading/instances/{id}/brief 复用。"""
    return instance_brief(instance_id)
