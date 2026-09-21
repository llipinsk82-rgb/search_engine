from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone

from backend import preview_enrichment
from backend.index import (
    initialize,
    record_preview_enrichment_attempt,
)
from backend.models import SearchItem
from backend.preview_enrichment import enrich_missing_previews

NOW = datetime(2026, 9, 21, 2, 0, tzinfo=timezone.utc)


class FakeProvider:
    def __init__(self, name, *, preview=None, error=None, enabled=True):
        self.name = name
        self.preview_enrichment = enabled
        self.preview = preview
        self.error = error
        self.calls = []

    async def extract_preview(self, item):
        self.calls.append(item.id)
        if self.error:
            raise self.error
        return self.preview


def _insert(db, item_id, provider="bigfuck", preview=None):
    initialize(db)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO items(id,provider,title,url,preview_url,active) VALUES(?,?,?,?,?,1)",
            (item_id, provider, item_id, f"https://example.com/{item_id}", preview),
        )


def _state(db, item_id):
    with sqlite3.connect(db) as conn:
        return conn.execute(
            "SELECT status,failure_count,last_attempt_at,next_attempt_at "
            "FROM preview_enrichment_state WHERE item_id=?",
            (item_id,),
        ).fetchone()


def test_allowed_preview_is_stored_and_marked_success(tmp_path):
    db = tmp_path / "e.db"
    _insert(db, "a")
    p = FakeProvider("bigfuck", preview="https://icdn05.bigfuck.tv/preview/a.mp4")
    report = asyncio.run(enrich_missing_previews([p], [], batch_size=10, max_seconds=10, path=db, now=NOW))
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT preview_url FROM items WHERE id='a'").fetchone()[0].endswith("/a.mp4")
    assert (report.attempted, report.extracted, report.stored, report.playable) == (1, 1, 1, 1)
    assert _state(db, "a")[0] == "success"


def test_policy_blocked_preview_is_not_stored(tmp_path):
    db = tmp_path / "e.db"
    _insert(db, "a")
    p = FakeProvider("bigfuck", preview="https://evil.example/a.mp4")
    report = asyncio.run(enrich_missing_previews([p], [], batch_size=10, max_seconds=10, path=db, now=NOW))
    assert report.extracted == 1
    assert report.blocked_policy == 1
    assert _state(db, "a")[0] == "blocked_policy"
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT preview_url FROM items WHERE id='a'").fetchone()[0] is None


def test_no_preview_gets_thirty_day_cooldown(tmp_path):
    db = tmp_path / "e.db"
    _insert(db, "a")
    p = FakeProvider("bigfuck", preview=None)
    report = asyncio.run(enrich_missing_previews([p], [], batch_size=10, max_seconds=10, path=db, now=NOW))
    state = _state(db, "a")
    assert report.no_preview == 1
    assert state[0] == "no_preview"
    assert datetime.fromisoformat(state[3]) == NOW + timedelta(days=30)


def test_failure_is_isolated_and_backoff_is_exponential(tmp_path):
    db = tmp_path / "e.db"
    _insert(db, "a", "bigfuck")
    _insert(db, "b", "hqporn")
    bad = FakeProvider("bigfuck", error=RuntimeError("boom"))
    good = FakeProvider("hqporn", preview="https://icdn05.hqporn.xxx/p.mp4")
    report = asyncio.run(enrich_missing_previews([bad, good], [], batch_size=10, max_seconds=10, path=db, now=NOW))
    assert report.attempted == 2
    assert report.failures == 1
    assert report.stored == 1
    assert datetime.fromisoformat(_state(db, "a")[3]) == NOW + timedelta(hours=6)


def test_failure_backoff_caps_at_seven_days(tmp_path):
    db = tmp_path / "e.db"
    _insert(db, "a")
    record_preview_enrichment_attempt(
        "a", provider="bigfuck", status="failure", failure_count=6,
        last_attempt_at=NOW-timedelta(days=8), next_attempt_at=NOW-timedelta(seconds=1), path=db,
    )
    p = FakeProvider("bigfuck", error=RuntimeError("boom"))
    asyncio.run(enrich_missing_previews([p], [], batch_size=10, max_seconds=10, path=db, now=NOW))
    state = _state(db, "a")
    assert state[1] == 7
    assert datetime.fromisoformat(state[3]) == NOW + timedelta(days=7)


def test_disabled_provider_and_existing_preview_are_not_called(tmp_path):
    db = tmp_path / "e.db"
    _insert(db, "a")
    _insert(db, "b", preview="https://icdn05.bigfuck.tv/p.mp4")
    p = FakeProvider("bigfuck", preview="https://icdn05.bigfuck.tv/new.mp4", enabled=False)
    report = asyncio.run(enrich_missing_previews([p], [], batch_size=10, max_seconds=10, path=db, now=NOW))
    assert report.attempted == 0
    assert p.calls == []


def test_deadline_stops_before_unstarted_candidate(tmp_path, monkeypatch):
    db = tmp_path / "e.db"
    _insert(db, "a")
    _insert(db, "b")
    p = FakeProvider("bigfuck", preview="https://icdn05.bigfuck.tv/p.mp4")
    ticks = iter([0.0, 0.5, 2.5])
    monkeypatch.setattr(preview_enrichment, "monotonic", lambda: next(ticks))
    report = asyncio.run(enrich_missing_previews([p], [], batch_size=10, max_seconds=2, path=db, now=NOW))
    assert report.attempted == 1
    assert p.calls == ["a"]
    assert _state(db, "b") is None
