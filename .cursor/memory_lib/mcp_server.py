#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP stdio server: Cursor local dev-memory tools.

Requires: pip install mcp chromadb
Run via .cursor/mcp.json (project MCP).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, List, Optional

_LIB = Path(__file__).resolve().parent
_CURSOR = _LIB.parent
if str(_CURSOR) not in sys.path:
    sys.path.insert(0, str(_CURSOR))

from memory_lib import store  # noqa: E402


def _run_fastmcp() -> None:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("dev-memory")

    @mcp.tool()
    def memory_search(
        query: str,
        kind: Optional[str] = None,
        n_results: int = 8,
    ) -> str:
        """Search persistent Cursor dev memories (decisions, bugfixes, conventions, tasks)."""
        hits = store.search_memory(query, kind=kind or None, n_results=n_results)
        return json.dumps(hits, ensure_ascii=False)

    @mcp.tool()
    def memory_upsert(
        text: str,
        kind: str,
        tags: Optional[List[str]] = None,
        pinned: bool = False,
        memory_id: Optional[str] = None,
    ) -> str:
        """Upsert a durable memory. kind: decision|bugfix|convention|task|session. No secrets."""
        out = store.upsert_memory(
            text,
            kind,
            tags=tags or [],
            pinned=bool(pinned),
            memory_id=memory_id,
            source="mcp",
        )
        return json.dumps(out, ensure_ascii=False)

    @mcp.tool()
    def memory_delete(memory_id: str) -> str:
        """Delete a memory by id."""
        return json.dumps(store.delete_memory(memory_id), ensure_ascii=False)

    @mcp.tool()
    def memory_stats() -> str:
        """Return collection path and document count."""
        return json.dumps(store.memory_stats(), ensure_ascii=False)

    mcp.run(transport="stdio")


def main() -> int:
    try:
        _run_fastmcp()
        return 0
    except ImportError:
        sys.stderr.write(
            "dev-memory MCP needs the `mcp` package.\n"
            "Install: pip install mcp\n"
            "CLI still works: python .cursor/memory_lib/cli.py stats\n"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
