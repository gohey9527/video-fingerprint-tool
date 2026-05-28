from __future__ import annotations

from pathlib import Path

import pytest

from auth import (
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USER,
    DEFAULT_MINEADMIN_BASE_URL,
    MineAdminAuthClient,
    UserStore,
    _normalize_mineadmin_base_url,
    load_auth_api_base_url,
)


def test_default_admin_can_authenticate(temp_db_path: Path) -> None:
    store = UserStore(temp_db_path)
    user = store.authenticate(DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASSWORD)
    assert user is not None
    assert user.username == DEFAULT_ADMIN_USER


def test_wrong_password_is_rejected(temp_db_path: Path) -> None:
    store = UserStore(temp_db_path)
    assert store.authenticate(DEFAULT_ADMIN_USER, "wrong-password") is None


def test_add_user_and_authenticate(temp_db_path: Path) -> None:
    store = UserStore(temp_db_path)
    store.add_user("editor", "secret99")
    user = store.authenticate("editor", "secret99")
    assert user is not None
    assert user.username == "editor"


def test_deactivated_user_cannot_login(temp_db_path: Path) -> None:
    store = UserStore(temp_db_path)
    store.add_user("guest", "guest123")
    store.deactivate_user("guest")
    assert store.authenticate("guest", "guest123") is None


def test_cannot_deactivate_default_admin(temp_db_path: Path) -> None:
    store = UserStore(temp_db_path)
    with pytest.raises(ValueError, match="不能禁用默认管理员"):
        store.deactivate_user(DEFAULT_ADMIN_USER)


def test_normalize_base_url_accepts_login_endpoint_url() -> None:
    url = _normalize_mineadmin_base_url("https://ad-api.paiwan.com/admin/passport/login")
    assert url == "https://ad-api.paiwan.com"


def test_load_auth_api_base_url_uses_default_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINEADMIN_BASE_URL", raising=False)
    assert load_auth_api_base_url() == DEFAULT_MINEADMIN_BASE_URL


def test_extract_result_error_contains_message_and_code() -> None:
    err = MineAdminAuthClient._extract_result_error({"code": 422, "message": "密码错误"}, "登录失败")
    assert err == "密码错误 (code=422)"
