"""日巡检 Agent：汇总监视 / 实例 / pending / 日志关键词 / 自愈。"""
from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _env_on(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() not in ("0", "false", "no", "off")


def _scan_log_keywords(limit_files: int = 2) -> List[str]:
    """最近 app 日志里找限流 / Stream 失败关键词。"""
    hits: List[str] = []
    keys = re.compile(r"(429|rate.?limit|Stream|钉钉.*失败|dingtalk.*fail|抢.*Stream)", re.I)
    cand = [
        Path(__file__).resolve().parents[1] / "log",
        Path(__file__).resolve().parents[2] / "log",
    ]
    log_dir = next((d for d in cand if d.exists()), cand[0])
    try:
        apps = sorted(log_dir.glob("app_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[
            :limit_files
        ]
    except Exception:
        apps = []
    for fp in apps:
        try:
            data = fp.read_bytes()[-80000:].decode("utf-8", errors="replace")
            for line in data.splitlines()[-200:]:
                if keys.search(line):
                    hits.append(line.strip()[:180])
                    if len(hits) >= 5:
                        return hits
        except Exception:
            continue
    return hits


def collect_patrol_snapshot(*, do_heal: bool = True) -> Dict[str, Any]:
    snap: Dict[str, Any] = {
        "ts": int(time.time()),
        "currency_monitor_running": False,
        "news_monitor_hint": "",
        "live_instances": 0,
        "live_running": 0,
        "pending_soon_expire": 0,
        "pending_total": 0,
        "log_hits": [],
        "healed": [],
        "needs_human": [],
        "notes": [],
    }

    # 币种监视
    try:
        from backpack_quant_trading.core.binance_monitor import (
            restore_currency_monitor_from_db_if_needed,
            get_monitor_instance,
        )

        restore_currency_monitor_from_db_if_needed()
        svc = get_monitor_instance()
        snap["currency_monitor_running"] = bool(svc)
    except Exception as exc:
        snap["notes"].append(f"币种监视探测失败: {exc}")

    # 新闻
    try:
        from backpack_quant_trading.core.stock_news_alert import get_stock_news_alert_user_stopped

        stopped = get_stock_news_alert_user_stopped()
        snap["news_monitor_hint"] = "用户已停止" if stopped else "未标记停止（可能在跑）"
    except Exception as exc:
        snap["news_monitor_hint"] = f"探测失败: {exc}"

    # live instances
    try:
        from backpack_quant_trading.database.models import DatabaseManager

        db = DatabaseManager()
        rows = []
        try:
            rows = list(db.list_live_instances_by_status("running") or [])
            snap["live_running"] = len(rows)
        except Exception:
            pass
        try:
            # 粗算全部 live
            all_n = 0
            for status in ("running", "stopped", "idle", "error", "unknown"):
                try:
                    all_n += len(db.list_live_instances_by_status(status) or [])
                except Exception:
                    continue
            snap["live_instances"] = all_n or snap["live_running"]
        except Exception:
            snap["live_instances"] = snap["live_running"]
    except Exception as exc:
        snap["notes"].append(f"实例统计失败: {exc}")

    # pending TTL
    try:
        from backpack_quant_trading.agents.execution_agent import count_pending_expiring_soon

        total, soon = count_pending_expiring_soon(within_min=30)
        snap["pending_total"] = total
        snap["pending_soon_expire"] = soon
    except Exception as exc:
        snap["notes"].append(f"pending 统计失败: {exc}")

    snap["log_hits"] = _scan_log_keywords()

    if do_heal:
        try:
            from backpack_quant_trading.agents.self_heal import check_and_heal_monitors

            heal = check_and_heal_monitors()
            snap["healed"] = heal.get("healed") or []
            snap["needs_human"] = heal.get("needs_human") or []
            snap["notes"].extend(heal.get("notes") or [])
        except Exception as exc:
            snap["needs_human"].append(f"自愈异常: {exc}")

    return snap


def format_patrol_markdown(snap: Dict[str, Any]) -> str:
    lines = [
        "## 提醒 · Agent 日巡检",
        "",
        f"- 币种监视：**{'运行中' if snap.get('currency_monitor_running') else '未运行'}**",
        f"- 新闻监控：{snap.get('news_monitor_hint') or '—'}",
        f"- 实盘实例：running **{snap.get('live_running', 0)}** / 统计约 **{snap.get('live_instances', 0)}**",
        f"- 待确认单：共 **{snap.get('pending_total', 0)}**，"
        f"**{snap.get('pending_soon_expire', 0)}** 单将在 30min 内过期",
        "",
    ]
    healed = snap.get("healed") or []
    needs = snap.get("needs_human") or []
    if healed:
        lines.append("### 已自愈")
        lines.extend(f"- {x}" for x in healed)
        lines.append("")
    if needs:
        lines.append("### 需人工")
        lines.extend(f"- {x}" for x in needs)
        lines.append("")
    hits = snap.get("log_hits") or []
    if hits:
        lines.append("### 最近日志关键词")
        lines.extend(f"- `{x}`" for x in hits[:5])
        lines.append("")
    notes = snap.get("notes") or []
    if notes:
        lines.append("### 备注")
        lines.extend(f"- {x}" for x in notes[:8])
    return "\n".join(lines).strip()


def run_daily_patrol(*, push: bool = True) -> Dict[str, Any]:
    if not _env_on("AGENT_PATROL_ENABLED", "1"):
        return {"ok": True, "skipped": True, "reason": "AGENT_PATROL_ENABLED=0"}
    snap = collect_patrol_snapshot(do_heal=True)
    md = format_patrol_markdown(snap)
    pushed = False
    push_err = ""
    if push:
        from backpack_quant_trading.agents.dingtalk_push import push_dingtalk_markdown

        ok, msg = push_dingtalk_markdown("Agent 日巡检", md, use_ops_webhook=True)
        pushed = ok
        push_err = "" if ok else msg
    return {"ok": True, "snapshot": snap, "markdown": md, "pushed": pushed, "push_error": push_err}
