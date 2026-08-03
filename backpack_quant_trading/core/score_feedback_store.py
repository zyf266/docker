"""Chroma 持久化：AI 信号评分用户反馈向量库。"""
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
_COLLECTION = "score_feedback"
_LOCK = threading.Lock()
_CLIENT = None
_COLLECTION_OBJ = None
_QUERY_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="score-fb")
_DEFAULT_QUERY_TIMEOUT = float(os.getenv("SCORE_FEEDBACK_TIMEOUT_SEC", "3") or 3)


def chroma_enabled() -> bool:
    env = os.getenv("SCORE_FEEDBACK_CHROMA_ENABLED", "1").strip().lower()
    return env not in ("0", "false", "no", "off")


def _chroma_path() -> Path:
    custom = os.getenv("SCORE_FEEDBACK_CHROMA_PATH", "").strip()
    return Path(custom) if custom else _CHROMA_DIR


def _get_collection():
    global _CLIENT, _COLLECTION_OBJ
    if not chroma_enabled():
        return None
    with _LOCK:
        if _COLLECTION_OBJ is not None:
            return _COLLECTION_OBJ
        try:
            import chromadb
        except ImportError:
            logger.warning("未安装 chromadb，评分反馈向量库不可用")
            return None
        path = _chroma_path()
        path.mkdir(parents=True, exist_ok=True)
        _CLIENT = chromadb.PersistentClient(path=str(path))
        from backpack_quant_trading.core.chroma_embedding import get_embedding_function

        ef = get_embedding_function()
        kwargs = {
            "name": _COLLECTION,
            "metadata": {"hnsw:space": "cosine"},
        }
        if ef is not None:
            kwargs["embedding_function"] = ef
        _COLLECTION_OBJ = _CLIENT.get_or_create_collection(**kwargs)
        return _COLLECTION_OBJ


def upsert_feedback(
    feedback_id: str,
    document: str,
    metadata: Dict[str, Any],
) -> bool:
    col = _get_collection()
    if col is None:
        return False
    meta = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
            for k, v in metadata.items()}
    for k, v in list(meta.items()):
        if v is None:
            meta[k] = ""
        elif not isinstance(v, (str, int, float, bool)):
            meta[k] = str(v)
    try:
        col.upsert(
            ids=[feedback_id],
            documents=[document],
            metadatas=[meta],
        )
        return True
    except Exception as exc:
        logger.exception("Chroma upsert 失败: %s", exc)
        return False


def query_similar(
    query_text: str,
    *,
    n_results: int = 5,
    symbol: str = "",
    timeout_sec: Optional[float] = None,
) -> List[Dict[str, Any]]:
    wait = _DEFAULT_QUERY_TIMEOUT if timeout_sec is None else float(timeout_sec)
    fut = _QUERY_POOL.submit(_query_similar_sync, query_text, n_results, symbol)
    try:
        return fut.result(timeout=max(0.5, wait))
    except FuturesTimeout:
        logger.warning("score_feedback query 超时(%.1fs)，跳过", wait)
        return []
    except Exception as exc:
        logger.warning("score_feedback query 失败: %s", exc)
        return []


def _query_similar_sync(
    query_text: str,
    n_results: int,
    symbol: str,
) -> List[Dict[str, Any]]:
    col = _get_collection()
    if col is None or not query_text.strip():
        return []
    n = max(1, min(int(n_results), 20))
    try:
        where = None
        sym = (symbol or "").strip().upper()
        if sym:
            where = {"symbol": sym}
        kwargs: Dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": n,
            "include": ["documents", "metadatas", "distances"],
        }
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
        for i, fid in enumerate(ids):
            meta = dict(metas[i] if i < len(metas) else {})
            for key in ("gate_patch", "metrics_compact"):
                raw = meta.get(key)
                if isinstance(raw, str) and raw.startswith("{"):
                    try:
                        meta[key] = json.loads(raw)
                    except Exception:
                        pass
            out.append({
                "id": fid,
                "document": docs[i] if i < len(docs) else "",
                "metadata": meta,
                "distance": dists[i] if i < len(dists) else None,
            })
        return out
    except Exception as exc:
        logger.warning("Chroma query 失败: %s", exc)
        return []


def count_feedbacks() -> int:
    col = _get_collection()
    if col is None:
        return 0
    try:
        return int(col.count())
    except Exception:
        return 0
