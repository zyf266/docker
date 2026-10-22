#!/usr/bin/env python
"""在云服务器上创建管理账号（superuser）。页面注册不能创建管理员。

用法（在项目根或 /opt/backpack-quant）:
  python -m backpack_quant_trading.tools.create_admin_user --username root --password '***'
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backpack_quant_trading.core.env_loader import load_project_env
from backpack_quant_trading.api.deps import get_password_hash
from backpack_quant_trading.database.models import DatabaseManager


def main() -> int:
    load_project_env()
    parser = argparse.ArgumentParser(description="创建管理用户 superuser")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    username = args.username.strip()
    if len(username) < 2 or len(args.password) < 6:
        print("用户名至少 2 字符，密码至少 6 位", file=sys.stderr)
        return 1
    db = DatabaseManager()
    db.create_tables()
    if db.get_user_by_username(username):
        print(f"用户已存在: {username}", file=sys.stderr)
        return 2
    user = db.create_user(username, get_password_hash(args.password), role="superuser")
    print(f"ok id={user.id} username={user.username} role={user.role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
