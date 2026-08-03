"""A股标的解析：中文名 / 6位代码 → 标准代码。"""
from __future__ import annotations

import logging
import re
import threading
import time
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_NAME_TO_CODE: Dict[str, str] = {}
_CODE_TO_NAME: Dict[str, str] = {}
_LOADED_AT = 0.0
_TTL_SEC = 6 * 3600

_NOISE_RE = re.compile(
    r"^(请?帮我|麻烦|帮忙)?(分析一下|分析下|分析|看看|看一下|帮我看|怎么看|研判一下|评一下)\s*",
    re.I,
)
_TRAIL_NOISE_RE = re.compile(r"(的走势|怎么样|如何|信号|评分|日线|周线)$")

# 高频别名兜底（列表/搜索失败时仍可用）
_BUILTIN = {
    "茅台": "600519",
    "贵州茅台": "600519",
    "宁德时代": "300750",
    "利通电子": "603629",
}


def strip_query_noise(text: str) -> str:
    t = (text or "").strip()
    t = _NOISE_RE.sub("", t).strip()
    t = _TRAIL_NOISE_RE.sub("", t).strip()
    return t


def _ensure_name_map() -> None:
    global _LOADED_AT, _NAME_TO_CODE, _CODE_TO_NAME
    now = time.time()
    if _NAME_TO_CODE and (now - _LOADED_AT) < _TTL_SEC:
        return
    with _LOCK:
        if _NAME_TO_CODE and (now - _LOADED_AT) < _TTL_SEC:
            return
        try:
            from backpack_quant_trading.core.stock_ai import _fetch_a_stock_list

            df = _fetch_a_stock_list()
        except Exception as exc:
            logger.warning("加载A股列表失败: %s", exc)
            return
        if df is None or getattr(df, "empty", True):
            return
        name_map: Dict[str, str] = {}
        code_map: Dict[str, str] = {}
        for _, row in df.iterrows():
            code = str(row.get("code") or "").strip()
            name = str(row.get("name") or "").strip()
            if not re.fullmatch(r"\d{6}", code) or not name:
                continue
            code_map[code] = name
            name_map[name] = code
            for suf in ("股份有限公司", "有限公司", "集团", "股份"):
                if name.endswith(suf) and len(name) > len(suf) + 1:
                    short = name[: -len(suf)]
                    name_map.setdefault(short, code)
        _NAME_TO_CODE = name_map
        _CODE_TO_NAME = code_map
        _LOADED_AT = now
        logger.info("A股名称表已加载 names=%s", len(_NAME_TO_CODE))


def _resolve_via_eastmoney_suggest(name: str) -> Optional[Tuple[str, str]]:
    q = (name or "").strip()
    if len(q) < 2:
        return None
    try:
        import requests

        r = requests.get(
            "https://searchapi.eastmoney.com/api/suggest/get",
            params={
                "input": q,
                "type": "14",
                "token": "D43EE5D25F24D5D2EB3919C1C3B1FA08",
                "count": "8",
            },
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://so.eastmoney.com/"},
            timeout=8,
        )
        r.raise_for_status()
        data = (r.json() or {}).get("QuotationCodeTable") or {}
        rows = data.get("Data") or []
        best = None
        for row in rows:
            code = str(row.get("Code") or "").strip()
            nm = str(row.get("Name") or "").strip()
            if not re.fullmatch(r"\d{6}", code):
                continue
            if nm == q or q in nm or nm in q:
                return code, nm or q
            if best is None:
                best = (code, nm or q)
        return best
    except Exception as exc:
        logger.debug("eastmoney suggest failed: %s", exc)
        return None


def resolve_a_share_token(token: str) -> Optional[Tuple[str, str]]:
    """返回 (code, name) 或 None。"""
    raw = strip_query_noise(token)
    if not raw:
        return None
    m = re.search(r"\b(\d{6})\b", raw)
    if m:
        code = m.group(1)
        _ensure_name_map()
        return code, _CODE_TO_NAME.get(code, code)

    if raw in _BUILTIN:
        # 内置仅作兜底；先试东方财富以免写错代码
        em = _resolve_via_eastmoney_suggest(raw)
        if em:
            return em
        return _BUILTIN[raw], raw

    em = _resolve_via_eastmoney_suggest(raw)
    if em:
        return em

    _ensure_name_map()
    if raw in _NAME_TO_CODE:
        code = _NAME_TO_CODE[raw]
        return code, raw
    hits: List[Tuple[str, str]] = []
    for name, code in _NAME_TO_CODE.items():
        if name and name in raw:
            hits.append((name, code))
        elif name and raw in name and len(raw) >= 2:
            hits.append((name, code))
    if not hits:
        return None
    hits.sort(key=lambda x: len(x[0]), reverse=True)
    name, code = hits[0]
    return code, name


def extract_a_share_from_text(text: str) -> Optional[Tuple[str, str]]:
    """从整句提取 A 股 (code, display_name)。"""
    cleaned = strip_query_noise(text)
    m = re.search(r"\b(\d{6})\b", cleaned or text or "")
    if m:
        code = m.group(1)
        _ensure_name_map()
        return code, _CODE_TO_NAME.get(code, code)

    blob = cleaned or text or ""
    for key in sorted(_BUILTIN.keys(), key=len, reverse=True):
        if key in blob:
            hit = resolve_a_share_token(key)
            if hit:
                return hit

    # 无中文时不必拉全市场名称表（分析 ETH/NVDA 等会被拖 5～10s）
    if not re.search(r"[\u4e00-\u9fff]{2,}", blob):
        return None

    parts = re.findall(r"[\u4e00-\u9fff]{2,}", blob)
    parts.sort(key=len, reverse=True)
    for p in parts:
        hit = resolve_a_share_token(p)
        if hit:
            return hit

    _ensure_name_map()
    for name in sorted(_NAME_TO_CODE.keys(), key=len, reverse=True):
        if len(name) >= 2 and name in blob:
            return _NAME_TO_CODE[name], name
    return None
