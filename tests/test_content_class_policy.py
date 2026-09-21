from pathlib import Path
import sqlite3

from backend.content_class_live import filter_live_items
from backend.index import count_search_items, get_item, search_items, upsert_items
from backend.models import SearchItem


def item(item_id: str, provider: str, *, tags=None, studio=None) -> SearchItem:
    return SearchItem(
        id=item_id,
        provider=provider,
        title=item_id,
        url=f"https://example.com/{item_id}",
        tags=list(tags or []),
        studio=studio,
    )


def test_untrusted_provider_tags_do_not_become_amateur_or_studio(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    upsert_items(
        [
            item("a", "demo", tags=["homemade"]),
            item("s", "demo", tags=["professional"]),
        ],
        path=db,
    )
    assert get_item("a", path=db).content_class == "unknown"
    assert get_item("s", path=db).content_class == "unknown"


def test_xgroovy_production_company_is_metadata_not_studio_class(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    upsert_items([item("xg", "xgroovy", studio="Bratty Sis")], path=db)
    stored = get_item("xg", path=db)
    assert stored.studio == "Bratty Sis"
    assert stored.content_class == "unknown"


def test_audited_amateur_provider_keeps_explicit_amateur_signal(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    upsert_items([item("xv", "xvideos", tags=["homemade"])], path=db)
    assert get_item("xv", path=db).content_class == "amateur"


def test_confirmed_item_bound_studio_provider_keeps_studio_label(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    upsert_items([item("xc", "xcafe", studio="Blacked")], path=db)
    assert get_item("xc", path=db).content_class == "studio"


def test_xgroovy_channel_metadata_does_not_pass_cached_studio_filter(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    upsert_items(
        [
            item("xg", "xgroovy", studio="Bratty Sis"),
            item("xc", "xcafe", studio="Blacked"),
        ],
        path=db,
    )
    assert [row.id for row in search_items("", path=db, content_class="studio")] == ["xc"]
    assert [row.id for row in search_items("", path=db, content_class="unknown")] == ["xg"]


def test_stale_legacy_class_is_filtered_by_current_provider_policy(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    upsert_items([item("legacy-xg", "xgroovy", studio="Bratty Sis")], path=db)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE items SET content_class='studio', content_class_source='studio_label' WHERE id='legacy-xg'"
        )

    assert search_items("", path=db, content_class="studio") == []
    assert count_search_items("", path=db, content_class="studio") == 0
    unknown = search_items("", path=db, content_class="unknown")
    assert [row.id for row in unknown] == ["legacy-xg"]
    assert unknown[0].content_class == "unknown"
    assert count_search_items("", path=db, content_class="unknown") == 1


def test_live_filter_uses_provider_specific_evidence_policy() -> None:
    rows = [
        item("untrusted", "demo", tags=["homemade"]),
        item("trusted", "xvideos", tags=["homemade"]),
        item("xg", "xgroovy", studio="Bratty Sis"),
        item("xc", "xcafe", studio="Blacked"),
    ]
    assert [row.id for row in filter_live_items(rows, "amateur")] == ["trusted"]
    assert [row.id for row in filter_live_items(rows, "studio")] == ["xc"]
    assert [row.id for row in filter_live_items(rows, "unknown")] == ["untrusted", "xg"]
