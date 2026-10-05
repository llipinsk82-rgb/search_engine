from __future__ import annotations

import asyncio

from backend.live import LiveProviderResult, refresh_live_search
from backend.models import SearchItem
from backend.query_syntax import parse_search_query


def _item(item_id: str, title: str, *, tags: list[str] | None = None) -> SearchItem:
    return SearchItem(
        id=item_id,
        provider="fixture",
        title=title,
        url=f"https://example.com/{item_id}",
        tags=tags or [],
    )


def test_plus_query_parses_as_explicit_and_without_order() -> None:
    parsed = parse_search_query("sis+step+perv")
    assert parsed.provider_query == "sis step perv"
    assert parsed.required_tokens == ("sis", "step", "perv")
    assert parsed.explicit_and is True


def test_plain_space_query_keeps_existing_live_semantics() -> None:
    parsed = parse_search_query("sis step perv")
    assert parsed.provider_query == "sis step perv"
    assert parsed.required_tokens == ()
    assert parsed.explicit_and is False


def test_plus_query_normalizes_spacing_and_case() -> None:
    parsed = parse_search_query("  SIS + step+  Perv ")
    assert parsed.provider_query == "SIS step Perv"
    assert parsed.required_tokens == ("sis", "step", "perv")


def test_live_plus_query_sends_normalized_query_and_filters_missing_terms() -> None:
    class FixtureAdapter:
        name = "fixture"

        def __init__(self) -> None:
            self.queries: list[str] = []

        async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
            self.queries.append(query)
            return LiveProviderResult(
                provider=self.name,
                items=[
                    _item("a", "Perv Step Sis"),
                    _item("b", "Sis Perv"),
                    _item("c", "Step clip", tags=["sis", "perv"]),
                ],
                total=3,
                page=page,
                elapsed_ms=1,
            )

    adapter = FixtureAdapter()
    result = asyncio.run(refresh_live_search("sis+step+perv", adapters=[adapter]))

    assert adapter.queries == ["sis step perv"]
    assert [item.id for item in result.providers[0].items] == ["a", "c"]


def test_plain_space_live_query_is_not_post_filtered() -> None:
    class FixtureAdapter:
        name = "fixture"

        async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
            return LiveProviderResult(
                provider=self.name,
                items=[_item("a", "Only sis")],
                total=1,
                page=page,
                elapsed_ms=1,
            )

    result = asyncio.run(refresh_live_search("sis step perv", adapters=[FixtureAdapter()]))
    assert [item.id for item in result.providers[0].items] == ["a"]
