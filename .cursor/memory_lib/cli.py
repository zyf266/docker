#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI for Cursor local dev-memory (smoke / manual).

Usage (from repo root):
  python .cursor/memory_lib/cli.py upsert --kind convention --text "..."
  python .cursor/memory_lib/cli.py search --query "热更"
  python .cursor/memory_lib/cli.py stats
  python .cursor/memory_lib/cli.py delete --id mem_xxx
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parent
_CURSOR = _LIB.parent
if str(_CURSOR) not in sys.path:
    sys.path.insert(0, str(_CURSOR))

from memory_lib import store  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dev-memory")
    sub = p.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser("upsert", help="Write or update a memory")
    up.add_argument("--kind", required=True, choices=sorted(store.KINDS))
    up.add_argument("--text", required=True)
    up.add_argument("--tags", default="", help="comma-separated")
    up.add_argument("--pinned", action="store_true")
    up.add_argument("--id", default="")
    up.add_argument("--source", default="cli")

    se = sub.add_parser("search", help="Semantic search")
    se.add_argument("--query", required=True)
    se.add_argument("--kind", default="")
    se.add_argument("--n", type=int, default=8)

    de = sub.add_parser("delete", help="Delete by id")
    de.add_argument("--id", required=True)

    sub.add_parser("stats", help="Collection stats")
    sub.add_parser("session-pack", help="Pinned + recent (for hooks)")

    args = p.parse_args(argv)
    if args.cmd == "upsert":
        tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
        out = store.upsert_memory(
            args.text,
            args.kind,
            tags=tags,
            pinned=bool(args.pinned),
            memory_id=args.id or None,
            source=args.source,
        )
    elif args.cmd == "search":
        out = store.search_memory(
            args.query,
            kind=args.kind or None,
            n_results=args.n,
        )
    elif args.cmd == "delete":
        out = store.delete_memory(args.id)
    elif args.cmd == "stats":
        out = store.memory_stats()
    elif args.cmd == "session-pack":
        out = store.list_pinned_and_recent()
    else:
        p.error(f"unknown cmd {args.cmd}")
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
