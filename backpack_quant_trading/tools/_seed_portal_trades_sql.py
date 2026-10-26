#!/usr/bin/env python
"""正式服灌 portal_trades：纯 SQL，不依赖镜像是否已含新 ORM 字段。"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta

# 容器内 cwd=/app，包已在 PYTHONPATH；勿依赖脚本物理路径
from sqlalchemy import text

from backpack_quant_trading.core.env_loader import load_project_env
from backpack_quant_trading.database.models import DatabaseManager

DDL = """
CREATE TABLE IF NOT EXISTS portal_trades (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  platform VARCHAR(32) NOT NULL DEFAULT '',
  symbol VARCHAR(32) NOT NULL DEFAULT '',
  side VARCHAR(16) NOT NULL DEFAULT '',
  action VARCHAR(16) NOT NULL DEFAULT '',
  strategy_name VARCHAR(80) NOT NULL DEFAULT '',
  timeframe VARCHAR(16) NOT NULL DEFAULT '',
  price DOUBLE NULL,
  quantity DOUBLE NULL,
  margin DOUBLE NULL,
  leverage INT NOT NULL DEFAULT 5,
  pnl DOUBLE NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT 'ok',
  detail VARCHAR(255) NOT NULL DEFAULT '',
  order_id VARCHAR(80) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL,
  INDEX ix_portal_trades_user_id (user_id),
  INDEX ix_portal_trades_platform (platform),
  INDEX ix_portal_trades_symbol (symbol),
  INDEX ix_portal_trades_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

INSERT = """
INSERT INTO portal_trades
(user_id, platform, symbol, side, action, strategy_name, timeframe,
 price, quantity, margin, leverage, pnl, status, detail, order_id, created_at)
VALUES
(:user_id, :platform, :symbol, :side, :action, :strategy_name, :timeframe,
 :price, :quantity, :margin, :leverage, :pnl, :status, :detail, :order_id, :created_at)
"""


def main() -> int:
    load_project_env()
    db = DatabaseManager()
    engine = db.engine

    with engine.begin() as conn:
        conn.execute(text(DDL))
        users = conn.execute(text("SELECT id, username, role FROM users ORDER BY id")).fetchall()
        print("USERS:")
        for u in users:
            print(f"  id={u[0]} username={u[1]} role={u[2]}")
        user_ids = [int(u[0]) for u in users]
        if not user_ids:
            print("no users", file=sys.stderr)
            return 1

        deleted = conn.execute(
            text("DELETE FROM portal_trades WHERE detail LIKE 'mock seed%'")
        ).rowcount
        print(f"cleared old mock: {deleted}")

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
        for uid in user_ids:
            for plat, sym, side, act, strat, tf, price, qty, margin, lev, pnl, status, days_ago in samples:
                detail = "mock seed"
                if status == "rejected":
                    detail = "mock seed 未站上MA"
                elif status == "dry-run":
                    detail = "mock seed dry-run"
                conn.execute(
                    text(INSERT),
                    {
                        "user_id": uid,
                        "platform": plat,
                        "symbol": sym,
                        "side": side,
                        "action": act,
                        "strategy_name": strat,
                        "timeframe": tf,
                        "price": price,
                        "quantity": qty,
                        "margin": margin,
                        "leverage": lev,
                        "pnl": pnl,
                        "status": status,
                        "detail": detail,
                        "order_id": f"mock-{uid}-{n}",
                        "created_at": now - timedelta(days=days_ago, hours=(n % 5)),
                    },
                )
                n += 1
        print(f"seeded {n} rows for {len(user_ids)} users")

        for uid in user_ids[:8]:
            row = conn.execute(
                text(
                    "SELECT COUNT(*), COALESCE(SUM(CASE WHEN status='ok' THEN pnl ELSE 0 END),0) "
                    "FROM portal_trades WHERE user_id=:uid"
                ),
                {"uid": uid},
            ).fetchone()
            print(f"user={uid} rows={row[0]} ok_pnl={row[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
