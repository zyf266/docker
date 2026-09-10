# -*- coding: utf-8 -*-
"""Cursor 本地开发记忆：Chroma PersistentClient。"""
from __future__ import annotations

import hashlib
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .embed import get_embedding_function

COLLECTION = "cursor_dev_memory"
KINDS = frozenset({"decision", "bugfix", "convention", "task", "session"})
_MAX_TEXT = 4000
_LOCK = threading.Lock()
_CLIENT = None
_COL = None

_SECRET_RES = [
    re.compile(r"access_token=[0-9a-f]{32,}", re.I),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"DINGTALK_.*SECRET\s*=\s*\S{8,}", re.I),
    re.compile(r"DEEPSEEK_API_KEY\s*=\s*\S{8,}", re.I),
    re.compile(r"mysql://[^:]+:[^@]+@"),
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def memory_dir() -> Path:
    d = repo_root() / ".cursor" / "dev-memory"
    d.mkdir(parents=True, exist_ok=True)
    return d


def chroma_path() -> Path:
    p = memory_dir() / "chroma"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _reject_secrets(text: str) -> None:
    for pat in _SECRET_RES:
        if pat.search(text or ""):
            raise ValueError("memory text looks like it contains secrets; refuse upsert")


def _get_collection():
    global _CLIENT, _COL
    with _LOCK:
        if _COL is not None:
            return _COL
        import chromadb

        path = chroma_path()
        if _CLIENT is None:
            _CLIENT = chromadb.PersistentClient(path=str(path))
        ef = get_embedding_function()
        kwargs: Dict[str, Any] = {
            "name": COLLECTION,
            "metadata": {"hnsw:space": "cosine"},
        }
        if ef is not None:
            kwargs["embedding_function"] = ef
        _COL = _CLIENT.get_or_create_collection(**kwargs)
        return _COL


def _make_id(text: str, kind: str, explicit: Optional[str] = None) -> str:
    if explicit and str(explicit).strip():
        return str(explicit).strip()[:128]
    raw = f"{kind}|{text.strip()}|{int(time.time())}"
    return "mem_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def upsert_memory(
    text: str,
    kind: str,
    *,
    tags: Optional[List[str]] = None,
    pinned: bool = False,
    memory_id: Optional[str] = None,
    source: str = "agent",
) -> Dict[str, Any]:
    kind = (kind or "").strip().lower()
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {sorted(KINDS)}")
    body = (text or "").strip()
    if not body:
        raise ValueError("text is empty")
    _reject_secrets(body)
    if len(body) > _MAX_TEXT:
        body = body[:_MAX_TEXT]
    mid = _make_id(body, kind, memory_id)
    tag_list = [str(t).strip() for t in (tags or []) if str(t).strip()]
    meta: Dict[str, Any] = {
        "kind": kind,
        "source": (source or "agent")[:64],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "pinned": bool(pinned),
        "tags": ",".join(tag_list)[:500],
    }
    col = _get_collection()
    col.upsert(ids=[mid], documents=[body], metadatas=[meta])
    return {"ok": True, "id": mid, "kind": kind, "pinned": bool(pinned)}


def search_memory(
    query: str,
    *,
    kind: Optional[str] = None,
    n_results: int = 8,
    max_chars: int = 600,
) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    n = max(1, min(int(n_results or 8), 20))
    col = _get_collection()
    kwargs: Dict[str, Any] = {"query_texts": [q], "n_results": n}
    if kind:
        k = kind.strip().lower()
        if k not in KINDS:
            raise ValueError(f"kind must be one of {sorted(KINDS)}")
        kwargs["where"] = {"kind": k}
    try:
        res = col.query(**kwargs)
    except Exception:
        # empty collection or filter miss
        return []
    out: List[Dict[str, Any]] = []
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    for i, mid in enumerate(ids):
        doc = docs[i] if i < len(docs) else ""
        if max_chars and doc and len(doc) > max_chars:
            doc = doc[: max_chars - 1] + "…"
        meta = metas[i] if i < len(metas) else {}
        dist = dists[i] if i < len(dists) else None
        out.append(
            {
                "id": mid,
                "text": doc,
                "metadata": meta or {},
                "distance": dist,
            }
        )
    return out


def delete_memory(memory_id: str) -> Dict[str, Any]:
    mid = (memory_id or "").strip()
    if not mid:
        raise ValueError("id is empty")
    col = _get_collection()
    col.delete(ids=[mid])
    return {"ok": True, "id": mid}


def list_pinned_and_recent(
    *,
    pinned_limit: int = 5,
    recent_limit: int = 5,
    max_chars: int = 280,
) -> List[Dict[str, Any]]:
    """Best-effort for sessionStart: pinned first, then recent by created_at."""
    col = _get_collection()
    out: List[Dict[str, Any]] = []
    seen: set = set()

    def _append(mid: str, doc: str, meta: Dict[str, Any]) -> None:
        if mid in seen:
            return
        seen.add(mid)
        text = doc or ""
        if max_chars and len(text) > max_chars:
            text = text[: max_chars - 1] + "…"
        out.append({"id": mid, "text": text, "metadata": meta or {}})

    try:
        pinned = col.get(where={"pinned": True}, limit=max(pinned_limit, 1) * 2)
    except Exception:
        pinned = {"ids": [], "documents": [], "metadatas": []}
    for i, mid in enumerate(pinned.get("ids") or []):
        if len([x for x in out if (x.get("metadata") or {}).get("pinned")]) >= pinned_limit:
            break
        doc = (pinned.get("documents") or [""])[i] if i < len(pinned.get("documents") or []) else ""
        meta = (pinned.get("metadatas") or [{}])[i] if i < len(pinned.get("metadatas") or []) else {}
        _append(mid, doc or "", meta or {})

    try:
        peek = col.peek(limit=max(20, recent_limit * 5))
    except Exception:
        peek = {"ids": [], "documents": [], "metadatas": []}
    rows = []
    for i, mid in enumerate(peek.get("ids") or []):
        meta = (peek.get("metadatas") or [{}])[i] if i < len(peek.get("metadatas") or []) else {}
        doc = (peek.get("documents") or [""])[i] if i < len(peek.get("documents") or []) else ""
        rows.append((str((meta or {}).get("created_at") or ""), mid, doc or "", meta or {}))
    rows.sort(key=lambda x: x[0], reverse=True)
    non_pinned = 0
    for _, mid, doc, meta in rows:
        if mid in seen:
            continue
        if meta.get("pinned"):
            continue
        _append(mid, doc, meta)
        non_pinned += 1
        if non_pinned >= recent_limit:
            break
    return out


def memory_stats() -> Dict[str, Any]:
    col = _get_collection()
    try:
        count = col.count()
    except Exception:
        count = 0
    return {
        "ok": True,
        "collection": COLLECTION,
        "count": count,
        "path": str(chroma_path()),
        "kinds": sorted(KINDS),
    }
