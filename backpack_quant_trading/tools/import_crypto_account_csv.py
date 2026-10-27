#!/usr/bin/env python
"""将 eth 200万.csv / hype 100万.csv 导入为 portal 加密账户交易记录。"""
from __future__ import annotations

import argparse
import sys

from backpack_quant_trading.core.env_loader import load_project_env
from backpack_quant_trading.core import portal_store as store


def main() -> int:
    load_project_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, action="append", default=None, help="指定用户，可重复；默认全部 users")
    parser.add_argument("--force", action="store_true", help="清除已有 csv import 后重导")
    args = parser.parse_args()

    from backpack_quant_trading.database.models import DatabaseManager
    from sqlalchemy import text

    db = DatabaseManager()
    with db.engine.connect() as conn:
        if args.user_id:
            user_ids = list(args.user_id)
        else:
            user_ids = [int(r[0]) for r in conn.execute(text("SELECT id FROM users ORDER BY id")).fetchall()]

    if not user_ids:
        print("no users", file=sys.stderr)
        return 1

    for uid in user_ids:
        res = store.import_crypto_account_csv_trades(uid, force=bool(args.force))
        eq = store.book_account_equity(uid, store.BOOK_PLATFORM_CRYPTO)
        print(f"user={uid} {res} equity={eq}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
