from __future__ import annotations

import sqlite3

import pytest

from backend.index import merge_provider_batches, update_preview_url
from backend.models import SearchItem


def _seed(db):
    item = SearchItem(
        id="p1", provider="bigfuck", title="Preview Item",
        url="https://bigfuck.tv/video/1", thumbnail="https://bigfuck.tv/t.jpg",
        duration_seconds=123, quality="HD", tags=["tag1"], studio="Studio",
        age_check_status="unknown",
    )
    merge_provider_batches({"bigfuck": [item]}, path=db)


def test_update_preview_url_changes_only_preview_and_never_replaces(tmp_path):
    db = tmp_path / "preview.db"
    _seed(db)
    with sqlite3.connect(db) as conn:
        before = conn.execute("SELECT * FROM items WHERE id='p1'").fetchone()
        columns = [r[1] for r in conn.execute("PRAGMA table_info(items)")]
        before = dict(zip(columns, before))
        fts_before = conn.execute("SELECT * FROM items_fts WHERE id='p1'").fetchall()
        state_before = conn.execute("SELECT * FROM provider_state ORDER BY provider,state_key").fetchall()

    url = "https://icdn05.bigfuck.tv/preview/p.mp4"
    assert update_preview_url("p1", preview_url=url, path=db) is True
    assert update_preview_url("p1", preview_url=url, path=db) is False
    assert update_preview_url("p1", preview_url="https://icdn05.bigfuck.tv/preview/other.mp4", path=db) is False

    with sqlite3.connect(db) as conn:
        after_row = conn.execute("SELECT * FROM items WHERE id='p1'").fetchone()
        after = dict(zip(columns, after_row))
        fts_after = conn.execute("SELECT * FROM items_fts WHERE id='p1'").fetchall()
        state_after = conn.execute("SELECT * FROM provider_state ORDER BY provider,state_key").fetchall()

    assert after["preview_url"] == url
    assert {k:v for k,v in after.items() if k != "preview_url"} == {k:v for k,v in before.items() if k != "preview_url"}
    assert fts_after == fts_before
    assert state_after == state_before


def test_update_preview_url_rejects_invalid_or_policy_blocked_urls(tmp_path):
    db = tmp_path / "preview.db"
    _seed(db)
    for value in ("", "http://icdn05.bigfuck.tv/p.mp4", "https://evil.example/p.mp4"):
        with pytest.raises(ValueError):
            update_preview_url("p1", preview_url=value, path=db)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT preview_url FROM items WHERE id='p1'").fetchone()[0] is None
