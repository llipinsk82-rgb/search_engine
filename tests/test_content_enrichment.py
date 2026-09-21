from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend import content_enrichment
from backend.content_enrichment import enrich_unknown_content
from backend.index import (
    get_item,
    initialize,
    record_content_enrichment_attempt,
    upsert_items,
)
from backend.models import SearchItem


NOW = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)


class FakeProvider:
    def __init__(self, name: str, *, tags=None, studio=None, error: Exception | None = None, enabled=True):
        self.name = name
        self.content_class_enrichment = enabled
        self.tags = list(tags or [])
        self.studio = studio
        self.error = error
        self.calls: list[str] = []

    async def enrich_content_evidence(self, item: SearchItem) -> SearchItem:
        self.calls.append(item.id)
        if self.error is not None:
            raise self.error
        return item.model_copy(
            update={
                "tags": list(dict.fromkeys([*item.tags, *self.tags])),
                "studio": self.studio or item.studio,
            }
        )


def _seed(db: Path, *rows: tuple[str, str]) -> None:
    items = [
        SearchItem(
            id=item_id,
            provider=provider,
            title=f"title-{item_id}",
            url=f"https://example.com/{item_id}",
            thumbnail=f"https://example.com/{item_id}.jpg",
            preview_url=f"https://example.com/{item_id}.mp4",
            tags=["hd"],
            age_check_status="not_required",
        )
        for item_id, provider in rows
    ]
    upsert_items(items, path=db)


def _state(db: Path, item_id: str):
    with sqlite3.connect(db) as conn:
        return conn.execute(
            """
            SELECT status,failure_count,last_attempt_at,next_attempt_at
            FROM content_enrichment_state WHERE item_id=?
            """,
            (item_id,),
        ).fetchone()


def test_explicit_studio_upgrades_unknown_to_studio(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    _seed(db, ("a", "p"))
    provider = FakeProvider("p", studio="Example Studio")

    report = asyncio.run(
        enrich_unknown_content([provider], batch_size=10, max_seconds=10, path=db, now=NOW)
    )

    item = get_item("a", path=db)
    assert item is not None
    assert item.content_class == "studio"
    assert item.studio == "Example Studio"
    assert report.attempted == 1
    assert report.enriched == 1
    assert report.classified_studio == 1
    assert _state(db, "a")[0] == "success"


def test_explicit_amateur_upgrades_unknown_to_amateur(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    _seed(db, ("a", "p"))
    provider = FakeProvider("p", tags=["homemade"])

    report = asyncio.run(
        enrich_unknown_content([provider], batch_size=10, max_seconds=10, path=db, now=NOW)
    )

    assert get_item("a", path=db).content_class == "amateur"
    assert report.classified_amateur == 1


def test_conflict_stays_unknown_with_conflict_source(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    _seed(db, ("a", "p"))
    provider = FakeProvider("p", tags=["homemade"], studio="Studio")

    report = asyncio.run(
        enrich_unknown_content([provider], batch_size=10, max_seconds=10, path=db, now=NOW)
    )

    item = get_item("a", path=db)
    assert item.content_class == "unknown"
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT content_class_source FROM items WHERE id='a'"
        ).fetchone() == ("conflict",)
    assert report.conflicts == 1
    assert _state(db, "a")[0] == "success"


def test_no_signal_records_thirty_day_backoff(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    _seed(db, ("a", "p"))
    provider = FakeProvider("p")

    report = asyncio.run(
        enrich_unknown_content([provider], batch_size=10, max_seconds=10, path=db, now=NOW)
    )

    state = _state(db, "a")
    assert report.no_signal == 1
    assert state[0] == "no_signal"
    assert state[1] == 0
    assert datetime.fromisoformat(state[3]) == NOW + timedelta(days=30)


def test_failure_is_isolated_and_uses_exponential_backoff(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    _seed(db, ("a", "bad"), ("b", "good"))
    bad = FakeProvider("bad", error=RuntimeError("boom"))
    good = FakeProvider("good", tags=["homemade"])

    report = asyncio.run(
        enrich_unknown_content([bad, good], batch_size=10, max_seconds=10, path=db, now=NOW)
    )

    assert report.attempted == 2
    assert report.failures == 1
    assert report.classified_amateur == 1
    failure = _state(db, "a")
    assert failure[0] == "failure"
    assert failure[1] == 1
    assert datetime.fromisoformat(failure[3]) == NOW + timedelta(hours=6)


def test_failure_backoff_grows_and_is_capped(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    _seed(db, ("a", "p"))
    provider = FakeProvider("p", error=RuntimeError("boom"))
    record_content_enrichment_attempt(
        "a",
        provider="p",
        status="failure",
        failure_count=6,
        last_attempt_at=NOW - timedelta(days=10),
        next_attempt_at=NOW - timedelta(seconds=1),
        path=db,
    )

    asyncio.run(
        enrich_unknown_content([provider], batch_size=10, max_seconds=10, path=db, now=NOW)
    )
    state = _state(db, "a")
    assert state[1] == 7
    assert datetime.fromisoformat(state[3]) == NOW + timedelta(days=7)


def test_future_retry_is_skipped_then_becomes_eligible(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    _seed(db, ("a", "p"))
    provider = FakeProvider("p", tags=["homemade"])
    record_content_enrichment_attempt(
        "a",
        provider="p",
        status="no_signal",
        failure_count=0,
        last_attempt_at=NOW,
        next_attempt_at=NOW + timedelta(days=1),
        path=db,
    )

    first = asyncio.run(
        enrich_unknown_content([provider], batch_size=10, max_seconds=10, path=db, now=NOW)
    )
    assert first.attempted == 0
    assert provider.calls == []

    second = asyncio.run(
        enrich_unknown_content(
            [provider],
            batch_size=10,
            max_seconds=10,
            path=db,
            now=NOW + timedelta(days=2),
        )
    )
    assert second.classified_amateur == 1
    assert provider.calls == ["a"]


def test_provider_without_capability_is_never_called(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    _seed(db, ("a", "p"))
    provider = FakeProvider("p", tags=["homemade"], enabled=False)

    report = asyncio.run(
        enrich_unknown_content([provider], batch_size=10, max_seconds=10, path=db, now=NOW)
    )

    assert report.attempted == 0
    assert provider.calls == []
    assert get_item("a", path=db).content_class == "unknown"


def test_enrichment_preserves_unrelated_fields_and_existing_studio(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    _seed(db, ("a", "p"))
    initialize(db)
    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            UPDATE items
            SET studio='Original Studio', content_class='unknown', content_class_source='none',
                source_order=9
            WHERE id='a'
            """
        )
    provider = FakeProvider("p", tags=["professional"], studio="Replacement Studio")

    asyncio.run(
        enrich_unknown_content([provider], batch_size=10, max_seconds=10, path=db, now=NOW)
    )

    with sqlite3.connect(db) as conn:
        row = conn.execute(
            """
            SELECT title,url,thumbnail,preview_url,age_check_status,source_order,studio,content_class
            FROM items WHERE id='a'
            """
        ).fetchone()
    assert row == (
        "title-a",
        "https://example.com/a",
        "https://example.com/a.jpg",
        "https://example.com/a.mp4",
        "not_required",
        9,
        "Original Studio",
        "studio",
    )


def test_time_budget_stops_before_starting_next_fetch(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "search.db"
    _seed(db, ("a", "p"), ("b", "p"))
    provider = FakeProvider("p", tags=["homemade"])
    ticks = iter([0.0, 0.5, 2.5])
    monkeypatch.setattr(content_enrichment, "monotonic", lambda: next(ticks))

    report = asyncio.run(
        enrich_unknown_content([provider], batch_size=50, max_seconds=2.0, path=db, now=NOW)
    )

    assert report.attempted == 1
    assert provider.calls == ["a"]
    assert get_item("a", path=db).content_class == "amateur"
    assert get_item("b", path=db).content_class == "unknown"


def test_content_enrichment_reuses_fetched_preview_without_second_fetch(tmp_path: Path) -> None:
    db = tmp_path / "reuse.db"
    item = SearchItem(
        id="reuse", provider="bigfuck", title="reuse",
        url="https://bigfuck.tv/video/reuse", tags=["hd"],
    )
    upsert_items([item], path=db)

    class ReuseProvider(FakeProvider):
        preview_enrichment = True
        async def enrich_content_evidence(self, item: SearchItem) -> SearchItem:
            self.calls.append(item.id)
            return item.model_copy(update={
                "tags": [*item.tags, "homemade"],
                "preview_url": "https://icdn05.bigfuck.tv/preview/reuse.mp4",
            })
        async def extract_preview(self, item: SearchItem):
            raise AssertionError("preview-specific second fetch must not run")

    provider = ReuseProvider("bigfuck")
    report = asyncio.run(
        enrich_unknown_content([provider], batch_size=10, max_seconds=10, path=db, now=NOW)
    )
    stored = get_item("reuse", path=db)
    assert provider.calls == ["reuse"]
    assert report.classified_amateur == 1
    assert stored is not None
    assert str(stored.preview_url) == "https://icdn05.bigfuck.tv/preview/reuse.mp4"
