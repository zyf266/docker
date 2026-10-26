"""普通用户产品站：自选、站内信、咨询、邮件口子。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean, UniqueConstraint
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
    leverage = Column(Integer, nullable=False, default=5)  # 开仓杠杆，默认 5x
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


class PortalTrade(StoreBase):
    """Portal Webhook / 跟单成交记录。"""
    __tablename__ = "portal_trades"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    platform = Column(String(32), nullable=False, default="", index=True)
    symbol = Column(String(32), nullable=False, default="", index=True)
    side = Column(String(16), nullable=False, default="")  # BUY / SELL
    action = Column(String(16), nullable=False, default="")  # open / close
    strategy_name = Column(String(80), nullable=False, default="")
    timeframe = Column(String(16), nullable=False, default="")
    price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=True)
    margin = Column(Float, nullable=True)
    leverage = Column(Integer, nullable=False, default=5)
    pnl = Column(Float, nullable=False, default=0.0)  # 已实现盈亏（开仓多为 0）
    status = Column(String(16), nullable=False, default="ok")  # ok | dry-run | skipped | error
    detail = Column(String(255), nullable=False, default="")
    order_id = Column(String(80), nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)


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
        if "leverage" not in existing:
            alters.append("ALTER TABLE portal_watch_configs ADD COLUMN leverage INT NOT NULL DEFAULT 5")
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


def _trade_dict(r: "PortalTrade") -> Dict[str, Any]:
    return {
        "id": r.id,
        "user_id": r.user_id,
        "platform": r.platform or "",
        "symbol": r.symbol or "",
        "side": r.side or "",
        "action": r.action or "",
        "strategy_name": r.strategy_name or "",
        "timeframe": r.timeframe or "",
        "price": r.price,
        "quantity": r.quantity,
        "margin": r.margin,
        "leverage": int(r.leverage or 5),
        "pnl": float(r.pnl or 0),
        "status": r.status or "",
        "detail": r.detail or "",
        "order_id": r.order_id or "",
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
    }


def record_trade(
    user_id: int,
    *,
    platform: str,
    symbol: str,
    side: str,
    action: str,
    strategy_name: str = "",
    timeframe: str = "",
    price: Optional[float] = None,
    quantity: Optional[float] = None,
    margin: Optional[float] = None,
    leverage: int = 5,
    pnl: float = 0.0,
    status: str = "ok",
    detail: str = "",
    order_id: str = "",
) -> Dict[str, Any]:
    session = _session()
    try:
        row = PortalTrade(
            user_id=int(user_id),
            platform=(platform or "").strip().lower(),
            symbol=(symbol or "").strip().upper(),
            side=(side or "").strip().upper(),
            action=(action or "").strip().lower(),
            strategy_name=(strategy_name or "").strip(),
            timeframe=(timeframe or "").strip(),
            price=price,
            quantity=quantity,
            margin=margin,
            leverage=int(leverage or 5),
            pnl=float(pnl or 0),
            status=(status or "ok").strip(),
            detail=(detail or "")[:255],
            order_id=(order_id or "")[:80],
            created_at=datetime.now(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        session.expunge(row)
        return _trade_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _apply_trade_filters(q, *, platform: str = "", symbol: str = "", strategy: str = ""):
    plat = (platform or "").strip().lower()
    if plat and plat not in ("all", "全部"):
        q = q.filter(PortalTrade.platform == plat)
    sym = (symbol or "").strip().upper().replace("/", "")
    if sym and sym not in ("ALL", "全部"):
        from sqlalchemy import or_

        bases = _symbol_bases(sym)
        conds = [PortalTrade.symbol == b for b in bases]
        conds.append(PortalTrade.symbol.like(f"%{sym}%"))
        q = q.filter(or_(*conds))
    stg = (strategy or "").strip()
    if stg and stg not in ("all", "全部", "ALL"):
        q = q.filter(PortalTrade.strategy_name == stg)
    return q


def _window_stats(subset) -> Dict[str, Any]:
    wins = sum(float(r.pnl or 0) for r in subset if float(r.pnl or 0) > 0)
    losses = abs(sum(float(r.pnl or 0) for r in subset if float(r.pnl or 0) < 0))
    if losses > 0:
        ratio: Optional[float] = round(wins / losses, 4)
        ratio_display = ratio
    elif wins > 0:
        ratio = None
        ratio_display = None  # 前端显示 ∞
    else:
        ratio = None
        ratio_display = None
    return {
        "orders": len(subset),
        "pnl": round(sum(float(r.pnl or 0) for r in subset), 4),
        "opens": sum(1 for r in subset if (r.action or "") == "open"),
        "closes": sum(1 for r in subset if (r.action or "") == "close"),
        "pnl_ratio": ratio,
        "pnl_ratio_infinite": bool(wins > 0 and losses <= 0),
        "gross_profit": round(wins, 4),
        "gross_loss": round(losses, 4),
    }


def list_trades(
    user_id: int,
    *,
    platform: str = "",
    symbol: str = "",
    strategy: str = "",
    limit: int = 200,
) -> List[Dict[str, Any]]:
    session = _session()
    try:
        q = session.query(PortalTrade).filter(PortalTrade.user_id == int(user_id))
        q = _apply_trade_filters(q, platform=platform, symbol=symbol, strategy=strategy)
        rows = q.order_by(PortalTrade.id.desc()).limit(max(1, min(int(limit or 200), 500))).all()
        return [_trade_dict(r) for r in rows]
    finally:
        session.close()


def trade_stats(
    user_id: int,
    *,
    platform: str = "",
    symbol: str = "",
    strategy: str = "",
) -> Dict[str, Any]:
    """按筛选条件统计 7/30/180 天订单数、已实现盈亏与盈亏比。"""
    session = _session()
    try:
        q = session.query(PortalTrade).filter(PortalTrade.user_id == int(user_id))
        q = _apply_trade_filters(q, platform=platform, symbol=symbol, strategy=strategy)
        # 只统计真实成交（ok），dry-run 不计入收益
        q = q.filter(PortalTrade.status == "ok")
        rows = q.all()
    finally:
        session.close()

    now = datetime.now()
    windows = {"7d": 7, "30d": 30, "180d": 180}
    out: Dict[str, Any] = {}
    for key, days in windows.items():
        since = now - timedelta(days=days)
        subset = [r for r in rows if r.created_at and r.created_at >= since]
        out[key] = _window_stats(subset)
    total = _window_stats(rows)
    out["total_orders"] = total["orders"]
    out["total_pnl"] = total["pnl"]
    out["pnl_ratio"] = total["pnl_ratio"]
    out["pnl_ratio_infinite"] = total["pnl_ratio_infinite"]
    out["gross_profit"] = total["gross_profit"]
    out["gross_loss"] = total["gross_loss"]
    return out


def delete_exchange_binding(user_id: int, platform: str) -> bool:
    plat = (platform or "").strip().lower()
    if not plat:
        return False
    session = _session()
    try:
        row = session.query(PortalExchangeBinding).filter_by(user_id=user_id, platform=plat).first()
        if not row:
            return False
        session.delete(row)
        # 从观察配置的 exchange 多选中移除该平台
        configs = session.query(PortalWatchConfig).filter_by(user_id=user_id).all()
        for cfg in configs:
            plats = _normalize_exchanges(getattr(cfg, "exchange", None) or "")
            if plat not in plats:
                continue
            remain = [p for p in plats if p != plat]
            cfg.exchange = ",".join(remain)
            if not remain and (getattr(cfg, "status", None) or "").lower() == "connected":
                cfg.status = "living"
            cfg.updated_at = datetime.now()
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def list_connected_watch_configs(user_id: int) -> List[Dict[str, Any]]:
    session = _session()
    try:
        rows = (
            session.query(PortalWatchConfig)
            .filter(
                PortalWatchConfig.user_id == int(user_id),
                PortalWatchConfig.status == "connected",
            )
            .all()
        )
        return [_watch_config_dict(r) for r in rows]
    finally:
        session.close()


def match_strategy_for_position(
    configs: List[Dict[str, Any]],
    *,
    symbol: str,
    platform: str = "",
) -> str:
    """持仓币种 → 观察库 connected 配置的策略名（优先同交易所）。"""
    want = _symbol_bases(symbol)
    plat = (platform or "").strip().lower()
    hits = []
    for c in configs or []:
        if not (_symbol_bases(c.get("symbol") or "") & want):
            continue
        hits.append(c)
    if not hits:
        return ""
    if plat:
        same = [c for c in hits if (c.get("exchange") or "").strip().lower() == plat]
        if same:
            hits = same
    return (hits[0].get("strategy_name") or "").strip()


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
    ex_raw = getattr(r, "exchange", None) or ""
    exchanges = _normalize_exchanges(ex_raw)
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
        "leverage": int(getattr(r, "leverage", None) or 5),
        "take_profit": getattr(r, "take_profit", None) or "",
        "stop_loss": getattr(r, "stop_loss", None) or "",
        "status": getattr(r, "status", None) or "",
        "exchange": ",".join(exchanges) if exchanges else (ex_raw or ""),
        "exchanges": exchanges,
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


def _normalize_exchanges(raw) -> List[str]:
    if isinstance(raw, (list, tuple)):
        items = [str(x or "").strip().lower() for x in raw]
    else:
        items = [p.strip().lower() for p in str(raw or "").replace(";", ",").split(",")]
    out: List[str] = []
    for p in items:
        if p in ("hyperliquid", "okx", "binance") and p not in out:
            out.append(p)
    return out


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
    leverage: int = 5,
    exchanges: Optional[List[str]] = None,
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
        raise ValueError("请选择策略名称")
    value = str(size_value or "").strip()
    if not value:
        raise ValueError("请填写仓位大小")
    try:
        lev = int(leverage)
    except (TypeError, ValueError):
        lev = 5
    if lev < 1 or lev > 125:
        raise ValueError("杠杆需在 1～125 之间")
    tp = str(take_profit or "").strip()
    sl = str(stop_loss or "").strip()
    plats = _normalize_exchanges(exchanges)
    # 若指定了平台，校验用户已绑定；全部有效则直接 connected
    if plats:
        missing = []
        for p in plats:
            if not get_exchange_binding(user_id, p):
                missing.append(p)
        if missing:
            raise ValueError(f"尚未连接平台: {', '.join(missing)}，请先连接交易所")
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
            row.leverage = lev
            row.take_profit = tp
            row.stop_loss = sl
            if plats:
                row.exchange = ",".join(plats)
                row.status = "connected"
            else:
                # 未选平台：进入 living，等连接弹窗；已 connected 的保留平台但退回 living 提示重连
                cur = (getattr(row, "status", None) or "").strip().lower()
                if cur != "connected":
                    row.status = "living"
                elif not (getattr(row, "exchange", None) or "").strip():
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
    plats = _normalize_exchanges(exchange)
    if not plats:
        plat = (exchange or "").strip().lower()
        plats = [plat] if plat else []
    if not plats:
        return []
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
            # 新连接平台并入已有多选（去重）
            existing = _normalize_exchanges(getattr(row, "exchange", None) or "")
            merged = list(existing)
            for p in plats:
                if p not in merged:
                    merged.append(p)
            row.exchange = ",".join(merged)
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
