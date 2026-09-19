import asyncio
import json
from unittest.mock import AsyncMock, patch
from urllib.parse import urlencode

from backend.app import app, search_post
from backend.models import SearchRequest


async def asgi_get(path: str, params: dict[str, str]):
    messages = []
    sent_request = False

    async def receive():
        nonlocal sent_request
        if not sent_request:
            sent_request = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": urlencode(params).encode(),
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "root_path": "",
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start["status"], json.loads(body or b"null")


def test_get_search_forwards_sort_mode():
    search = AsyncMock(return_value=([], [], False, 0))
    with (
        patch("backend.app.search_all", search),
        patch("backend.app.trusted_provider_names", return_value=set()),
    ):
        status, _ = asyncio.run(asgi_get("/api/search", {"q": "alpha", "sort": "views"}))

    assert status == 200
    assert search.await_args.kwargs["sort"] == "views"


def test_get_search_rejects_invalid_sort_mode():
    search = AsyncMock(return_value=([], [], False, 0))
    with (
        patch("backend.app.search_all", search),
        patch("backend.app.trusted_provider_names", return_value=set()),
    ):
        status, payload = asyncio.run(asgi_get("/api/search", {"q": "alpha", "sort": "popular"}))

    assert status == 422
    assert payload["detail"]


def test_post_search_forwards_sort_mode():
    search = AsyncMock(return_value=([], [], False, 0))
    with (
        patch("backend.app.search_all", search),
        patch("backend.app.trusted_provider_names", return_value=set()),
    ):
        response = asyncio.run(search_post(SearchRequest(q="alpha", sort="rating")))

    assert response.query == "alpha"
    assert search.await_args.kwargs["sort"] == "rating"
