from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
import urllib.robotparser
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from backend.models import SearchItem
from backend.providers.base import SearchProvider

_USER_AGENT = "SearchEngineIndexer/0.3"
_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$",
    re.IGNORECASE,
)


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title_parts: list[str] = []
        self.jsonld_parts: list[str] = []
        self._in_title = False
        self._in_jsonld = False
        self._jsonld_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {str(k).lower(): (v or "") for k, v in attrs}
        tag = tag.lower()

        if tag == "meta":
            key = (
                attrs_map.get("property")
                or attrs_map.get("name")
                or attrs_map.get("itemprop")
                or ""
            ).strip().lower()
            content = attrs_map.get("content", "").strip()
            if key and content and key not in self.meta:
                self.meta[key] = content
            return

        if tag == "title":
            self._in_title = True
            return

        if tag == "script":
            script_type = attrs_map.get("type", "").split(";", 1)[0].strip().lower()
            if script_type == "application/ld+json":
                self._in_jsonld = True
                self._jsonld_buffer = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_jsonld:
            raw = "".join(self._jsonld_buffer).strip()
            if raw:
                self.jsonld_parts.append(raw)
            self._jsonld_buffer = []
            self._in_jsonld = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._in_jsonld:
            self._jsonld_buffer.append(data)


def _duration_seconds(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return max(0, int(value))

    raw = str(value).strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)

    match = _DURATION_RE.match(raw)
    if not match:
        return None

    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = float(match.group("seconds") or 0)
    return int(days * 86400 + hours * 3600 + minutes * 60 + seconds)


def _flatten_jsonld(value: Any):
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if graph is not None:
            yield from _flatten_jsonld(graph)
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_jsonld(item)


def _is_video_object(value: dict[str, Any]) -> bool:
    kind = value.get("@type")
    if isinstance(kind, str):
        return kind.lower() == "videoobject"
    if isinstance(kind, list):
        return any(str(item).lower() == "videoobject" for item in kind)
    return False


def _first_string(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, list):
        for item in value:
            candidate = _first_string(item)
            if candidate:
                return candidate
    return None


def _keywords(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[,;]", value)
        return [part.strip() for part in parts if part.strip()]
    return []


def _quality_from_metadata(meta: dict[str, str], video: dict[str, Any] | None) -> str | None:
    candidates: list[Any] = []
    if video:
        candidates.extend([video.get("height"), video.get("videoHeight")])
    candidates.extend([meta.get("video:height"), meta.get("og:video:height")])

    for value in candidates:
        try:
            height = int(str(value))
        except (TypeError, ValueError):
            continue
        if height >= 4320:
            return "8K"
        if height >= 2160:
            return "4K"
        if height >= 1440:
            return "1440p"
        if height >= 1080:
            return "1080p"
        if height >= 720:
            return "720p"
    return None


def parse_video_metadata(
    html: str,
    *,
    provider: str,
    page_url: str,
) -> SearchItem | None:
    parser = _MetadataParser()
    parser.feed(html)

    video: dict[str, Any] | None = None
    for raw in parser.jsonld_parts:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for obj in _flatten_jsonld(parsed):
            if _is_video_object(obj):
                video = obj
                break
        if video:
            break

    meta = parser.meta
    title = (
        _first_string(video.get("name") if video else None)
        or meta.get("og:title")
        or meta.get("twitter:title")
        or " ".join(parser.title_parts).strip()
    )
    if not title:
        return None

    thumbnail = (
        _first_string(video.get("thumbnailUrl") if video else None)
        or meta.get("og:image")
        or meta.get("twitter:image")
    )
    if thumbnail:
        thumbnail = urljoin(page_url, thumbnail)

    duration = _duration_seconds(video.get("duration") if video else None)
    if duration is None:
        duration = _duration_seconds(
            meta.get("video:duration")
            or meta.get("og:video:duration")
            or meta.get("og:duration")
        )

    tags: list[str] = []
    if video:
        tags.extend(_keywords(video.get("keywords")))
    tags.extend(_keywords(meta.get("keywords")))
    tags = list(dict.fromkeys(tag for tag in tags if tag))

    item_id = hashlib.sha256(f"{provider}:{page_url}".encode("utf-8")).hexdigest()[:24]
    return SearchItem(
        id=item_id,
        provider=provider,
        title=title[:500],
        url=page_url,
        thumbnail=thumbnail,
        duration_seconds=duration,
        quality=_quality_from_metadata(meta, video),
        tags=tags[:80],
        score=1.0,
    )


class SitemapProvider(SearchProvider):
    def __init__(
        self,
        *,
        name: str,
        sitemap_url: str,
        max_pages: int = 1000,
        delay_seconds: float = 0.25,
        timeout_seconds: float = 15.0,
        obey_robots: bool = True,
    ) -> None:
        self.name = name.strip()
        self.sitemap_url = sitemap_url.strip()
        self.max_pages = max(1, int(max_pages))
        self.delay_seconds = max(0.0, float(delay_seconds))
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self.obey_robots = bool(obey_robots)
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

        if not self.name:
            raise ValueError("provider name cannot be empty")
        if urlparse(self.sitemap_url).scheme not in {"http", "https"}:
            raise ValueError("sitemap_url must use http or https")

    def _fetch_text(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xml,text/xml,application/xhtml+xml;q=0.9,*/*;q=0.5",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")

    def _robots_for(self, page_url: str) -> urllib.robotparser.RobotFileParser | None:
        parsed = urlparse(page_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin in self._robots:
            return self._robots[origin]

        robots_url = f"{origin}/robots.txt"
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        try:
            text = self._fetch_text(robots_url)
            parser.parse(text.splitlines())
            self._robots[origin] = parser
        except Exception:
            self._robots[origin] = None
        return self._robots[origin]

    def _allowed(self, page_url: str) -> bool:
        if not self.obey_robots:
            return True
        parser = self._robots_for(page_url)
        if parser is None:
            return True
        return parser.can_fetch(_USER_AGENT, page_url)

    def _sitemap_urls(self, url: str, limit: int) -> list[str]:
        pending = [url]
        seen_sitemaps: set[str] = set()
        pages: list[str] = []

        while pending and len(pages) < limit:
            current = pending.pop(0)
            if current in seen_sitemaps:
                continue
            seen_sitemaps.add(current)

            xml = self._fetch_text(current)
            root = ElementTree.fromstring(xml)
            root_name = root.tag.rsplit("}", 1)[-1].lower()

            locations = [
                (node.text or "").strip()
                for node in root.iter()
                if node.tag.rsplit("}", 1)[-1].lower() == "loc" and (node.text or "").strip()
            ]

            if root_name == "sitemapindex":
                for location in locations:
                    if location not in seen_sitemaps:
                        pending.append(location)
            else:
                for location in locations:
                    if urlparse(location).scheme in {"http", "https"}:
                        pages.append(location)
                        if len(pages) >= limit:
                            break

        return pages

    def _collect_sync(self, limit: int) -> list[SearchItem]:
        page_limit = min(max(1, limit), self.max_pages)
        pages = self._sitemap_urls(self.sitemap_url, page_limit)
        items: list[SearchItem] = []

        for page_url in pages:
            if not self._allowed(page_url):
                continue
            try:
                html = self._fetch_text(page_url)
                item = parse_video_metadata(
                    html,
                    provider=self.name,
                    page_url=page_url,
                )
                if item is not None:
                    items.append(item)
            except Exception:
                continue

            if self.delay_seconds:
                time.sleep(self.delay_seconds)

        return items

    async def collect(self, limit: int = 1000) -> list[SearchItem]:
        return await asyncio.to_thread(self._collect_sync, limit)

    async def search(self, query: str, limit: int = 40) -> list[SearchItem]:
        items = await self.collect(limit=max(limit * 5, 100))
        needle = query.strip().lower()
        if not needle:
            return items[:limit]

        matched = [
            item
            for item in items
            if needle in f"{item.title} {' '.join(item.tags)}".lower()
        ]
        return matched[:limit]
