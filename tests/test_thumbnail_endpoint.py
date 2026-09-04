from __future__ import annotations
import unittest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from backend.app import thumbnail_redirect
from backend.models import SearchItem

class Provider:
    name="tube8"
    resolve_thumbnail=AsyncMock(return_value="https://cdn.example/new.jpg")

class ThumbnailEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_item_is_404(self):
        with patch("backend.app.get_item",return_value=None):
            with self.assertRaises(HTTPException) as cm:
                await thumbnail_redirect("missing")
            self.assertEqual(cm.exception.status_code,404)

    async def test_resolved_thumbnail_redirects_and_updates_cache(self):
        item=SearchItem(id="x",provider="tube8",title="X",url="https://www.tube8.com/v",thumbnail="https://cdn.example/old.jpg",tags=[])
        provider=Provider()
        with patch("backend.app.get_item",return_value=item), patch("backend.app.PROVIDERS",[provider]), patch("backend.app.update_item_thumbnail") as update:
            response=await thumbnail_redirect("x")
        self.assertEqual(response.status_code,302)
        self.assertEqual(response.headers["location"],"https://cdn.example/new.jpg")
        update.assert_called_once_with("x","https://cdn.example/new.jpg")

    async def test_resolution_failure_falls_back(self):
        item=SearchItem(id="x",provider="tube8",title="X",url="https://www.tube8.com/v",thumbnail="https://cdn.example/old.jpg",tags=[])
        provider=Provider()
        provider.resolve_thumbnail=AsyncMock(side_effect=RuntimeError("upstream"))
        with patch("backend.app.get_item",return_value=item), patch("backend.app.PROVIDERS",[provider]):
            response=await thumbnail_redirect("x")
        self.assertEqual(response.headers["location"],"https://cdn.example/old.jpg")

if __name__ == "__main__":
    unittest.main()
