#!/usr/bin/env python
"""在云服务器上创建或提权管理账号。页面注册只能是普通 user。

用法（容器内 /opt/backpack-quant）:
  # 新建管理员
  python -m backpack_quant_trading.tools.create_admin_user --username root --password '***'

  # 把已有账号提权为 root（不改密码）
  python -m backpack_quant_trading.tools.create_admin_user --username zyf --promote --role root

  # 列出全部用户
  python -m backpack_quant_trading.tools.create_admin_user --list
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
from backpack_quant_trading.database.models import DatabaseManager, User


def main() -> int:
    load_project_env()
    parser = argparse.ArgumentParser(description="创建/提权管理用户")
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument(
        "--role",
        default="superuser",
        choices=("superuser", "admin", "root"),
        help="管理角色，前端/后端均认 superuser|admin|root",
    )
    parser.add_argument(
        "--promote",
        action="store_true",
        help="已有用户只改 role，不新建、不改密码",
    )
    parser.add_argument("--list", action="store_true", help="列出 users 表")
    args = parser.parse_args()

    db = DatabaseManager()
    db.create_tables()

    if args.list:
        session = db.get_session()
        try:
            rows = session.query(User).order_by(User.id).all()
            if not rows:
                print("(empty)")
                return 0
            for u in rows:
                print(f"id={u.id}\tusername={u.username}\trole={u.role}")
            return 0
        finally:
            session.close()

    username = (args.username or "").strip()
    if len(username) < 2:
        print("请提供 --username（至少 2 字符），或用 --list", file=sys.stderr)
        return 1

    if args.promote:
        user = db.set_user_role(username, args.role)
        if not user:
            print(f"用户不存在: {username}", file=sys.stderr)
            return 2
        print(f"ok promoted id={user.id} username={user.username} role={user.role}")
        return 0

    if len(args.password or "") < 6:
        print("新建用户需 --password（至少 6 位）；已有账号请用 --promote", file=sys.stderr)
        return 1
    if db.get_user_by_username(username):
        print(f"用户已存在: {username}；提权请加 --promote", file=sys.stderr)
        return 2
    user = db.create_user(username, get_password_hash(args.password), role=args.role)
    print(f"ok id={user.id} username={user.username} role={user.role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
