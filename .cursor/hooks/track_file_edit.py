#!/usr/bin/env python3
"""afterFileEdit: record edited paths for stop-time verification reminders."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_io import emit

STATE = Path(__file__).resolve().parents[1] / "harness-state.json"


def _load() -> dict:
    if STATE.is_file():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"pending": [], "edited": []}


def _save(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")


def _classify(path: str) -> list[str]:
    p = path.replace("\\", "/")
    tags = []
    if "/frontend/" in p or p.endswith((".jsx", ".tsx", ".css")):
        tags.append("frontend_build")
    if p.endswith(".py") and ("a_share_ai_agent" in p or "/tests/" in p):
        tags.append("pytest_a_share")
    if p.endswith("tradingview_bot.py"):
        tags.append("tv_bot_health")
    if p.endswith(".py") and "/tests/" not in p:
        tags.append("pytest_touched")
    return tags


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        emit({})
        return 0

    path = str(
        data.get("file_path")
        or data.get("path")
        or data.get("filePath")
        or (data.get("file") or {}).get("path")
        or ""
    )
    if not path and isinstance(data.get("edits"), list) and data["edits"]:
        path = str(data["edits"][0].get("path") or data["edits"][0].get("file_path") or "")

    state = _load()
    edited = list(state.get("edited") or [])
    pending = set(state.get("pending") or [])

    if path:
        if path not in edited:
            edited.append(path)
            edited = edited[-80:]
        for t in _classify(path):
            pending.add(t)

    state["edited"] = edited
    state["pending"] = sorted(pending)
    _save(state)
    emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
