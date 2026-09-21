from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.content_reclassify import content_class_stats, reclassify_content
from backend.index import initialize


def _seed(db: Path) -> None:
    initialize(db)
    with sqlite3.connect(db) as conn:
        rows = [
            ("a", "xcafe", "A", "https://example.com/a", '["homemade"]', None, "unknown", "none", 1),
            ("c", "xcafe", "C", "https://example.com/c", '["homemade","professional"]', "Studio C", "studio", "studio_label", 1),
            ("n", "xcafe", "N", "https://example.com/n", '["hd"]', None, "studio", "tag_studio", 1),
            ("s", "xcafe", "S", "https://example.com/s", '["production"]', None, "unknown", "none", 1),
            ("l", "xcafe", "L", "https://example.com/l", '["hd"]', "Label Studio", "unknown", "none", 1),
            ("z", "xcafe", "Z", "https://example.com/z", '["homemade"]', None, "unknown", "none", 0),
        ]
        conn.executemany(
            """
            INSERT INTO items(
                id,provider,title,url,tags_json,studio,content_class,content_class_source,active
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        conn.executemany(
            "INSERT INTO items_fts(id,title,tags,provider) VALUES(?,?,?,?)",
            [(r[0], r[2], "", r[1]) for r in rows],
        )
        conn.execute(
            "INSERT INTO provider_state(provider,state_key,state_value) VALUES('xcafe','backfill_cursor','123')"
        )


def _row_snapshot(db: Path):
    with sqlite3.connect(db) as conn:
        return conn.execute(
            """
            SELECT id, content_class, content_class_source, indexed_at
            FROM items ORDER BY id
            """
        ).fetchall()


def _fts_snapshot(db: Path):
    with sqlite3.connect(db) as conn:
        return conn.execute(
            "SELECT id,title,tags,provider FROM items_fts ORDER BY id"
        ).fetchall()


def test_dry_run_predicts_changes_without_writing(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    _seed(db)
    before = _row_snapshot(db)
    report = reclassify_content(path=db, batch_size=2, apply=False)

    assert report.scanned == 5
    assert report.changed == 4
    assert report.conflicts == 1
    assert report.before == {"amateur": 0, "studio": 2, "unknown": 3}
    assert report.after == {"amateur": 1, "studio": 1, "unknown": 3}
    assert report.sources == {
        "conflict": 1,
        "none": 2,
        "studio_label": 1,
        "tag_amateur": 1,
    }
    assert report.complete is True
    assert report.next_after_id is None
    assert _row_snapshot(db) == before


def test_apply_is_idempotent_and_preserves_fts_and_provider_state(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    _seed(db)
    fts_before = _fts_snapshot(db)

    first = reclassify_content(path=db, batch_size=2, apply=True)
    second = reclassify_content(path=db, batch_size=2, apply=True)

    assert first.changed == 4
    assert second.changed == 0
    assert _fts_snapshot(db) == fts_before
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT state_value FROM provider_state WHERE provider='xcafe' AND state_key='backfill_cursor'"
        ).fetchone() == ("123",)
        assert conn.execute(
            "SELECT content_class,content_class_source FROM items WHERE id='a'"
        ).fetchone() == ("amateur", "tag_amateur")
        assert conn.execute(
            "SELECT content_class,content_class_source FROM items WHERE id='c'"
        ).fetchone() == ("unknown", "conflict")


def test_bounded_resume_does_not_skip_or_repeat_rows(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    _seed(db)

    first = reclassify_content(path=db, batch_size=2, apply=True, max_rows=2)
    assert first.scanned == 2
    assert first.complete is False
    assert first.next_after_id is not None

    second = reclassify_content(
        path=db,
        batch_size=2,
        apply=True,
        after_id=first.next_after_id,
    )
    assert second.scanned == 3
    assert second.complete is True
    assert second.next_after_id is None

    with sqlite3.connect(db) as conn:
        active = conn.execute(
            "SELECT id,content_class,content_class_source FROM items WHERE active=1 ORDER BY id"
        ).fetchall()
    assert active == [
        ("a", "amateur", "tag_amateur"),
        ("c", "unknown", "conflict"),
        ("l", "studio", "studio_label"),
        ("n", "unknown", "none"),
        ("s", "unknown", "none"),
    ]


def test_content_class_stats_reconcile_active_rows(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    _seed(db)
    reclassify_content(path=db, batch_size=10, apply=True)

    stats = content_class_stats(path=db)
    assert stats.total == 5
    assert stats.class_counts == {"amateur": 1, "studio": 1, "unknown": 3}
    assert sum(stats.class_counts.values()) == stats.total
    assert stats.source_counts["conflict"] == 1
    assert stats.conflicts == 1
    assert stats.providers["xcafe"] == {
        "total": 5,
        "amateur": 1,
        "studio": 1,
        "unknown": 3,
        "none_source": 2,
    }
