#!/usr/bin/env python3
"""Gate shell: block prod code hotfixes / docker cp of sources."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HOOK_DIR = Path(__file__).resolve().parent
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))

try:
    from hook_io import emit
except Exception:

    def emit(obj: dict) -> None:  # type: ignore[misc]
        sys.stdout.write(json.dumps(obj, ensure_ascii=True) + "\n")
        sys.stdout.flush()


DENY_PATTERNS = [
    (r"47\.110\.57\.118.*(vi |vim |sed |nano |tee |cat >|/opt/backpack-quant/.*\.py)", "no edit prod business code"),
    (r"ssh\s+.*47\.110\.57\.118.*(vi |vim |sed |nano )", "no ssh edit on prod"),
    (r"docker\s+cp\s+.*backpack-(api|dingtalk-agent|webhook)", "no docker cp hotfix into containers"),
    (r"docker\s+cp\s+.*\.(py|jsx|js|tsx|css|html)\s+.*:", "no docker cp overwrite source/frontend"),
    (r"scp\s+.*\.(py|jsx|js|tsx)\s+.*(47\.110\.57\.118|/opt/backpack)", "no scp overwrite prod source"),
    (r"hotfix-.*\.sh", "no hotfix scripts; use Deploy to Prod ECS"),
    (r"restore-prod-hotfixes\.sh", "no restore-prod-hotfixes; use Deploy pipeline"),
]


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
        cmd = str(data.get("command") or data.get("commandLine") or "")
        low = cmd.lower()

        if any(h in low for h in ("docker logs", "docker ps", "ss -tlnp", "curl -sf", "curl -k")):
            emit({"permission": "allow"})
            return 0

        for pattern, reason in DENY_PATTERNS:
            if re.search(pattern, cmd, re.I):
                if (
                    any(a in low for a in ("docker logs", "docker ps", "health", "tail ", ".env"))
                    and "hotfix" not in low
                    and "docker cp" not in low
                ):
                    continue
                emit(
                    {
                        "permission": "deny",
                        "user_message": f"Blocked: {reason}",
                        "agent_message": (
                            f"Harness blocked prod hotfix: {reason}. "
                            "Correct path: local change -> commit/push -> Deploy to Prod ECS. "
                            "Allowed: logs, health checks, prod .env with user consent."
                        ),
                    }
                )
                return 0

        emit({"permission": "allow"})
        return 0
    except Exception:
        # fail-open output so failClosed hooks don't brick the session
        emit({"permission": "allow"})
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
