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
APP_CLIENT_ID = "video-fingerprint-tool"
APP_VERSION = "1.0.0"
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
    nickname: str = ""
    is_admin: bool = False


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


def saved_login_path() -> Path:
    return app_data_dir() / "saved_login.json"


def load_admin_usernames() -> set[str]:
    admins = {DEFAULT_ADMIN_USER}
    config_path = auth_api_config_path()
    if config_path.is_file():
        with suppress(OSError, json.JSONDecodeError):
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            extra = payload.get("admin_usernames", [])
            if isinstance(extra, list):
                admins.update(str(name).strip().lower() for name in extra if str(name).strip())
    return admins


def is_admin_user(username: str, *, nickname: str = "") -> bool:
    normalized = username.strip().lower()
    if normalized in load_admin_usernames():
        return True
    nickname_text = nickname.strip()
    return nickname_text in {"管理员", "超级管理员"}


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


def _machine_key() -> bytes:
    import platform

    seed = f"{APP_DIR_NAME}:{platform.node()}:{sys.platform}"
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _encode_secret(plain: str) -> str:
    import base64

    key = _machine_key()
    encrypted = bytes(byte ^ key[index % len(key)] for index, byte in enumerate(plain.encode("utf-8")))
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def _decode_secret(encoded: str) -> str:
    import base64

    key = _machine_key()
    encrypted = base64.urlsafe_b64decode(encoded.encode("ascii"))
    plain = bytes(byte ^ key[index % len(key)] for index, byte in enumerate(encrypted))
    return plain.decode("utf-8")


@dataclass
class SavedLogin:
    username: str
    remember_username: bool = False
    remember_session: bool = False
    login_mode: str = "API"
    refresh_token: str = ""


class SavedLoginStore:
    def load(self) -> SavedLogin | None:
        path = saved_login_path()
        if not path.is_file():
            return None
        with suppress(OSError, json.JSONDecodeError, ValueError):
            payload = json.loads(path.read_text(encoding="utf-8"))
            refresh_token = ""
            encoded = str(payload.get("refresh_token", "")).strip()
            if encoded:
                refresh_token = _decode_secret(encoded)
            return SavedLogin(
                username=str(payload.get("username", "")).strip(),
                remember_username=bool(payload.get("remember_username", False)),
                remember_session=bool(payload.get("remember_session", False)),
                login_mode=str(payload.get("login_mode", "API")),
                refresh_token=refresh_token,
            )
        return None

    def save(self, saved: SavedLogin) -> None:
        path = saved_login_path()
        payload: dict[str, object] = {
            "username": saved.username.strip(),
            "remember_username": saved.remember_username,
            "remember_session": saved.remember_session,
            "login_mode": saved.login_mode,
        }
        if saved.remember_session and saved.refresh_token:
            payload["refresh_token"] = _encode_secret(saved.refresh_token)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def clear(self) -> None:
        with suppress(OSError):
            saved_login_path().unlink(missing_ok=True)


def try_restore_session() -> tuple[User, AuthSession, str] | None:
    saved = SavedLoginStore().load()
    if not saved or not saved.remember_session or not saved.refresh_token:
        return None
    if saved.login_mode != "API":
        return None

    api_client = MineAdminAuthClient.from_config()
    if not api_client:
        return None

    try:
        session = api_client.refresh(saved.refresh_token)
    except AuthApiError:
        return None

    saved_login_store = SavedLoginStore()
    saved_login_store.save(
        SavedLogin(
            username=session.user.username,
            remember_username=True,
            remember_session=True,
            login_mode="API",
            refresh_token=session.refresh_token,
        )
    )
    return session.user, session, "API"


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

        return self._session_from_info(
            username,
            access_token,
            refresh_token,
            expire_at,
            info,
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
        return self._session_from_info(
            "",
            access_token,
            new_refresh_token,
            expire_at,
            info,
        )

    def logout(self, access_token: str) -> None:
        result = self._post_with_bearer("/admin/passport/logout", access_token)
        code = int(result.get("code", 500))
        if code != 200:
            raise AuthApiError(self._extract_result_error(result, "退出登录失败"))

    def _post_json_with_bearer(self, path: str, access_token: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
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

    def report_usage(
        self,
        access_token: str,
        *,
        username: str,
        event_type: str,
        event_detail: str = "",
        client_id: str = APP_CLIENT_ID,
        client_platform: str = "",
        client_version: str = APP_VERSION,
        created_at: str = "",
    ) -> None:
        payload = {
            "username": username,
            "client_id": client_id,
            "client_platform": client_platform,
            "client_version": client_version,
            "event_type": event_type,
            "event_detail": event_detail,
            "created_at": created_at,
        }
        result = self._post_json_with_bearer(
            "/admin/app/clientUsage/report",
            access_token,
            payload,
        )
        code = int(result.get("code", 500))
        if code not in (200, 404):
            raise AuthApiError(self._extract_result_error(result, "上报使用记录失败"))

    def list_usage(self, access_token: str, *, page: int = 1, page_size: int = 200) -> dict:
        query = f"page={page}&pageSize={page_size}"
        url = f"{self.base_url}/admin/app/clientUsage/list?{query}"
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
            raise AuthApiError(f"使用记录接口 HTTP 错误: {exc.code} {message}") from exc
        except error.URLError as exc:
            raise AuthApiError(f"使用记录接口连接失败: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise AuthApiError("使用记录接口返回了非 JSON 数据") from exc

    @staticmethod
    def _session_from_info(
        username: str,
        access_token: str,
        refresh_token: str,
        expire_at: int,
        info_payload: dict,
    ) -> AuthSession:
        info_data = info_payload.get("data") or {}
        username_from_info = str(info_data.get("username", "")).strip() or username.strip().lower()
        nickname = str(info_data.get("nickname", "")).strip()
        return AuthSession(
            user=User(username=username_from_info),
            access_token=access_token,
            refresh_token=refresh_token,
            expire_at=expire_at,
            nickname=nickname,
            is_admin=is_admin_user(username_from_info, nickname=nickname),
        )


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
