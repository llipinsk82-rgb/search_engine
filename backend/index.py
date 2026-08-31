from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from backend.models import SearchItem
from backend.settings import DB_PATH

_token_re = re.compile(r"\w+", re.UNICODE)


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


def upsert_items(items: list[SearchItem], path: Path = DB_PATH) -> int:
    initialize(path)
    with _connect(path) as conn:
        for item in items:
            tags_json = json.dumps(item.tags, ensure_ascii=False)
            conn.execute(
                """
                INSERT INTO items (
                    id, provider, title, url, thumbnail, duration_seconds,
                    quality, tags_json, indexed_at, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
                ON CONFLICT(id) DO UPDATE SET
                    provider=excluded.provider,
                    title=excluded.title,
                    url=excluded.url,
                    thumbnail=excluded.thumbnail,
                    duration_seconds=excluded.duration_seconds,
                    quality=excluded.quality,
                    tags_json=excluded.tags_json,
                    indexed_at=CURRENT_TIMESTAMP,
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
                ),
            )
            conn.execute("DELETE FROM items_fts WHERE id = ?", (item.id,))
            conn.execute(
                "INSERT INTO items_fts (id, title, tags, provider) VALUES (?, ?, ?, ?)",
                (item.id, item.title, " ".join(item.tags), item.provider),
            )
    return len(items)


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
    order = "i.indexed_at DESC"

    tokens = _token_re.findall(query.lower())
    if tokens:
        fts_query = " ".join(f'"{token}"' for token in tokens)
        joins = "JOIN items_fts ON items_fts.id = i.id"
        where.append("items_fts MATCH ?")
        params.append(fts_query)
        order = "bm25(items_fts) ASC"

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
            i.duration_seconds, i.quality, i.tags_json
        FROM items i
        {joins}
        WHERE {' AND '.join(where)}
        ORDER BY {order}
        LIMIT ?
    """
    params.append(limit * 3)

    with _connect(path) as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        SearchItem(
            id=row["id"],
            provider=row["provider"],
            title=row["title"],
            url=row["url"],
            thumbnail=row["thumbnail"],
            duration_seconds=row["duration_seconds"],
            quality=row["quality"],
            tags=json.loads(row["tags_json"] or "[]"),
            score=1.0,
        )
        for row in rows
    ]
