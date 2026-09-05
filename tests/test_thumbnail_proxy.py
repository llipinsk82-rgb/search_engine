from __future__ import annotations
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from backend.app import _thumbnail_proxy_fetch, thumbnail_proxy, thumbnail_redirect
from backend.models import SearchItem

class ThumbnailProxyTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_provider_is_rejected(self):
        with self.assertRaises(HTTPException) as cm:
            await thumbnail_proxy("unknown", "https://cdn.example/a.jpg")
        self.assertEqual(cm.exception.status_code, 400)

    async def test_untrusted_thumbzilla_host_is_rejected(self):
        with self.assertRaises(HTTPException) as cm:
            await thumbnail_proxy("thumbzilla", "https://evil.example/a.jpg")
        self.assertEqual(cm.exception.status_code, 400)

    async def test_credentials_are_rejected(self):
        with self.assertRaises(HTTPException) as cm:
            await thumbnail_proxy(
                "thumbzilla", "https://user:pass@pix-cdn77.ypncdn.com/example.jpg"
            )
        self.assertEqual(cm.exception.status_code, 400)

    async def test_non_default_port_is_rejected(self):
        with self.assertRaises(HTTPException) as cm:
            await thumbnail_proxy(
                "thumbzilla", "https://pix-cdn77.ypncdn.com:8443/example.jpg"
            )
        self.assertEqual(cm.exception.status_code, 400)

    def test_redirects_are_not_followed(self):
        from urllib.error import HTTPError
        with patch("backend.app.build_opener") as build:
            opener = MagicMock()
            opener.open.side_effect = HTTPError(
                "https://pix-cdn77.ypncdn.com/example.jpg", 302, "Found", {}, None
            )
            build.return_value = opener
            with self.assertRaises(HTTPError):
                _thumbnail_proxy_fetch(
                    "thumbzilla", "https://pix-cdn77.ypncdn.com/example.jpg"
                )
            handler = build.call_args.args[0]
            self.assertIsNone(
                handler.redirect_request(None, None, 302, "Found", {}, "https://evil.example/x")
            )

    async def test_valid_proxy_response(self):
        with patch("backend.app._thumbnail_proxy_fetch", return_value=(b"jpeg", "image/jpeg")):
            response = await thumbnail_proxy(
                "thumbzilla", "https://pix-cdn77.ypncdn.com/example.jpg"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "image/jpeg")
        self.assertEqual(response.body, b"jpeg")

    async def test_thumbzilla_refresh_returns_same_origin_image(self):
        item = SearchItem(
            id="tz1", provider="thumbzilla", title="X",
            url="https://www.thumbzilla.com/watch/1/",
            thumbnail="https://pix-cdn77.ypncdn.com/old.jpg", tags=[]
        )
        fresh = "https://pix-cdn77.ypncdn.com/fresh.jpg"
        with patch("backend.app.get_item", return_value=item), \
             patch("backend.app.SitemapProvider.resolve_thumbnail", new=AsyncMock(return_value=fresh)), \
             patch("backend.app.update_item_thumbnail", return_value=True), \
             patch("backend.app._thumbnail_proxy_fetch", return_value=(b"img", "image/jpeg")):
            response = await thumbnail_redirect("tz1", refresh=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, b"img")

    async def test_tube8_refresh_redirects_to_fresh_thumbnail(self):
        item = SearchItem(
            id="t81", provider="tube8", title="X",
            url="https://www.tube8.com/porn-video/1/",
            thumbnail="https://ei-ph.t8cdn.com/old.jpg", tags=[]
        )
        fresh = "https://ei-ph.t8cdn.com/fresh.jpg"
        with patch("backend.app.get_item", return_value=item), \
             patch("backend.app.SitemapProvider.resolve_thumbnail", new=AsyncMock(return_value=fresh)), \
             patch("backend.app.update_item_thumbnail", return_value=True):
            response = await thumbnail_redirect("t81", refresh=True)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], fresh)

    def test_proxy_prefers_jpeg_for_mobile_compatibility(self):
        with patch("backend.app._thumbnail_proxy_open") as opened:
            response = MagicMock()
            response.__enter__.return_value = response
            response.__exit__.return_value = False
            response.headers.get_content_type.return_value = "image/jpeg"
            response.read.return_value = b"jpeg"
            opened.return_value = response
            _thumbnail_proxy_fetch("thumbzilla", "https://pix-cdn77.ypncdn.com/example.jpg")
            request = opened.call_args.args[0]
            self.assertTrue(request.headers["Accept"].startswith("image/jpeg"))

if __name__ == "__main__":
    unittest.main()
