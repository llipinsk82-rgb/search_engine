from __future__ import annotations
import sqlite3
import tempfile
import unittest
from pathlib import Path
from backend.index import get_item, initialize, upsert_items
from backend.models import SearchItem
from backend.live import LIVE_ADAPTERS

class PreviewMetadataTests(unittest.TestCase):
    def test_existing_database_gets_preview_url_column(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"x.db"
            with sqlite3.connect(db) as c:
                c.execute("CREATE TABLE items (id TEXT PRIMARY KEY, provider TEXT NOT NULL, title TEXT NOT NULL, url TEXT NOT NULL, thumbnail TEXT, duration_seconds INTEGER, quality TEXT, tags_json TEXT NOT NULL DEFAULT '[]', indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, source_order INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1)")
            initialize(db)
            with sqlite3.connect(db) as c:
                cols={r[1] for r in c.execute("PRAGMA table_info(items)")}
            self.assertIn("preview_url", cols)
            self.assertIn("age_check_status", cols)

    def test_preview_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"x.db"
            item=SearchItem(id="a",provider="beeg",title="A",url="https://beeg.com/-0123",preview_url="https://cdn.example/a.mp4",tags=[])
            upsert_items([item],db)
            stored=get_item("a",db)
            self.assertIsNotNone(stored)
            self.assertEqual(str(stored.preview_url),"https://cdn.example/a.mp4")

    def test_final_live_provider_set(self):
        self.assertEqual(
            {a.name for a in LIVE_ADAPTERS},
            {"beeg","xnxx","youjizz","pornone","hqporner","eporner","tnaflix"},
        )

if __name__ == "__main__":
    unittest.main()
