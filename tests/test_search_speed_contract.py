from __future__ import annotations

import asyncio
import threading
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
