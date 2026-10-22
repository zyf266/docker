"""普通用户产品站：自选、站内信、咨询、邮件口子。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base

from backpack_quant_trading.database.models import DatabaseManager

StoreBase = declarative_base()


class PortalFavorite(StoreBase):
    __tablename__ = "portal_favorites"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(32), nullable=False)
    market = Column(String(16), nullable=False, default="crypto")  # crypto | us
    name = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_portal_fav_user_symbol"),)


class PortalInbox(StoreBase):
    __tablename__ = "portal_inbox"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(120), nullable=False)
    body = Column(Text, nullable=False, default="")
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.now)


class PortalContact(StoreBase):
    __tablename__ = "portal_contacts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    phone = Column(String(32), nullable=False)
    experience = Column(String(32), nullable=True)
    interests = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class PortalEmailOutbox(StoreBase):
    """邮件口子：先落库，真正 SMTP 后期再补。"""
    __tablename__ = "portal_email_outbox"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    to_addr = Column(String(120), nullable=False)
    subject = Column(String(200), nullable=False)
    body = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="pending")  # pending | stub
    created_at = Column(DateTime, default=datetime.now)


class PortalWatchConfig(StoreBase):
    """观察库跟单/策略配置（按用户+交易对）。"""
    __tablename__ = "portal_watch_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(32), nullable=False)
    require_short = Column(Boolean, nullable=False, default=True)
    require_mid = Column(Boolean, nullable=False, default=True)
    require_long = Column(Boolean, nullable=False, default=False)
    strategy_name = Column(String(80), nullable=False, default="")
    timeframe = Column(String(16), nullable=False, default="2h")
    size_mode = Column(String(16), nullable=False, default="percent")  # fixed | percent
    size_value = Column(String(32), nullable=False, default="10")
    take_profit = Column(String(32), nullable=False, default="")  # 止盈%，空=未设
    stop_loss = Column(String(32), nullable=False, default="")  # 止损%，空=未设
    status = Column(String(16), nullable=False, default="")  # '' | living | connected
    exchange = Column(String(32), nullable=False, default="")  # okx | hyperliquid | binance
    updated_at = Column(DateTime, default=datetime.now)
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_portal_watch_cfg"),)


class PortalExchangeBinding(StoreBase):
    """用户交易所连接（密钥 RSA 加密后 JSON 落库）。"""
    __tablename__ = "portal_exchange_bindings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    platform = Column(String(32), nullable=False)  # okx | hyperliquid | binance
    config_json = Column(Text, nullable=False, default="{}")
    status = Column(String(16), nullable=False, default="connected")
    updated_at = Column(DateTime, default=datetime.now)
    __table_args__ = (UniqueConstraint("user_id", "platform", name="uq_portal_ex_user_plat"),)


# 搜索占位目录（后期换真数据）
_SEARCH_CATALOG = [
    {"type": "strategy", "id": "trend-crypto", "title": "趋势-加密", "subtitle": "BTC/ETH 趋势跟踪"},
    {"type": "strategy", "id": "grid-crypto", "title": "网格-加密", "subtitle": "震荡行情网格"},
    {"type": "strategy", "id": "momentum-us", "title": "动量-美股", "subtitle": "NVDA/TSLA 动量"},
    {"type": "strategy", "id": "cross-market", "title": "跨市场", "subtitle": "加密+美股组合"},
    {"type": "symbol", "id": "BTCUSDT", "title": "BTCUSDT", "subtitle": "Bitcoin · 加密", "market": "crypto"},
    {"type": "symbol", "id": "ETHUSDT", "title": "ETHUSDT", "subtitle": "Ethereum · 加密", "market": "crypto"},
    {"type": "symbol", "id": "SOLUSDT", "title": "SOLUSDT", "subtitle": "Solana · 加密", "market": "crypto"},
    {"type": "symbol", "id": "NVDA", "title": "NVDA", "subtitle": "英伟达 · 美股", "market": "us"},
    {"type": "symbol", "id": "AAPL", "title": "AAPL", "subtitle": "苹果 · 美股", "market": "us"},
    {"type": "symbol", "id": "TSLA", "title": "TSLA", "subtitle": "特斯拉 · 美股", "market": "us"},
]


def _ensure_watch_config_columns(engine) -> None:
    """已有表时 create_all 不会加列，补止盈/止损/状态字段。"""
    from sqlalchemy import text

    with engine.begin() as conn:
        try:
            rows = conn.execute(text("SHOW COLUMNS FROM portal_watch_configs")).fetchall()
        except Exception:
            return
        existing = {str(r[0]) for r in rows}
        alters = []
        if "take_profit" not in existing:
            alters.append("ALTER TABLE portal_watch_configs ADD COLUMN take_profit VARCHAR(32) NOT NULL DEFAULT ''")
        if "stop_loss" not in existing:
            alters.append("ALTER TABLE portal_watch_configs ADD COLUMN stop_loss VARCHAR(32) NOT NULL DEFAULT ''")
        if "status" not in existing:
            alters.append("ALTER TABLE portal_watch_configs ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT ''")
        if "exchange" not in existing:
            alters.append("ALTER TABLE portal_watch_configs ADD COLUMN exchange VARCHAR(32) NOT NULL DEFAULT ''")
        for sql in alters:
            conn.execute(text(sql))


def _session():
    manager = DatabaseManager()
    StoreBase.metadata.create_all(manager.engine, checkfirst=True)
    try:
        _ensure_watch_config_columns(manager.engine)
    except Exception:
        pass
    return manager.get_session()


def list_favorites(user_id: int) -> List[Dict[str, Any]]:
    session = _session()
    try:
        rows = (
            session.query(PortalFavorite)
            .filter_by(user_id=user_id)
            .order_by(PortalFavorite.created_at.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "symbol": r.symbol,
                "market": r.market,
                "name": r.name or r.symbol,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
            }
            for r in rows
        ]
    finally:
        session.close()


def add_favorite(user_id: int, symbol: str, market: str = "crypto", name: str = "") -> Dict[str, Any]:
    sym = (symbol or "").strip().upper()
    if not sym:
        raise ValueError("symbol 不能为空")
    mkt = "us" if (market or "").lower() in ("us", "美股") else "crypto"
    session = _session()
    try:
        row = session.query(PortalFavorite).filter_by(user_id=user_id, symbol=sym).first()
        if row:
            return {"id": row.id, "symbol": row.symbol, "market": row.market, "name": row.name or row.symbol}
        row = PortalFavorite(user_id=user_id, symbol=sym, market=mkt, name=(name or sym).strip())
        session.add(row)
        session.commit()
        return {"id": row.id, "symbol": row.symbol, "market": row.market, "name": row.name}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def remove_favorite(user_id: int, symbol: str) -> bool:
    sym = (symbol or "").strip().upper()
    session = _session()
    try:
        row = session.query(PortalFavorite).filter_by(user_id=user_id, symbol=sym).first()
        if not row:
            return False
        session.delete(row)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def search_catalog(q: str, limit: int = 30) -> List[Dict[str, Any]]:
    key = (q or "").strip().lower()
    if not key:
        return list(_SEARCH_CATALOG)[:limit]
    hits = []
    for item in _SEARCH_CATALOG:
        blob = f"{item.get('title','')} {item.get('subtitle','')} {item.get('id','')}".lower()
        if key in blob:
            hits.append(item)
    return hits[:limit]


def list_inbox(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    session = _session()
    try:
        rows = (
            session.query(PortalInbox)
            .filter_by(user_id=user_id)
            .order_by(PortalInbox.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "title": r.title,
                "body": r.body,
                "is_read": bool(r.is_read),
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
            }
            for r in rows
        ]
    finally:
        session.close()


def create_inbox(user_id: int, title: str, body: str = "") -> Dict[str, Any]:
    session = _session()
    try:
        row = PortalInbox(user_id=user_id, title=title.strip() or "通知", body=body or "")
        session.add(row)
        session.commit()
        return {"id": row.id, "title": row.title, "body": row.body, "is_read": False}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def mark_inbox_read(user_id: int, msg_id: int) -> bool:
    session = _session()
    try:
        row = session.query(PortalInbox).filter_by(id=msg_id, user_id=user_id).first()
        if not row:
            return False
        row.is_read = True
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def enqueue_email(user_id: Optional[int], to_addr: str, subject: str, body: str = "") -> Dict[str, Any]:
    """邮件口子：写入 outbox，status=stub，不真正发送。"""
    session = _session()
    try:
        row = PortalEmailOutbox(
            user_id=user_id,
            to_addr=(to_addr or "").strip(),
            subject=(subject or "").strip() or "沐龙量化通知",
            body=body or "",
            status="stub",
        )
        session.add(row)
        session.commit()
        return {
            "id": row.id,
            "status": "stub",
            "message": "邮件口子已记录，SMTP 发送后期接入",
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_contact(
    name: str,
    phone: str,
    experience: str = "",
    interests: Optional[List[str]] = None,
    message: str = "",
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    session = _session()
    try:
        row = PortalContact(
            name=(name or "").strip(),
            phone=(phone or "").strip(),
            experience=(experience or "").strip() or None,
            interests=",".join(interests or []) if interests else None,
            message=(message or "").strip() or None,
            user_id=user_id,
        )
        session.add(row)
        session.commit()
        return {"id": row.id, "ok": True}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _watch_config_dict(r: PortalWatchConfig) -> Dict[str, Any]:
    return {
        "id": r.id,
        "user_id": r.user_id,
        "symbol": r.symbol,
        "require_short": bool(r.require_short),
        "require_mid": bool(r.require_mid),
        "require_long": bool(r.require_long),
        "strategy_name": r.strategy_name or "",
        "timeframe": r.timeframe or "2h",
        "size_mode": r.size_mode or "percent",
        "size_value": r.size_value or "10",
        "take_profit": getattr(r, "take_profit", None) or "",
        "stop_loss": getattr(r, "stop_loss", None) or "",
        "status": getattr(r, "status", None) or "",
        "exchange": getattr(r, "exchange", None) or "",
        "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else "",
    }


def list_watch_configs(user_id: int) -> List[Dict[str, Any]]:
    session = _session()
    try:
        rows = session.query(PortalWatchConfig).filter_by(user_id=user_id).all()
        return [_watch_config_dict(r) for r in rows]
    finally:
        session.close()


def _norm_tf(raw: str) -> str:
    return (raw or "").strip().lower().replace(" ", "")


def _symbol_bases(raw: str) -> set:
    """BTC / BTCUSDT / btc-usdt → 可比对的 base 集合。"""
    s = (raw or "").strip().upper().replace("/", "").replace("-", "").replace("_", "")
    if not s:
        return set()
    bases = {s}
    for suffix in ("USDT", "USDC", "USD", "PERP"):
        if s.endswith(suffix) and len(s) > len(suffix):
            bases.add(s[: -len(suffix)])
    if not s.endswith("USDT") and s.isalpha() and 2 <= len(s) <= 10:
        bases.add(f"{s}USDT")
    return bases


def find_connected_configs(
    strategy_name: str,
    symbol: str,
    timeframe: str,
) -> List[Dict[str, Any]]:
    """全库匹配 status=connected 且策略名/币种/周期一致的观察配置。"""
    name = (strategy_name or "").strip()
    tf = _norm_tf(timeframe)
    want_bases = _symbol_bases(symbol)
    if not name or not tf or not want_bases:
        return []
    session = _session()
    try:
        rows = (
            session.query(PortalWatchConfig)
            .filter(PortalWatchConfig.status == "connected")
            .all()
        )
        out = []
        for r in rows:
            if (r.strategy_name or "").strip() != name:
                continue
            if _norm_tf(r.timeframe or "") != tf:
                continue
            cfg_bases = _symbol_bases(r.symbol or "")
            if not (cfg_bases & want_bases):
                continue
            out.append(_watch_config_dict(r))
        return out
    finally:
        session.close()


def get_exchange_binding(user_id: int, platform: str) -> Optional[Dict[str, Any]]:
    plat = (platform or "").strip().lower()
    session = _session()
    try:
        row = session.query(PortalExchangeBinding).filter_by(user_id=user_id, platform=plat).first()
        if not row:
            return None
        try:
            cfg = json.loads(row.config_json or "{}")
        except Exception:
            cfg = {}
        return {
            "id": row.id,
            "platform": row.platform,
            "status": row.status or "connected",
            "config": cfg,
            "updated_at": row.updated_at.strftime("%Y-%m-%d %H:%M:%S") if row.updated_at else "",
        }
    finally:
        session.close()


def upsert_watch_configs(
    user_id: int,
    symbols: List[str],
    *,
    require_short: bool,
    require_mid: bool,
    require_long: bool,
    strategy_name: str,
    timeframe: str,
    size_mode: str,
    size_value: str,
    take_profit: str = "",
    stop_loss: str = "",
) -> List[Dict[str, Any]]:
    cleaned = []
    for raw in symbols or []:
        sym = (raw or "").strip().upper()
        if sym and sym not in cleaned:
            cleaned.append(sym)
    if not cleaned:
        raise ValueError("请至少选择一个交易对")
    mode = "fixed" if (size_mode or "").lower() in ("fixed", "amount", "固定", "固定金额") else "percent"
    tf = (timeframe or "2h").strip() or "2h"
    name = (strategy_name or "").strip()
    if not name:
        raise ValueError("请填写策略名称")
    value = str(size_value or "").strip()
    if not value:
        raise ValueError("请填写仓位大小")
    tp = str(take_profit or "").strip()
    sl = str(stop_loss or "").strip()
    session = _session()
    try:
        out = []
        now = datetime.now()
        for sym in cleaned:
            row = session.query(PortalWatchConfig).filter_by(user_id=user_id, symbol=sym).first()
            if not row:
                row = PortalWatchConfig(user_id=user_id, symbol=sym)
                session.add(row)
            row.require_short = bool(require_short)
            row.require_mid = bool(require_mid)
            row.require_long = bool(require_long)
            row.strategy_name = name
            row.timeframe = tf
            row.size_mode = mode
            row.size_value = value
            row.take_profit = tp
            row.stop_loss = sl
            # 保存配置后进入 living；已连接交易所的保持 connected
            cur = (getattr(row, "status", None) or "").strip().lower()
            if cur != "connected":
                row.status = "living"
            row.updated_at = now
            session.flush()
            out.append(_watch_config_dict(row))
        session.commit()
        return out
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def mark_watch_connected(user_id: int, symbols: List[str], exchange: str) -> List[Dict[str, Any]]:
    cleaned = []
    for raw in symbols or []:
        sym = (raw or "").strip().upper()
        if not sym:
            continue
        # 与 /watchlist/config 一致：USDT 结尾或长代码当加密对
        if sym.endswith("USDT") or len(sym) > 5:
            if not sym.endswith("USDT"):
                sym = f"{sym}USDT"
        if sym not in cleaned:
            cleaned.append(sym)
    if not cleaned:
        return []
    plat = (exchange or "").strip().lower()
    session = _session()
    try:
        out = []
        now = datetime.now()
        for sym in cleaned:
            row = session.query(PortalWatchConfig).filter_by(user_id=user_id, symbol=sym).first()
            if not row and sym.endswith("USDT"):
                # 兜底：配置里可能存了不带 USDT 的短码
                short = sym[:-4]
                row = session.query(PortalWatchConfig).filter_by(user_id=user_id, symbol=short).first()
            if not row:
                continue
            row.status = "connected"
            row.exchange = plat
            row.updated_at = now
            session.flush()
            out.append(_watch_config_dict(row))
        session.commit()
        return out
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_exchange_binding(user_id: int, platform: str, config: Dict[str, Any]) -> Dict[str, Any]:
    plat = (platform or "").strip().lower()
    session = _session()
    try:
        row = session.query(PortalExchangeBinding).filter_by(user_id=user_id, platform=plat).first()
        if not row:
            row = PortalExchangeBinding(user_id=user_id, platform=plat)
            session.add(row)
        row.config_json = json.dumps(config or {}, ensure_ascii=False)
        row.status = "connected"
        row.updated_at = datetime.now()
        session.commit()
        return {
            "id": row.id,
            "platform": row.platform,
            "status": row.status,
            "updated_at": row.updated_at.strftime("%Y-%m-%d %H:%M:%S") if row.updated_at else "",
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def list_exchange_bindings(user_id: int) -> List[Dict[str, Any]]:
    session = _session()
    try:
        rows = session.query(PortalExchangeBinding).filter_by(user_id=user_id).all()
        out = []
        for r in rows:
            try:
                cfg = json.loads(r.config_json or "{}")
            except Exception:
                cfg = {}
            out.append({
                "id": r.id,
                "platform": r.platform,
                "status": r.status or "connected",
                "config": cfg,
                "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else "",
            })
        return out
    finally:
        session.close()


def equity_overlay_mock(strategy_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """多策略净值叠加占位数据。"""
    ids = strategy_ids or ["trend-crypto", "grid-crypto", "momentum-us"]
    series = []
    for i, sid in enumerate(ids[:4]):
        base = 1.0 + i * 0.02
        points = []
        for d in range(0, 30):
            points.append({"t": f"2026-09-{d+1:02d}" if d < 30 else "2026-10-01", "v": round(base + d * (0.003 + i * 0.001), 4)})
        # fix fake dates simply
        points = [{"t": f"D{d+1}", "v": round(base + d * (0.003 + i * 0.001), 4)} for d in range(30)]
        series.append({"id": sid, "name": next((x["title"] for x in _SEARCH_CATALOG if x["id"] == sid), sid), "points": points})
    return {"series": series, "note": "占位数据，后期接真实净值"}
