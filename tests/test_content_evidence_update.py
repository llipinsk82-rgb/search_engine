from pathlib import Path
import sqlite3

from backend.index import get_item, update_content_evidence, upsert_items
from backend.models import SearchItem


def test_update_content_evidence_is_additive_and_preserves_unrelated_fields(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    item = SearchItem(
        id="evidence-1",
        provider="demo",
        title="Original title",
        url="https://example.com/watch/1",
        thumbnail="https://example.com/thumb.jpg",
        preview_url="https://example.com/preview.mp4",
        age_check_status="not_required",
        tags=["hd"],
        score=1.0,
    )
    upsert_items([item], path=db)

    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE items SET source_order=17 WHERE id=?", (item.id,))
        before = conn.execute(
            "SELECT url,title,thumbnail,preview_url,age_check_status,source_order FROM items WHERE id=?",
            (item.id,),
        ).fetchone()
        fts_title_before = conn.execute(
            "SELECT title FROM items_fts WHERE id=?", (item.id,)
        ).fetchone()[0]

    changed = update_content_evidence(
        item.id,
        tags=["hd", "professional"],
        studio="Example Studio",
        path=db,
    )
    assert changed is True
    stored = get_item(item.id, path=db)
    assert stored is not None
    assert stored.tags == ["hd", "professional"]
    assert stored.studio == "Example Studio"
    assert stored.content_class == "studio"

    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT url,title,thumbnail,preview_url,age_check_status,source_order,content_class_source "
            "FROM items WHERE id=?",
            (item.id,),
        ).fetchone()
        assert tuple(row[k] for k in ("url","title","thumbnail","preview_url","age_check_status","source_order")) == before
        assert row["content_class_source"] == "studio_label"
        assert conn.execute("SELECT title FROM items_fts WHERE id=?", (item.id,)).fetchone()[0] == fts_title_before
        assert conn.execute("SELECT tags FROM items_fts WHERE id=?", (item.id,)).fetchone()[0] == "hd professional"

    assert update_content_evidence(
        item.id,
        tags=["hd", "professional"],
        studio="Different Studio",
        path=db,
    ) is False
    stored = get_item(item.id, path=db)
    assert stored is not None
    assert stored.studio == "Example Studio"

def test_enrichment_candidates_respect_provider_and_retry_time(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone
    from backend.index import (
        list_content_enrichment_candidates,
        record_content_enrichment_attempt,
    )

    db = tmp_path / "candidates.db"
    item = SearchItem(
        id="candidate-1",
        provider="eligible",
        title="Unknown",
        url="https://example.com/v/1",
        tags=["hd"],
    )
    upsert_items([item], path=db)
    now = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)

    rows = list_content_enrichment_candidates({"eligible"}, limit=10, now=now, path=db)
    assert len(rows) == 1
    assert rows[0].item.id == item.id
    assert rows[0].failure_count == 0
    assert list_content_enrichment_candidates({"other"}, limit=10, now=now, path=db) == []

    record_content_enrichment_attempt(
        item.id,
        provider="eligible",
        status="failure",
        failure_count=1,
        last_attempt_at=now,
        next_attempt_at=now + timedelta(hours=6),
        path=db,
    )
    assert list_content_enrichment_candidates({"eligible"}, limit=10, now=now, path=db) == []

    later = now + timedelta(hours=7)
    rows = list_content_enrichment_candidates({"eligible"}, limit=10, now=later, path=db)
    assert len(rows) == 1
    assert rows[0].failure_count == 1
