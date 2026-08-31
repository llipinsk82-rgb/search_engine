from __future__ import annotations

import hashlib

from backend.models import SearchItem
from backend.providers.base import SearchProvider


class DemoProvider(SearchProvider):
    name = "demo"

    _catalog = (
        ("Studio Sample Alpha", "https://example.com/watch/alpha", 725, "1080p", ["sample", "studio"]),
        ("Independent Sample Beta", "https://example.com/watch/beta", 1260, "4K", ["sample", "independent"]),
        ("Long Form Sample", "https://example.com/watch/long", 2420, "1080p", ["sample", "long"]),
        ("Studio Sample Alpha", "https://example.com/watch/alpha-alt", 728, "4K", ["sample", "studio"]),
    )

    async def search(self, query: str, limit: int = 40) -> list[SearchItem]:
        needle = query.strip().lower()
        rows = []
        for title, url, duration, quality, tags in self._catalog:
            haystack = f"{title} {' '.join(tags)}".lower()
            if needle and needle not in haystack:
                continue

            digest = hashlib.sha1(f"{self.name}:{url}".encode()).hexdigest()[:16]
            score = 1.0 if needle and needle in title.lower() else 0.6
            rows.append(
                SearchItem(
                    id=digest,
                    provider=self.name,
                    title=title,
                    url=url,
                    duration_seconds=duration,
                    quality=quality,
                    tags=tags,
                    score=score,
                )
            )
        return rows[:limit]
