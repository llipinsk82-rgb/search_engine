from __future__ import annotations

import json
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from backend.content_class import classify_content_evidence
from backend.models import SearchItem, SortMode
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
                    published_at TEXT,
                    views INTEGER,
                    rating_percent REAL,
                    rating_count INTEGER,
                    quality TEXT,
                    content_class TEXT NOT NULL DEFAULT 'unknown',
                    content_class_source TEXT NOT NULL DEFAULT 'none',
                    studio TEXT,
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

                CREATE TABLE IF NOT EXISTS content_enrichment_state (
                    item_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    last_attempt_at TEXT NOT NULL,
                    next_attempt_at TEXT
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
                "published_at": "TEXT",
                "views": "INTEGER",
                "rating_percent": "REAL",
                "rating_count": "INTEGER",
                "content_class": "TEXT NOT NULL DEFAULT 'unknown'",
                "content_class_source": "TEXT NOT NULL DEFAULT 'none'",
                "studio": "TEXT",
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

            # Schema indexes are also migrations: do not make every uvicorn worker
            # contend on CREATE INDEX against a large production database.
            index_key = "migration:indexes_v1"
            indexes_done = conn.execute(
                "SELECT 1 FROM provider_state WHERE provider = ? AND state_key = ?",
                ("__system__", index_key),
            ).fetchone()
            if indexes_done is None:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_source_order ON items(source_order)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_age_check ON items(age_check_status)")
                conn.execute(
                    "INSERT OR REPLACE INTO provider_state(provider,state_key,state_value,updated_at) VALUES(?,?, 'done', CURRENT_TIMESTAMP)",
                    ("__system__", index_key),
                )

            metadata_index_key = "migration:metadata_sort_indexes_v1"
            metadata_indexes_done = conn.execute(
                "SELECT 1 FROM provider_state WHERE provider = ? AND state_key = ?",
                ("__system__", metadata_index_key),
            ).fetchone()
            if metadata_indexes_done is None:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_published_at ON items(published_at)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_views ON items(views)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_rating_percent ON items(rating_percent)")
                conn.execute(
                    "INSERT OR REPLACE INTO provider_state(provider,state_key,state_value,updated_at) VALUES(?,?, 'done', CURRENT_TIMESTAMP)",
                    ("__system__", metadata_index_key),
                )

            content_class_index_key = "migration:content_class_index_v1"
            content_class_index_done = conn.execute(
                "SELECT 1 FROM provider_state WHERE provider = ? AND state_key = ?",
                ("__system__", content_class_index_key),
            ).fetchone()
            if content_class_index_done is None:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_content_class ON items(content_class)")
                conn.execute(
                    "INSERT OR REPLACE INTO provider_state(provider,state_key,state_value,updated_at) VALUES(?,?, 'done', CURRENT_TIMESTAMP)",
                    ("__system__", content_class_index_key),
                )

            content_enrichment_index_key = "migration:content_enrichment_index_v1"
            content_enrichment_index_done = conn.execute(
                "SELECT 1 FROM provider_state WHERE provider = ? AND state_key = ?",
                ("__system__", content_enrichment_index_key),
            ).fetchone()
            if content_enrichment_index_done is None:
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_content_enrichment_next_attempt "
                    "ON content_enrichment_state(next_attempt_at)"
                )
                conn.execute(
                    "INSERT OR REPLACE INTO provider_state(provider,state_key,state_value,updated_at) "
                    "VALUES(?,?, 'done', CURRENT_TIMESTAMP)",
                    ("__system__", content_enrichment_index_key),
                )

            # Older indexed Beeg rows used /-0/<id>, while the accepted public
            # route is /-0<id>. Run the data migration once instead of scanning
            # the full production index on every API worker startup.
            migration_key = "migration:beeg_url_dash0_v1"
            migrated = conn.execute(
                "SELECT 1 FROM provider_state WHERE provider = ? AND state_key = ?",
                ("__system__", migration_key),
            ).fetchone()
            if migrated is None:
                conn.execute(
                    """
                    UPDATE items
                    SET url = REPLACE(url, 'https://beeg.com/-0/', 'https://beeg.com/-0')
                    WHERE provider = 'beeg'
                      AND url LIKE 'https://beeg.com/-0/%'
                    """
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO provider_state(provider, state_key, state_value, updated_at)
                    VALUES (?, ?, 'done', CURRENT_TIMESTAMP)
                    """,
                    ("__system__", migration_key),
                )
        _initialized_paths.add(key)


def _upsert_item_row(
    conn: sqlite3.Connection,
    item: SearchItem,
    *,
    source_order: int = 0,
) -> None:
    tags_json = json.dumps(item.tags, ensure_ascii=False)
    classification = classify_content_evidence(tags=item.tags, studio=item.studio)
    content_class = classification.content_class
    content_class_source = classification.source
    conn.execute(
        """
        INSERT INTO items (
            id, provider, title, url, thumbnail, preview_url, duration_seconds,
            published_at, views, rating_percent, rating_count, quality,
            content_class, content_class_source, studio, age_check_status, tags_json, indexed_at, source_order, active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, 1)
        ON CONFLICT(id) DO UPDATE SET
            provider=excluded.provider,
            title=excluded.title,
            url=excluded.url,
            thumbnail=excluded.thumbnail,
            preview_url=COALESCE(excluded.preview_url, items.preview_url),
            duration_seconds=excluded.duration_seconds,
            published_at=excluded.published_at,
            views=excluded.views,
            rating_percent=excluded.rating_percent,
            rating_count=excluded.rating_count,
            quality=excluded.quality,
            content_class=excluded.content_class,
            content_class_source=excluded.content_class_source,
            studio=excluded.studio,
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
            item.published_at.astimezone(timezone.utc).isoformat() if item.published_at is not None else None,
            item.views,
            item.rating_percent,
            item.rating_count,
            item.quality,
            content_class,
            content_class_source,
            item.studio,
            item.age_check_status,
            tags_json,
            max(0, int(source_order)),
        ),
    )


def _refresh_fts_items(conn: sqlite3.Connection, items: list[SearchItem]) -> None:
    # FTS5 cannot use a normal B-tree index for the UNINDEXED id column. Deleting
    # each id separately therefore scans the virtual table once per item. Collapse
    # the refresh into bounded IN() batches so a provider sync scans FTS once per
    # chunk instead of once per record. Last duplicate id wins, matching UPSERT.
    latest = {item.id: item for item in items}
    if not latest:
        return
    ids = list(latest)
    chunk_size = 500
    for offset in range(0, len(ids), chunk_size):
        chunk = ids[offset : offset + chunk_size]
        placeholders = ",".join("?" for _ in chunk)
        conn.execute(
            f"DELETE FROM items_fts WHERE id IN ({placeholders})",
            chunk,
        )
    conn.executemany(
        "INSERT INTO items_fts (id, title, tags, provider) VALUES (?, ?, ?, ?)",
        [
            (item.id, item.title, " ".join(item.tags), item.provider)
            for item in latest.values()
        ],
    )


def _write_items(
    conn: sqlite3.Connection,
    entries: list[tuple[SearchItem, int]],
) -> None:
    for item, source_order in entries:
        _upsert_item_row(conn, item, source_order=source_order)
    _refresh_fts_items(conn, [item for item, _ in entries])



def upsert_items(items: list[SearchItem], path: Path = DB_PATH) -> int:
    initialize(path)
    with _connect(path) as conn:
        _write_items(
            conn,
            [(item, source_order) for source_order, item in enumerate(items)],
        )
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
        entries: list[tuple[SearchItem, int]] = []
        for provider, items in pairs:
            for source_order, item in enumerate(items):
                if item.provider != provider:
                    continue
                entries.append((item, source_order))
                written += 1
        _write_items(conn, entries)
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
        _write_items(
            conn,
            [(item, source_order) for source_order, item in enumerate(items)],
        )
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
        _write_items(
            conn,
            [(item, source_order) for source_order, item in enumerate(items)],
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
    content_class: str | None,
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
    if content_class:
        where.append("i.content_class = ?")
        params.append(content_class)
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
    content_class: str | None = None,
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
        content_class=content_class,
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
                   duration_seconds, published_at, views, rating_percent, rating_count,
                   quality, content_class, studio, age_check_status, tags_json
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
        published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
        views=row["views"],
        rating_percent=row["rating_percent"],
        rating_count=row["rating_count"],
        quality=row["quality"],
        tags=json.loads(row["tags_json"] or "[]"),
        content_class=row["content_class"],
        studio=row["studio"],
        age_check_status=row["age_check_status"],
        score=0.0,
    )



@dataclass(frozen=True)
class ContentEnrichmentCandidate:
    item: SearchItem
    failure_count: int = 0


def update_content_evidence(
    item_id: str,
    *,
    tags: list[str],
    studio: str | None,
    path: Path = DB_PATH,
) -> bool:
    initialize(path)
    with _connect(path) as conn:
        row = conn.execute(
            """
            SELECT id, provider, title, url, thumbnail, preview_url,
                   duration_seconds, published_at, views, rating_percent, rating_count,
                   quality, content_class, content_class_source, studio,
                   age_check_status, tags_json, source_order
            FROM items
            WHERE id = ? AND active = 1
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            return False

        current_tags = json.loads(row["tags_json"] or "[]")
        merged_tags = list(dict.fromkeys([*current_tags, *tags]))
        current_studio = row["studio"]
        incoming_studio = (studio or "").strip() or None
        merged_studio = current_studio or incoming_studio
        classification = classify_content_evidence(
            tags=merged_tags,
            studio=merged_studio,
        )

        tags_changed = merged_tags != current_tags
        changed = (
            tags_changed
            or merged_studio != current_studio
            or classification.content_class != row["content_class"]
            or classification.source != row["content_class_source"]
        )
        if not changed:
            return False

        conn.execute(
            """
            UPDATE items
            SET tags_json = ?,
                studio = ?,
                content_class = ?,
                content_class_source = ?,
                indexed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                json.dumps(merged_tags, ensure_ascii=False),
                merged_studio,
                classification.content_class,
                classification.source,
                item_id,
            ),
        )
        if tags_changed:
            conn.execute("DELETE FROM items_fts WHERE id = ?", (item_id,))
            conn.execute(
                "INSERT INTO items_fts(id, title, tags, provider) VALUES (?, ?, ?, ?)",
                (item_id, row["title"], " ".join(merged_tags), row["provider"]),
            )
        return True


def record_content_enrichment_attempt(
    item_id: str,
    *,
    provider: str,
    status: str,
    failure_count: int,
    last_attempt_at: datetime,
    next_attempt_at: datetime | None,
    path: Path = DB_PATH,
) -> None:
    initialize(path)
    last_value = last_attempt_at.astimezone(timezone.utc).isoformat()
    next_value = (
        next_attempt_at.astimezone(timezone.utc).isoformat()
        if next_attempt_at is not None
        else None
    )
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO content_enrichment_state(
                item_id, provider, status, failure_count, last_attempt_at, next_attempt_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                provider=excluded.provider,
                status=excluded.status,
                failure_count=excluded.failure_count,
                last_attempt_at=excluded.last_attempt_at,
                next_attempt_at=excluded.next_attempt_at
            """,
            (
                item_id,
                provider,
                status,
                max(0, int(failure_count)),
                last_value,
                next_value,
            ),
        )


def list_content_enrichment_candidates(
    provider_names: set[str] | list[str] | tuple[str, ...],
    *,
    limit: int,
    now: datetime,
    path: Path = DB_PATH,
) -> list[ContentEnrichmentCandidate]:
    initialize(path)
    names = sorted({name.strip() for name in provider_names if name.strip()})
    if not names or limit < 1:
        return []

    placeholders = ",".join("?" for _ in names)
    now_value = now.astimezone(timezone.utc).isoformat()
    sql = f"""
        SELECT i.id, COALESCE(s.failure_count, 0) AS failure_count
        FROM items i
        LEFT JOIN content_enrichment_state s ON s.item_id = i.id
        WHERE i.active = 1
          AND i.content_class = 'unknown'
          AND i.content_class_source = 'none'
          AND i.url LIKE 'https://%'
          AND i.provider IN ({placeholders})
          AND (s.next_attempt_at IS NULL OR s.next_attempt_at <= ?)
        ORDER BY i.id
        LIMIT ?
    """
    with _connect(path) as conn:
        rows = conn.execute(
            sql,
            [*names, now_value, max(1, int(limit))],
        ).fetchall()

    result: list[ContentEnrichmentCandidate] = []
    for row in rows:
        item = get_item(str(row["id"]), path=path)
        if item is not None:
            result.append(
                ContentEnrichmentCandidate(
                    item=item,
                    failure_count=int(row["failure_count"] or 0),
                )
            )
    return result


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
    content_class: str | None = None,
    age_check: str | None = None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    allowed_providers: set[str] | None = None,
    exclude_ids: set[str] | None = None,
    offset: int = 0,
    limit: int = 40,
    sort: SortMode = "relevance",
    path: Path = DB_PATH,
) -> list[SearchItem]:
    initialize(path)
    where, params, joins, rank_select = _where_for_search(
        query,
        provider=provider,
        allowed_providers=allowed_providers,
        quality=quality,
        content_class=content_class,
        age_check=age_check,
        min_duration=min_duration,
        max_duration=max_duration,
        exclude_ids=exclude_ids,
    )
    tokens = _token_re.findall(query.lower())
    if sort == "relevance":
        order = (
            "fts_rank ASC, i.indexed_at DESC, i.source_order ASC"
            if tokens
            else "i.indexed_at DESC, i.source_order ASC"
        )
    else:
        sort_orders: dict[SortMode, str] = {
            "newest": "(i.published_at IS NULL) ASC, i.published_at DESC, i.indexed_at DESC, i.source_order ASC",
            "views": "(i.views IS NULL) ASC, i.views DESC, i.indexed_at DESC, i.source_order ASC",
            "rating": "(i.rating_percent IS NULL) ASC, i.rating_percent DESC, (i.rating_count IS NULL) ASC, i.rating_count DESC, i.indexed_at DESC, i.source_order ASC",
            "longest": "(i.duration_seconds IS NULL) ASC, i.duration_seconds DESC, i.indexed_at DESC, i.source_order ASC",
            "shortest": "(i.duration_seconds IS NULL) ASC, i.duration_seconds ASC, i.indexed_at DESC, i.source_order ASC",
        }
        order = sort_orders[sort]
    sql = f"""
        SELECT
            i.id, i.provider, i.title, i.url, i.thumbnail, i.preview_url,
            i.duration_seconds, i.published_at, i.views, i.rating_percent, i.rating_count,
            i.quality, i.content_class, i.studio, i.age_check_status, i.tags_json,
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
                published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
                views=row["views"],
                rating_percent=row["rating_percent"],
                rating_count=row["rating_count"],
                quality=row["quality"],
                tags=json.loads(row["tags_json"] or "[]"),
                content_class=row["content_class"],
                studio=row["studio"],
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
