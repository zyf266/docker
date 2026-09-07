#!/usr/bin/env python3
"""stop: if code was edited this session, nudge agent to verify before claiming done."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_io import emit

STATE = Path(__file__).resolve().parents[1] / "harness-state.json"

CMDS = {
    "frontend_build": "cd backpack_quant_trading/frontend && npm run build",
    "pytest_a_share": "python -m pytest backpack_quant_trading/tests/test_a_share_ai_agent_intraday.py -q",
    "tv_bot_health": "curl -sf http://127.0.0.1:5001/health",
    "pytest_touched": "run pytest for touched modules; at least import smoke",
}


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        data = {}

    _ = data  # reserved for future status filtering
    state = {}
    if STATE.is_file():
        try:
            state = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            state = {}

    pending = list(state.get("pending") or [])
    edited = list(state.get("edited") or [])

    if not pending and not edited:
        emit({})
        return 0

    # Prefer ASCII/English in followup to avoid UI mojibake; keep meaning clear.
    lines = [
        "Harness: code was edited this turn. Before claiming done, paste verification evidence.",
        f"Edited files: {len(edited)}; pending tags: {', '.join(pending) or 'none'}",
        "Suggested commands:",
    ]
    for tag in pending:
        lines.append(f"- [{tag}] {CMDS.get(tag, 'run verification-before-completion checks')}")
    lines.append("Prod: no hotfixes; commit -> push -> Deploy to Prod ECS.")
    lines.append("After verify: delete or reset .cursor/harness-state.json")

    state["pending"] = []
    state["edited"] = []
    try:
        STATE.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")
    except Exception:
        pass

    emit({"followup_message": "\n".join(lines)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
