from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.index import count_search_items_capped, replace_provider_items
from backend.models import SearchItem
from backend.search import search_all


def _item(n: int) -> SearchItem:
    return SearchItem(
        id=f"id-{n}",
        provider="speed",
        title=f"Alpha item {n}",
        url=f"https://example.com/{n}",
        duration_seconds=60,
    )


def test_capped_count_reports_5000_plus_without_exact_full_count() -> None:
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "search.db"
        replace_provider_items("speed", [_item(n) for n in range(7)], path=db)

        total, capped = count_search_items_capped(
            "alpha",
            allowed_providers={"speed"},
            cap=5,
            path=db,
        )

        assert total == 5
        assert capped is True


def test_capped_count_stays_exact_below_cap() -> None:
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "search.db"
        replace_provider_items("speed", [_item(n) for n in range(3)], path=db)

        total, capped = count_search_items_capped(
            "alpha",
            allowed_providers={"speed"},
            cap=5,
            path=db,
        )

        assert total == 3
        assert capped is False


def test_search_all_offloads_blocking_sqlite_work() -> None:
    result = ([], [], False, 0, False)
    runner = AsyncMock(return_value=result)
    with patch("backend.search.asyncio.to_thread", runner):
        got = asyncio.run(search_all("alpha"))

    assert got == result
    runner.assert_awaited_once()


def test_search_all_skips_indexed_provider_scan_when_allowlist_is_supplied() -> None:
    from backend import search as search_module
    with (
        patch.object(search_module, "indexed_providers", side_effect=AssertionError("unexpected provider scan")),
        patch.object(search_module, "count_search_items_capped", return_value=(0, False)),
        patch.object(search_module, "search_items", return_value=[]),
    ):
        got = search_module._search_all_sync("alpha", allowed_providers={"speed"})
    assert got == ([], ["speed"], False, 0, False)


def test_search_response_exposes_capped_total_flag() -> None:
    from backend.models import SearchResponse
    assert "total_is_capped" in SearchResponse.model_fields


def test_health_offloads_blocking_snapshot() -> None:
    import backend.app as app_module
    runner = AsyncMock(return_value=(123, {"indexed_provider_count": 0, "indexed_providers": [], "configured_index_provider_count": 0, "configured_index_providers": [], "live_provider_count": 0, "live_providers": [], "trusted_provider_count": 0, "trusted_providers": [], "available_provider_count": 0, "available_providers": []}))
    with patch("backend.app.asyncio.to_thread", runner):
        result = asyncio.run(app_module.health())
    assert result["indexed_items"] == 123
    runner.assert_awaited_once()
