from __future__ import annotations
import unittest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from backend.app import _thumbnail_proxy_fetch, thumbnail_proxy

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

if __name__ == "__main__":
    unittest.main()
