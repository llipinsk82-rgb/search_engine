from __future__ import annotations

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from backend.index import count_search_items, upsert_items
from backend.models import SearchItem
from backend.search import SEARCH_TOTAL_CAP, search_all


def _item(i: int) -> SearchItem:
    return SearchItem(
        id=f"id-{i}",
        provider="sample",
        title=f"common title {i}",
        url=f"https://example.com/{i}",
        thumbnail=f"https://example.com/{i}.jpg",
        duration_seconds=60,
    )


def test_count_search_items_can_cap_large_totals() -> None:
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "search.db"
        upsert_items([_item(i) for i in range(9)], path=db)
        assert count_search_items("common", path=db, max_count=3) == 4
        assert count_search_items("common", path=db) == 9


def test_search_all_keeps_event_loop_responsive_during_sqlite_work() -> None:
    def slow_count(*args, **kwargs):
        time.sleep(0.08)
        return SEARCH_TOTAL_CAP + 1

    def slow_search(*args, **kwargs):
        time.sleep(0.08)
        return [_item(i) for i in range(40)]

    async def scenario():
        ticked = False

        async def ticker():
            nonlocal ticked
            await asyncio.sleep(0.02)
            ticked = True

        with (
            patch("backend.search.indexed_providers", return_value=["sample"]),
            patch("backend.search.count_search_items", side_effect=slow_count),
            patch("backend.search.search_items", side_effect=slow_search),
        ):
            task = asyncio.create_task(search_all("common", allowed_providers={"sample"}))
            tick = asyncio.create_task(ticker())
            result = await task
            await tick
        return ticked, result

    ticked, (items, _, has_more, total) = asyncio.run(scenario())
    assert ticked is True
    assert len(items) == 40
    assert total == SEARCH_TOTAL_CAP + 1
    assert has_more is True


def test_search_all_skips_indexed_provider_scan_when_allowlist_is_supplied() -> None:
    async def scenario():
        with (
            patch("backend.search.indexed_providers") as indexed,
            patch("backend.search.count_search_items", return_value=0),
            patch("backend.search.search_items", return_value=[]),
        ):
            result = await search_all("needle", allowed_providers={"sample"})
        return indexed, result

    indexed, (_, used, _, _) = asyncio.run(scenario())
    indexed.assert_not_called()
    assert used == ["sample"]


def test_search_response_exposes_capped_total_explicitly() -> None:
    from backend.app import _search_response

    async def scenario():
        with patch(
            "backend.app.search_all",
            new_callable=__import__("unittest.mock").mock.AsyncMock,
            return_value=([], [], True, SEARCH_TOTAL_CAP + 1),
        ):
            return await _search_response(
                q="broad", provider=None, quality=None, content_class=None,
                age_check=None, min_duration=None, max_duration=None,
                sort="relevance", offset=0, limit=40, exclude_ids=None,
            )

    response = asyncio.run(scenario())
    assert response.total == SEARCH_TOTAL_CAP
    assert response.total_is_capped is True


def test_health_database_work_does_not_block_event_loop() -> None:
    from backend.app import health

    def slow_count():
        time.sleep(0.08)
        return 1

    def slow_observability():
        time.sleep(0.08)
        return {}

    async def scenario():
        with (
            patch("backend.app.count_items", side_effect=slow_count),
            patch("backend.app._provider_observability", side_effect=slow_observability),
        ):
            task = asyncio.create_task(health())
            await asyncio.sleep(0.02)
            responsive = not task.done()
            result = await task
        return responsive, result

    responsive, result = asyncio.run(scenario())
    assert responsive is True
    assert result["status"] == "ok"


def test_providers_index_scan_does_not_block_event_loop() -> None:
    from backend.app import providers

    def slow_indexed():
        time.sleep(0.08)
        return []

    async def scenario():
        with patch("backend.app.indexed_providers", side_effect=slow_indexed):
            task = asyncio.create_task(providers())
            await asyncio.sleep(0.02)
            responsive = not task.done()
            result = await task
        return responsive, result

    responsive, result = asyncio.run(scenario())
    assert responsive is True
    assert "providers" in result
