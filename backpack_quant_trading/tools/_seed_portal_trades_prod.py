#!/usr/bin/env python
"""在服务器上灌 portal_trades 演示数据（可重复跑：先按 detail=mock seed 清理）。"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backpack_quant_trading.core.env_loader import load_project_env
from backpack_quant_trading.database.models import DatabaseManager, User


def main() -> int:
    load_project_env()
    # 确保用到带 PortalTrade 的 store（若正式镜像尚无该表，用 SQLAlchemy create）
    from backpack_quant_trading.core.portal_store import PortalTrade, _session, trade_stats

    db = DatabaseManager()
    sess = db.get_session()
    try:
        users = sess.query(User).all()
        print("USERS:")
        for u in users:
            print(f"  id={u.id} username={u.username} role={u.role}")
        user_ids = [u.id for u in users]
    finally:
        sess.close()

    if not user_ids:
        print("no users", file=sys.stderr)
        return 1

    session = _session()
    try:
        # 清掉旧 mock
        deleted = (
            session.query(PortalTrade)
            .filter(PortalTrade.detail.like("mock seed%"))
            .delete(synchronize_session=False)
        )
        session.commit()
        print(f"cleared old mock: {deleted}")
    except Exception as e:
        session.rollback()
        print(f"clear skip/err: {e}")
        # 表可能不存在，_session create_all 已执行；再试一次
        session = _session()

    samples = [
        ("hyperliquid", "BTCUSDT", "BUY", "open", "test", "2h", 79800, 0.01, 100, 5, 0, "ok", 1),
        ("hyperliquid", "BTCUSDT", "SELL", "close", "test", "2h", 81200, 0.01, 100, 5, 140, "ok", 2),
        ("okx", "ETHUSDT", "BUY", "open", "eth-trend", "1h", 2450, 0.5, 200, 10, 0, "ok", 3),
        ("okx", "ETHUSDT", "SELL", "close", "eth-trend", "1h", 2380, 0.5, 200, 10, -35, "ok", 4),
        ("hyperliquid", "SOLUSDT", "BUY", "open", "sol-ma", "4h", 178, 2, 80, 8, 0, "ok", 5),
        ("hyperliquid", "SOLUSDT", "SELL", "close", "sol-ma", "4h", 185, 2, 80, 8, 56, "ok", 6),
        ("okx", "BTCUSDT", "BUY", "open", "btc-grid", "2h", 72000, 0.02, 150, 5, 0, "ok", 12),
        ("okx", "BTCUSDT", "SELL", "close", "btc-grid", "2h", 74500, 0.02, 150, 5, 220, "ok", 15),
        ("hyperliquid", "ETHUSDT", "SELL", "open", "short-eth", "2h", 2600, 0.4, 120, 8, 0, "ok", 18),
        ("hyperliquid", "ETHUSDT", "BUY", "close", "short-eth", "2h", 2520, 0.4, 120, 8, 48, "ok", 20),
        ("okx", "SOLUSDT", "BUY", "open", "sol-follow", "1d", 165, 3, 90, 5, 0, "ok", 22),
        ("okx", "SOLUSDT", "SELL", "close", "sol-follow", "1d", 155, 3, 90, 5, -60, "ok", 25),
        ("hyperliquid", "BTCUSDT", "BUY", "open", "legacy", "2h", 61000, 0.03, 200, 5, 0, "ok", 60),
        ("hyperliquid", "BTCUSDT", "SELL", "close", "legacy", "2h", 64000, 0.03, 200, 5, 310, "ok", 65),
        ("okx", "AAVEUSDT", "BUY", "open", "aave-test", "4h", 180, 1, 50, 5, 0, "ok", 90),
        ("okx", "AAVEUSDT", "SELL", "close", "aave-test", "4h", 195, 1, 50, 5, 42, "ok", 95),
        ("hyperliquid", "NEARUSDT", "BUY", "open", "near-ma", "2h", 4.8, 20, 60, 8, 0, "ok", 120),
        ("hyperliquid", "NEARUSDT", "SELL", "close", "near-ma", "2h", 4.2, 20, 60, 8, -28, "ok", 130),
        ("hyperliquid", "BTCUSDT", "BUY", "open", "test", "2h", 80000, None, 100, 5, 0, "rejected", 1),
        ("okx", "ETHUSDT", "BUY", "open", "eth-trend", "1h", 2440, None, 100, 10, 0, "dry-run", 2),
    ]

    now = datetime.now()
    n = 0
    try:
        for uid in user_ids:
            for plat, sym, side, act, strat, tf, price, qty, margin, lev, pnl, status, days_ago in samples:
                detail = "mock seed"
                if status == "rejected":
                    detail = "mock seed 未站上MA"
                elif status == "dry-run":
                    detail = "mock seed dry-run"
                row = PortalTrade(
                    user_id=uid,
                    platform=plat,
                    symbol=sym,
                    side=side,
                    action=act,
                    strategy_name=strat,
                    timeframe=tf,
                    price=price,
                    quantity=qty,
                    margin=margin,
                    leverage=lev,
                    pnl=pnl,
                    status=status,
                    detail=detail,
                    order_id=f"mock-{uid}-{n}",
                    created_at=now - timedelta(days=days_ago, hours=(n % 5)),
                )
                session.add(row)
                n += 1
        session.commit()
        print(f"seeded {n} rows for user_ids={user_ids}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    for uid in user_ids[:5]:
        st = trade_stats(uid)
        print(f"stats user={uid} total_orders={st['total_orders']} total_pnl={st['total_pnl']} 7d={st['7d']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
