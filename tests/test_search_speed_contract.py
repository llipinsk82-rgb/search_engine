from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

import backend.search as search_module
from backend.index import count_search_items_capped, upsert_items
from backend.models import SearchItem


def _item(i: int) -> SearchItem:
    return SearchItem(
        id=f"id-{i}",
        provider="demo",
        title=f"common result {i}",
        url=f"https://example.com/{i}",
        thumbnail=f"https://example.com/{i}.jpg",
        duration_seconds=60,
        tags=[],
        score=1.0,
    )


def test_capped_count_preserves_small_exact_total_and_caps_broad_result(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    upsert_items([_item(i) for i in range(12)], path=db)

    exact, exact_capped = count_search_items_capped(
        "common", allowed_providers={"demo"}, cap=20, path=db
    )
    broad, broad_capped = count_search_items_capped(
        "common", allowed_providers={"demo"}, cap=5, path=db
    )

    assert (exact, exact_capped) == (12, False)
    assert (broad, broad_capped) == (5, True)


def test_search_all_runs_sqlite_work_off_event_loop(monkeypatch) -> None:
    main_thread = threading.get_ident()
    worker_threads: list[int] = []

    def fake_count(*args, **kwargs):
        worker_threads.append(threading.get_ident())
        return 1, False

    def fake_search(*args, **kwargs):
        worker_threads.append(threading.get_ident())
        return []

    monkeypatch.setattr(search_module, "indexed_providers", lambda: ["demo"])
    monkeypatch.setattr(search_module, "count_search_items_capped", fake_count)
    monkeypatch.setattr(search_module, "search_items", fake_search)

    result = asyncio.run(search_module.search_all("query", allowed_providers={"demo"}))

    assert result[3:] == (1, False)
    assert len(worker_threads) == 2
    assert all(thread_id != main_thread for thread_id in worker_threads)


def test_search_all_skips_indexed_provider_scan_when_allowlist_is_supplied(monkeypatch) -> None:
    def forbidden_indexed_providers():
        raise AssertionError("indexed_providers must not run in the API allowlist hot path")

    monkeypatch.setattr(search_module, "indexed_providers", forbidden_indexed_providers)
    monkeypatch.setattr(search_module, "count_search_items_capped", lambda *a, **k: (0, False))
    monkeypatch.setattr(search_module, "search_items", lambda *a, **k: [])

    result = asyncio.run(search_module.search_all("query", allowed_providers={"demo"}))

    assert result[1] == ["demo"]


def test_search_all_uses_limit_plus_one_for_has_more(monkeypatch) -> None:
    captured: dict[str, int] = {}

    def fake_count(*args, **kwargs):
        return 10, False

    def fake_search(*args, **kwargs):
        captured["limit"] = kwargs["limit"]
        return [_item(1), _item(2), _item(3)]

    monkeypatch.setattr(search_module, "count_search_items_capped", fake_count)
    monkeypatch.setattr(search_module, "search_items", fake_search)

    items, _, has_more, total, capped = asyncio.run(
        search_module.search_all("query", allowed_providers={"demo"}, limit=2)
    )

    assert captured["limit"] == 3
    assert [item.id for item in items] == ["id-1", "id-2"]
    assert has_more is True
    assert (total, capped) == (10, False)


def test_health_database_work_does_not_block_event_loop(monkeypatch) -> None:
    import backend.app as app_module

    def slow_count():
        time.sleep(0.08)
        return 1

    def slow_observability():
        time.sleep(0.08)
        return {}

    async def scenario():
        monkeypatch.setattr(app_module, "count_items", slow_count)
        monkeypatch.setattr(app_module, "_provider_observability", slow_observability)
        task = asyncio.create_task(app_module.health())
        await asyncio.sleep(0.02)
        responsive = not task.done()
        result = await task
        return responsive, result

    responsive, result = asyncio.run(scenario())
    assert responsive is True
    assert result["status"] == "ok"


def test_provider_and_stats_scans_do_not_block_event_loop(monkeypatch) -> None:
    import backend.app as app_module

    def slow_indexed():
        time.sleep(0.08)
        return []

    def slow_counts():
        time.sleep(0.08)
        return {}

    async def scenario():
        monkeypatch.setattr(app_module, "indexed_providers", slow_indexed)
        monkeypatch.setattr(app_module, "count_items", lambda: 1)
        monkeypatch.setattr(app_module, "provider_counts", slow_counts)
        monkeypatch.setattr(app_module, "_provider_observability", lambda: {})
        providers_task = asyncio.create_task(app_module.providers())
        await asyncio.sleep(0.02)
        providers_responsive = not providers_task.done()
        await providers_task

        stats_task = asyncio.create_task(app_module.stats())
        await asyncio.sleep(0.02)
        stats_responsive = not stats_task.done()
        await stats_task
        return providers_responsive, stats_responsive

    providers_responsive, stats_responsive = asyncio.run(scenario())
    assert providers_responsive is True
    assert stats_responsive is True


def test_count_and_page_query_start_concurrently(monkeypatch) -> None:
    count_started = threading.Event()
    search_started = threading.Event()

    def fake_count(*args, **kwargs):
        count_started.set()
        assert search_started.wait(1.0)
        return 1, False

    def fake_search(*args, **kwargs):
        search_started.set()
        assert count_started.wait(1.0)
        return []

    monkeypatch.setattr(search_module, "count_search_items_capped", fake_count)
    monkeypatch.setattr(search_module, "search_items", fake_search)

    result = asyncio.run(search_module.search_all("query", allowed_providers={"demo"}))

    assert result[3:] == (1, False)
