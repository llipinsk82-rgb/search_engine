from __future__ import annotations

import sqlite3

from backend.index import initialize
from backend.preview_stats import preview_coverage_stats


def _insert(db, item_id, provider, preview=None):
    initialize(db)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO items(id,provider,title,url,preview_url,active) VALUES(?,?,?,?,?,1)",
            (item_id, provider, item_id, f"https://example.com/{item_id}", preview),
        )


def test_preview_coverage_reconciles_stored_and_playable(tmp_path):
    db = tmp_path / "stats.db"
    _insert(db, "a", "bigfuck", "https://icdn05.bigfuck.tv/p.mp4")
    _insert(db, "b", "pornhat", "https://www.pornhat.one/p.mp4")
    _insert(db, "c", "bigfuck")
    _insert(db, "d", "tube8")
    stats = preview_coverage_stats(path=db)
    assert stats.total == 4
    assert stats.stored == 2
    assert stats.playable == 1
    assert stats.stored_percent == 50.0
    assert stats.playable_percent == 25.0
    assert sum(v.total for v in stats.providers.values()) == stats.total
    assert sum(v.stored for v in stats.providers.values()) == stats.stored
    assert sum(v.playable for v in stats.providers.values()) == stats.playable
