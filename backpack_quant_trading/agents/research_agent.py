"""信息检索 Agent：固定源 B（不上通用搜索 Key）。"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Protocol

from backpack_quant_trading.agents.types import Citation, Market
from backpack_quant_trading.core.agent_memory_store import upsert_memory
from backpack_quant_trading.core.stock_news_feeds import DEFAULT_JIN10_APP_ID

logger = logging.getLogger(__name__)


class GenericSearchProvider(Protocol):
    """预留 A 类通用搜索；本期不调用。"""

    def search(self, query: str, *, limit: int = 8) -> List[Citation]:
        ...


class NullGenericSearchProvider:
    def search(self, query: str, *, limit: int = 8) -> List[Citation]:
        return []


def _to_citations_from_us(ctx: Dict[str, Any]) -> List[Citation]:
    out: List[Citation] = []
    items = (ctx or {}).get("items") or (ctx or {}).get("news") or []
    if not items and isinstance(ctx, dict):
        # fetch_us_stock_news_context 可能直接返回 list-like 字段
        for key in ("rows", "list"):
            if isinstance(ctx.get(key), list):
                items = ctx[key]
                break
    for it in items:
        out.append(
            Citation(
                title=str(it.get("title") or it.get("text") or "")[:200],
                snippet=str(it.get("text") or it.get("summary") or "")[:400],
                url=str(it.get("url") or ""),
                source=str(it.get("source") or it.get("feed_key") or "us_news"),
            )
        )
    return out


def _research_us(symbol: str, limit: int) -> tuple[List[Citation], str]:
    try:
        from backpack_quant_trading.core.us_stock_news import fetch_us_stock_news_context

        ctx = fetch_us_stock_news_context(symbol, max_items=limit)
        if isinstance(ctx, dict) and "items" not in ctx:
            # 兼容：把常见字段归一
            maybe = []
            for v in ctx.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    maybe = v
                    break
            if maybe:
                ctx = {"items": maybe}
        cites = _to_citations_from_us(ctx if isinstance(ctx, dict) else {})
        if not cites:
            return [], "美股固定源暂无新闻"
        return cites[:limit], ""
    except Exception as exc:
        logger.warning("US research failed %s: %s", symbol, exc)
        return [], f"美股检索失败: {exc}"


def _research_a_share(symbol: str, limit: int) -> tuple[List[Citation], str]:
    try:
        from backpack_quant_trading.core.stock_news_feeds import (
            fetch_jin10_flash_rows,
            fetch_unified_for_source,
            jin10_row_to_unified,
        )

        cites: List[Citation] = []
        x_app = DEFAULT_JIN10_APP_ID
        for source_key in ("eastmoney", "ths", "sina"):
            rows, err = fetch_unified_for_source(source_key, jin10_x_app_id=x_app, timeout=12.0)
            if err or not rows:
                continue
            sym = symbol.upper().replace(".SH", "").replace(".SZ", "")
            for it in rows:
                blob = f"{it.get('text') or ''} {it.get('title') or ''}"
                if sym and sym not in blob.replace(" ", "") and symbol not in blob:
                    continue
                cites.append(
                    Citation(
                        title=str(it.get("text") or it.get("title") or "")[:200],
                        snippet=str(it.get("text") or "")[:400],
                        url=str(it.get("url") or ""),
                        source=str(it.get("feed") or source_key),
                    )
                )
                if len(cites) >= limit:
                    break
            if len(cites) >= limit:
                break

        if len(cites) < 2:
            rows, _err = fetch_jin10_flash_rows(x_app, timeout=10.0)
            for row in rows or []:
                u = jin10_row_to_unified(row) or {}
                text = str(u.get("text") or "")
                if not text:
                    continue
                cites.append(
                    Citation(title=text[:200], snippet=text[:400], url=str(u.get("url") or ""), source="jin10")
                )
                if len(cites) >= limit:
                    break

        if not cites:
            return [], "A股固定源暂无匹配新闻"
        return cites[:limit], ""
    except Exception as exc:
        logger.warning("A-share research failed %s: %s", symbol, exc)
        return [], f"A股检索失败: {exc}"


def _research_crypto(symbol: str, limit: int) -> tuple[List[Citation], str]:
    try:
        from backpack_quant_trading.core.stock_news_feeds import (
            fetch_jin10_flash_rows,
            jin10_row_to_unified,
        )

        hint = (symbol or "").upper().replace("USDT", "").replace("-", "")
        rows, err = fetch_jin10_flash_rows(DEFAULT_JIN10_APP_ID, timeout=10.0)
        cites: List[Citation] = []
        for row in rows or []:
            u = jin10_row_to_unified(row) or {}
            text = str(u.get("text") or "")
            if not text:
                continue
            if hint and hint not in text.upper():
                if not any(k in text for k in ("币", "比特币", "以太", "加密", "BTC", "ETH")):
                    continue
            cites.append(
                Citation(
                    title=text[:200],
                    snippet=text[:400],
                    url=str(u.get("url") or ""),
                    source="jin10",
                )
            )
            if len(cites) >= limit:
                break
        if not cites and rows:
            for row in rows[: max(1, limit // 2)]:
                u = jin10_row_to_unified(row) or {}
                text = str(u.get("text") or "")
                if text:
                    cites.append(Citation(title=text[:200], snippet=text[:400], source="jin10"))
        if not cites:
            return [], err or "加密固定源暂无新闻"
        return cites[:limit], ""
    except Exception as exc:
        logger.warning("Crypto research failed %s: %s", symbol, exc)
        return [], f"加密检索失败: {exc}"


def research(
    symbol: str,
    market: Market | str,
    *,
    limit: int = 8,
    persist: bool = True,
    generic: Optional[GenericSearchProvider] = None,
) -> Dict[str, Any]:
    """检索固定源；generic 预留，本期默认 Null。"""
    if isinstance(market, Market):
        m = market
    else:
        try:
            m = Market(str(market))
        except Exception:
            m = Market.UNKNOWN
    sym = (symbol or "").strip()
    cites: List[Citation] = []
    err = ""

    if m == Market.US_STOCK:
        cites, err = _research_us(sym, limit)
    elif m == Market.A_SHARE:
        cites, err = _research_a_share(sym, limit)
    elif m == Market.CRYPTO:
        cites, err = _research_crypto(sym, limit)
    else:
        err = f"未知市场: {m}"

    provider = generic or NullGenericSearchProvider()
    if not cites:
        try:
            cites.extend(provider.search(f"{sym} 新闻", limit=limit) or [])
        except Exception:
            pass

    if persist and cites:
        blob = "\n".join(f"{c.source}:{c.title}" for c in cites)
        mid = "res_" + hashlib.sha1(f"{m.value}|{sym}|{blob[:200]}".encode()).hexdigest()[:16]
        upsert_memory(
            "agent_research",
            mid,
            f"[{m.value}] {sym}\n{blob}",
            {
                "symbol": sym.upper(),
                "market": m.value,
                "scope": "research",
                "ts": int(time.time()),
            },
        )

    return {
        "ok": bool(cites) or not err,
        "symbol": sym,
        "market": m.value,
        "citations": cites,
        "error": err if not cites else "",
        "degraded": not bool(cites),
    }
