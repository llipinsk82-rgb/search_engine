from pathlib import Path
import sqlite3

from backend.index import get_item, search_items, upsert_items
from backend.models import SearchItem


def test_explicit_class_and_studio_round_trip(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    item = SearchItem(
        id="studio-1",
        provider="demo",
        title="Real source metadata",
        url="https://example.com/studio-1",
        tags=["production"],
        content_class="studio",
        studio="Example Studio",
    )
    assert upsert_items([item], path=db) == 1
    stored = get_item("studio-1", path=db)
    assert stored is not None
    assert stored.content_class == "studio"
    assert stored.studio == "Example Studio"
    listed = search_items("", path=db)
    assert [(row.content_class, row.studio) for row in listed] == [("studio", "Example Studio")]


def test_unknown_is_classified_from_explicit_tags_at_ingestion(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    item = SearchItem(
        id="amateur-1",
        provider="demo",
        title="Title must not drive classification",
        url="https://example.com/amateur-1",
        tags=["homemade"],
    )
    upsert_items([item], path=db)
    stored = get_item("amateur-1", path=db)
    assert stored is not None
    assert stored.content_class == "amateur"
    assert stored.studio is None


def test_title_only_amateur_word_remains_unknown(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    item = SearchItem(
        id="unknown-1",
        provider="demo",
        title="Amateur clip",
        url="https://example.com/unknown-1",
        tags=["hd"],
    )
    upsert_items([item], path=db)
    stored = get_item("unknown-1", path=db)
    assert stored is not None
    assert stored.content_class == "unknown"

def test_upsert_recomputes_class_and_source_from_current_evidence(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    first = SearchItem(
        id="reclass-1",
        provider="demo",
        title="X",
        url="https://example.com/reclass-1",
        tags=["professional"],
    )
    upsert_items([first], path=db)
    stored = get_item("reclass-1", path=db)
    assert stored is not None and stored.content_class == "studio"
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT content_class_source FROM items WHERE id='reclass-1'"
        ).fetchone()[0] == "tag_studio"

    second = first.model_copy(update={"tags": ["homemade"], "studio": None})
    upsert_items([second], path=db)
    stored = get_item("reclass-1", path=db)
    assert stored is not None and stored.content_class == "amateur"
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT content_class_source FROM items WHERE id='reclass-1'"
        ).fetchone()[0] == "tag_amateur"
