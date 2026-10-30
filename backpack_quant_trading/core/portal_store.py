"""普通用户产品站：自选、站内信、咨询、邮件口子。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import hashlib

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    and_,
    or_,
)
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
    require_2h = Column(Boolean, nullable=False, default=False)  # 2H 收盘站上日线 WMA15
    require_4h = Column(Boolean, nullable=False, default=False)  # 4H 收盘站上日线 WMA15
    # 条件全满足时，观察库「状态」列展示的标签：空头 | 反弹 | 趋势（兼容旧单配置）
    status_mode = Column(String(16), nullable=False, default="趋势")
    # 三套状态配置 JSON：{"趋势":{require_2h..},"反弹":{...},"空头":{...}}
    status_profiles = Column(Text, nullable=False, default="{}")
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

# 判定优先级顺序：趋势 → 反弹 → 空头（eval_tradable 按此顺序取首个满足）
WATCH_STATUS_MODES = ("趋势", "反弹", "空头")


def normalize_status_mode(raw: Any) -> str:
    s = str(raw or "").strip()
    if s in WATCH_STATUS_MODES:
        return s
    low = s.lower()
    if low in ("bear", "short", "空", "bearish"):
        return "空头"
    if low in ("rebound", "bounce", "反弹中"):
        return "反弹"
    if low in ("trend", "趋势中", "trending"):
        return "趋势"
    return "趋势"


def _empty_status_profile() -> Dict[str, bool]:
    return {
        "require_2h": False,
        "require_4h": False,
        "require_mid": False,
        "require_long": False,
        "require_short": False,
    }


def normalize_status_profiles(raw: Any) -> Dict[str, Dict[str, bool]]:
    """趋势/反弹/空头 各一套站上条件。"""
    data = raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw or "{}")
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}
    out: Dict[str, Dict[str, bool]] = {}
    for mode in WATCH_STATUS_MODES:
        src = data.get(mode) if isinstance(data.get(mode), dict) else {}
        out[mode] = {
            "require_2h": bool(src.get("require_2h")),
            "require_4h": bool(src.get("require_4h")),
            "require_mid": bool(src.get("require_mid")),
            "require_long": bool(src.get("require_long")),
            "require_short": False,
        }
    return out


def status_profiles_configured(profiles: Optional[Dict[str, Any]]) -> bool:
    for mode in WATCH_STATUS_MODES:
        g = (profiles or {}).get(mode) or {}
        if any(g.get(k) for k in ("require_2h", "require_4h", "require_mid", "require_long")):
            return True
    return False


def dump_status_profiles(profiles: Any) -> str:
    return json.dumps(normalize_status_profiles(profiles), ensure_ascii=False)


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


class PortalBookAccount(StoreBase):
    """管理员新增的账面账户卡（市场 + 本金）；可绑定普通用户 owner_user_id。"""

    __tablename__ = "portal_book_accounts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(16), nullable=False, default="crypto")  # crypto | us
    account_no = Column(String(64), nullable=False, default="")
    initial_capital = Column(Float, nullable=False, default=0.0)
    label = Column(String(64), nullable=False, default="")
    owner_user_id = Column(Integer, nullable=True, index=True)  # 绑定的普通用户
    created_at = Column(DateTime, nullable=False, default=datetime.now)


BOOK_USER_DEFAULT_PASSWORD = "123456"


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
        if "require_2h" not in existing:
            alters.append("ALTER TABLE portal_watch_configs ADD COLUMN require_2h TINYINT(1) NOT NULL DEFAULT 0")
        if "require_4h" not in existing:
            alters.append("ALTER TABLE portal_watch_configs ADD COLUMN require_4h TINYINT(1) NOT NULL DEFAULT 0")
        if "status_mode" not in existing:
            alters.append(
                "ALTER TABLE portal_watch_configs ADD COLUMN status_mode VARCHAR(16) NOT NULL DEFAULT '趋势'"
            )
        if "status_profiles" not in existing:
            alters.append(
                "ALTER TABLE portal_watch_configs ADD COLUMN status_profiles TEXT NULL"
            )
        for sql in alters:
            conn.execute(text(sql))


def _ensure_book_account_columns(engine) -> None:
    """已有 portal_book_accounts 时补 owner_user_id。"""
    from sqlalchemy import text

    with engine.begin() as conn:
        try:
            rows = conn.execute(text("SHOW COLUMNS FROM portal_book_accounts")).fetchall()
        except Exception:
            return
        existing = {str(r[0]) for r in rows}
        if "owner_user_id" not in existing:
            conn.execute(
                text(
                    "ALTER TABLE portal_book_accounts "
                    "ADD COLUMN owner_user_id INT NULL"
                )
            )


def _session():
    manager = DatabaseManager()
    StoreBase.metadata.create_all(manager.engine, checkfirst=True)
    try:
        _ensure_watch_config_columns(manager.engine)
    except Exception:
        pass
    try:
        _ensure_book_account_columns(manager.engine)
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


# 账面账户（非交易所连接）：全站共享，任意登录用户可见同一套数据
BOOK_PLATFORM_CRYPTO = "crypto_account"
BOOK_PLATFORM_US = "us_account"
BOOK_PLATFORMS = frozenset({BOOK_PLATFORM_CRYPTO, BOOK_PLATFORM_US})
BOOK_SHARED_USER_ID = 0  # 账面成交挂在此虚拟用户下
BOOK_PLATFORM_LABELS = {
    BOOK_PLATFORM_CRYPTO: "加密账户",
    BOOK_PLATFORM_US: "美股账户",
}
BOOK_MARKET_TITLES = {
    "crypto": "Binance Crypto",
    "us": "Binance 美股",
}
CRYPTO_ACCOUNT_INITIAL_USD = 5_000_000.0  # 加密账面默认本金 500 万
US_ACCOUNT_INITIAL_USD = 5_000_000.0  # 美股账面默认本金 500 万
CSV_IMPORT_DETAIL_PREFIX = "csv import"
US_CSV_IMPORT_DETAIL_PREFIX = "csv import soxl"
US_CSV_CUTOFF = datetime(2025, 5, 16)  # 仅导入 5.16 及之后
US_STRATEGY_NAME = "美股追踪策略"


def book_platform_key(account_id: int) -> str:
    return f"ba_{int(account_id)}"


def parse_book_account_id(platform: str) -> Optional[int]:
    p = (platform or "").strip().lower()
    if not p.startswith("ba_"):
        return None
    try:
        return int(p[3:])
    except ValueError:
        return None


def is_book_platform(platform: str) -> bool:
    p = (platform or "").strip().lower()
    if p in BOOK_PLATFORMS:
        return True
    return parse_book_account_id(p) is not None


def _book_platform_sql():
    """SQL：legacy crypto/us + 动态 ba_*。"""
    return or_(
        PortalTrade.platform.in_(tuple(BOOK_PLATFORMS)),
        PortalTrade.platform.like("ba_%"),
    )


def _not_book_platform_sql():
    return and_(
        ~PortalTrade.platform.in_(tuple(BOOK_PLATFORMS)),
        ~PortalTrade.platform.like("ba_%"),
    )


def _book_capital_path():
    from pathlib import Path

    return Path(__file__).resolve().parents[1] / "data" / "portal_book_capital.json"


def _load_book_capital_file() -> Dict[str, Any]:
    path = _book_capital_path()
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")) or {}
    except Exception:
        pass
    return {}


def _save_book_capital_file(data: Dict[str, Any]) -> None:
    path = _book_capital_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def normalize_book_market(market: str) -> str:
    """返回 crypto | us。"""
    plat = resolve_book_platform_from_market(market)
    return "crypto" if plat == BOOK_PLATFORM_CRYPTO else "us"


def get_book_initial_capital(platform: str) -> float:
    """账面账户初始本金：ba_* 读表；legacy 读覆盖文件或默认 500 万。"""
    plat = (platform or "").strip().lower()
    ba_id = parse_book_account_id(plat)
    if ba_id is not None:
        session = _session()
        try:
            row = session.query(PortalBookAccount).filter(PortalBookAccount.id == ba_id).first()
            return float(row.initial_capital) if row else 0.0
        finally:
            session.close()
    data = _load_book_capital_file()
    raw = data.get(plat)
    try:
        if raw is not None and float(raw) > 0:
            return float(raw)
    except (TypeError, ValueError):
        pass
    if plat == BOOK_PLATFORM_CRYPTO:
        return float(CRYPTO_ACCOUNT_INITIAL_USD)
    if plat == BOOK_PLATFORM_US:
        return float(US_ACCOUNT_INITIAL_USD)
    return 0.0


def parse_capital_amount(raw: Any) -> float:
    """解析本金：支持 200w / 200W / 200万 / 2000000。"""
    s = str(raw or "").strip().replace(",", "").replace(" ", "").lower()
    if not s:
        raise ValueError("本金不能为空")
    mult = 1.0
    if s.endswith("万"):
        mult = 10_000.0
        s = s[:-1]
    elif s.endswith("w"):
        mult = 10_000.0
        s = s[:-1]
    try:
        val = float(s) * mult
    except (TypeError, ValueError) as exc:
        raise ValueError("本金格式无效，例：200w 或 2000000") from exc
    if val <= 0:
        raise ValueError("本金须大于 0")
    return val


def resolve_book_platform_from_market(market: str) -> str:
    m = (market or "").strip().lower()
    if m in ("crypto", "加密", "crypto_account", "binance crypto", "加密账户"):
        return BOOK_PLATFORM_CRYPTO
    if m in ("us", "美股", "us_account", "binance 美股", "美股账户"):
        return BOOK_PLATFORM_US
    raise ValueError("市场仅支持：加密 / 美股")


def list_dynamic_book_platform_keys() -> List[str]:
    session = _session()
    try:
        ids = [int(r[0]) for r in session.query(PortalBookAccount.id).all()]
        return [book_platform_key(i) for i in ids]
    finally:
        session.close()


def list_portal_book_accounts(*, owner_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """动态账面账户列表（含权益）。owner_user_id 非空时只返回该用户绑定账户。"""
    session = _session()
    try:
        q = session.query(PortalBookAccount).order_by(PortalBookAccount.id.asc())
        if owner_user_id is not None:
            q = q.filter(PortalBookAccount.owner_user_id == int(owner_user_id))
        rows = q.all()
        out: List[Dict[str, Any]] = []
        for r in rows:
            plat = book_platform_key(r.id)
            pnl = 0.0
            trades = (
                session.query(PortalTrade)
                .filter(
                    PortalTrade.user_id == BOOK_SHARED_USER_ID,
                    PortalTrade.platform == plat,
                    PortalTrade.status == "ok",
                )
                .all()
            )
            for t in trades:
                pnl += float(t.pnl or 0)
            init_cap = float(r.initial_capital or 0)
            market = (r.market or "crypto").strip().lower()
            if market not in ("crypto", "us"):
                market = "crypto"
            out.append(
                {
                    "id": int(r.id),
                    "platform": plat,
                    "market": market,
                    "title": BOOK_MARKET_TITLES.get(market, "Binance Crypto"),
                    "platform_label": BOOK_MARKET_TITLES.get(market, market),
                    "account_no": r.account_no or "",
                    "initial_capital": init_cap,
                    "equity": round(init_cap + pnl, 4),
                    "label": r.label or "",
                    "owner_user_id": int(r.owner_user_id) if r.owner_user_id is not None else None,
                    "book": True,
                }
            )
        return out
    finally:
        session.close()


def list_owned_book_platform_keys(user_id: int) -> List[str]:
    return [a["platform"] for a in list_portal_book_accounts(owner_user_id=int(user_id))]


def user_owns_book_platform(user_id: int, platform: str) -> bool:
    plat = (platform or "").strip().lower()
    ba_id = parse_book_account_id(plat)
    if ba_id is None:
        return False
    session = _session()
    try:
        row = (
            session.query(PortalBookAccount)
            .filter(
                PortalBookAccount.id == ba_id,
                PortalBookAccount.owner_user_id == int(user_id),
            )
            .first()
        )
        return row is not None
    finally:
        session.close()


def normalize_phone_username(phone: Any) -> str:
    s = str(phone or "").strip().replace(" ", "").replace("-", "")
    if not s:
        raise ValueError("手机号不能为空")
    if not s.isdigit() or len(s) < 6 or len(s) > 20:
        raise ValueError("手机号格式无效")
    return s


def ensure_portal_user_by_phone(phone: Any) -> Dict[str, Any]:
    """按手机号确保普通用户存在；新建时密码为 123456。"""
    from backpack_quant_trading.api.deps import get_password_hash

    username = normalize_phone_username(phone)
    db = DatabaseManager()
    existing = db.get_user_by_username(username)
    if existing:
        return {
            "ok": True,
            "created": False,
            "user_id": int(existing.id),
            "username": existing.username,
            "role": existing.role or "user",
        }
    user = db.create_user(
        username,
        get_password_hash(BOOK_USER_DEFAULT_PASSWORD),
        role="user",
    )
    return {
        "ok": True,
        "created": True,
        "user_id": int(user.id),
        "username": user.username,
        "role": "user",
        "default_password": BOOK_USER_DEFAULT_PASSWORD,
    }


def legacy_platform_for_market(market: str) -> str:
    mkt = normalize_book_market(market) if market not in ("crypto", "us") else market
    return BOOK_PLATFORM_CRYPTO if mkt == "crypto" else BOOK_PLATFORM_US


def clone_legacy_trades_into_book_account(
    account_id: int,
    *,
    replace: bool = False,
) -> Dict[str, Any]:
    """把对应市场 legacy 成交按本金比例复制到 ba_*（不改源账户）。"""
    session = _session()
    try:
        acc = (
            session.query(PortalBookAccount)
            .filter(PortalBookAccount.id == int(account_id))
            .first()
        )
        if not acc:
            raise ValueError(f"账面账户不存在: {account_id}")
        mkt = (acc.market or "crypto").strip().lower()
        if mkt not in ("crypto", "us"):
            mkt = "crypto"
        src_plat = legacy_platform_for_market(mkt)
        dest_plat = book_platform_key(acc.id)
        existing_n = (
            session.query(PortalTrade)
            .filter(
                PortalTrade.user_id == BOOK_SHARED_USER_ID,
                PortalTrade.platform == dest_plat,
            )
            .count()
        )
        if existing_n and not replace:
            return {
                "ok": True,
                "skipped": True,
                "copied": 0,
                "platform": dest_plat,
                "source": src_plat,
            }
        if replace and existing_n:
            session.query(PortalTrade).filter(
                PortalTrade.user_id == BOOK_SHARED_USER_ID,
                PortalTrade.platform == dest_plat,
            ).delete(synchronize_session=False)

        src_cap = get_book_initial_capital(src_plat)
        dest_cap = float(acc.initial_capital or 0)
        if src_cap <= 0 or dest_cap <= 0:
            raise ValueError("本金无效，无法复制成交")
        factor = dest_cap / src_cap

        src_rows = (
            session.query(PortalTrade)
            .filter(
                PortalTrade.user_id == BOOK_SHARED_USER_ID,
                PortalTrade.platform == src_plat,
            )
            .order_by(PortalTrade.created_at.asc(), PortalTrade.id.asc())
            .all()
        )
        copied = 0
        for r in src_rows:
            margin = None
            if r.margin is not None:
                margin = round(float(r.margin) * factor, 4)
            session.add(
                PortalTrade(
                    user_id=BOOK_SHARED_USER_ID,
                    platform=dest_plat,
                    symbol=r.symbol or "",
                    side=r.side or "",
                    action=r.action or "",
                    strategy_name=r.strategy_name or "",
                    timeframe=r.timeframe or "",
                    price=r.price,
                    quantity=r.quantity,
                    margin=margin,
                    leverage=int(r.leverage or 5),
                    pnl=round(float(r.pnl or 0) * factor, 4),
                    status=r.status or "ok",
                    detail=((r.detail or "") + " | clone→" + dest_plat)[:255],
                    order_id=r.order_id or "",
                    created_at=r.created_at or datetime.now(),
                )
            )
            copied += 1
        session.commit()
        equity = round(dest_cap + sum_trade_pnl(BOOK_SHARED_USER_ID, platform=dest_plat), 4)
        return {
            "ok": True,
            "skipped": False,
            "copied": copied,
            "factor": round(factor, 8),
            "platform": dest_plat,
            "source": src_plat,
            "initial_capital": dest_cap,
            "equity": equity,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_empty_dynamic_book_trades_cloned() -> Dict[str, Any]:
    """已有 ba_* 若尚无成交，则从对应 legacy 复制一份（幂等）。"""
    session = _session()
    try:
        ids = [int(r[0]) for r in session.query(PortalBookAccount.id).all()]
    finally:
        session.close()
    results = []
    for aid in ids:
        try:
            results.append(clone_legacy_trades_into_book_account(aid, replace=False))
        except Exception as exc:
            results.append({"ok": False, "id": aid, "error": str(exc)[:160]})
    return {"ok": True, "items": results}


def delete_book_account(account_ref: Any) -> Dict[str, Any]:
    """删除动态账面账户 ba_* 及其成交；不可删 legacy crypto_account / us_account。"""
    ba_id = parse_book_account_id(str(account_ref or ""))
    if ba_id is None:
        try:
            ba_id = int(str(account_ref).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError("账户 id 无效") from exc
    plat = book_platform_key(ba_id)
    session = _session()
    try:
        row = session.query(PortalBookAccount).filter(PortalBookAccount.id == ba_id).first()
        if not row:
            raise ValueError(f"账面账户不存在: {plat}")
        deleted_trades = (
            session.query(PortalTrade)
            .filter(
                PortalTrade.user_id == BOOK_SHARED_USER_ID,
                PortalTrade.platform == plat,
            )
            .delete(synchronize_session=False)
        )
        session.delete(row)
        session.commit()
        return {
            "ok": True,
            "deleted": True,
            "id": ba_id,
            "platform": plat,
            "deleted_trades": int(deleted_trades or 0),
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_book_account(
    market: str,
    capital_raw: Any,
    *,
    phone: Any = "",
    label: str = "",
) -> Dict[str, Any]:
    """新增账面账户，并按手机号创建/绑定普通用户（默认密码 123456）；复制 legacy 成交。"""
    mkt = normalize_book_market(market)
    capital = parse_capital_amount(capital_raw)
    user_info = ensure_portal_user_by_phone(phone)
    owner_id = int(user_info["user_id"])
    session = _session()
    try:
        row = PortalBookAccount(
            market=mkt,
            account_no="",
            initial_capital=float(capital),
            label=(label or "").strip()[:64],
            owner_user_id=owner_id,
        )
        session.add(row)
        session.flush()
        dig = hashlib.sha256(
            f"portal-book-ba:{row.id}:{mkt}:{capital}:{owner_id}".encode("utf-8")
        ).hexdigest()
        row.account_no = f"0x{dig[:4]}…{dig[-4:]}"
        session.commit()
        ba_id = int(row.id)
        account_no = row.account_no
        init_cap = float(row.initial_capital)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    plat = book_platform_key(ba_id)
    clone_info: Dict[str, Any] = {}
    try:
        clone_info = clone_legacy_trades_into_book_account(ba_id, replace=True)
    except Exception as exc:
        clone_info = {"ok": False, "error": str(exc)[:200]}
    equity = float(clone_info.get("equity") or init_cap)
    return {
        "ok": True,
        "created": True,
        "id": ba_id,
        "platform": plat,
        "market": mkt,
        "title": BOOK_MARKET_TITLES.get(mkt, "Binance Crypto"),
        "account_no": account_no,
        "initial_capital": init_cap,
        "equity": equity,
        "label": label or "",
        "clone": clone_info,
        "owner_user_id": owner_id,
        "login_username": user_info.get("username"),
        "user_created": bool(user_info.get("created")),
        "default_password": BOOK_USER_DEFAULT_PASSWORD if user_info.get("created") else None,
    }


def restore_legacy_book_accounts_from_csv() -> Dict[str, Any]:
    """清除本金覆盖并以 CSV 重导恢复原始 crypto/us（不碰 ba_*）。"""
    data = _load_book_capital_file()
    changed = False
    for k in (BOOK_PLATFORM_CRYPTO, BOOK_PLATFORM_US):
        if k in data:
            data.pop(k, None)
            changed = True
    if changed or data:
        # 写回剩余键；若只剩空对象也落盘
        _save_book_capital_file(data)
    crypto = import_crypto_account_csv_trades(BOOK_SHARED_USER_ID, force=True)
    us = import_us_account_csv_trades(force=True)
    return {"ok": True, "crypto": crypto, "us": us}


_LEGACY_BOOK_RESTORE_DONE = False


def maybe_restore_scaled_legacy_books() -> Optional[Dict[str, Any]]:
    """若此前误用 scale 把 legacy 缩得很小，则一次性 CSV 恢复。"""
    global _LEGACY_BOOK_RESTORE_DONE
    if _LEGACY_BOOK_RESTORE_DONE:
        return None
    _LEGACY_BOOK_RESTORE_DONE = True
    data = _load_book_capital_file()
    need = bool(data.get(BOOK_PLATFORM_CRYPTO) or data.get(BOOK_PLATFORM_US))
    if not need:
        try:
            # 无覆盖文件时仍可能已缩放成交：权益远低于默认本金则恢复
            eq = book_account_equity(BOOK_SHARED_USER_ID, BOOK_PLATFORM_CRYPTO)
            if eq < CRYPTO_ACCOUNT_INITIAL_USD * 0.02:
                need = True
        except Exception:
            pass
    if not need:
        return None
    try:
        return restore_legacy_book_accounts_from_csv()
    except Exception:
        return None


def scale_book_account_capital(market: str, new_capital_raw: Any) -> Dict[str, Any]:
    """【已弃用】按比例缩放会改坏已有账户。请改用 create_book_account。"""
    raise ValueError(
        "已不再支持缩放已有账面本金；请用「连接」新增账户（create_book_account）"
    )


# 观察库：按市场（加密/美股）保存的默认状态配置，新加标的自动继承
_MARKET_DEFAULTS_PATH = None


def _market_defaults_path():
    global _MARKET_DEFAULTS_PATH
    if _MARKET_DEFAULTS_PATH is None:
        from pathlib import Path

        _MARKET_DEFAULTS_PATH = (
            Path(__file__).resolve().parents[1] / "data" / "portal_watch_market_defaults.json"
        )
    return _MARKET_DEFAULTS_PATH


def _norm_watch_market(market: str) -> str:
    return "us" if (market or "").strip().lower() in ("us", "美股") else "crypto"


def _load_market_defaults() -> Dict[str, Any]:
    path = _market_defaults_path()
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")) or {}
    except Exception:
        pass
    return {}


def _save_market_defaults(data: Dict[str, Any]) -> None:
    path = _market_defaults_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def get_watch_market_default(user_id: int, market: str) -> Optional[Dict[str, Any]]:
    key = f"{int(user_id)}:{_norm_watch_market(market)}"
    row = _load_market_defaults().get(key)
    return dict(row) if isinstance(row, dict) else None


def save_watch_market_default(
    user_id: int,
    market: str,
    *,
    gates: Optional[Dict[str, Any]] = None,
    trade: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """保存某用户某市场的默认配置（状态 / 交易可分别更新）。"""
    mkt = _norm_watch_market(market)
    key = f"{int(user_id)}:{mkt}"
    data = _load_market_defaults()
    cur = dict(data.get(key) or {})
    cur["market"] = mkt
    if gates:
        cur["require_short"] = False
        if gates.get("status_profiles") is not None:
            profiles = normalize_status_profiles(gates.get("status_profiles"))
            cur["status_profiles"] = profiles
            # 兼容旧字段：取优先级最高且已配置的一套写入 require_*
            for mode in WATCH_STATUS_MODES:
                g = profiles.get(mode) or {}
                if any(g.get(k) for k in ("require_2h", "require_4h", "require_mid", "require_long")):
                    cur["require_mid"] = bool(g.get("require_mid"))
                    cur["require_long"] = bool(g.get("require_long"))
                    cur["require_2h"] = bool(g.get("require_2h"))
                    cur["require_4h"] = bool(g.get("require_4h"))
                    cur["status_mode"] = mode
                    break
        else:
            cur["require_mid"] = bool(gates.get("require_mid"))
            cur["require_long"] = bool(gates.get("require_long"))
            cur["require_2h"] = bool(gates.get("require_2h"))
            cur["require_4h"] = bool(gates.get("require_4h"))
            cur["status_mode"] = normalize_status_mode(gates.get("status_mode"))
            cur["status_profiles"] = normalize_status_profiles({
                normalize_status_mode(gates.get("status_mode")): {
                    "require_mid": cur["require_mid"],
                    "require_long": cur["require_long"],
                    "require_2h": cur["require_2h"],
                    "require_4h": cur["require_4h"],
                }
            })
    if trade:
        if trade.get("strategy_name") is not None:
            cur["strategy_name"] = str(trade.get("strategy_name") or "").strip()
        if trade.get("timeframe") is not None:
            cur["timeframe"] = str(trade.get("timeframe") or "2h").strip() or "2h"
        if trade.get("size_mode") is not None:
            cur["size_mode"] = str(trade.get("size_mode") or "percent")
        if trade.get("size_value") is not None:
            cur["size_value"] = str(trade.get("size_value") or "10")
        if trade.get("leverage") is not None:
            try:
                cur["leverage"] = int(trade.get("leverage") or 5)
            except (TypeError, ValueError):
                cur["leverage"] = 5
        if trade.get("take_profit") is not None:
            cur["take_profit"] = str(trade.get("take_profit") or "")
        if trade.get("stop_loss") is not None:
            cur["stop_loss"] = str(trade.get("stop_loss") or "")
        if trade.get("exchanges") is not None:
            cur["exchanges"] = _normalize_exchanges(trade.get("exchanges"))
            cur["exchange"] = ",".join(cur["exchanges"])
    cur["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data[key] = cur
    _save_market_defaults(data)
    return cur


def list_favorite_symbols_by_market(user_id: int, market: str) -> List[str]:
    mkt = _norm_watch_market(market)
    return [
        f["symbol"]
        for f in list_favorites(user_id)
        if _norm_watch_market(f.get("market") or "crypto") == mkt
    ]


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
    created_at: Optional[datetime] = None,
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
            created_at=created_at or datetime.now(),
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


def _parse_optional_float(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(str(raw).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def _norm_book_trade_action(payload: Dict[str, Any]) -> str:
    """open | close"""
    raw = str(
        payload.get("动作")
        or payload.get("action")
        or payload.get("trade_action")
        or payload.get("order_action")
        or ""
    ).strip().lower()
    if raw in ("open", "开仓", "entry", "enter"):
        return "open"
    if raw in ("close", "平仓", "exit", "flat"):
        return "close"
    # TradingView strategy.order.action: buy/sell 需结合仓位变化推断；默认开仓
    sig = str(
        payload.get("方向")
        or payload.get("操作")
        or payload.get("signal")
        or payload.get("side")
        or ""
    ).strip().lower()
    if sig in ("close", "平仓", "flat"):
        return "close"
    pos = str(payload.get("position") or payload.get("仓位状态") or "").strip().lower()
    if pos in ("flat", "0", "平", "平仓"):
        return "close"
    # 先前仓位>0 且操作为反向 → 常见平仓写法
    try:
        prev = float(payload.get("先前仓位大小") or payload.get("prev_position") or 0)
        if prev != 0 and sig in ("buy", "sell", "long", "short", "多", "空"):
            # TV 常在平仓时仍发 buy/sell；若显式带 pnl 则当平仓
            if payload.get("pnl") is not None or payload.get("盈亏") is not None:
                return "close"
    except (TypeError, ValueError):
        pass
    return "open"


def _norm_book_trade_side(payload: Dict[str, Any], *, action: str) -> str:
    raw = str(
        payload.get("方向")
        or payload.get("操作")
        or payload.get("signal")
        or payload.get("side")
        or payload.get("action")
        or ""
    ).strip().lower()
    if raw in ("buy", "long", "开多", "做多", "多"):
        return "BUY"
    if raw in ("sell", "short", "开空", "做空", "空"):
        return "SELL"
    # 平仓时可从持仓方向推断
    pos_side = str(payload.get("position_side") or payload.get("持仓方向") or "").lower()
    if pos_side in ("long", "多"):
        return "BUY" if action == "open" else "SELL"
    if pos_side in ("short", "空"):
        return "SELL" if action == "open" else "BUY"
    return "BUY"


def record_book_trade_from_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """TradingView → 只记账面交易清单（不下真实交易所单）。

    默写 legacy crypto_account / us_account；可传 book_id / platform=ba_N 写入指定账户。
    """
    if not isinstance(payload, dict):
        raise ValueError("请求体须为 JSON 对象")

    platform = ""
    raw_plat = str(
        payload.get("platform") or payload.get("book_platform") or ""
    ).strip().lower()
    if is_book_platform(raw_plat):
        platform = raw_plat
    else:
        ba_raw = (
            payload.get("book_id")
            or payload.get("book_account_id")
            or payload.get("account_id")
        )
        if ba_raw is not None and str(ba_raw).strip():
            s = str(ba_raw).strip().lower()
            if s.startswith("ba_"):
                s = s[3:]
            try:
                ba_id = int(s)
            except ValueError as exc:
                raise ValueError("book_id 无效") from exc
            platform = book_platform_key(ba_id)
            if get_book_initial_capital(platform) <= 0:
                raise ValueError(f"账面账户不存在: {platform}")

    if not platform:
        market_raw = str(
            payload.get("market")
            or payload.get("市场")
            or payload.get("account")
            or payload.get("平台")
            or "加密"
        )
        try:
            platform = resolve_book_platform_from_market(market_raw)
        except ValueError:
            # 无明确市场时：美股代码无 USDT 后缀倾向 us
            sym0 = str(payload.get("交易品种") or payload.get("symbol") or "").upper()
            platform = (
                BOOK_PLATFORM_US
                if sym0 and not sym0.endswith("USDT") and "/" not in sym0 and len(sym0) <= 6
                else BOOK_PLATFORM_CRYPTO
            )

    symbol = str(
        payload.get("交易品种") or payload.get("symbol") or payload.get("ticker") or payload.get("coin") or ""
    ).strip().upper()
    if not symbol:
        raise ValueError("缺少 symbol / 交易品种")

    book_market = "crypto"
    if platform == BOOK_PLATFORM_US:
        book_market = "us"
    elif platform == BOOK_PLATFORM_CRYPTO:
        book_market = "crypto"
    else:
        ba_id = parse_book_account_id(platform)
        if ba_id is not None:
            session = _session()
            try:
                brow = (
                    session.query(PortalBookAccount)
                    .filter(PortalBookAccount.id == ba_id)
                    .first()
                )
                if brow and (brow.market or "").strip().lower() == "us":
                    book_market = "us"
            finally:
                session.close()

    if book_market == "crypto" and not symbol.endswith("USDT") and symbol.isalpha():
        symbol = f"{symbol}USDT"

    action = _norm_book_trade_action(payload)
    side = _norm_book_trade_side(payload, action=action)
    strategy_name = str(
        payload.get("策略名称")
        or payload.get("strategy_name")
        or payload.get("strategy")
        or ("美股追踪策略" if book_market == "us" else "加密追踪策略")
    ).strip()
    timeframe = str(
        payload.get("周期") or payload.get("timeframe") or payload.get("interval") or ""
    ).strip()
    price = _parse_optional_float(
        payload.get("价格") or payload.get("price") or payload.get("close") or payload.get("open_price")
    )
    margin = _parse_optional_float(
        payload.get("仓位")
        or payload.get("margin")
        or payload.get("size_value")
        or payload.get("大小（价值）")
        or payload.get("value")
    )
    quantity = _parse_optional_float(
        payload.get("数量") or payload.get("quantity") or payload.get("qty") or payload.get("contracts")
    )
    pnl = _parse_optional_float(payload.get("盈亏") or payload.get("pnl") or payload.get("profit"))
    if action == "open":
        pnl = 0.0
    elif pnl is None:
        pnl = 0.0

    # 仓位缺省：按当前本金一半（与历史半仓习惯接近）
    if margin is None or margin <= 0:
        init_cap = get_book_initial_capital(platform)
        margin = round(init_cap * 0.4, 4) if init_cap > 0 else None

    row = record_trade(
        BOOK_SHARED_USER_ID,
        platform=platform,
        symbol=symbol,
        side=side,
        action=action,
        strategy_name=strategy_name,
        timeframe=timeframe,
        price=price,
        quantity=quantity,
        margin=margin,
        leverage=int(_parse_optional_float(payload.get("leverage") or payload.get("杠杆")) or 5),
        pnl=float(pnl or 0),
        status="ok",
        detail="tv book webhook",
        order_id=str(payload.get("order_id") or payload.get("id") or "")[:80],
    )
    return {
        "ok": True,
        "recorded": True,
        "platform": platform,
        "action": action,
        "trade": row,
        "open_positions": list_book_open_positions(platform),
    }


def list_book_open_positions(platform: str = "") -> List[Dict[str, Any]]:
    """由账面成交配对还原未平仓：开仓未匹配平仓 → 当前持仓。"""
    if is_book_platform(platform):
        plats = [platform.strip().lower()]
    else:
        plats = [BOOK_PLATFORM_CRYPTO, BOOK_PLATFORM_US] + list_dynamic_book_platform_keys()
        if not plats:
            return []
    session = _session()
    try:
        rows = (
            session.query(PortalTrade)
            .filter(
                PortalTrade.user_id == BOOK_SHARED_USER_ID,
                PortalTrade.platform.in_(tuple(plats)),
                PortalTrade.status == "ok",
            )
            .order_by(PortalTrade.created_at.asc(), PortalTrade.id.asc())
            .all()
        )
    finally:
        session.close()

    # key: (platform, symbol, position_side Long/Short)
    stacks: Dict[tuple, List[Any]] = {}
    for r in rows:
        plat = (r.platform or "").lower()
        sym = (r.symbol or "").upper()
        side_u = (r.side or "").upper()
        act = (r.action or "").lower()
        # 开仓 BUY=Long，开仓 SELL=Short；平仓时 BUY 常平空、SELL 常平多（与列表方向展示对齐）
        if act == "open":
            pos_side = "Long" if side_u == "BUY" else "Short"
            key = (plat, sym, pos_side)
            stacks.setdefault(key, []).append(r)
        elif act == "close":
            # 平多多用 SELL，平空多用 BUY；若只有一侧，也尝试同 symbol 任意方向栈
            prefer = "Long" if side_u == "SELL" else "Short"
            key = (plat, sym, prefer)
            if stacks.get(key):
                stacks[key].pop(0)
            else:
                alt = "Short" if prefer == "Long" else "Long"
                alt_key = (plat, sym, alt)
                if stacks.get(alt_key):
                    stacks[alt_key].pop(0)

    out: List[Dict[str, Any]] = []
    for (plat, sym, pos_side), opens in stacks.items():
        for r in opens:
            out.append(
                {
                    "platform": plat,
                    "symbol": sym,
                    "side": pos_side,
                    "action": "open",
                    "entry_price": r.price,
                    "margin": r.margin,
                    "quantity": r.quantity,
                    "pnl": 0.0,
                    "pnl_pct": None,
                    "strategy_name": r.strategy_name or "",
                    "book": True,
                    "opened_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
                }
            )
    return out


def _trade_rows_for_view(
    session,
    user_id: int,
    *,
    platform: str = "",
    symbol: str = "",
    strategy: str = "",
    status_ok_only: bool = False,
):
    """个人交易所成交 + 全站共享账面成交。

    platform=connected / self → 仅自己连接的交易所成交（不含账面账户）
    """
    plat = (platform or "").strip().lower()
    uid = int(user_id)

    def _finish(q, *, plat_override: Optional[str] = None):
        q = _apply_trade_filters(
            q, platform=plat_override if plat_override is not None else platform,
            symbol=symbol, strategy=strategy,
        )
        if status_ok_only:
            q = q.filter(PortalTrade.status == "ok")
        return q

    if is_book_platform(plat):
        q = session.query(PortalTrade).filter(PortalTrade.user_id == BOOK_SHARED_USER_ID)
        return _finish(q).all()

    # 自己连接的账户：仅本人交易所成交
    if plat in ("connected", "self", "exchange", "自己连接", "自己连接的账户"):
        q = session.query(PortalTrade).filter(
            PortalTrade.user_id == uid,
            _not_book_platform_sql(),
        )
        return _finish(q, plat_override="").all()

    if plat and plat not in ("all", "全部"):
        q = session.query(PortalTrade).filter(PortalTrade.user_id == uid)
        return _finish(q).all()

    # 全部：本人非账面 + 共享账面
    q_user = session.query(PortalTrade).filter(
        PortalTrade.user_id == uid,
        _not_book_platform_sql(),
    )
    q_user = _apply_trade_filters(q_user, platform="", symbol=symbol, strategy=strategy)
    if status_ok_only:
        q_user = q_user.filter(PortalTrade.status == "ok")
    q_book = session.query(PortalTrade).filter(
        PortalTrade.user_id == BOOK_SHARED_USER_ID,
        _book_platform_sql(),
    )
    q_book = _apply_trade_filters(q_book, platform="", symbol=symbol, strategy=strategy)
    if status_ok_only:
        q_book = q_book.filter(PortalTrade.status == "ok")
    return list(q_user.all()) + list(q_book.all())


def sum_trade_pnl(user_id: int, *, platform: str = "") -> float:
    """已实现盈亏合计（status=ok）；账面平台读共享数据。"""
    session = _session()
    try:
        rows = _trade_rows_for_view(
            session, user_id, platform=platform, status_ok_only=True
        )
        total = sum(float(r.pnl or 0) for r in rows)
        return round(total, 4)
    finally:
        session.close()


def book_account_equity(user_id: int, platform: str) -> float:
    """账面账户权益 = 初始本金 + 共享已实现盈亏（与登录用户无关）。"""
    plat = (platform or "").strip().lower()
    # user_id 保留入参以兼容调用方，实际始终读共享库
    _ = user_id
    if is_book_platform(plat):
        return round(
            get_book_initial_capital(plat)
            + sum_trade_pnl(BOOK_SHARED_USER_ID, platform=plat),
            4,
        )
    return 0.0


def _project_root():
    from pathlib import Path

    return Path(__file__).resolve().parents[2]


def _parse_csv_float(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "").replace("%", "")
    if not s or s in ("—", "-", "nan", "NaN"):
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _parse_csv_trade_type(type_raw: str) -> Optional[Dict[str, str]]:
    t = (type_raw or "").strip()
    mapping = {
        "多头进场": {"side": "BUY", "action": "open"},
        "多头出场": {"side": "SELL", "action": "close"},
        "空头进场": {"side": "SELL", "action": "open"},
        "空头出场": {"side": "BUY", "action": "close"},
        "多头入场": {"side": "BUY", "action": "open"},
        "多头平仓": {"side": "SELL", "action": "close"},
        "空头入场": {"side": "SELL", "action": "open"},
        "空头平仓": {"side": "BUY", "action": "close"},
    }
    return mapping.get(t)


def _crypto_csv_candidates():
    """按优先级解析 ETH/HYPE CSV 路径（包内 data → 仓库根 → 环境变量）。"""
    import os
    from pathlib import Path

    root = _project_root()
    pkg_data = Path(__file__).resolve().parents[1] / "data"
    specs = [
        (
            "ETHUSDT",
            2_000_000.0,
            [
                os.environ.get("CRYPTO_CSV_ETH") or "",
                str(pkg_data / "eth_200w.csv"),
                str(root / "eth 200万.csv"),
                str(root / "eth_200w.csv"),
            ],
        ),
        (
            "HYPEUSDT",
            1_000_000.0,
            [
                os.environ.get("CRYPTO_CSV_HYPE") or "",
                str(pkg_data / "hype_100w.csv"),
                str(root / "hype 100万.csv"),
                str(root / "hype_100w.csv"),
            ],
        ),
    ]
    out = []
    for symbol, capital, paths in specs:
        chosen = None
        for raw in paths:
            if not raw:
                continue
            p = Path(raw)
            if p.is_file():
                chosen = p
                break
        if chosen is not None:
            out.append((symbol, capital, chosen))
    return out


def _iter_crypto_csv_rows():
    """读取 ETH/HYPE TradingView 导出 CSV，产出统一字段字典。"""
    import csv

    for symbol, capital, path in _crypto_csv_candidates():
        with path.open(encoding="utf-8-sig", newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                yield symbol, capital, row


def purge_per_user_book_trades() -> int:
    """清理历史「按用户复制」的账面成交，只保留共享 user_id=0。"""
    session = _session()
    try:
        n = (
            session.query(PortalTrade)
            .filter(
                PortalTrade.platform.in_(tuple(BOOK_PLATFORMS)),
                PortalTrade.user_id != BOOK_SHARED_USER_ID,
            )
            .delete(synchronize_session=False)
        )
        session.commit()
        return int(n or 0)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def import_crypto_account_csv_trades(user_id: int = BOOK_SHARED_USER_ID, *, force: bool = False) -> Dict[str, Any]:
    """将 eth/hype CSV 导入为全站共享 crypto_account（默认 user_id=0）。

    - 出场行写入净损益，进场行 pnl=0（避免双边双计）
    - detail 前缀 csv import，便于幂等清理
    """
    uid = BOOK_SHARED_USER_ID  # 忽略入参，强制写入共享账户
    _ = user_id
    session = _session()
    try:
        # 顺带清掉旧的按用户副本，避免「全部」视图双计
        session.query(PortalTrade).filter(
            PortalTrade.platform.in_(tuple(BOOK_PLATFORMS)),
            PortalTrade.user_id != BOOK_SHARED_USER_ID,
        ).delete(synchronize_session=False)

        existing_q = session.query(PortalTrade).filter(
            PortalTrade.user_id == uid,
            PortalTrade.platform == BOOK_PLATFORM_CRYPTO,
            PortalTrade.detail.like(f"{CSV_IMPORT_DETAIL_PREFIX}%"),
        )
        existing_n = existing_q.count()
        if existing_n and not force:
            session.commit()
            return {
                "ok": True,
                "skipped": True,
                "existing": existing_n,
                "imported": 0,
                "shared_user_id": uid,
            }
        if existing_n and force:
            existing_q.delete(synchronize_session=False)

        csv_files = _crypto_csv_candidates()
        if not csv_files:
            session.commit()
            return {
                "ok": False,
                "skipped": False,
                "imported": 0,
                "error": (
                    "未找到 eth/hype CSV（镜像可能被 .dockerignore 的 *.csv 排除）。"
                    "请将 eth_200w.csv / hype_100w.csv 放到 "
                    "backpack_quant_trading/data/ 后重试"
                ),
                "shared_user_id": uid,
            }

        imported = 0
        skipped = 0
        for symbol, capital, row in _iter_crypto_csv_rows():
            meta = _parse_csv_trade_type(str(row.get("类型") or ""))
            if not meta:
                skipped += 1
                continue
            dt_raw = str(row.get("日期和时间") or "").strip()
            try:
                created = datetime.strptime(dt_raw, "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    created = datetime.strptime(dt_raw, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    skipped += 1
                    continue
            trade_no = str(row.get("交易编号") or "").strip() or "0"
            action = meta["action"]
            # 仅出场计入净损益
            pnl = _parse_csv_float(row.get("净损益 USDT")) or 0.0
            if action == "open":
                pnl = 0.0
            price = _parse_csv_float(row.get("价格 USDT"))
            qty = _parse_csv_float(row.get("大小（数量）"))
            margin = _parse_csv_float(row.get("大小（价值）"))
            signal = str(row.get("信号") or "").strip()
            order_id = f"csv-{symbol}-{trade_no}-{action}"[:80]
            detail = f"{CSV_IMPORT_DETAIL_PREFIX} {symbol} capital={int(capital)} {signal}"[:255]
            session.add(
                PortalTrade(
                    user_id=uid,
                    platform=BOOK_PLATFORM_CRYPTO,
                    symbol=symbol,
                    side=meta["side"],
                    action=action,
                    strategy_name="加密追踪策略",
                    timeframe="",
                    price=price,
                    quantity=qty,
                    margin=margin,
                    leverage=1,
                    pnl=float(pnl),
                    status="ok",
                    detail=detail,
                    order_id=order_id,
                    created_at=created,
                )
            )
            imported += 1
        session.commit()
        return {
            "ok": True,
            "skipped": False,
            "imported": imported,
            "parse_skipped": skipped,
            "platform": BOOK_PLATFORM_CRYPTO,
            "initial_capital": CRYPTO_ACCOUNT_INITIAL_USD,
            "shared_user_id": uid,
            "csv_files": [str(p) for _, _, p in csv_files],
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_crypto_account_csv_trades(user_id: int = BOOK_SHARED_USER_ID) -> Dict[str, Any]:
    """确保全站共享加密账户 CSV 已导入（与当前登录用户无关）。"""
    try:
        _ = user_id
        return import_crypto_account_csv_trades(BOOK_SHARED_USER_ID, force=False)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _soxl_csv_candidates():
    import os
    from pathlib import Path

    root = _project_root()
    pkg_data = Path(__file__).resolve().parents[1] / "data"
    paths = [
        os.environ.get("US_CSV_SOXL") or "",
        str(pkg_data / "soxl_us.csv"),
        str(root / "soxl_us.csv"),
    ]
    # 仓库根目录模糊匹配 soxl*.csv
    try:
        for p in sorted(root.glob("soxl*.csv")):
            paths.append(str(p))
    except Exception:
        pass
    for raw in paths:
        if not raw:
            continue
        p = Path(raw)
        if p.is_file():
            return p
    return None


def import_us_account_csv_trades(*, force: bool = False) -> Dict[str, Any]:
    """导入 SOXL CSV → 全站共享美股账户（5.16 之后；单笔半仓以 CSV 价值为准）。"""
    import csv

    uid = BOOK_SHARED_USER_ID
    path = _soxl_csv_candidates()
    session = _session()
    try:
        existing_q = session.query(PortalTrade).filter(
            PortalTrade.user_id == uid,
            PortalTrade.platform == BOOK_PLATFORM_US,
            PortalTrade.detail.like(f"{US_CSV_IMPORT_DETAIL_PREFIX}%"),
        )
        existing_n = existing_q.count()
        if existing_n and not force:
            return {
                "ok": True,
                "skipped": True,
                "existing": existing_n,
                "imported": 0,
                "shared_user_id": uid,
            }
        if not path:
            return {
                "ok": False,
                "imported": 0,
                "error": "未找到 soxl CSV（请放到 backpack_quant_trading/data/soxl_us.csv）",
            }
        if existing_n and force:
            existing_q.delete(synchronize_session=False)

        imported = 0
        skipped = 0
        with path.open(encoding="utf-8-sig", newline="") as fp:
            for row in csv.DictReader(fp):
                meta = _parse_csv_trade_type(str(row.get("类型") or ""))
                if not meta:
                    skipped += 1
                    continue
                dt_raw = str(row.get("日期和时间") or "").strip()
                try:
                    created = datetime.strptime(dt_raw, "%Y-%m-%d %H:%M")
                except ValueError:
                    try:
                        created = datetime.strptime(dt_raw, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        skipped += 1
                        continue
                if created < US_CSV_CUTOFF:
                    skipped += 1
                    continue
                trade_no = str(row.get("交易编号") or "").strip() or "0"
                action = meta["action"]
                pnl = _parse_csv_float(row.get("净损益 USD")) or _parse_csv_float(row.get("净损益 USDT")) or 0.0
                if action == "open":
                    pnl = 0.0
                price = _parse_csv_float(row.get("价格 USD")) or _parse_csv_float(row.get("价格 USDT"))
                qty = _parse_csv_float(row.get("大小（数量）"))
                margin = _parse_csv_float(row.get("大小（价值）"))
                signal = str(row.get("信号") or "").strip()
                order_id = f"csv-SOXL-{trade_no}-{action}"[:80]
                detail = f"{US_CSV_IMPORT_DETAIL_PREFIX} half_pos {signal}"[:255]
                session.add(
                    PortalTrade(
                        user_id=uid,
                        platform=BOOK_PLATFORM_US,
                        symbol="SOXL",
                        side=meta["side"],
                        action=action,
                        strategy_name=US_STRATEGY_NAME,
                        timeframe="",
                        price=price,
                        quantity=qty,
                        margin=margin,
                        leverage=1,
                        pnl=float(pnl),
                        status="ok",
                        detail=detail,
                        order_id=order_id,
                        created_at=created,
                    )
                )
                imported += 1
        session.commit()
        return {
            "ok": True,
            "skipped": False,
            "imported": imported,
            "parse_skipped": skipped,
            "platform": BOOK_PLATFORM_US,
            "initial_capital": US_ACCOUNT_INITIAL_USD,
            "csv_file": str(path),
            "cutoff": US_CSV_CUTOFF.strftime("%Y-%m-%d"),
            "note": "半仓：沿用 CSV 中约 250 万名义本金/笔",
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_us_account_csv_trades(user_id: int = BOOK_SHARED_USER_ID) -> Dict[str, Any]:
    try:
        _ = user_id
        return import_us_account_csv_trades(force=False)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


_BOOK_ENSURE_TS = 0.0
_BOOK_ENSURE_CACHE: Dict[str, Any] = {}


def ensure_book_account_csv_trades(user_id: int = BOOK_SHARED_USER_ID) -> Dict[str, Any]:
    """加密 + 美股账面 CSV 一并确保。短时去抖，避免每次拉余额都扫 CSV。"""
    import time as _time

    global _BOOK_ENSURE_TS, _BOOK_ENSURE_CACHE
    now = _time.time()
    if _BOOK_ENSURE_CACHE and now - _BOOK_ENSURE_TS < 60:
        return _BOOK_ENSURE_CACHE
    out = {
        "crypto": ensure_crypto_account_csv_trades(user_id),
        "us": ensure_us_account_csv_trades(user_id),
    }
    _BOOK_ENSURE_CACHE = out
    _BOOK_ENSURE_TS = now
    return out


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


def _initial_capital_for_platform(platform: str = "") -> Optional[float]:
    plat = (platform or "").strip().lower()
    if is_book_platform(plat):
        return get_book_initial_capital(plat)
    if plat in ("", "all", "全部"):
        total = get_book_initial_capital(BOOK_PLATFORM_CRYPTO) + get_book_initial_capital(
            BOOK_PLATFORM_US
        )
        for key in list_dynamic_book_platform_keys():
            total += get_book_initial_capital(key)
        return total
    return None


def _symbol_position_capital(subset) -> Optional[float]:
    """单币种仓位基数：开仓 margin 的均值（如固定半仓 200 万则约为 200 万）。"""
    opens = [
        abs(float(r.margin))
        for r in subset
        if (r.action or "") == "open"
        and r.margin is not None
        and abs(float(r.margin or 0)) > 0
    ]
    if not opens:
        opens = [
            abs(float(r.margin))
            for r in subset
            if r.margin is not None and abs(float(r.margin or 0)) > 0
        ]
    if not opens:
        return None
    return round(sum(opens) / len(opens), 4)


def _window_stats(subset, *, initial_capital: Optional[float] = None) -> Dict[str, Any]:
    wins = sum(float(r.pnl or 0) for r in subset if float(r.pnl or 0) > 0)
    losses = abs(sum(float(r.pnl or 0) for r in subset if float(r.pnl or 0) < 0))
    pnl = round(sum(float(r.pnl or 0) for r in subset), 4)
    if losses > 0:
        ratio: Optional[float] = round(wins / losses, 4)
    elif wins > 0:
        ratio = None
    else:
        ratio = None
    ret = None
    try:
        cap = float(initial_capital) if initial_capital is not None else None
    except (TypeError, ValueError):
        cap = None
    if cap and cap > 0:
        ret = round(pnl / cap * 100.0, 4)
    return {
        "orders": len(subset),
        "pnl": pnl,
        "return_pct": ret,
        "capital_base": cap,
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
        rows = _trade_rows_for_view(
            session,
            user_id,
            platform=platform,
            symbol=symbol,
            strategy=strategy,
        )
        rows = sorted(
            rows,
            key=lambda r: (r.created_at or datetime.min, r.id or 0),
            reverse=True,
        )
        lim = max(1, min(int(limit or 200), 500))
        return [_trade_dict(r) for r in rows[:lim]]
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
        rows = _trade_rows_for_view(
            session,
            user_id,
            platform=platform,
            symbol=symbol,
            strategy=strategy,
            status_ok_only=True,
        )
    finally:
        session.close()

    init_cap = _initial_capital_for_platform(platform)
    # 筛了单币种：收益率 = 该币收益 / 该币仓位(开仓 margin 均值)
    sym = (symbol or "").strip()
    use_pos_cap = bool(sym) and sym.upper() not in ("ALL", "全部")
    now = datetime.now()
    windows = {"7d": 7, "30d": 30, "180d": 180}
    out: Dict[str, Any] = {}
    for key, days in windows.items():
        since = now - timedelta(days=days)
        subset = [r for r in rows if r.created_at and r.created_at >= since]
        cap = (_symbol_position_capital(subset) if use_pos_cap else None) or init_cap
        out[key] = _window_stats(subset, initial_capital=cap)
    total_cap = (_symbol_position_capital(rows) if use_pos_cap else None) or init_cap
    total = _window_stats(rows, initial_capital=total_cap)
    out["total_orders"] = total["orders"]
    out["total_pnl"] = total["pnl"]
    out["return_pct"] = total.get("return_pct")
    out["initial_capital"] = total_cap
    out["capital_mode"] = "position" if use_pos_cap else "account"
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
        "require_2h": bool(getattr(r, "require_2h", False)),
        "require_4h": bool(getattr(r, "require_4h", False)),
        "status_mode": normalize_status_mode(getattr(r, "status_mode", None)),
        "status_profiles": normalize_status_profiles(getattr(r, "status_profiles", None) or "{}"),
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


def upsert_watch_gates(
    user_id: int,
    symbols: List[str],
    *,
    require_short: bool = False,
    require_mid: bool = False,
    require_long: bool = False,
    require_2h: bool = False,
    require_4h: bool = False,
    status_mode: str = "趋势",
    status_profiles: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """只保存观察条件（第一步），不改交易参数、不自动变 living/connected。"""
    cleaned = []
    for raw in symbols or []:
        sym = (raw or "").strip().upper()
        if sym and sym not in cleaned:
            cleaned.append(sym)
    if not cleaned:
        raise ValueError("请至少选择一个交易对")
    if status_profiles is not None:
        profiles = normalize_status_profiles(status_profiles)
        mode_label = "趋势"
        for mode in WATCH_STATUS_MODES:
            g = profiles.get(mode) or {}
            if any(g.get(k) for k in ("require_2h", "require_4h", "require_mid", "require_long")):
                mode_label = mode
                require_mid = bool(g.get("require_mid"))
                require_long = bool(g.get("require_long"))
                require_2h = bool(g.get("require_2h"))
                require_4h = bool(g.get("require_4h"))
                break
    else:
        mode_label = normalize_status_mode(status_mode)
        profiles = normalize_status_profiles({
            mode_label: {
                "require_mid": require_mid,
                "require_long": require_long,
                "require_2h": require_2h,
                "require_4h": require_4h,
            }
        })
    profiles_json = dump_status_profiles(profiles)
    session = _session()
    try:
        out = []
        now = datetime.now()
        for sym in cleaned:
            row = session.query(PortalWatchConfig).filter_by(user_id=user_id, symbol=sym).first()
            if not row:
                row = PortalWatchConfig(user_id=user_id, symbol=sym)
                session.add(row)
            row.require_short = False
            row.require_mid = bool(require_mid)
            row.require_long = bool(require_long)
            row.require_2h = bool(require_2h)
            row.require_4h = bool(require_4h)
            row.status_mode = mode_label
            row.status_profiles = profiles_json
            # 仅条件保存：不强制 living；已 connected 保持
            cur = (getattr(row, "status", None) or "").strip().lower()
            if cur not in ("connected", "living"):
                row.status = "watching"
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
    require_2h: bool = False,
    require_4h: bool = False,
    status_mode: str = "趋势",
    status_profiles: Optional[Any] = None,
    gates_only: bool = False,
) -> List[Dict[str, Any]]:
    if gates_only:
        return upsert_watch_gates(
            user_id,
            symbols,
            require_short=require_short,
            require_mid=require_mid,
            require_long=require_long,
            require_2h=require_2h,
            require_4h=require_4h,
            status_mode=status_mode,
            status_profiles=status_profiles,
        )
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
            row.require_2h = bool(require_2h)
            row.require_4h = bool(require_4h)
            row.status_mode = normalize_status_mode(status_mode)
            if status_profiles is not None:
                row.status_profiles = dump_status_profiles(status_profiles)
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
        points = [{"t": f"D{d+1}", "v": round(base + d * (0.003 + i * 0.001), 4)} for d in range(30)]
        series.append({"id": sid, "name": next((x["title"] for x in _SEARCH_CATALOG if x["id"] == sid), sid), "points": points})
    return {"series": series, "note": "占位数据，后期接真实净值"}


def _fetch_btc_daily_closes(days: int) -> List[Dict[str, Any]]:
    """BTCUSDT 日线收盘价，失败返回空。"""
    try:
        from backpack_quant_trading.core.binance_monitor import fetch_binance_klines

        bars = fetch_binance_klines("BTCUSDT", "1d", limit=max(days + 5, 10), market="spot") or []
        out = []
        for b in bars:
            ts = int(b.get("open_time") or 0)
            if ts <= 0:
                continue
            day = datetime.utcfromtimestamp(ts / 1000.0).strftime("%Y-%m-%d")
            out.append({"date": day, "close": float(b.get("close") or 0)})
        return [x for x in out if x["close"] > 0]
    except Exception:
        return []


def build_equity_curve(
    user_id: int,
    *,
    platform: str = "",
    days: int = 90,
    current_equity: Optional[float] = None,
    initial_capital: Optional[float] = None,
    include_btc: bool = False,
) -> Dict[str, Any]:
    """用 portal_trades 已实现盈亏重建净值曲线。

    - live：按日累加已实现 pnl，末点对齐当前权益（若有）
    - include_btc=True 时叠加 BTC 同起点基准（默认关闭）
    - initial_capital：账面账户本金，无交易所权益时用作起点
    - *_index：归一化到起点=1
    """
    now = datetime.now()
    end_day = now.date()
    raw_days = int(days if days is not None else 90)

    plat = (platform or "").strip().lower()
    session = _session()
    try:
        rows = _trade_rows_for_view(
            session, user_id, platform=plat, status_ok_only=True
        )
        rows = sorted(rows, key=lambda r: (r.created_at or datetime.min, r.id or 0))
    finally:
        session.close()

    # days<=0 或很大：全部历史（自首笔成交日起）
    if raw_days <= 0 or raw_days >= 9000:
        first = next((r.created_at.date() for r in rows if r.created_at), end_day)
        days = max(7, (end_day - first).days + 1)
        days = min(days, 3650)
    else:
        days = max(7, min(raw_days, 3650))
    start_day = (now - timedelta(days=days - 1)).date()

    # 按日汇总已实现盈亏
    daily_pnl: Dict[str, float] = {}
    for r in rows:
        if not r.created_at:
            continue
        d = r.created_at.date()
        if d < start_day:
            # 窗口前盈亏计入起点调整
            key = "_before"
            daily_pnl[key] = daily_pnl.get(key, 0.0) + float(r.pnl or 0)
            continue
        if d > end_day:
            continue
        key = d.strftime("%Y-%m-%d")
        daily_pnl[key] = daily_pnl.get(key, 0.0) + float(r.pnl or 0)

    pnl_before = float(daily_pnl.pop("_before", 0.0))
    pnl_in_window = sum(float(v) for v in daily_pnl.values())
    try:
        cur = float(current_equity) if current_equity is not None else None
    except (TypeError, ValueError):
        cur = None
    # 权益为 0/负数视为「未读到有效余额」，避免末点被压成 0 导致假 -100%
    if cur is None or cur <= 0:
        cur = None

    try:
        init_cap = float(initial_capital) if initial_capital is not None else None
    except (TypeError, ValueError):
        init_cap = None
    if init_cap is not None and init_cap < 0:
        init_cap = None

    # 起点权益：优先用「当前权益 − 窗口内累计盈亏」；其次账面本金+窗口前盈亏
    if cur is not None:
        start_equity = cur - pnl_in_window
        if start_equity <= 0:
            start_equity = max(cur * 0.5, 100.0)
    elif init_cap is not None:
        start_equity = init_cap + pnl_before
        if start_equity <= 0:
            start_equity = max(init_cap, 100.0)
    else:
        # 无余额时仍展示相对曲线：以窗口盈亏波动为中心
        start_equity = max(abs(pnl_before) + abs(pnl_in_window) + 1000.0, 1000.0)

    dates: List[str] = []
    live: List[float] = []
    cum = 0.0
    d = start_day
    while d <= end_day:
        key = d.strftime("%Y-%m-%d")
        cum += float(daily_pnl.get(key, 0.0))
        dates.append(key)
        live.append(round(start_equity + cum, 4))
        d += timedelta(days=1)

    if cur is not None and live:
        live[-1] = round(cur, 4)

    btc: List[Optional[float]] = []
    btc_index: List[Optional[float]] = []
    btc_ret = None
    if include_btc:
        # BTC 基准：同起点资金按涨跌比缩放
        btc_bars = _fetch_btc_daily_closes(days + 3)
        btc_map = {x["date"]: x["close"] for x in btc_bars}
        btc0 = None
        for day in dates:
            px = btc_map.get(day)
            if px and px > 0:
                if btc0 is None:
                    btc0 = px
                btc.append(round(start_equity * (px / btc0), 4) if btc0 else None)
            else:
                btc.append(btc[-1] if btc else (round(start_equity, 4) if btc0 is None else None))
        if not any(v is not None for v in btc):
            btc = []
        if btc:
            b0 = next((v for v in btc if v is not None and v > 0), None) or start_equity
            for v in btc:
                if v is None:
                    btc_index.append(None)
                else:
                    btc_index.append(round(float(v) / b0, 6))
            if btc_index and btc_index[-1] is not None:
                btc_ret = round((float(btc_index[-1]) - 1.0) * 100.0, 4)

    live0 = live[0] if live else 1.0
    if live0 == 0:
        live0 = 1.0
    live_index = [round(v / live0, 6) for v in live]

    live_ret = round((live[-1] / live0 - 1.0) * 100.0, 4) if live else 0.0

    return {
        "dates": dates,
        "live": live,
        "btc": btc,
        "live_index": live_index,
        "btc_index": btc_index,
        "start_equity": round(start_equity, 4),
        "end_equity": round(live[-1], 4) if live else None,
        "current_equity": cur,
        "live_return_pct": live_ret,
        "btc_return_pct": btc_ret,
        "trade_count": len(rows),
        "pnl_in_window": round(pnl_in_window, 4),
        "platform": plat if plat and plat not in ("all", "全部") else "all",
        "days": days,
        "currency": "USD",
        "include_btc": bool(include_btc),
        "note": (
            "由成交已实现盈亏重建净值"
            + ("；含 BTC 同起点基准" if include_btc else "")
        ),
    }

