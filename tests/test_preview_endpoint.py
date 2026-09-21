from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.app import resolve_preview
from backend.models import SearchItem


class FakeAdapter:
    def __init__(self, name: str, *, enabled: bool = True, value: str | None = None):
        self.name = name
        self.preview_resolution = enabled
        self.extract_preview = AsyncMock(return_value=value)


class PreviewResolutionEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_item_is_404(self):
        with patch("backend.app.get_item", return_value=None):
            with self.assertRaises(HTTPException) as cm:
                await resolve_preview("missing")
        self.assertEqual(cm.exception.status_code, 404)

    async def test_ephemeral_preview_is_resolved_fresh_and_not_persisted(self):
        stale = "https://ev-ph.t8cdn.com/old.mp4?validto=1"
        fresh = "https://ev-ph.t8cdn.com/new.mp4?validto=9999999999"
        item = SearchItem(
            id="x",
            provider="tube8",
            title="Tiny sample",
            url="https://www.tube8.com/porn-video/123/",
            preview_url=stale,
        )
        adapter = FakeAdapter("tube8", value=fresh)
        with (
            patch("backend.app.get_item", return_value=item),
            patch("backend.app.LIVE_ADAPTERS", [adapter]),
            patch("backend.app.media_url_allowed", return_value=True),
        ):
            payload = await resolve_preview("x")
        self.assertEqual(payload, {"preview_url": fresh})
        adapter.extract_preview.assert_awaited_once_with(item)
        self.assertEqual(str(item.preview_url), stale)

    async def test_non_resolvable_provider_is_404(self):
        item = SearchItem(
            id="x",
            provider="tube8",
            title="X",
            url="https://www.tube8.com/porn-video/123/",
        )
        adapter = FakeAdapter("tube8", enabled=False, value="https://ev-ph.t8cdn.com/x.mp4")
        with patch("backend.app.get_item", return_value=item), patch("backend.app.LIVE_ADAPTERS", [adapter]):
            with self.assertRaises(HTTPException) as cm:
                await resolve_preview("x")
        self.assertEqual(cm.exception.status_code, 404)

    async def test_policy_rejected_resolution_is_502(self):
        item = SearchItem(
            id="x",
            provider="tube8",
            title="X",
            url="https://www.tube8.com/porn-video/123/",
        )
        adapter = FakeAdapter("tube8", value="https://evil.example/x.mp4")
        with (
            patch("backend.app.get_item", return_value=item),
            patch("backend.app.LIVE_ADAPTERS", [adapter]),
            patch("backend.app.media_url_allowed", return_value=False),
        ):
            with self.assertRaises(HTTPException) as cm:
                await resolve_preview("x")
        self.assertEqual(cm.exception.status_code, 502)

    async def test_upstream_failure_is_502(self):
        item = SearchItem(
            id="x",
            provider="tube8",
            title="X",
            url="https://www.tube8.com/porn-video/123/",
        )
        adapter = FakeAdapter("tube8", value=None)
        adapter.extract_preview = AsyncMock(side_effect=RuntimeError("upstream"))
        with patch("backend.app.get_item", return_value=item), patch("backend.app.LIVE_ADAPTERS", [adapter]):
            with self.assertRaises(HTTPException) as cm:
                await resolve_preview("x")
        self.assertEqual(cm.exception.status_code, 502)


if __name__ == "__main__":
    unittest.main()
