"""用户账户与登录校验。"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


APP_DIR_NAME = "短视频指纹工具"
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


@dataclass(frozen=True)
class User:
    username: str


def app_data_dir() -> Path:
    base = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def database_path() -> Path:
    return app_data_dir() / "users.db"


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, password_hash: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    _, digest_hex = _hash_password(password, salt)
    return secrets.compare_digest(digest_hex, password_hash)


class UserStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or database_path()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
                """
            )
            count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            if count == 0:
                self._create_user(conn, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASSWORD)

    def _create_user(self, conn: sqlite3.Connection, username: str, password: str) -> None:
        salt_hex, hash_hex = _hash_password(password)
        conn.execute(
            """
            INSERT INTO users (username, salt, password_hash, is_active, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            (
                username.strip().lower(),
                salt_hex,
                hash_hex,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def authenticate(self, username: str, password: str) -> User | None:
        normalized = username.strip().lower()
        if not normalized or not password:
            return None

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT username, salt, password_hash, is_active
                FROM users WHERE username = ?
                """,
                (normalized,),
            ).fetchone()

        if not row or not row["is_active"]:
            return None
        if not _verify_password(password, row["salt"], row["password_hash"]):
            return None
        return User(username=row["username"])

    def add_user(self, username: str, password: str) -> None:
        normalized = username.strip().lower()
        if len(normalized) < 3:
            raise ValueError("用户名至少 3 个字符")
        if len(password) < 6:
            raise ValueError("密码至少 6 个字符")

        with self._connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM users WHERE username = ?", (normalized,)
            ).fetchone()
            if exists:
                raise ValueError(f"用户 {normalized} 已存在")
            self._create_user(conn, normalized, password)

    def change_password(self, username: str, new_password: str) -> None:
        normalized = username.strip().lower()
        if len(new_password) < 6:
            raise ValueError("密码至少 6 个字符")

        salt_hex, hash_hex = _hash_password(new_password)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE users SET salt = ?, password_hash = ?
                WHERE username = ? AND is_active = 1
                """,
                (salt_hex, hash_hex, normalized),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"用户 {normalized} 不存在")

    def deactivate_user(self, username: str) -> None:
        normalized = username.strip().lower()
        if normalized == DEFAULT_ADMIN_USER:
            raise ValueError("不能禁用默认管理员账户")
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE users SET is_active = 0 WHERE username = ?", (normalized,)
            )
            if cursor.rowcount == 0:
                raise ValueError(f"用户 {normalized} 不存在")

    def list_users(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT username, is_active FROM users ORDER BY username"
            ).fetchall()
        return [f"{row['username']}{' (已禁用)' if not row['is_active'] else ''}" for row in rows]
