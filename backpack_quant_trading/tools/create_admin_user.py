#!/usr/bin/env python
"""在云服务器上创建/提权/降权/改密。页面注册只能是普通 user。

用法（正式服：先 docker exec 进 backpack-api）:
  # 列出全部用户
  python -m backpack_quant_trading.tools.create_admin_user --list

  # 新建管理员
  python -m backpack_quant_trading.tools.create_admin_user --username root --password '***' --role superuser

  # 把已有账号提权（不改密码）
  python -m backpack_quant_trading.tools.create_admin_user --username zyf --set-role --role root

  # 降为普通用户
  python -m backpack_quant_trading.tools.create_admin_user --username alice --set-role --role user

  # 只改密码
  python -m backpack_quant_trading.tools.create_admin_user --username alice --reset-password 'NewPass123'
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

ADMIN_ROLES = ("superuser", "admin", "root")
ALL_ROLES = ("user",) + ADMIN_ROLES


def _set_password(db: DatabaseManager, username: str, password: str) -> User:
    session = db.get_session()
    try:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise LookupError(f"用户不存在: {username}")
        user.password_hash = get_password_hash(password)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> int:
    load_project_env()
    parser = argparse.ArgumentParser(description="创建/改角色/改密（users 表）")
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="", help="新建管理员时的密码")
    parser.add_argument(
        "--role",
        default="superuser",
        choices=ALL_ROLES,
        help="角色：user=普通；superuser|admin|root=管理后台（三者权限等价）",
    )
    parser.add_argument(
        "--set-role",
        "--promote",
        dest="set_role",
        action="store_true",
        help="已有用户只改 role（可用 --role user 降权）；不新建、默认不改密码",
    )
    parser.add_argument(
        "--reset-password",
        default="",
        metavar="NEW_PASSWORD",
        help="已有用户重置密码（至少 6 位）；可与 --set-role 同用",
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

    new_password = (args.reset_password or "").strip()
    if args.set_role or new_password:
        if not db.get_user_by_username(username):
            print(f"用户不存在: {username}", file=sys.stderr)
            return 2
        if args.set_role:
            user = db.set_user_role(username, args.role)
            print(f"ok set-role id={user.id} username={user.username} role={user.role}")
        if new_password:
            if len(new_password) < 6:
                print("--reset-password 至少 6 位", file=sys.stderr)
                return 1
            user = _set_password(db, username, new_password)
            print(f"ok reset-password id={user.id} username={user.username}")
        return 0

    if args.role not in ADMIN_ROLES:
        print("新建账号请用管理角色（superuser|admin|root）；普通用户请走网页注册", file=sys.stderr)
        return 1
    if len(args.password or "") < 6:
        print("新建用户需 --password（至少 6 位）；已有账号请用 --set-role / --reset-password", file=sys.stderr)
        return 1
    if db.get_user_by_username(username):
        print(f"用户已存在: {username}；改角色用 --set-role，改密用 --reset-password", file=sys.stderr)
        return 2
    user = db.create_user(username, get_password_hash(args.password), role=args.role)
    print(f"ok created id={user.id} username={user.username} role={user.role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
