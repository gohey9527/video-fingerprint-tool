#!/usr/bin/env python3
"""管理工具账户（添加、改密、禁用、列表）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from auth import UserStore  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="管理短视频指纹工具用户账户")
    sub = parser.add_subparsers(dest="command", required=True)

    add_cmd = sub.add_parser("add", help="添加用户")
    add_cmd.add_argument("username")
    add_cmd.add_argument("password")

    passwd_cmd = sub.add_parser("passwd", help="修改密码")
    passwd_cmd.add_argument("username")
    passwd_cmd.add_argument("password")

    del_cmd = sub.add_parser("disable", help="禁用用户")
    del_cmd.add_argument("username")

    sub.add_parser("list", help="列出用户")

    args = parser.parse_args()
    store = UserStore()

    try:
        if args.command == "add":
            store.add_user(args.username, args.password)
            print(f"已添加用户：{args.username.strip().lower()}")
        elif args.command == "passwd":
            store.change_password(args.username, args.password)
            print(f"已更新用户密码：{args.username.strip().lower()}")
        elif args.command == "disable":
            store.deactivate_user(args.username)
            print(f"已禁用用户：{args.username.strip().lower()}")
        elif args.command == "list":
            users = store.list_users()
            if not users:
                print("暂无用户")
            else:
                print("用户列表：")
                for name in users:
                    print(f"  - {name}")
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
