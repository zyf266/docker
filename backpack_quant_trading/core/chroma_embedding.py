"""Chroma 向量函数：国内环境可跳过 79MB ONNX 下载。

CHROMA_EMBEDDING_MODE=
  auto  — 已有 onnx 缓存则用默认模型，否则用 hash（默认）
  onnx  — 强制 DefaultEmbeddingFunction（会下载）
  hash  — 强制本地哈希向量（零下载，语义弱于 ONNX，够用做反馈/偏好检索）
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
    # chroma 解压后通常有 model.onnx；仅有未下完的 tar 不算就绪
    base = home / ".cache" / "chroma" / "onnx_models" / "all-MiniLM-L6-v2"
    if (base / "model.onnx").is_file():
        return True
    # 部分版本解压到子目录
    if any(base.rglob("model.onnx")):
        return True
    return False


class HashEmbeddingFunction:
    """无网络依赖的确定性伪嵌入（384 维），兼容 Chroma EmbeddingFunction 协议。"""

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
        # 每个 token 贡献若干桶
        for i in range(0, 32, 4):
            idx = int.from_bytes(h[i : i + 2], "little") % _DIM
            sign = 1.0 if (h[i + 2] & 1) == 0 else -1.0
            vec[idx] += sign
        # 二元组增强一点短语匹配
    for a, b in zip(tokens, tokens[1:]):
        h = hashlib.sha256(f"{a}_{b}".encode("utf-8")).digest()
        idx = int.from_bytes(h[:2], "little") % _DIM
        vec[idx] += 1.0
    # L2 normalize
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [x / norm for x in vec]


def get_embedding_function() -> Optional[Any]:
    """返回供 get_or_create_collection(embedding_function=...) 使用的对象。"""
    global _CACHED
    if _CACHED is not None:
        return _CACHED

    mode = (os.getenv("CHROMA_EMBEDDING_MODE") or "auto").strip().lower()
    if mode in ("hash", "local", "offline"):
        logger.info("Chroma 使用 hash 嵌入（跳过 ONNX 下载）")
        _CACHED = HashEmbeddingFunction()
        return _CACHED

    if mode == "auto" and not _onnx_cache_ready():
        logger.warning(
            "未检测到 Chroma ONNX 缓存，使用 hash 嵌入。"
            "若需语义更强：把 onnx.tar.gz 放到 ~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/ "
            "后设 CHROMA_EMBEDDING_MODE=onnx 并重建 collection"
        )
        _CACHED = HashEmbeddingFunction()
        return _CACHED

    try:
        from chromadb.utils import embedding_functions

        _CACHED = embedding_functions.DefaultEmbeddingFunction()
        logger.info("Chroma 使用 DefaultEmbeddingFunction (ONNX)")
        return _CACHED
    except Exception as exc:
        logger.warning("ONNX 嵌入不可用，回退 hash: %s", exc)
        _CACHED = HashEmbeddingFunction()
        return _CACHED
