from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from backend.content_class import classify_content_evidence
from backend.index import initialize
from backend.settings import DB_PATH


_CLASS_KEYS = ("amateur", "studio", "unknown")


@dataclass(frozen=True)
class ReclassifyReport:
    scanned: int
    changed: int
    conflicts: int
    before: dict[str, int]
    after: dict[str, int]
    sources: dict[str, int]
    next_after_id: str | None
    complete: bool


@dataclass(frozen=True)
class ContentClassStats:
    total: int
    class_counts: dict[str, int]
    percentages: dict[str, float]
    source_counts: dict[str, int]
    conflicts: int
    providers: dict[str, dict[str, int]]


def _class_counts() -> dict[str, int]:
    return {key: 0 for key in _CLASS_KEYS}


def reclassify_content(
    *,
    path: Path = DB_PATH,
    batch_size: int = 5000,
    apply: bool = False,
    after_id: str | None = None,
    max_rows: int | None = None,
) -> ReclassifyReport:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if max_rows is not None and max_rows < 1:
        raise ValueError("max_rows must be positive")

    initialize(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    before = _class_counts()
    after = _class_counts()
    sources: Counter[str] = Counter()
    scanned = 0
    changed = 0
    conflicts = 0
    cursor = after_id or ""
    complete = True
    next_after_id: str | None = None

    try:
        while True:
            remaining = None if max_rows is None else max_rows - scanned
            if remaining is not None and remaining <= 0:
                more = conn.execute(
                    "SELECT 1 FROM items WHERE active = 1 AND id > ? LIMIT 1",
                    (cursor,),
                ).fetchone()
                complete = more is None
                next_after_id = None if complete else cursor
                break

            limit = batch_size if remaining is None else min(batch_size, remaining)
            rows = conn.execute(
                """
                SELECT id, tags_json, studio, content_class, content_class_source
                FROM items
                WHERE active = 1 AND id > ?
                ORDER BY id
                LIMIT ?
                """,
                (cursor, limit),
            ).fetchall()
            if not rows:
                complete = True
                next_after_id = None
                break

            updates: list[tuple[str, str, str]] = []
            for row in rows:
                stored_class = str(row["content_class"])
                before.setdefault(stored_class, 0)
                before[stored_class] += 1

                tags = json.loads(row["tags_json"] or "[]")
                classification = classify_content_evidence(
                    tags=list(tags),
                    studio=row["studio"],
                )
                after[classification.content_class] += 1
                sources[classification.source] += 1
                if classification.source == "conflict":
                    conflicts += 1

                if (
                    classification.content_class != stored_class
                    or classification.source != str(row["content_class_source"])
                ):
                    changed += 1
                    if apply:
                        updates.append(
                            (
                                classification.content_class,
                                classification.source,
                                str(row["id"]),
                            )
                        )

            if apply and updates:
                conn.executemany(
                    """
                    UPDATE items
                    SET content_class = ?, content_class_source = ?
                    WHERE id = ?
                    """,
                    updates,
                )
                conn.commit()

            scanned += len(rows)
            cursor = str(rows[-1]["id"])

            if max_rows is not None and scanned >= max_rows:
                more = conn.execute(
                    "SELECT 1 FROM items WHERE active = 1 AND id > ? LIMIT 1",
                    (cursor,),
                ).fetchone()
                complete = more is None
                next_after_id = None if complete else cursor
                break

            if len(rows) < limit:
                complete = True
                next_after_id = None
                break
    finally:
        conn.close()

    return ReclassifyReport(
        scanned=scanned,
        changed=changed,
        conflicts=conflicts,
        before=before,
        after=after,
        sources=dict(sorted(sources.items())),
        next_after_id=next_after_id,
        complete=complete,
    )


def content_class_stats(path: Path = DB_PATH) -> ContentClassStats:
    initialize(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        total = int(
            conn.execute("SELECT COUNT(*) AS n FROM items WHERE active = 1").fetchone()["n"]
        )

        class_counts = _class_counts()
        for row in conn.execute(
            """
            SELECT content_class, COUNT(*) AS n
            FROM items
            WHERE active = 1
            GROUP BY content_class
            """
        ):
            class_counts[str(row["content_class"])] = int(row["n"])

        source_counts = {
            str(row["content_class_source"]): int(row["n"])
            for row in conn.execute(
                """
                SELECT content_class_source, COUNT(*) AS n
                FROM items
                WHERE active = 1
                GROUP BY content_class_source
                ORDER BY content_class_source
                """
            )
        }

        providers: dict[str, dict[str, int]] = {}
        for row in conn.execute(
            """
            SELECT
                provider,
                COUNT(*) AS total,
                SUM(CASE WHEN content_class = 'amateur' THEN 1 ELSE 0 END) AS amateur,
                SUM(CASE WHEN content_class = 'studio' THEN 1 ELSE 0 END) AS studio,
                SUM(CASE WHEN content_class = 'unknown' THEN 1 ELSE 0 END) AS unknown,
                SUM(CASE WHEN content_class_source = 'none' THEN 1 ELSE 0 END) AS none_source
            FROM items
            WHERE active = 1
            GROUP BY provider
            ORDER BY provider
            """
        ):
            providers[str(row["provider"])] = {
                "total": int(row["total"]),
                "amateur": int(row["amateur"] or 0),
                "studio": int(row["studio"] or 0),
                "unknown": int(row["unknown"] or 0),
                "none_source": int(row["none_source"] or 0),
            }
    finally:
        conn.close()

    percentages = {
        key: (round((count * 100.0) / total, 2) if total else 0.0)
        for key, count in class_counts.items()
    }
    return ContentClassStats(
        total=total,
        class_counts=class_counts,
        percentages=percentages,
        source_counts=source_counts,
        conflicts=source_counts.get("conflict", 0),
        providers=providers,
    )
