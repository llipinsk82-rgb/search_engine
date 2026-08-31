from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from backend.models import SearchItem
from backend.settings import DB_PATH

_token_re = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class ProviderSyncStats:
    provider: str
    fetched: int
    active_before: int
    active_after: int
    deactivated: int


def _connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize(path: Path = DB_PATH) -> None:
    with _connect(path) as conn:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                thumbnail TEXT,
                duration_seconds INTEGER,
                quality TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                source_order INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE INDEX IF NOT EXISTS idx_items_provider ON items(provider);
            CREATE INDEX IF NOT EXISTS idx_items_quality ON items(quality);
            CREATE INDEX IF NOT EXISTS idx_items_duration ON items(duration_seconds);

            CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
                id UNINDEXED,
                title,
                tags,
                provider UNINDEXED
            );
            """
        )

        columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(items)").fetchall()
        }
        if "source_order" not in columns:
            try:
                conn.execute(
                    "ALTER TABLE items ADD COLUMN source_order INTEGER NOT NULL DEFAULT 0"
                )
            except sqlite3.OperationalError:
                columns = {
                    str(row["name"])
                    for row in conn.execute("PRAGMA table_info(items)").fetchall()
                }
                if "source_order" not in columns:
                    raise
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_items_source_order ON items(source_order)"
        )


def _write_item(
    conn: sqlite3.Connection,
    item: SearchItem,
    *,
    source_order: int = 0,
) -> None:
    tags_json = json.dumps(item.tags, ensure_ascii=False)
    conn.execute(
        """
        INSERT INTO items (
            id, provider, title, url, thumbnail, duration_seconds,
            quality, tags_json, indexed_at, source_order, active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, 1)
        ON CONFLICT(id) DO UPDATE SET
            provider=excluded.provider,
            title=excluded.title,
            url=excluded.url,
            thumbnail=excluded.thumbnail,
            duration_seconds=excluded.duration_seconds,
            quality=excluded.quality,
            tags_json=excluded.tags_json,
            indexed_at=CURRENT_TIMESTAMP,
            source_order=excluded.source_order,
            active=1
        """,
        (
            item.id,
            item.provider,
            item.title,
            str(item.url),
            str(item.thumbnail) if item.thumbnail else None,
            item.duration_seconds,
            item.quality,
            tags_json,
            max(0, int(source_order)),
        ),
    )
    conn.execute("DELETE FROM items_fts WHERE id = ?", (item.id,))
    conn.execute(
        "INSERT INTO items_fts (id, title, tags, provider) VALUES (?, ?, ?, ?)",
        (item.id, item.title, " ".join(item.tags), item.provider),
    )


def upsert_items(items: list[SearchItem], path: Path = DB_PATH) -> int:
    initialize(path)
    with _connect(path) as conn:
        for source_order, item in enumerate(items):
            _write_item(conn, item, source_order=source_order)
    return len(items)


def merge_provider_items(
    provider: str,
    items: list[SearchItem],
    *,
    allow_empty: bool = False,
    path: Path = DB_PATH,
) -> ProviderSyncStats:
    """Merge a partial provider batch without deactivating older items."""
    if not provider.strip():
        raise ValueError("provider cannot be empty")
    if not items and not allow_empty:
        raise ValueError("refusing to merge an empty provider result set")

    mismatched = [item.id for item in items if item.provider != provider]
    if mismatched:
        raise ValueError(
            f"provider mismatch for {len(mismatched)} item(s); expected {provider!r}"
        )

    initialize(path)
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM items WHERE provider = ? AND active = 1",
            (provider,),
        ).fetchone()
        active_before = int(row["n"])

        for source_order, item in enumerate(items):
            _write_item(conn, item, source_order=source_order)

        row = conn.execute(
            "SELECT COUNT(*) AS n FROM items WHERE provider = ? AND active = 1",
            (provider,),
        ).fetchone()
        active_after = int(row["n"])

    return ProviderSyncStats(
        provider=provider,
        fetched=len(items),
        active_before=active_before,
        active_after=active_after,
        deactivated=0,
    )


def replace_provider_items(
    provider: str,
    items: list[SearchItem],
    *,
    allow_empty: bool = False,
    path: Path = DB_PATH,
) -> ProviderSyncStats:
    """Atomically replace the active snapshot for one provider.

    Provider collection happens before this function is called. If the fetched
    set is empty, the existing index is preserved unless allow_empty=True.
    """
    if not provider.strip():
        raise ValueError("provider cannot be empty")
    if not items and not allow_empty:
        raise ValueError("refusing to replace provider with an empty result set")

    mismatched = [item.id for item in items if item.provider != provider]
    if mismatched:
        raise ValueError(
            f"provider mismatch for {len(mismatched)} item(s); expected {provider!r}"
        )

    initialize(path)
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT id FROM items WHERE provider = ? AND active = 1",
            (provider,),
        ).fetchall()
        previous_ids = {str(row["id"]) for row in rows}
        active_before = len(previous_ids)
        incoming_ids = {item.id for item in items}

        conn.execute(
            "UPDATE items SET active = 0 WHERE provider = ? AND active = 1",
            (provider,),
        )
        for source_order, item in enumerate(items):
            _write_item(conn, item, source_order=source_order)

        conn.execute(
            """
            DELETE FROM items_fts
            WHERE id IN (
                SELECT id FROM items WHERE provider = ? AND active = 0
            )
            """,
            (provider,),
        )

        row = conn.execute(
            "SELECT COUNT(*) AS n FROM items WHERE provider = ? AND active = 1",
            (provider,),
        ).fetchone()
        active_after = int(row["n"])

    return ProviderSyncStats(
        provider=provider,
        fetched=len(items),
        active_before=active_before,
        active_after=active_after,
        deactivated=len(previous_ids - incoming_ids),
    )


def deactivate_provider(provider: str, path: Path = DB_PATH) -> int:
    initialize(path)
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT id FROM items WHERE provider = ? AND active = 1",
            (provider,),
        ).fetchall()
        ids = [str(row["id"]) for row in rows]
        if not ids:
            return 0

        conn.execute(
            "UPDATE items SET active = 0 WHERE provider = ? AND active = 1",
            (provider,),
        )
        conn.execute(
            """
            DELETE FROM items_fts
            WHERE id IN (
                SELECT id FROM items WHERE provider = ? AND active = 0
            )
            """,
            (provider,),
        )
        return len(ids)


def count_items(path: Path = DB_PATH) -> int:
    initialize(path)
    with _connect(path) as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM items WHERE active = 1").fetchone()
        return int(row["n"])


def indexed_providers(path: Path = DB_PATH) -> list[str]:
    initialize(path)
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT provider FROM items WHERE active = 1 ORDER BY provider"
        ).fetchall()
        return [str(row["provider"]) for row in rows]


def provider_counts(path: Path = DB_PATH) -> dict[str, int]:
    initialize(path)
    with _connect(path) as conn:
        rows = conn.execute(
            """
            SELECT provider, COUNT(*) AS n
            FROM items
            WHERE active = 1
            GROUP BY provider
            ORDER BY provider
            """
        ).fetchall()
        return {str(row["provider"]): int(row["n"]) for row in rows}


def search_items(
    query: str,
    *,
    provider: str | None = None,
    quality: str | None = None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    limit: int = 40,
    path: Path = DB_PATH,
) -> list[SearchItem]:
    initialize(path)

    where = ["i.active = 1"]
    params: list[object] = []
    joins = ""
    rank_select = "0.0 AS fts_rank"
    order = "i.indexed_at DESC, i.source_order ASC"

    tokens = _token_re.findall(query.lower())
    if tokens:
        fts_query = " ".join(f'"{token}"' for token in tokens)
        joins = "JOIN items_fts ON items_fts.id = i.id"
        where.append("items_fts MATCH ?")
        params.append(fts_query)
        rank_select = "bm25(items_fts, 0.0, 8.0, 2.0, 0.0) AS fts_rank"
        order = "fts_rank ASC, i.indexed_at DESC, i.source_order ASC"

    if provider:
        where.append("i.provider = ?")
        params.append(provider)
    if quality:
        where.append("LOWER(COALESCE(i.quality, '')) = LOWER(?)")
        params.append(quality)
    if min_duration is not None:
        where.append("COALESCE(i.duration_seconds, 0) >= ?")
        params.append(min_duration)
    if max_duration is not None:
        where.append("i.duration_seconds IS NOT NULL AND i.duration_seconds <= ?")
        params.append(max_duration)

    sql = f"""
        SELECT
            i.id, i.provider, i.title, i.url, i.thumbnail,
            i.duration_seconds, i.quality, i.tags_json,
            {rank_select}
        FROM items i
        {joins}
        WHERE {' AND '.join(where)}
        ORDER BY {order}
        LIMIT ?
    """
    params.append(limit * 3)

    with _connect(path) as conn:
        rows = conn.execute(sql, params).fetchall()

    result: list[SearchItem] = []
    total_rows = max(1, len(rows))
    for position, row in enumerate(rows):
        if tokens:
            score = -float(row["fts_rank"] or 0.0)
        else:
            score = 1.0 - (position / total_rows)

        result.append(
            SearchItem(
                id=row["id"],
                provider=row["provider"],
                title=row["title"],
                url=row["url"],
                thumbnail=row["thumbnail"],
                duration_seconds=row["duration_seconds"],
                quality=row["quality"],
                tags=json.loads(row["tags_json"] or "[]"),
                score=score,
            )
        )
    return result
