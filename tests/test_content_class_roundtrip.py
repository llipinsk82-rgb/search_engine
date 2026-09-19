from pathlib import Path

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
