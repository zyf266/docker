#!/usr/bin/env python3
"""beforeSubmitPrompt: warn if prompt looks like it contains secrets."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_io import emit

SECRET_PATTERNS = [
    (r"access_token=[0-9a-f]{32,}", "DingTalk webhook access_token"),
    (r"sk-[A-Za-z0-9]{20,}", "API key (sk-)"),
    (r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----", "private key PEM"),
    (r"DINGTALK_.*SECRET\s*=\s*\S{8,}", "DingTalk Client Secret"),
    (r"DEEPSEEK_API_KEY\s*=\s*\S{8,}", "DeepSeek API Key"),
    (r"mysql://[^:]+:[^@]+@", "DB URL with password"),
]


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        emit({})
        return 0

    text = " ".join(
        str(data.get(k) or "")
        for k in ("prompt", "text", "content", "user_message", "message")
    )
    if not text.strip():
        text = json.dumps(data, ensure_ascii=True)

    hits = [label for pat, label in SECRET_PATTERNS if re.search(pat, text)]
    if hits:
        emit(
            {
                "continue": True,
                "user_message": (
                    "Warning: prompt may contain secrets ("
                    + ", ".join(hits)
                    + "). Avoid committing plaintext keys; prefer local .env."
                ),
            }
        )
        return 0

    emit({"continue": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
