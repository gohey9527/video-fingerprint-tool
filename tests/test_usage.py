from __future__ import annotations

from pathlib import Path

import pytest

from auth import (
    DEFAULT_ADMIN_USER,
    SavedLogin,
    SavedLoginStore,
    _decode_secret,
    _encode_secret,
    is_admin_user,
    saved_login_path,
)
from usage import UsageStore, client_info


def test_is_admin_user_recognizes_default_admin() -> None:
    assert is_admin_user(DEFAULT_ADMIN_USER) is True
    assert is_admin_user("editor") is False


def test_is_admin_user_recognizes_admin_nickname() -> None:
    assert is_admin_user("demo", nickname="管理员") is True


def test_saved_login_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("auth.saved_login_path", lambda: tmp_path / "saved_login.json")
    store = SavedLoginStore()
    store.save(
        SavedLogin(
            username="alice",
            remember_username=True,
            remember_session=True,
            login_mode="API",
            refresh_token="refresh-token-123",
        )
    )
    loaded = store.load()
    assert loaded is not None
    assert loaded.username == "alice"
    assert loaded.remember_session is True
    assert loaded.refresh_token == "refresh-token-123"


def test_saved_login_clear(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "saved_login.json"
    monkeypatch.setattr("auth.saved_login_path", lambda: path)
    store = SavedLoginStore()
    store.save(SavedLogin(username="bob", remember_username=True))
    store.clear()
    assert store.load() is None
    assert not path.exists()


def test_encode_decode_secret_roundtrip() -> None:
    plain = "secret-refresh-token"
    assert _decode_secret(_encode_secret(plain)) == plain


def test_usage_store_records_and_lists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "usage.db"
    monkeypatch.setattr("usage.app_data_dir", lambda: tmp_path)
    store = UsageStore(db_path)
    record = store.record("alice", "login", "manual login")
    assert record.username == "alice"
    assert record.event_type == "login"

    records = store.list_recent()
    assert len(records) == 1
    assert records[0].event_detail == "manual login"


def test_client_info_contains_platform_fields() -> None:
    info = client_info()
    assert info["client_id"] == "video-fingerprint-tool"
    assert info["client_platform"]
    assert info["client_version"]
