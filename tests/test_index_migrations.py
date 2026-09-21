from pathlib import Path
import sqlite3

from backend import index


def test_beeg_url_migration_is_recorded_and_idempotent(tmp_path: Path):
    db = tmp_path / "search.db"
    index._initialized_paths.discard(str(db.resolve()))
    index.initialize(db)
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO items(id,provider,title,url) VALUES(?,?,?,?)", ("b1","beeg","x","https://beeg.com/-0/123"))
        conn.execute("DELETE FROM provider_state WHERE provider='__system__' AND state_key='migration:beeg_url_dash0_v1'")
    index._initialized_paths.discard(str(db.resolve()))
    index.initialize(db)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT url FROM items WHERE id='b1'").fetchone()[0] == "https://beeg.com/-0123"
        assert conn.execute("SELECT state_value FROM provider_state WHERE provider='__system__' AND state_key='migration:beeg_url_dash0_v1'").fetchone()[0] == "done"
        conn.execute("UPDATE items SET url='https://beeg.com/-0/999' WHERE id='b1'")
    index._initialized_paths.discard(str(db.resolve()))
    index.initialize(db)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT url FROM items WHERE id='b1'").fetchone()[0] == "https://beeg.com/-0/999"


def test_sort_metadata_columns_are_added_without_losing_existing_rows(tmp_path: Path):
    db = tmp_path / "search.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            CREATE TABLE items (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                thumbnail TEXT,
                preview_url TEXT,
                duration_seconds INTEGER,
                quality TEXT,
                age_check_status TEXT NOT NULL DEFAULT 'unknown',
                tags_json TEXT NOT NULL DEFAULT '[]',
                indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                source_order INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute(
            "INSERT INTO items(id,provider,title,url) VALUES(?,?,?,?)",
            ("legacy", "demo", "Legacy", "https://example.com/legacy"),
        )

    index._initialized_paths.discard(str(db.resolve()))
    index.initialize(db)

    with sqlite3.connect(db) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(items)")}
        assert {"published_at", "views", "rating_percent", "rating_count"} <= columns
        assert conn.execute("SELECT title FROM items WHERE id='legacy'").fetchone()[0] == "Legacy"
        marker = conn.execute(
            "SELECT state_value FROM provider_state WHERE provider='__system__' AND state_key='migration:metadata_sort_indexes_v1'"
        ).fetchone()
        assert marker == ("done",)


def test_content_class_columns_are_added_without_losing_existing_rows(tmp_path: Path):
    db = tmp_path / "content-class.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            CREATE TABLE items (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                thumbnail TEXT,
                preview_url TEXT,
                duration_seconds INTEGER,
                published_at TEXT,
                views INTEGER,
                rating_percent REAL,
                rating_count INTEGER,
                quality TEXT,
                age_check_status TEXT NOT NULL DEFAULT 'unknown',
                tags_json TEXT NOT NULL DEFAULT '[]',
                indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                source_order INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute(
            "INSERT INTO items(id,provider,title,url) VALUES(?,?,?,?)",
            ("legacy", "demo", "Legacy Amateur Title", "https://example.com/legacy"),
        )

    index._initialized_paths.discard(str(db.resolve()))
    index.initialize(db)

    with sqlite3.connect(db) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(items)")}
        assert {"content_class", "studio", "content_class_source"} <= columns
        row = conn.execute(
            "SELECT title, content_class, studio, content_class_source FROM items WHERE id='legacy'"
        ).fetchone()
        assert row == ("Legacy Amateur Title", "unknown", None, "none")
        marker = conn.execute(
            "SELECT state_value FROM provider_state WHERE provider='__system__' AND state_key='migration:content_class_index_v1'"
        ).fetchone()
        assert marker == ("done",)

def test_content_enrichment_state_schema_is_additive(tmp_path: Path):
    db = tmp_path / "content-enrichment.db"
    index._initialized_paths.discard(str(db.resolve()))
    index.initialize(db)
    with sqlite3.connect(db) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(content_enrichment_state)")}
        assert columns == {
            "item_id", "provider", "status", "failure_count",
            "last_attempt_at", "next_attempt_at",
        }
        pk = [
            row
            for row in conn.execute("PRAGMA table_info(content_enrichment_state)")
            if row[5] == 1
        ]
        assert [row[1] for row in pk] == ["item_id"]
