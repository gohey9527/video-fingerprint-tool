"""客户端使用记录：本机存储 + 上报 MineAdmin API。"""

from __future__ import annotations

import json
import platform
import sqlite3
import sys
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from auth import APP_CLIENT_ID, APP_VERSION, app_data_dir

if TYPE_CHECKING:
    from auth import MineAdminAuthClient


@dataclass(frozen=True)
class UsageRecord:
    id: int
    username: str
    client_id: str
    client_platform: str
    client_version: str
    event_type: str
    event_detail: str
    created_at: str


def client_platform() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return sys.platform


def client_info() -> dict[str, str]:
    return {
        "client_id": APP_CLIENT_ID,
        "client_platform": client_platform(),
        "client_version": APP_VERSION,
        "client_name": "短视频指纹工具",
    }


class UsageStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or (app_data_dir() / "usage.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    client_platform TEXT NOT NULL,
                    client_version TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_detail TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_usage_created_at ON usage_logs(created_at DESC)"
            )

    def record(
        self,
        username: str,
        event_type: str,
        event_detail: str = "",
        *,
        client_id: str | None = None,
        client_platform_name: str | None = None,
        client_version: str | None = None,
    ) -> UsageRecord:
        info = client_info()
        normalized = username.strip().lower()
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO usage_logs (
                    username, client_id, client_platform, client_version,
                    event_type, event_detail, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized,
                    client_id or info["client_id"],
                    client_platform_name or info["client_platform"],
                    client_version or info["client_version"],
                    event_type,
                    event_detail,
                    created_at,
                ),
            )
            row_id = int(cursor.lastrowid)
        return UsageRecord(
            id=row_id,
            username=normalized,
            client_id=client_id or info["client_id"],
            client_platform=client_platform_name or info["client_platform"],
            client_version=client_version or info["client_version"],
            event_type=event_type,
            event_detail=event_detail,
            created_at=created_at,
        )

    def list_recent(self, limit: int = 200) -> list[UsageRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, username, client_id, client_platform, client_version,
                       event_type, event_detail, created_at
                FROM usage_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_row_to_record(row) for row in rows]


def _row_to_record(row: sqlite3.Row) -> UsageRecord:
    return UsageRecord(
        id=int(row["id"]),
        username=str(row["username"]),
        client_id=str(row["client_id"]),
        client_platform=str(row["client_platform"]),
        client_version=str(row["client_version"]),
        event_type=str(row["event_type"]),
        event_detail=str(row["event_detail"] or ""),
        created_at=str(row["created_at"]),
    )


def _parse_api_records(payload: dict) -> list[UsageRecord]:
    data = payload.get("data")
    if isinstance(data, dict):
        items = data.get("list") or data.get("items") or []
    elif isinstance(data, list):
        items = data
    else:
        items = []

    records: list[UsageRecord] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        records.append(
            UsageRecord(
                id=int(item.get("id", index)),
                username=str(item.get("username", "")),
                client_id=str(item.get("client_id", APP_CLIENT_ID)),
                client_platform=str(item.get("client_platform", "")),
                client_version=str(item.get("client_version", "")),
                event_type=str(item.get("event_type", "")),
                event_detail=str(item.get("event_detail", "")),
                created_at=str(item.get("created_at", "")),
            )
        )
    return records


class UsageReporter:
    def __init__(
        self,
        store: UsageStore | None = None,
        api_client: MineAdminAuthClient | None = None,
    ) -> None:
        self.store = store or UsageStore()
        self.api_client = api_client

    def report(
        self,
        username: str,
        event_type: str,
        event_detail: str = "",
        *,
        access_token: str | None = None,
    ) -> UsageRecord:
        record = self.store.record(username, event_type, event_detail)
        if self.api_client and access_token:
            with suppress(Exception):
                self.api_client.report_usage(
                    access_token,
                    username=record.username,
                    event_type=record.event_type,
                    event_detail=record.event_detail,
                    client_id=record.client_id,
                    client_platform=record.client_platform,
                    client_version=record.client_version,
                    created_at=record.created_at,
                )
        return record

    def list_for_admin(
        self,
        access_token: str | None = None,
        *,
        limit: int = 200,
    ) -> tuple[list[UsageRecord], str | None]:
        if self.api_client and access_token:
            try:
                payload = self.api_client.list_usage(access_token, page_size=limit)
                records = _parse_api_records(payload)
                if records:
                    return records, None
            except Exception as exc:  # noqa: BLE001 - surface to admin UI
                return self.store.list_recent(limit), f"服务端记录暂不可用，已显示本机记录：{exc}"
        return self.store.list_recent(limit), None
