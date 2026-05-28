"""用户账户与登录校验。"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import sys
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request


APP_DIR_NAME = "短视频指纹工具"
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_MINEADMIN_BASE_URL = "https://ad-api.paiwan.com"


@dataclass(frozen=True)
class User:
    username: str


@dataclass(frozen=True)
class AuthSession:
    user: User
    access_token: str
    refresh_token: str
    expire_at: int


class AuthApiError(RuntimeError):
    """MineAdmin 认证 API 调用失败。"""


def app_data_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.getenv("APPDATA", Path.home())) / APP_DIR_NAME
    else:
        base = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def database_path() -> Path:
    return app_data_dir() / "users.db"


def auth_api_config_path() -> Path:
    return app_data_dir() / "auth_api.json"


def _normalize_mineadmin_base_url(raw_url: str) -> str:
    url = raw_url.strip().rstrip("/")
    suffix = "/admin/passport/login"
    if url.endswith(suffix):
        return url[: -len(suffix)]
    return url


def load_auth_api_base_url() -> str | None:
    """优先读取环境变量，其次读取本地配置文件。"""
    env_url = os.getenv("MINEADMIN_BASE_URL", "").strip()
    if env_url:
        return _normalize_mineadmin_base_url(env_url)

    config_path = auth_api_config_path()
    if not config_path.is_file():
        return DEFAULT_MINEADMIN_BASE_URL

    with suppress(OSError, json.JSONDecodeError):
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        url = str(payload.get("base_url", "")).strip()
        if url:
            return _normalize_mineadmin_base_url(url)
    return DEFAULT_MINEADMIN_BASE_URL


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, password_hash: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    _, digest_hex = _hash_password(password, salt)
    return secrets.compare_digest(digest_hex, password_hash)


class MineAdminAuthClient:
    def __init__(self, base_url: str, timeout: float = 12.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @classmethod
    def from_config(cls) -> MineAdminAuthClient | None:
        base_url = load_auth_api_base_url()
        if not base_url:
            return None
        return cls(base_url=base_url)

    def _post_json(self, path: str, payload: dict[str, str]) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="ignore")
            raise AuthApiError(f"登录接口 HTTP 错误: {exc.code} {message}") from exc
        except error.URLError as exc:
            raise AuthApiError(f"登录接口连接失败: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise AuthApiError("登录接口返回了非 JSON 数据") from exc

    @staticmethod
    def _extract_result_error(payload: dict, default_message: str) -> str:
        code = payload.get("code")
        message = str(payload.get("message", "")).strip()
        if code is None and not message:
            return default_message
        if message:
            return f"{message} (code={code})" if code is not None else message
        return default_message

    def _get_json(self, path: str, access_token: str) -> dict:
        url = f"{self.base_url}{path}"
        req = request.Request(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="ignore")
            raise AuthApiError(f"用户信息接口 HTTP 错误: {exc.code} {message}") from exc
        except error.URLError as exc:
            raise AuthApiError(f"用户信息接口连接失败: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise AuthApiError("用户信息接口返回了非 JSON 数据") from exc

    def _post_refresh(self, refresh_token: str) -> dict:
        url = f"{self.base_url}/admin/passport/refresh"
        req = request.Request(
            url,
            data=b"",
            headers={"Authorization": f"Bearer {refresh_token}"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="ignore")
            raise AuthApiError(f"刷新 Token 失败: {exc.code} {message}") from exc
        except error.URLError as exc:
            raise AuthApiError(f"刷新 Token 连接失败: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise AuthApiError("刷新 Token 接口返回了非 JSON 数据") from exc

    def _post_with_bearer(self, path: str, token: str) -> dict:
        url = f"{self.base_url}{path}"
        req = request.Request(
            url,
            data=b"",
            headers={"Authorization": f"Bearer {token}"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="ignore")
            raise AuthApiError(f"接口 HTTP 错误: {exc.code} {message}") from exc
        except error.URLError as exc:
            raise AuthApiError(f"接口连接失败: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise AuthApiError("接口返回了非 JSON 数据") from exc

    def login(self, username: str, password: str) -> AuthSession:
        payload = {"username": username, "password": password}
        result = self._post_json("/admin/passport/login", payload)
        code = int(result.get("code", 500))
        if code != 200:
            raise AuthApiError(self._extract_result_error(result, "登录失败"))

        data = result.get("data") or {}
        access_token = str(data.get("access_token", "")).strip()
        refresh_token = str(data.get("refresh_token", "")).strip()
        expire_at = int(data.get("expire_at", 0) or 0)
        if not access_token:
            raise AuthApiError("登录成功但缺少 access_token")

        info = self._get_json("/admin/passport/getInfo", access_token)
        info_code = int(info.get("code", 500))
        if info_code != 200:
            raise AuthApiError(self._extract_result_error(info, "获取用户信息失败"))
        username_from_info = str((info.get("data") or {}).get("username", "")).strip()
        if not username_from_info:
            username_from_info = username.strip().lower()

        return AuthSession(
            user=User(username=username_from_info),
            access_token=access_token,
            refresh_token=refresh_token,
            expire_at=expire_at,
        )

    def refresh(self, refresh_token: str) -> AuthSession:
        result = self._post_refresh(refresh_token)
        code = int(result.get("code", 500))
        if code != 200:
            raise AuthApiError(self._extract_result_error(result, "刷新失败"))
        data = result.get("data") or {}
        access_token = str(data.get("access_token", "")).strip()
        new_refresh_token = str(data.get("refresh_token", "")).strip()
        expire_at = int(data.get("expire_at", 0) or 0)
        if not access_token or not new_refresh_token:
            raise AuthApiError("刷新成功但返回 Token 不完整")
        info = self._get_json("/admin/passport/getInfo", access_token)
        info_code = int(info.get("code", 500))
        if info_code != 200:
            raise AuthApiError(self._extract_result_error(info, "获取用户信息失败"))
        username = str((info.get("data") or {}).get("username", "")).strip() or "unknown"
        return AuthSession(
            user=User(username=username),
            access_token=access_token,
            refresh_token=new_refresh_token,
            expire_at=expire_at,
        )

    def logout(self, access_token: str) -> None:
        result = self._post_with_bearer("/admin/passport/logout", access_token)
        code = int(result.get("code", 500))
        if code != 200:
            raise AuthApiError(self._extract_result_error(result, "退出登录失败"))


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
