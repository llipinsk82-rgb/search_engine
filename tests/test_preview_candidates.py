from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

from backend.index import (
    initialize,
    list_preview_enrichment_candidates,
    record_preview_enrichment_attempt,
)


def _insert(db, item_id, provider="tube8", url=None, preview=None, active=1):
    initialize(db)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO items(id,provider,title,url,preview_url,active) VALUES(?,?,?,?,?,?)",
            (item_id, provider, item_id, url or f"https://example.com/{item_id}", preview, active),
        )


def test_preview_candidate_filters_active_https_provider_and_existing_preview(tmp_path):
    db = tmp_path / "candidates.db"
    _insert(db, "ok")
    _insert(db, "has", preview="https://ev-ph.t8cdn.com/p.mp4")
    _insert(db, "inactive", active=0)
    _insert(db, "http", url="http://example.com/http")
    _insert(db, "other", provider="other")
    now = datetime(2026, 9, 21, tzinfo=timezone.utc)
    rows = list_preview_enrichment_candidates({"tube8"}, limit=20, now=now, path=db)
    assert [row.item.id for row in rows] == ["ok"]


def test_preview_candidate_respects_retry_time_and_failure_count(tmp_path):
    db = tmp_path / "retry.db"
    _insert(db, "p1")
    now = datetime(2026, 9, 21, tzinfo=timezone.utc)
    record_preview_enrichment_attempt(
        "p1", provider="tube8", status="failure", failure_count=2,
        last_attempt_at=now, next_attempt_at=now + timedelta(hours=6), path=db,
    )
    assert list_preview_enrichment_candidates({"tube8"}, limit=10, now=now, path=db) == []
    rows = list_preview_enrichment_candidates(
        {"tube8"}, limit=10, now=now + timedelta(hours=6), path=db
    )
    assert len(rows) == 1
    assert rows[0].item.id == "p1"
    assert rows[0].failure_count == 2
