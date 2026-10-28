#!/usr/bin/env python
"""将 eth/hype CSV 导入为全站共享「加密账户」（user_id=0），所有登录用户可见。"""
from __future__ import annotations

import argparse
import sys

from backpack_quant_trading.core.env_loader import load_project_env
from backpack_quant_trading.core import portal_store as store


def main() -> int:
    load_project_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="清除已有共享 csv import 后重导")
    args = parser.parse_args()

    purged = store.purge_per_user_book_trades()
    res = store.import_crypto_account_csv_trades(store.BOOK_SHARED_USER_ID, force=bool(args.force))
    eq = store.book_account_equity(0, store.BOOK_PLATFORM_CRYPTO)
    print(f"purged_per_user={purged} {res} equity={eq}")

    # 抽查：任意用户 list_trades 应能看到共享账面
    from backpack_quant_trading.database.models import DatabaseManager
    from sqlalchemy import text

    db = DatabaseManager()
    with db.engine.connect() as conn:
        user_ids = [int(r[0]) for r in conn.execute(text("SELECT id FROM users ORDER BY id")).fetchall()]
    for uid in user_ids[:3]:
        items = store.list_trades(uid, platform=store.BOOK_PLATFORM_CRYPTO, limit=5)
        stats = store.trade_stats(uid, platform=store.BOOK_PLATFORM_CRYPTO)
        print(
            f"user={uid} crypto_items={len(items)} "
            f"total_orders={stats.get('total_orders')} total_pnl={stats.get('total_pnl')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
