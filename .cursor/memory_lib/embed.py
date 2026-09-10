# -*- coding: utf-8 -*-
"""Cursor 本地开发记忆：嵌入函数（默认 hash，可选 ONNX）。

CURSOR_MEMORY_EMBEDDING=
  hash  — 强制哈希向量（默认，零下载）
  auto  — 有 ONNX 缓存则用 DefaultEmbeddingFunction，否则 hash
  onnx  — 强制 ONNX（会下载）
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

_DIM = 384
_CACHED: Any = None


def _onnx_cache_ready() -> bool:
    home = Path(os.path.expanduser("~"))
    base = home / ".cache" / "chroma" / "onnx_models" / "all-MiniLM-L6-v2"
    if (base / "model.onnx").is_file():
        return True
    return any(base.rglob("model.onnx")) if base.is_dir() else False


class HashEmbeddingFunction:
    """确定性伪嵌入（384 维），兼容 Chroma EmbeddingFunction。"""

    def name(self) -> str:
        return "hash"

    def __call__(self, input: List[str]) -> List[List[float]]:
        texts = input if isinstance(input, list) else [str(input)]
        return [_hash_embed(t) for t in texts]

    def embed_documents(self, input: List[str]) -> List[List[float]]:
        return self(input)

    def embed_query(self, input: List[str] | str) -> List[List[float]]:
        if isinstance(input, str):
            return self([input])
        return self(list(input))


def _hash_embed(text: str) -> List[float]:
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", (text or "").lower())
    if not tokens:
        tokens = ["empty"]
    vec = [0.0] * _DIM
    for tok in tokens:
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        for i in range(0, 32, 4):
            idx = int.from_bytes(h[i : i + 2], "little") % _DIM
            sign = 1.0 if (h[i + 2] & 1) == 0 else -1.0
            vec[idx] += sign
    for a, b in zip(tokens, tokens[1:]):
        h = hashlib.sha256(f"{a}_{b}".encode("utf-8")).digest()
        idx = int.from_bytes(h[:2], "little") % _DIM
        vec[idx] += 1.0
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [x / norm for x in vec]


def get_embedding_function() -> Any:
    global _CACHED
    if _CACHED is not None:
        return _CACHED

    mode = (os.getenv("CURSOR_MEMORY_EMBEDDING") or "hash").strip().lower()
    if mode in ("hash", "local", "offline"):
        _CACHED = HashEmbeddingFunction()
        return _CACHED

    if mode == "auto" and not _onnx_cache_ready():
        _CACHED = HashEmbeddingFunction()
        return _CACHED

    try:
        from chromadb.utils import embedding_functions

        _CACHED = embedding_functions.DefaultEmbeddingFunction()
        return _CACHED
    except Exception as exc:
        logger.warning("ONNX embed unavailable, fallback hash: %s", exc)
        _CACHED = HashEmbeddingFunction()
        return _CACHED
