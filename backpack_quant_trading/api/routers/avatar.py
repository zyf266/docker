"""小沫数字人 API。"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from backpack_quant_trading.api.deps import require_user
from backpack_quant_trading.core.avatar_agent import handle_avatar_chat
from backpack_quant_trading.core.avatar_did import create_talk_video, did_enabled
from backpack_quant_trading.core.avatar_tts import DEFAULT_VOICE, synthesize_mp3, tts_available

logger = logging.getLogger(__name__)
router = APIRouter()

_PORTRAIT = Path(__file__).resolve().parents[2] / "static" / "avatar" / "xiaomo-avatar.png"


class AvatarChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: Optional[List[Dict[str, str]]] = None


class AvatarChatResponse(BaseModel):
    reply: str
    intent: str = "llm"
    speak: bool = True
    speak_text: Optional[str] = None
    navigate: Optional[str] = None
    suggestions: Optional[List[str]] = None
    agent_ok: Optional[bool] = None


class AvatarTtsRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    voice: Optional[str] = None


class AvatarTalkRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    voice: Optional[str] = None


@router.get("/meta")
def avatar_meta(user: dict = Depends(require_user)) -> Dict[str, Any]:
    porcupine_ready = bool(os.getenv("PICOVOICE_ACCESS_KEY", "").strip())
    return {
        "name": "小沫",
        "wake_mode": "hotword_after_permission",
        "wake_engine": "porcupine" if porcupine_ready else "web_speech",
        "wake_words": ["小沫", "小默", "小魔"],
        "tts": "edge_tts" if tts_available() else "browser_speech_synthesis",
        "tts_voice": DEFAULT_VOICE if tts_available() else None,
        "asr": "browser_web_speech",
        "avatar": "portrait_png_v1",
        "portrait_url": "/xiaomo-avatar.png",
        "did_enabled": did_enabled(),
        "capabilities": [
            "menu",
            "feature_guide",
            "strategy_overview",
            "market_quote",
            "navigate",
            "agent",
            "wake_hotword",
            "cloud_tts",
            "did_talk" if did_enabled() else "portrait_still",
            "llm_fallback",
        ],
        "notes": {
            "portrait": "使用 static/avatar/xiaomo-avatar.png 科幻女半身",
            "did": "配置 DID_API_KEY 后 /api/avatar/talk 可生成口型视频（免费额度有限、较慢）",
            "porcupine": "需 PICOVOICE_ACCESS_KEY + 自定义「小沫」.ppn；默认 web_speech",
        },
    }


@router.get("/portrait")
def avatar_portrait(user: dict = Depends(require_user)):
    if not _PORTRAIT.is_file():
        raise HTTPException(status_code=404, detail="形象文件不存在")
    return FileResponse(_PORTRAIT, media_type="image/png", filename="xiaomo-avatar.png")


@router.post("/chat", response_model=AvatarChatResponse)
def avatar_chat(req: AvatarChatRequest, user: dict = Depends(require_user)) -> AvatarChatResponse:
    out = handle_avatar_chat(req.message, req.history or [])
    return AvatarChatResponse(
        reply=str(out.get("reply") or ""),
        intent=str(out.get("intent") or "llm"),
        speak=bool(out.get("speak", True)),
        speak_text=out.get("speak_text"),
        navigate=out.get("navigate"),
        suggestions=out.get("suggestions"),
        agent_ok=out.get("agent_ok"),
    )


@router.post("/tts")
async def avatar_tts(req: AvatarTtsRequest, user: dict = Depends(require_user)) -> Response:
    if not tts_available():
        raise HTTPException(status_code=503, detail="edge-tts 未安装")
    try:
        data, voice = await synthesize_mp3(req.text, req.voice)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.warning("avatar tts failed: %s", e)
        raise HTTPException(status_code=502, detail=f"TTS 失败: {e}") from e
    return Response(
        content=data,
        media_type="audio/mpeg",
        headers={
            "X-Avatar-TTS-Voice": voice,
            "Cache-Control": "no-store",
        },
    )


@router.post("/talk")
async def avatar_talk(req: AvatarTalkRequest, user: dict = Depends(require_user)) -> Dict[str, Any]:
    """D-ID 口型视频；无 Key 返回 503，前端回退静图+TTS。"""
    if not did_enabled():
        raise HTTPException(status_code=503, detail="未配置 DID_API_KEY")
    voice = (req.voice or "zh-CN-XiaoyiNeural").strip()
    try:
        url, talk_id = await create_talk_video(req.text, voice_id=voice)
    except Exception as e:
        logger.warning("avatar did talk failed: %s", e)
        raise HTTPException(status_code=502, detail=f"D-ID 失败: {e}") from e
    return {"video_url": url, "talk_id": talk_id, "provider": "d-id"}
