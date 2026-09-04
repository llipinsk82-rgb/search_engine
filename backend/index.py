from __future__ import annotations

import json
import re
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

from backend.models import SearchItem
from backend.settings import DB_PATH

_token_re = re.compile(r"\w+", re.UNICODE)
_initialized_paths: set[str] = set()
_initialize_lock = threading.Lock()


@dataclass(frozen=True)
class ProviderSyncStats:
    provider: str
    fetched: int
    active_before: int
    active_after: int
    deactivated: int


def _connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def initialize(path: Path = DB_PATH) -> None:
    key = str(path.resolve())
    if key in _initialized_paths:
        return
    with _initialize_lock:
        if key in _initialized_paths:
            return
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
                    preview_url TEXT,
                    duration_seconds INTEGER,
                    quality TEXT,
                    age_check_status TEXT NOT NULL DEFAULT 'unknown',
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

                CREATE TABLE IF NOT EXISTS provider_state (
                    provider TEXT NOT NULL,
                    state_key TEXT NOT NULL,
                    state_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (provider, state_key)
                );
                """
            )
            columns = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(items)").fetchall()
            }
            additions = {
                "source_order": "INTEGER NOT NULL DEFAULT 0",
                "preview_url": "TEXT",
                "age_check_status": "TEXT NOT NULL DEFAULT 'unknown'",
            }
            for name, ddl in additions.items():
                if name in columns:
                    continue
                try:
                    conn.execute(f"ALTER TABLE items ADD COLUMN {name} {ddl}")
                except sqlite3.OperationalError:
                    current = {
                        str(row["name"])
                        for row in conn.execute("PRAGMA table_info(items)").fetchall()
                    }
                    if name not in current:
                        raise

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_items_source_order ON items(source_order)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_items_age_check ON items(age_check_status)"
            )

            # Older indexed Beeg rows used /-0/<id>, while the accepted public
            # route is /-0<id>. This migration is idempotent and URL-only.
            conn.execute(
                """
                UPDATE items
                SET url = REPLACE(url, 'https://beeg.com/-0/', 'https://beeg.com/-0')
                WHERE provider = 'beeg'
                  AND url LIKE 'https://beeg.com/-0/%'
                """
            )
        _initialized_paths.add(key)


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
            id, provider, title, url, thumbnail, preview_url, duration_seconds,
            quality, age_check_status, tags_json, indexed_at, source_order, active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, 1)
        ON CONFLICT(id) DO UPDATE SET
            provider=excluded.provider,
            title=excluded.title,
            url=excluded.url,
            thumbnail=excluded.thumbnail,
            preview_url=COALESCE(excluded.preview_url, items.preview_url),
            duration_seconds=excluded.duration_seconds,
            quality=excluded.quality,
            age_check_status=CASE
                WHEN excluded.age_check_status = 'unknown'
                    THEN items.age_check_status
                ELSE excluded.age_check_status
            END,
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
            str(item.preview_url) if item.preview_url else None,
            item.duration_seconds,
            item.quality,
            item.age_check_status,
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


def merge_provider_batches(
    batches,
    *,
    path: Path = DB_PATH,
) -> int:
    """Merge several live-provider batches in one transaction.

    Historical callers pass a list of (provider, items) pairs. A mapping is
    accepted too for recovery compatibility.
    """
    initialize(path)
    pairs = batches.items() if isinstance(batches, dict) else batches
    written = 0
    with _connect(path) as conn:
        for provider, items in pairs:
            for source_order, item in enumerate(items):
                if item.provider != provider:
                    continue
                _write_item(conn, item, source_order=source_order)
                written += 1
    return written


def merge_provider_items(
    provider: str,
    items: list[SearchItem],
    *,
    allow_empty: bool = False,
    path: Path = DB_PATH,
) -> ProviderSyncStats:
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
        active_before = int(
            conn.execute(
                "SELECT COUNT(*) AS n FROM items WHERE provider = ? AND active = 1",
                (provider,),
            ).fetchone()["n"]
        )
        for source_order, item in enumerate(items):
            _write_item(conn, item, source_order=source_order)
        active_after = int(
            conn.execute(
                "SELECT COUNT(*) AS n FROM items WHERE provider = ? AND active = 1",
                (provider,),
            ).fetchone()["n"]
        )
    return ProviderSyncStats(provider, len(items), active_before, active_after, 0)


def replace_provider_items(
    provider: str,
    items: list[SearchItem],
    *,
    allow_empty: bool = False,
    path: Path = DB_PATH,
) -> ProviderSyncStats:
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
            "SELECT id FROM items WHERE provider = ? AND active = 1", (provider,)
        ).fetchall()
        previous_ids = {str(row["id"]) for row in rows}
        incoming_ids = {item.id for item in items}
        conn.execute(
            "UPDATE items SET active = 0 WHERE provider = ? AND active = 1", (provider,)
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
        active_after = int(
            conn.execute(
                "SELECT COUNT(*) AS n FROM items WHERE provider = ? AND active = 1",
                (provider,),
            ).fetchone()["n"]
        )
    return ProviderSyncStats(
        provider,
        len(items),
        len(previous_ids),
        active_after,
        len(previous_ids - incoming_ids),
    )


def deactivate_provider(provider: str, path: Path = DB_PATH) -> int:
    initialize(path)
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT id FROM items WHERE provider = ? AND active = 1", (provider,)
        ).fetchall()
        ids = [str(row["id"]) for row in rows]
        if not ids:
            return 0
        conn.execute(
            "UPDATE items SET active = 0 WHERE provider = ? AND active = 1", (provider,)
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


def _where_for_search(
    query: str,
    *,
    provider: str | None,
    allowed_providers: set[str] | None,
    quality: str | None,
    age_check: str | None,
    min_duration: int | None,
    max_duration: int | None,
    exclude_ids: set[str] | None = None,
) -> tuple[str, list[object], str, str]:
    where = ["i.active = 1"]
    params: list[object] = []
    joins = ""
    rank_select = "0.0 AS fts_rank"
    tokens = _token_re.findall(query.lower())
    if tokens:
        fts_query = " ".join(f'"{token}"' for token in tokens)
        joins = "JOIN items_fts ON items_fts.id = i.id"
        where.append("items_fts MATCH ?")
        params.append(fts_query)
        rank_select = "bm25(items_fts, 0.0, 8.0, 2.0, 0.0) AS fts_rank"

    if provider:
        where.append("i.provider = ?")
        params.append(provider)
    elif allowed_providers is not None:
        names = sorted(allowed_providers)
        if not names:
            where.append("1 = 0")
        else:
            where.append("i.provider IN (" + ",".join("?" for _ in names) + ")")
            params.extend(names)

    if quality:
        where.append("LOWER(COALESCE(i.quality, '')) = LOWER(?)")
        params.append(quality)
    if age_check:
        where.append("i.age_check_status = ?")
        params.append(age_check)
    if min_duration is not None:
        where.append("COALESCE(i.duration_seconds, 0) >= ?")
        params.append(min_duration)
    if max_duration is not None:
        where.append("i.duration_seconds IS NOT NULL AND i.duration_seconds <= ?")
        params.append(max_duration)
    if exclude_ids:
        ids = sorted(exclude_ids)[:800]
        where.append("i.id NOT IN (" + ",".join("?" for _ in ids) + ")")
        params.extend(ids)
    return " AND ".join(where), params, joins, rank_select


def count_search_items(
    query: str,
    *,
    provider: str | None = None,
    quality: str | None = None,
    age_check: str | None = None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    allowed_providers: set[str] | None = None,
    path: Path = DB_PATH,
) -> int:
    initialize(path)
    where, params, joins, _ = _where_for_search(
        query,
        provider=provider,
        allowed_providers=allowed_providers,
        quality=quality,
        age_check=age_check,
        min_duration=min_duration,
        max_duration=max_duration,
    )
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM items i " + joins + " WHERE " + where, params
        ).fetchone()
        return int(row["n"])


def get_item(item_id: str, path: Path = DB_PATH) -> SearchItem | None:
    initialize(path)
    with _connect(path) as conn:
        row = conn.execute(
            """
            SELECT id, provider, title, url, thumbnail, preview_url,
                   duration_seconds, quality, age_check_status, tags_json
            FROM items WHERE id = ? AND active = 1
            """,
            (item_id,),
        ).fetchone()
    if row is None:
        return None
    return SearchItem(
        id=row["id"],
        provider=row["provider"],
        title=row["title"],
        url=row["url"],
        thumbnail=row["thumbnail"],
        preview_url=row["preview_url"],
        duration_seconds=row["duration_seconds"],
        quality=row["quality"],
        tags=json.loads(row["tags_json"] or "[]"),
        age_check_status=row["age_check_status"],
        score=0.0,
    )


def update_item_thumbnail(
    item_id: str,
    thumbnail: str,
    *,
    path: Path = DB_PATH,
) -> bool:
    initialize(path)
    with _connect(path) as conn:
        cursor = conn.execute(
            "UPDATE items SET thumbnail = ? WHERE id = ? AND active = 1",
            (thumbnail, item_id),
        )
        return cursor.rowcount == 1


def search_items(
    query: str,
    *,
    provider: str | None = None,
    quality: str | None = None,
    age_check: str | None = None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    allowed_providers: set[str] | None = None,
    exclude_ids: set[str] | None = None,
    offset: int = 0,
    limit: int = 40,
    path: Path = DB_PATH,
) -> list[SearchItem]:
    initialize(path)
    where, params, joins, rank_select = _where_for_search(
        query,
        provider=provider,
        allowed_providers=allowed_providers,
        quality=quality,
        age_check=age_check,
        min_duration=min_duration,
        max_duration=max_duration,
        exclude_ids=exclude_ids,
    )
    tokens = _token_re.findall(query.lower())
    order = (
        "fts_rank ASC, i.indexed_at DESC, i.source_order ASC"
        if tokens
        else "i.indexed_at DESC, i.source_order ASC"
    )
    sql = f"""
        SELECT
            i.id, i.provider, i.title, i.url, i.thumbnail, i.preview_url,
            i.duration_seconds, i.quality, i.age_check_status, i.tags_json,
            {rank_select}
        FROM items i
        {joins}
        WHERE {where}
        ORDER BY {order}
        LIMIT ? OFFSET ?
    """
    params.extend((max(1, int(limit)), max(0, int(offset))))
    with _connect(path) as conn:
        rows = conn.execute(sql, params).fetchall()

    result: list[SearchItem] = []
    total_rows = max(1, len(rows))
    for position, row in enumerate(rows):
        score = (
            -float(row["fts_rank"] or 0.0)
            if tokens
            else 1.0 - (position / total_rows)
        )
        result.append(
            SearchItem(
                id=row["id"],
                provider=row["provider"],
                title=row["title"],
                url=row["url"],
                thumbnail=row["thumbnail"],
                preview_url=row["preview_url"],
                duration_seconds=row["duration_seconds"],
                quality=row["quality"],
                tags=json.loads(row["tags_json"] or "[]"),
                age_check_status=row["age_check_status"],
                score=score,
            )
        )
    return result


def get_provider_state(
    provider: str,
    state_key: str,
    *,
    path: Path = DB_PATH,
) -> str | None:
    initialize(path)
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT state_value FROM provider_state WHERE provider = ? AND state_key = ?",
            (provider, state_key),
        ).fetchone()
        return None if row is None else str(row["state_value"])


def set_provider_state(
    provider: str,
    state_key: str,
    state_value: str,
    *,
    path: Path = DB_PATH,
) -> None:
    initialize(path)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO provider_state (provider, state_key, state_value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(provider, state_key) DO UPDATE SET
                state_value=excluded.state_value,
                updated_at=CURRENT_TIMESTAMP
            """,
            (provider, state_key, state_value),
        )


def delete_provider_state(
    provider: str,
    state_key: str,
    *,
    path: Path = DB_PATH,
) -> None:
    initialize(path)
    with _connect(path) as conn:
        conn.execute(
            "DELETE FROM provider_state WHERE provider = ? AND state_key = ?",
            (provider, state_key),
        )
