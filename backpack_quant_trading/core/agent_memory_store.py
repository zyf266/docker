"""Agent 长期记忆：复用 score_feedback 同 Chroma 目录，独立 collection。"""
from __future__ import annotations

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_CHROMA_DIR = _DATA_DIR / "chroma_score_feedback"
_LOCK = threading.Lock()
_CLIENT = None
_COLLECTIONS: Dict[str, Any] = {}
# 首次拉 onnx 模型极慢；热路径必须超时跳过，避免钉钉「有回执无正文」
_OP_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="agent-mem")
_DEFAULT_TIMEOUT_SEC = float(os.getenv("AGENT_MEMORY_TIMEOUT_SEC", "4") or 4)

KIND_TO_COLLECTION = {
    "agent_prefs": "agent_prefs",
    "agent_reports": "agent_reports",
    "agent_research": "agent_research",
    "agent_reviews": "agent_reviews",
    "prefs": "agent_prefs",
    "reports": "agent_reports",
    "research": "agent_research",
    "reviews": "agent_reviews",
}


def agent_memory_enabled() -> bool:
    env = os.getenv("AGENT_MEMORY_CHROMA_ENABLED", "1").strip().lower()
    return env not in ("0", "false", "no", "off")


def _chroma_path() -> Path:
    custom = os.getenv("SCORE_FEEDBACK_CHROMA_PATH", "").strip()
    return Path(custom) if custom else _CHROMA_DIR


def _normalize_kind(kind: str) -> str:
    key = (kind or "").strip()
    if hasattr(kind, "value"):
        key = str(kind.value)
    name = KIND_TO_COLLECTION.get(key, key)
    if name not in KIND_TO_COLLECTION.values():
        raise ValueError(f"未知 memory kind: {kind}")
    return name


def _get_collection(kind: str):
    global _CLIENT
    if not agent_memory_enabled():
        return None
    name = _normalize_kind(kind)
    with _LOCK:
        if name in _COLLECTIONS:
            return _COLLECTIONS[name]
        try:
            import chromadb
        except ImportError:
            logger.warning("未安装 chromadb，Agent 记忆不可用")
            return None
        path = _chroma_path()
        path.mkdir(parents=True, exist_ok=True)
        if _CLIENT is None:
            _CLIENT = chromadb.PersistentClient(path=str(path))
        col = _CLIENT.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
        _COLLECTIONS[name] = col
        return col


def _sanitize_meta(metadata: Dict[str, Any]) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    for k, v in (metadata or {}).items():
        if isinstance(v, (dict, list)):
            meta[k] = json.dumps(v, ensure_ascii=False)
        elif v is None:
            meta[k] = ""
        elif isinstance(v, (str, int, float, bool)):
            meta[k] = v
        else:
            meta[k] = str(v)
    return meta


def _upsert_sync(
    kind: str,
    memory_id: str,
    document: str,
    metadata: Optional[Dict[str, Any]],
) -> bool:
    col = _get_collection(kind)
    if col is None or not memory_id or not (document or "").strip():
        return False
    col.upsert(
        ids=[memory_id],
        documents=[document],
        metadatas=[_sanitize_meta(metadata or {})],
    )
    return True


def upsert_memory(
    kind: str,
    memory_id: str,
    document: str,
    metadata: Optional[Dict[str, Any]] = None,
    *,
    timeout_sec: Optional[float] = None,
) -> bool:
    if not agent_memory_enabled():
        return False
    wait = _DEFAULT_TIMEOUT_SEC if timeout_sec is None else float(timeout_sec)
    fut = _OP_POOL.submit(_upsert_sync, kind, memory_id, document, metadata)
    try:
        return bool(fut.result(timeout=max(0.5, wait)))
    except FuturesTimeout:
        logger.warning("Agent memory upsert 超时(%.1fs)，跳过 kind=%s", wait, kind)
        return False
    except Exception as exc:
        logger.exception("Agent memory upsert 失败: %s", exc)
        return False


def _query_sync(
    kind: str,
    query_text: str,
    n_results: int,
    filters: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    col = _get_collection(kind)
    if col is None or not (query_text or "").strip():
        return []
    n = max(1, min(int(n_results), 20))
    kwargs: Dict[str, Any] = {
        "query_texts": [query_text],
        "n_results": n,
        "include": ["documents", "metadatas", "distances"],
    }
    where = {k: v for k, v in (filters or {}).items() if v not in (None, "")}
    if where:
        try:
            kwargs["where"] = where
            res = col.query(**kwargs)
        except Exception:
            kwargs.pop("where", None)
            res = col.query(**kwargs)
    else:
        res = col.query(**kwargs)

    out: List[Dict[str, Any]] = []
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    for i, mid in enumerate(ids):
        out.append({
            "id": mid,
            "document": docs[i] if i < len(docs) else "",
            "metadata": dict(metas[i] if i < len(metas) else {}),
            "distance": dists[i] if i < len(dists) else None,
        })
    return out


def query_memory(
    kind: str,
    query_text: str,
    *,
    n_results: int = 5,
    filters: Optional[Dict[str, Any]] = None,
    timeout_sec: Optional[float] = None,
) -> List[Dict[str, Any]]:
    if not agent_memory_enabled():
        return []
    wait = _DEFAULT_TIMEOUT_SEC if timeout_sec is None else float(timeout_sec)
    fut = _OP_POOL.submit(_query_sync, kind, query_text, n_results, filters)
    try:
        return fut.result(timeout=max(0.5, wait))
    except FuturesTimeout:
        logger.warning("Agent memory query 超时(%.1fs)，跳过 kind=%s", wait, kind)
        return []
    except Exception as exc:
        logger.warning("Agent memory query 失败: %s", exc)
        return []


def count_memory(kind: str) -> int:
    col = _get_collection(kind)
    if col is None:
        return 0
    try:
        return int(col.count())
    except Exception:
        return 0
