from __future__ import annotations
import unittest
from unittest.mock import patch
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
