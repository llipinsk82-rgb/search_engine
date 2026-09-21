from pathlib import Path

from backend.index import get_item, search_items, upsert_items
from backend.models import SearchItem

ROOT = Path(__file__).resolve().parents[1]


def item(item_id: str, provider: str, *, tags=None, studio=None) -> SearchItem:
    return SearchItem(
        id=item_id,
        provider=provider,
        title=item_id,
        url=f"https://example.com/{item_id}",
        tags=list(tags or []),
        studio=studio,
    )


def test_production_filter_accepts_explicit_studio_metadata_from_any_provider(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    upsert_items([item("xg", "xgroovy", studio="Bratty Sis")], path=db)
    stored = get_item("xg", path=db)
    assert stored is not None
    assert stored.content_class == "studio"
    assert [row.id for row in search_items("", path=db, content_class="studio")] == ["xg"]


def test_production_filter_accepts_exact_professional_or_production_tag(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    upsert_items(
        [
            item("p1", "demo", tags=["professional"]),
            item("p2", "demo", tags=["production"]),
            item("u", "demo", tags=["hd"]),
        ],
        path=db,
    )
    assert {row.id for row in search_items("", path=db, content_class="studio")} == {"p1", "p2"}
    assert [row.id for row in search_items("", path=db, content_class="unknown")] == ["u"]


def test_ui_exposes_only_amateur_and_production_content_filters() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    start = html.index('id="content-class"')
    end = html.index("</select>", start)
    select = html[start:end]
    assert '<option value="amateur">Amateur</option>' in select
    assert '<option value="studio">Production</option>' in select
    assert 'value="unknown"' not in select
