import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import urlencode

import pytest
from pydantic import ValidationError

from backend.app import app, live_refresh, search_post
from backend.index import count_search_items, search_items, upsert_items
from backend.live import LiveProviderResult, LiveRefreshResult
from backend.models import LiveRefreshRequest, SearchItem, SearchRequest


def item(item_id: str, *, content_class: str = "unknown", tags=None, studio=None, title=None) -> SearchItem:
    return SearchItem(id=item_id, provider="demo", title=title or item_id, url=f"https://example.com/{item_id}", tags=list(tags or []), content_class=content_class, studio=studio)


def ids(rows):
    return [row.id for row in rows]


def test_index_filter_none_returns_all_and_explicit_values_are_exact(tmp_path: Path) -> None:
    db = tmp_path / "search.db"
    upsert_items([item("a", tags=["homemade"]), item("s", studio="Example Studio"), item("u")], path=db)
    assert set(ids(search_items("", path=db, content_class=None))) == {"a", "s", "u"}
    assert ids(search_items("", path=db, content_class="amateur")) == ["a"]
    assert ids(search_items("", path=db, content_class="studio")) == ["s"]
    assert ids(search_items("", path=db, content_class="unknown")) == ["u"]
    assert count_search_items("", path=db, content_class="unknown") == 1


def test_request_models_accept_only_explicit_content_classes() -> None:
    assert SearchRequest(content_class="amateur").content_class == "amateur"
    assert LiveRefreshRequest(q="alpha", content_class="studio").content_class == "studio"
    assert SearchRequest().content_class is None
    with pytest.raises(ValidationError): SearchRequest(content_class="professional")
    with pytest.raises(ValidationError): LiveRefreshRequest(q="alpha", content_class="other")


async def asgi_get(path: str, params: dict[str, str]):
    messages=[]; sent_request=False
    async def receive():
        nonlocal sent_request
        if not sent_request:
            sent_request=True
            return {"type":"http.request","body":b"","more_body":False}
        return {"type":"http.disconnect"}
    async def send(message): messages.append(message)
    scope={"type":"http","asgi":{"version":"3.0"},"http_version":"1.1","method":"GET","scheme":"http","path":path,"raw_path":path.encode(),"query_string":urlencode(params).encode(),"headers":[],"client":("127.0.0.1",12345),"server":("test",80),"root_path":""}
    await app(scope,receive,send)
    start=next(m for m in messages if m["type"]=="http.response.start")
    body=b"".join(m.get("body",b"") for m in messages if m["type"]=="http.response.body")
    return start["status"],json.loads(body or b"null")


def test_get_search_forwards_content_class_and_rejects_invalid_value() -> None:
    search=AsyncMock(return_value=([],[],False,0))
    with patch("backend.app.search_all",search), patch("backend.app.trusted_provider_names",return_value=set()):
        status,_=asyncio.run(asgi_get("/api/search",{"q":"alpha","content_class":"studio"}))
    assert status==200
    assert search.await_args.kwargs["content_class"]=="studio"
    status,payload=asyncio.run(asgi_get("/api/search",{"q":"alpha","content_class":"professional"}))
    assert status==422 and payload["detail"]


def test_post_search_forwards_content_class() -> None:
    search=AsyncMock(return_value=([],[],False,0))
    with patch("backend.app.search_all",search), patch("backend.app.trusted_provider_names",return_value=set()):
        response=asyncio.run(search_post(SearchRequest(q="alpha",content_class="unknown")))
    assert response.query=="alpha"
    assert search.await_args.kwargs["content_class"]=="unknown"


def live_result():
    return LiveRefreshResult(providers=[LiveProviderResult("demo",[item("amateur-tag",tags=["homemade"]),item("studio-tag",tags=["professional"]),item("studio-label",studio="Example Studio"),item("title-only",tags=["hd"],title="Amateur only in title")],4,1,1)],cached_items=0)


def run_live(content_class: str):
    from fastapi import BackgroundTasks
    with patch("backend.app.refresh_live_search",AsyncMock(return_value=live_result())), patch("backend.app.count_items",return_value=4):
        return asyncio.run(live_refresh(LiveRefreshRequest(q="alpha",content_class=content_class),BackgroundTasks()))


def test_live_results_are_classified_before_content_filtering_and_cache() -> None:
    amateur=run_live("amateur"); assert ids(amateur.items)==["amateur-tag"]; assert amateur.items[0].content_class=="amateur"
    studio=run_live("studio"); assert ids(studio.items)==["studio-tag","studio-label"]; assert all(row.content_class=="studio" for row in studio.items)
    unknown=run_live("unknown"); assert ids(unknown.items)==["title-only"]; assert unknown.items[0].content_class=="unknown"

def test_filtered_live_response_caches_full_classified_batch() -> None:
    from fastapi import BackgroundTasks

    background_tasks = BackgroundTasks()
    cache = Mock(return_value=4)
    with (
        patch("backend.app.refresh_live_search", AsyncMock(return_value=live_result())),
        patch("backend.app.count_items", return_value=4),
        patch("backend.app.cache_live_provider_results", cache),
    ):
        response = asyncio.run(
            live_refresh(
                LiveRefreshRequest(q="alpha", content_class="amateur"),
                background_tasks,
            )
        )
        asyncio.run(background_tasks())

    assert ids(response.items) == ["amateur-tag"]
    cached_results = cache.call_args.args[0]
    cached_items = cached_results[0].items
    assert ids(cached_items) == [
        "amateur-tag",
        "studio-tag",
        "studio-label",
        "title-only",
    ]
    assert [row.content_class for row in cached_items] == [
        "amateur",
        "studio",
        "studio",
        "unknown",
    ]
