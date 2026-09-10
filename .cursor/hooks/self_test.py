#!/usr/bin/env python3
"""本地冒烟：Harness hooks 脚本 JSON 契约。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".cursor" / "hooks"


def run_hook(name: str, payload: dict) -> dict:
    script = HOOKS / name
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload, ensure_ascii=True),
        text=True,
        capture_output=True,
        cwd=str(ROOT),
        timeout=15,
        encoding="utf-8",
    )
    assert proc.returncode == 0, (name, proc.stderr, proc.stdout)
    out = (proc.stdout or "").strip() or "{}"
    return json.loads(out)


def main() -> None:
    r = run_hook("block_prod_hotfix.py", {"command": "curl -sf http://127.0.0.1:5001/health"})
    assert r.get("permission") == "allow", r

    r = run_hook("block_prod_hotfix.py", {"command": "bash deploy/hotfix-agent-seven.sh"})
    assert r.get("permission") == "deny", r

    r = run_hook(
        "block_prod_hotfix.py",
        {"command": "docker cp tradingview_bot.py backpack-api:/app/tradingview_bot.py"},
    )
    assert r.get("permission") == "deny", r

    r = run_hook(
        "scan_prompt_secrets.py",
        {"prompt": "please use access_token=abcdef0123456789abcdef0123456789abcdef01"},
    )
    assert r.get("continue") is True
    assert "secret" in str(r.get("user_message") or "").lower()

    r = run_hook(
        "track_file_edit.py",
        {"file_path": "backpack_quant_trading/frontend/src/views/AShareAiAgent.jsx"},
    )
    assert isinstance(r, dict)

    r = run_hook("stop_verification.py", {"status": "completed"})
    assert "followup_message" in r or r == {}
    if "followup_message" in r:
        msg = r["followup_message"]
        assert "Harness" in msg
        assert "Deploy to Prod ECS" in msg
        # must be readable English (no mojibake markers)
        assert "\ufffd" not in msg

    # sessionStart inject: empty/fail-open OK; with data may return additional_context
    r = run_hook("session_inject_dev_memory.py", {})
    assert isinstance(r, dict)
    if r.get("additional_context"):
        assert isinstance(r["additional_context"], str)

    print("harness_hooks_ok")


if __name__ == "__main__":
    main()
