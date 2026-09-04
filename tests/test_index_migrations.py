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
