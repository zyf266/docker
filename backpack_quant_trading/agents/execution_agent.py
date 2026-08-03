"""执行 Agent：propose 待确认，confirm 后才打专用 webhook（验签 + 禁止广播）。"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from backpack_quant_trading.agents.types import AnalyzeReport

logger = logging.getLogger(__name__)

_DATA = Path(__file__).resolve().parents[1] / "data" / "agent_pending_orders.json"
_LOCK_PATH = Path(__file__).resolve().parents[1] / "data" / "agent_pending_orders.lock"


def _ttl_min() -> int:
    try:
        return max(1, int(os.getenv("AGENT_EXEC_CONFIRM_TTL_MIN", "30")))
    except Exception:
        return 30


def _webhook_base() -> str:
    return os.getenv("WEBHOOK_BASE", "http://127.0.0.1:8005").rstrip("/")


def _webhook_secret() -> str:
    return (os.getenv("WEBHOOK_SECRET") or "").strip()


def _default_instance_id() -> str:
    return (os.getenv("AGENT_EXEC_INSTANCE_ID") or "").strip()


@contextmanager
def _file_lock(timeout_sec: float = 10.0):
    """简单跨进程文件锁（Windows 用 msvcrt，POSIX 用 fcntl）。"""
    _LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fh = open(_LOCK_PATH, "a+", encoding="utf-8")
    start = time.time()
    locked = False
    try:
        while True:
            try:
                try:
                    import msvcrt

                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    locked = True
                    break
                except ImportError:
                    import fcntl

                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
            except (OSError, BlockingIOError):
                if time.time() - start > timeout_sec:
                    raise TimeoutError("获取 pending orders 文件锁超时")
                time.sleep(0.05)
        yield
    finally:
        if locked:
            try:
                try:
                    import msvcrt

                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                except ImportError:
                    import fcntl

                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
        fh.close()


def _load() -> Dict[str, Any]:
    if not _DATA.is_file():
        return {"orders": {}}
    try:
        return json.loads(_DATA.read_text(encoding="utf-8"))
    except Exception:
        return {"orders": {}}


def _save(data: Dict[str, Any]) -> None:
    _DATA.parent.mkdir(parents=True, exist_ok=True)
    _DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def propose_order(report: AnalyzeReport, *, staff_id: str = "") -> Dict[str, Any]:
    if report.risk and report.risk.decision == "reject":
        return {"ok": False, "error": f"风控拒绝，不可下单：{report.risk.reason}"}
    if (report.action or "").lower() not in ("buy", "sell"):
        return {"ok": False, "error": f"当前建议为 {report.action}，无需下单"}
    if not (staff_id or "").strip():
        return {"ok": False, "error": "缺少 staff_id，无法生成可确认订单"}

    pending_id = "ord_" + uuid.uuid4().hex[:10]
    now = int(time.time())
    instance_id = _default_instance_id()
    order = {
        "id": pending_id,
        "symbol": report.symbol,
        "market": report.market.value if hasattr(report.market, "value") else str(report.market),
        "action": (report.action or "").lower(),
        "support": report.support,
        "resistance": report.resistance,
        "staff_id": staff_id.strip(),
        "instance_id": instance_id,
        "created_at": now,
        "expires_at": now + _ttl_min() * 60,
        "status": "pending",
        "agent_id": report.agent_id.value if hasattr(report.agent_id, "value") else str(report.agent_id),
    }
    with _file_lock():
        data = _load()
        orders = data.setdefault("orders", {})
        orders[pending_id] = order
        # latest 按 staff 隔离，避免他人裸「确认」抢单
        latest_map = data.setdefault("latest_by_staff", {})
        latest_map[staff_id.strip()] = pending_id
        data["latest_id"] = pending_id
        _save(data)
    msg = (
        f"已生成待确认订单 `{pending_id}`（约 {_ttl_min()} 分钟内有效），"
        f"请回复「确认」或「确认 {pending_id}」提交；也可「取消」/「待确认列表」"
    )
    if not instance_id:
        msg += "\n（未配置 AGENT_EXEC_INSTANCE_ID：确认时将只校验不实盘，避免广播误触）"
    return {
        "ok": True,
        "pending_id": pending_id,
        "message": msg,
        "order": order,
        "ttl_min": _ttl_min(),
        "expires_at": order["expires_at"],
    }


def _build_webhook_payload(order: Dict[str, Any]) -> Dict[str, Any]:
    """构造符合 TradingViewSignal 的载荷；必须走 /webhook/agent-confirm。"""
    action = str(order.get("action") or "buy").lower()
    if action not in ("buy", "sell", "close"):
        action = "buy"
    payload: Dict[str, Any] = {
        "signal": action,
        "symbol": order["symbol"],
        "action": action,
        "ticker": order["symbol"],
        "side": action,
        "strategy_name": "agent_execution",
        "indicator": "agent_confirm",
        "manual_test": True,
        "agent_execution": True,
        "pending_id": order["id"],
        "filter_id": "agent_confirm",
        "strategy": "agent_execution",
    }
    iid = (order.get("instance_id") or "").strip()
    if iid:
        payload["instance_id"] = iid
    return payload


def _sign_body(body: bytes) -> str:
    secret = _webhook_secret()
    if not secret or secret == "your-secret-key-here":
        return ""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def confirm_order(
    pending_id: str = "",
    *,
    staff_id: str = "",
    dry_run: bool = False,
) -> Dict[str, Any]:
    staff = (staff_id or "").strip()
    if not staff:
        return {"ok": False, "error": "缺少 staff_id，拒绝确认（防订单劫持）"}

    with _file_lock():
        data = _load()
        orders = data.get("orders") or {}
        pid = (pending_id or "").strip()
        if not pid:
            pid = str((data.get("latest_by_staff") or {}).get(staff) or "")
        if not pid or pid not in orders:
            return {"ok": False, "error": "没有待确认订单（或 ID 无效）"}

        order = dict(orders[pid])
        now = int(time.time())
        if order.get("status") != "pending":
            return {"ok": False, "error": f"订单状态为 {order.get('status')}，无法确认"}
        if int(order.get("expires_at") or 0) < now:
            orders[pid]["status"] = "expired"
            _save(data)
            return {"ok": False, "error": "订单已过期，请重新分析后 propose"}

        owner = str(order.get("staff_id") or "").strip()
        if owner and owner != staff:
            return {"ok": False, "error": "无权确认他人订单"}

        payload = _build_webhook_payload(order)
        url = f"{_webhook_base()}/webhook/agent-confirm"
        instance_id = str(payload.get("instance_id") or "").strip()

        # 无实例 ID：强制 dry-run，禁止广播实盘
        force_dry = dry_run or not instance_id
        if force_dry and not dry_run and not instance_id:
            orders[pid]["status"] = "confirmed_dry_run"
            orders[pid]["note"] = "未配置 AGENT_EXEC_INSTANCE_ID，未实盘提交"
            _save(data)
            return {
                "ok": True,
                "pending_id": pid,
                "dry_run": True,
                "url": url,
                "payload": payload,
                "message": (
                    f"订单 `{pid}` 已校验通过（dry-run）。"
                    "请设置 AGENT_EXEC_INSTANCE_ID 后再「确认」以实盘提交。"
                ),
            }

        if dry_run:
            orders[pid]["status"] = "confirmed_dry_run"
            _save(data)
            return {
                "ok": True,
                "pending_id": pid,
                "dry_run": True,
                "url": url,
                "payload": payload,
            }

        secret = _webhook_secret()
        if not secret or secret == "your-secret-key-here":
            return {
                "ok": False,
                "error": "未配置有效 WEBHOOK_SECRET，拒绝实盘确认（请修改默认密钥）",
                "payload": payload,
            }

        try:
            import urllib.request

            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            sig = _sign_body(body)
            headers = {
                "Content-Type": "application/json",
                "X-Signature": sig,
            }
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_text = resp.read().decode("utf-8", errors="replace")[:500]
            orders[pid]["status"] = "submitted"
            orders[pid]["submitted_at"] = now
            orders[pid]["confirmed_by"] = staff
            orders[pid]["webhook_response"] = resp_text
            _save(data)
            return {
                "ok": True,
                "pending_id": pid,
                "message": f"已提交下单请求 `{pid}` → 实例 {instance_id}",
                "response": resp_text,
            }
        except Exception as exc:
            logger.warning("confirm webhook failed: %s", exc)
            return {"ok": False, "error": f"提交 webhook 失败: {exc}", "payload": payload}


def parse_confirm_command(text: str) -> Tuple[bool, str]:
    """兼容旧接口：仅识别「确认」；取消/列表见 parse_exec_command。"""
    kind, pid = parse_exec_command(text)
    if kind == "confirm":
        return True, pid
    return False, ""


def parse_exec_command(text: str) -> Tuple[str, str]:
    """
    解析执行工作流口令。
    返回 (kind, pending_id)：
      kind: confirm | cancel | list | ""
    """
    t = (text or "").strip()
    if not t:
        return "", ""
    low = t.lower()

    if t in ("待确认列表", "待确认单", "确认列表", "pending", "list pending") or (
        "待确认" in t and "列表" in t
    ):
        return "list", ""

    if t in ("取消", "取消确认", "取消下单", "cancel") or t.startswith("取消确认"):
        rest = ""
        if t.startswith("取消确认"):
            rest = t[4:].strip()
        elif t.startswith("取消") and t not in ("取消", "取消确认", "取消下单"):
            rest = t[2:].strip()
        if rest.startswith("`") and rest.endswith("`"):
            rest = rest[1:-1]
        return "cancel", rest

    if t in ("确认", "确认下单", "confirm"):
        return "confirm", ""
    if t.startswith("确认"):
        rest = t[2:].strip()
        if rest.startswith("`") and rest.endswith("`"):
            rest = rest[1:-1]
        # 「确认停止实例」不是下单确认
        if rest.startswith("停止实例") or rest.startswith("启动实例"):
            return "", ""
        return "confirm", rest
    return "", ""


def _purge_expired_locked(data: Dict[str, Any], now: int) -> int:
    n = 0
    orders = data.get("orders") or {}
    for pid, order in list(orders.items()):
        if order.get("status") != "pending":
            continue
        if int(order.get("expires_at") or 0) < now:
            orders[pid]["status"] = "expired"
            orders[pid]["expired_note"] = "TTL 到期自动标记 expired"
            n += 1
    return n


def list_pending(staff_id: str = "") -> Dict[str, Any]:
    staff = (staff_id or "").strip()
    now = int(time.time())
    with _file_lock():
        data = _load()
        _purge_expired_locked(data, now)
        _save(data)
        rows = []
        for pid, order in (data.get("orders") or {}).items():
            if order.get("status") != "pending":
                continue
            owner = str(order.get("staff_id") or "").strip()
            if staff and owner and owner != staff:
                continue
            exp = int(order.get("expires_at") or 0)
            left = max(0, (exp - now) // 60)
            rows.append(
                {
                    "id": pid,
                    "symbol": order.get("symbol"),
                    "action": order.get("action"),
                    "expires_at": exp,
                    "minutes_left": left,
                    "staff_id": owner,
                }
            )
        rows.sort(key=lambda x: int(x.get("expires_at") or 0))
    return {"ok": True, "orders": rows, "count": len(rows)}


def cancel_order(pending_id: str = "", *, staff_id: str = "") -> Dict[str, Any]:
    staff = (staff_id or "").strip()
    if not staff:
        return {"ok": False, "error": "缺少 staff_id，拒绝取消"}
    now = int(time.time())
    with _file_lock():
        data = _load()
        _purge_expired_locked(data, now)
        orders = data.get("orders") or {}
        pid = (pending_id or "").strip()
        if not pid:
            pid = str((data.get("latest_by_staff") or {}).get(staff) or "")
        if not pid or pid not in orders:
            _save(data)
            return {"ok": False, "error": "没有可取消的待确认订单"}
        order = orders[pid]
        owner = str(order.get("staff_id") or "").strip()
        if owner and owner != staff:
            return {"ok": False, "error": "无权取消他人订单"}
        if order.get("status") != "pending":
            return {"ok": False, "error": f"订单状态为 {order.get('status')}，无法取消"}
        orders[pid]["status"] = "cancelled"
        orders[pid]["cancelled_at"] = now
        orders[pid]["cancelled_by"] = staff
        latest_map = data.get("latest_by_staff") or {}
        if latest_map.get(staff) == pid:
            latest_map.pop(staff, None)
        _save(data)
    return {"ok": True, "pending_id": pid, "message": f"已取消待确认订单 `{pid}`"}


def count_pending_expiring_soon(within_min: int = 30) -> Tuple[int, int]:
    """返回 (pending 总数, within_min 内将过期数)。顺带标记已过期。"""
    now = int(time.time())
    horizon = now + max(1, int(within_min)) * 60
    with _file_lock():
        data = _load()
        _purge_expired_locked(data, now)
        _save(data)
        total = 0
        soon = 0
        for order in (data.get("orders") or {}).values():
            if order.get("status") != "pending":
                continue
            total += 1
            exp = int(order.get("expires_at") or 0)
            if now <= exp <= horizon:
                soon += 1
        return total, soon


def format_pending_list_markdown(result: Dict[str, Any]) -> str:
    rows = result.get("orders") or []
    if not rows:
        return "### 待确认列表\n（暂无 pending 订单）"
    lines = ["### 待确认列表", ""]
    for r in rows:
        lines.append(
            f"- `{r.get('id')}` · {r.get('symbol')} · {r.get('action')} · "
            f"剩余约 **{r.get('minutes_left')}** 分钟"
        )
    lines.append("\n回复「确认 <id>」提交，或「取消」/「取消确认 <id>」")
    return "\n".join(lines)
