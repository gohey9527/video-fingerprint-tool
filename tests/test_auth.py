from __future__ import annotations

from pathlib import Path

import pytest

from auth import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USER, UserStore


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
