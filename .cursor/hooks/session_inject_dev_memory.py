#!/usr/bin/env python3
"""sessionStart: best-effort inject pinned + recent dev memories."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_io import emit

_CURSOR = Path(__file__).resolve().parents[1]
if str(_CURSOR) not in sys.path:
    sys.path.insert(0, str(_CURSOR))

_MAX_CTX = 2800


def main() -> int:
    try:
        _ = json.loads(sys.stdin.read() or "{}")
    except Exception:
        pass

    try:
        from memory_lib import store

        rows = store.list_pinned_and_recent(pinned_limit=5, recent_limit=5, max_chars=240)
    except Exception:
        emit({})
        return 0

    if not rows:
        emit({})
        return 0

    lines = ["[dev-memory] Pinned / recent project memories (local Chroma):"]
    for r in rows:
        meta = r.get("metadata") or {}
        kind = meta.get("kind") or "?"
        pin = " pinned" if meta.get("pinned") else ""
        text = (r.get("text") or "").replace("\n", " ").strip()
        lines.append(f"- ({kind}{pin}) {text}")
    ctx = "\n".join(lines)
    if len(ctx) > _MAX_CTX:
        ctx = ctx[: _MAX_CTX - 1] + "…"
    emit({"additional_context": ctx})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
