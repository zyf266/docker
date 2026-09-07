#!/usr/bin/env python3
"""Shared stdout helpers for Cursor hooks (Windows-safe)."""
from __future__ import annotations

import json
import sys


def emit(obj: dict) -> None:
    """Print JSON for Cursor. Use ASCII escapes so cp936 pipes don't mojibake."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    sys.stdout.write(json.dumps(obj, ensure_ascii=True))
    sys.stdout.write("\n")
    sys.stdout.flush()
