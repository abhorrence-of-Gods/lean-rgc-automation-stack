from __future__ import annotations

from typing import Any
import sqlite3
import time


def ensure_migration_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at REAL NOT NULL,
            payload_json TEXT
        )
        """
    )


def record_migration(
    conn: sqlite3.Connection,
    *,
    version: str,
    name: str,
    payload_json: str = "{}",
) -> None:
    ensure_migration_schema(conn)
    conn.execute(
        """
        INSERT OR IGNORE INTO schema_migrations(version, name, applied_at, payload_json)
        VALUES (?,?,?,?)
        """,
        (version, name, float(time.time()), payload_json),
    )


__all__ = ["ensure_migration_schema", "record_migration"]
