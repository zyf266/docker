"""小沫云端 TTS（edge-tts 免费神经女声，失败由前端回退浏览器）。"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_VOICE = os.getenv("AVATAR_TTS_VOICE", "zh-CN-XiaoyiNeural")
MAX_CHARS = int(os.getenv("AVATAR_TTS_MAX_CHARS", "500"))


def _plain_for_tts(text: str) -> str:
    import re

    s = str(text or "")
    s = re.sub(r"[#>*_`]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:MAX_CHARS]


def tts_available() -> bool:
    try:
        import edge_tts  # noqa: F401

        return True
    except Exception:
        return False


async def synthesize_mp3(text: str, voice: Optional[str] = None) -> Tuple[bytes, str]:
    """返回 (mp3_bytes, voice_used)。"""
    plain = _plain_for_tts(text)
    if not plain:
        raise ValueError("empty text")
    try:
        import edge_tts
    except ImportError as e:
        raise RuntimeError("edge-tts 未安装") from e

    v = (voice or DEFAULT_VOICE).strip() or DEFAULT_VOICE
    communicate = edge_tts.Communicate(plain, v)
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio" and chunk.get("data"):
            chunks.append(chunk["data"])
    data = b"".join(chunks)
    if not data:
        raise RuntimeError("TTS 无音频数据")
    return data, v


def synthesize_mp3_sync(text: str, voice: Optional[str] = None) -> Tuple[bytes, str]:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        # 不应在已有 loop 里用 asyncio.run；路由用 async 版
        raise RuntimeError("use synthesize_mp3 in async context")
    return asyncio.run(synthesize_mp3(text, voice))
