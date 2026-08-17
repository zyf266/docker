"""D-ID 仿真说话视频（可选；无 DID_API_KEY 则跳过）。"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from pathlib import Path
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

DID_API_BASE = os.getenv("DID_API_BASE", "https://api.d-id.com").rstrip("/")
DID_API_KEY = os.getenv("DID_API_KEY", "").strip()
# 可选：已上传到 D-ID / 公网可访问的形象 URL；空则用本地图上传一次并缓存
DID_SOURCE_URL = os.getenv("DID_SOURCE_URL", "").strip()

_LOCAL_IMAGE = Path(__file__).resolve().parents[1] / "static" / "avatar" / "xiaomo-avatar.png"
_cached_source_url: Optional[str] = None


def did_enabled() -> bool:
    return bool(DID_API_KEY)


def _auth_header() -> str:
    # Studio 给出 username:password，按 Basic 编码
    raw = DID_API_KEY
    if raw.lower().startswith("basic "):
        return raw
    # 已是 base64 或 username:password
    if ":" in raw and not raw.startswith("ey"):
        token = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        return f"Basic {token}"
    return f"Basic {raw}"


async def _ensure_source_url(client: httpx.AsyncClient) -> str:
    global _cached_source_url
    if DID_SOURCE_URL:
        return DID_SOURCE_URL
    if _cached_source_url:
        return _cached_source_url
    if not _LOCAL_IMAGE.is_file():
        raise FileNotFoundError(f"缺少形象文件: {_LOCAL_IMAGE}")
    headers = {"Authorization": _auth_header(), "Accept": "application/json"}
    with _LOCAL_IMAGE.open("rb") as f:
        files = {"image": ("xiaomo-avatar.png", f, "image/png")}
        r = await client.post(f"{DID_API_BASE}/images", headers=headers, files=files, timeout=60.0)
    if r.status_code >= 400:
        raise RuntimeError(f"D-ID 上传形象失败: {r.status_code} {r.text[:300]}")
    data = r.json() if r.content else {}
    url = data.get("url") or data.get("image_url") or data.get("source_url")
    if not url:
        raise RuntimeError(f"D-ID 上传形象无 url: {data}")
    _cached_source_url = str(url)
    return _cached_source_url


async def create_talk_video(text: str, voice_id: str = "zh-CN-XiaoyiNeural") -> Tuple[str, str]:
    """
    文本 → D-ID 说话视频。
    返回 (result_url, talk_id)。免费额度耗尽会抛错。
    """
    if not did_enabled():
        raise RuntimeError("未配置 DID_API_KEY")
    plain = str(text or "").strip()[:280]
    if not plain:
        raise ValueError("empty text")

    headers = {
        "Authorization": _auth_header(),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        source_url = await _ensure_source_url(client)
        payload = {
            "source_url": source_url,
            "script": {
                "type": "text",
                "input": plain,
                "provider": {"type": "microsoft", "voice_id": voice_id},
            },
            "config": {"stitch": True, "result_format": "mp4"},
        }
        r = await client.post(f"{DID_API_BASE}/talks", headers=headers, json=payload, timeout=60.0)
        if r.status_code >= 400:
            raise RuntimeError(f"D-ID 创建 talk 失败: {r.status_code} {r.text[:400]}")
        talk_id = (r.json() or {}).get("id")
        if not talk_id:
            raise RuntimeError(f"D-ID 无 talk id: {r.text[:300]}")

        # 轮询（免费试用常见 10～40s）
        deadline = time.monotonic() + 90.0
        while time.monotonic() < deadline:
            await asyncio.sleep(2.0)
            g = await client.get(f"{DID_API_BASE}/talks/{talk_id}", headers=headers, timeout=30.0)
            if g.status_code >= 400:
                raise RuntimeError(f"D-ID 查询失败: {g.status_code} {g.text[:300]}")
            body = g.json() or {}
            status = str(body.get("status") or "")
            if status == "done":
                url = body.get("result_url")
                if not url:
                    raise RuntimeError("D-ID done 但无 result_url")
                return str(url), str(talk_id)
            if status in ("error", "rejected", "failed"):
                raise RuntimeError(f"D-ID talk 失败: {body}")
        raise TimeoutError("D-ID 生成超时")
