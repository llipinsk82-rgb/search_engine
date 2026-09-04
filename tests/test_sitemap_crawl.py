from __future__ import annotations

import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from backend.providers.sitemap import SitemapProvider


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/robots.txt":
            body = b"User-agent: *\nAllow: /\n"
            content_type = "text/plain"
        elif self.path == "/sitemap.xml":
            origin = f"http://127.0.0.1:{self.server.server_port}"
            body = f"""<?xml version="1.0" encoding="UTF-8"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
              <url><loc>{origin}/watch/1</loc></url>
            </urlset>""".encode()
            content_type = "application/xml"
        elif self.path == "/watch/1":
            body = b"""
            <html><head>
              <script type="application/ld+json">
              {
                "@context":"https://schema.org",
                "@type":"VideoObject",
                "name":"Crawler Integration Sample",
                "duration":"PT2M5S",
                "thumbnailUrl":"/thumb.jpg",
                "keywords":"integration, crawler"
              }
              </script>
              <meta property="video:height" content="720">
            </head></html>
            """
            content_type = "text/html"
        else:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        pass


class SitemapCrawlerIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    async def asyncTearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    async def test_collects_video_metadata_from_sitemap(self) -> None:
        provider = SitemapProvider(
            name="local",
            sitemap_url=f"http://127.0.0.1:{self.server.server_port}/sitemap.xml",
            max_pages=10,
            delay_seconds=0,
            timeout_seconds=2,
            obey_robots=True,
        )

        items = await provider.collect(limit=10)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.provider, "local")
        self.assertEqual(item.title, "Crawler Integration Sample")
        self.assertEqual(item.duration_seconds, 125)
        self.assertEqual(item.quality, "720p")
        self.assertEqual(item.tags, ["integration", "crawler"])

    async def test_missing_child_sitemap_does_not_abort_index(self) -> None:
        provider = SitemapProvider(
            name="local",
            sitemap_url=f"http://127.0.0.1:{self.server.server_port}/sitemap-index.xml",
            max_pages=10,
            delay_seconds=0,
            timeout_seconds=2,
            obey_robots=False,
        )
        original = provider._fetch_text

        def fake_fetch(url: str, *, timeout_seconds=None):
            if url.endswith("/sitemap-index.xml"):
                origin = f"http://127.0.0.1:{self.server.server_port}"
                return (
                    '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    f'<sitemap><loc>{origin}/missing.xml</loc></sitemap>'
                    f'<sitemap><loc>{origin}/sitemap.xml</loc></sitemap></sitemapindex>'
                )
            return original(url, timeout_seconds=timeout_seconds)

        provider._fetch_text = fake_fetch
        items = await provider.collect(limit=10)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Crawler Integration Sample")


if __name__ == "__main__":
    unittest.main()
