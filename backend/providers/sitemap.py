from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import gzip
import json
import re
import time
import urllib.robotparser
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from backend.models import SearchItem
from backend.providers.base import SearchProvider

_USER_AGENT = "SearchEngineIndexer/0.5"
_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
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
        self.quality_hints: list[str] = []
        self._in_title = False
        self._in_jsonld = False
        self._jsonld_buffer: list[str] = []
        self._quality_depth = 0
        self._quality_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {str(k).lower(): (v or "") for k, v in attrs}
        tag = tag.lower()

        if self._quality_depth > 0:
            if tag not in _VOID_TAGS:
                self._quality_depth += 1
        else:
            classes = {
                item.strip().lower()
                for item in attrs_map.get("class", "").split()
                if item.strip()
            }
            if tag not in _VOID_TAGS and any(
                "quality" in item
                or "resolution" in item
                or "hd-mark" in item
                for item in classes
            ):
                self._quality_depth = 1
                self._quality_buffer = []

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

        if self._quality_depth > 0:
            self._quality_depth -= 1
            if self._quality_depth == 0:
                hint = " ".join(self._quality_buffer).strip()
                if hint:
                    self.quality_hints.append(hint)
                self._quality_buffer = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._in_jsonld:
            self._jsonld_buffer.append(data)
        if self._quality_depth > 0:
            self._quality_buffer.append(data)


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


def _quality_from_metadata(
    meta: dict[str, str],
    video: dict[str, Any] | None,
    hints: list[str] | None = None,
) -> str | None:
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

    for hint in hints or []:
        match = re.search(r"(?<!\d)(4320|2160|1440|1080|720)p\b", hint, re.IGNORECASE)
        if match:
            height = int(match.group(1))
            if height >= 4320:
                return "8K"
            if height >= 2160:
                return "4K"
            return f"{height}p"
        match = re.search(r"\b(8k|4k)\b", hint, re.IGNORECASE)
        if match:
            return match.group(1).upper()
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
        quality=_quality_from_metadata(meta, video, parser.quality_hints),
        tags=tags[:80],
        score=1.0,
    )



def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _first_xml_text(node: ElementTree.Element, name: str) -> str | None:
    for child in node.iter():
        if _local_name(child.tag) != name:
            continue
        value = (child.text or "").strip()
        if value:
            return value
    return None


def parse_sitemap_video_metadata(
    node: ElementTree.Element,
    *,
    provider: str,
) -> SearchItem | None:
    page_url = _first_xml_text(node, "loc")
    title = _first_xml_text(node, "title")
    thumbnail = _first_xml_text(node, "thumbnail_loc")
    if not page_url or not title or not thumbnail:
        return None
    if urlparse(page_url).scheme not in {"http", "https"}:
        return None

    duration = _duration_seconds(_first_xml_text(node, "duration"))
    tags: list[str] = []
    for child in node.iter():
        name = _local_name(child.tag)
        if name not in {"tag", "category"}:
            continue
        value = (child.text or "").strip()
        if value:
            tags.append(value)
    tags = list(dict.fromkeys(tags))

    item_id = hashlib.sha256(f"{provider}:{page_url}".encode("utf-8")).hexdigest()[:24]
    return SearchItem(
        id=item_id,
        provider=provider,
        title=title[:500],
        url=page_url,
        thumbnail=thumbnail,
        duration_seconds=duration,
        quality=None,
        tags=tags[:80],
        score=1.0,
    )


def needs_thumbnail_resolution(item: SearchItem) -> bool:
    if item.thumbnail is None:
        return False
    parsed = urlparse(str(item.thumbnail))
    return (
        item.provider == "tube8"
        and parsed.hostname == "ei-ph.t8cdn.com"
        and parsed.path.startswith("/m=")
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
        sync_mode: str = "incremental",
        sitemap_include_pattern: str | None = None,
        sitemap_child_order: str = "listed",
        fetch_concurrency: int = 1,
        backfill_batch_size: int | None = None,
        backfill_priority: int = 100,
        backfill_max_records: int | None = None,
    ) -> None:
        self.name = name.strip()
        self.sitemap_url = sitemap_url.strip()
        self.max_pages = max(1, int(max_pages))
        self.delay_seconds = max(0.0, float(delay_seconds))
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self.obey_robots = bool(obey_robots)
        self.sync_mode = sync_mode.strip().lower()
        self.sitemap_include_pattern = (
            re.compile(sitemap_include_pattern)
            if sitemap_include_pattern
            else None
        )
        self.sitemap_child_order = sitemap_child_order.strip().lower()
        self.fetch_concurrency = max(1, min(16, int(fetch_concurrency)))
        self.backfill_batch_size = (
            max(1, int(backfill_batch_size))
            if backfill_batch_size is not None
            else None
        )
        self.backfill_priority = int(backfill_priority)
        self.backfill_max_records = (
            max(1, int(backfill_max_records))
            if backfill_max_records is not None
            else None
        )
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

        if not self.name:
            raise ValueError("provider name cannot be empty")
        if urlparse(self.sitemap_url).scheme not in {"http", "https"}:
            raise ValueError("sitemap_url must use http or https")
        if self.sync_mode not in {"incremental", "snapshot"}:
            raise ValueError("sync_mode must be 'incremental' or 'snapshot'")
        if self.sitemap_child_order not in {"listed", "reverse"}:
            raise ValueError("sitemap_child_order must be 'listed' or 'reverse'")

    def _fetch_text(self, url: str, *, timeout_seconds: float | None = None) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xml,text/xml,application/xhtml+xml;q=0.9,*/*;q=0.5",
            },
        )
        timeout = self.timeout_seconds if timeout_seconds is None else max(1.0, float(timeout_seconds))
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read()
            if urlparse(response.geturl()).path.lower().endswith(".gz") or body[:2] == b"\x1f\x8b":
                body = gzip.decompress(body)
            return body.decode(charset, errors="replace")

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

    def _sitemap_records(
        self,
        url: str,
        limit: int,
        *,
        offset: int = 0,
        deadline: float | None = None,
    ) -> list[tuple[str, SearchItem | None]]:
        pending = [url]
        seen_sitemaps: set[str] = set()
        records: list[tuple[str, SearchItem | None]] = []
        skipped = 0
        target_offset = max(0, int(offset))

        while pending and len(records) < limit:
            if deadline is not None and time.monotonic() >= deadline:
                break
            current = pending.pop(0)
            if current in seen_sitemaps:
                continue
            seen_sitemaps.add(current)

            timeout = None
            if deadline is not None:
                timeout = max(1.0, min(self.timeout_seconds, deadline - time.monotonic()))
            try:
                xml = self._fetch_text(current, timeout_seconds=timeout)
            except HTTPError as exc:
                # Some sitemap indexes briefly advertise child shards that are
                # not published yet or were just rotated out. Skip only missing
                # child shards; root and all other HTTP failures remain fatal.
                if current != url and exc.code == 404:
                    continue
                raise
            root = ElementTree.fromstring(xml)
            root_name = _local_name(root.tag)

            if root_name == "sitemapindex":
                children: list[str] = []
                for node in root.iter():
                    if _local_name(node.tag) != "loc":
                        continue
                    location = (node.text or "").strip()
                    if not location or urlparse(location).scheme not in {"http", "https"}:
                        continue
                    if (
                        self.sitemap_include_pattern is not None
                        and self.sitemap_include_pattern.search(location) is None
                    ):
                        continue
                    if location not in seen_sitemaps:
                        children.append(location)
                if self.sitemap_child_order == "reverse":
                    children.reverse()
                pending.extend(children)
                continue

            url_nodes = [node for node in root.iter() if _local_name(node.tag) == "url"]
            for node in url_nodes:
                page_url = _first_xml_text(node, "loc")
                if not page_url or urlparse(page_url).scheme not in {"http", "https"}:
                    continue
                if skipped < target_offset:
                    skipped += 1
                    continue
                sitemap_item = parse_sitemap_video_metadata(
                    node,
                    provider=self.name,
                )
                records.append((page_url, sitemap_item))
                if len(records) >= limit:
                    break

        return records

    def _fetch_page_item(self, page_url: str) -> SearchItem | None:
        try:
            html = self._fetch_text(page_url)
            return parse_video_metadata(
                html,
                provider=self.name,
                page_url=page_url,
            )
        except Exception:
            return None
        finally:
            if self.delay_seconds:
                time.sleep(self.delay_seconds)

    def _materialize_records(
        self,
        records: list[tuple[str, SearchItem | None]],
    ) -> list[SearchItem]:
        ordered: list[SearchItem | None] = [None] * len(records)
        html_jobs: list[tuple[int, str]] = []

        for index, (page_url, sitemap_item) in enumerate(records):
            if not self._allowed(page_url):
                continue
            if sitemap_item is not None:
                ordered[index] = sitemap_item
            else:
                html_jobs.append((index, page_url))

        if html_jobs:
            urls = [page_url for _, page_url in html_jobs]
            if self.fetch_concurrency == 1:
                fetched = [self._fetch_page_item(page_url) for page_url in urls]
            else:
                with ThreadPoolExecutor(max_workers=self.fetch_concurrency) as executor:
                    fetched = list(executor.map(self._fetch_page_item, urls))
            for (index, _), item in zip(html_jobs, fetched):
                ordered[index] = item

        return [item for item in ordered if item is not None]

    def _materialize_records_bounded(
        self,
        records: list[tuple[str, SearchItem | None]],
        *,
        deadline: float,
    ) -> tuple[list[SearchItem], int]:
        """Materialize records in small waves and stop near a wall-clock deadline.

        Only fully processed records count toward the returned cursor advance, so
        unstarted URLs are retried on the next scheduled backfill rather than
        silently skipped. A network wave is at most fetch_concurrency URLs, which
        bounds deadline overshoot to roughly one request timeout.
        """
        items: list[SearchItem] = []
        consumed = 0
        wave_size = max(1, self.fetch_concurrency)

        while consumed < len(records):
            if time.monotonic() >= deadline:
                break
            wave = records[consumed : consumed + wave_size]
            ordered: list[SearchItem | None] = [None] * len(wave)
            html_jobs: list[tuple[int, str]] = []
            processed = 0

            for index, (page_url, sitemap_item) in enumerate(wave):
                if time.monotonic() >= deadline:
                    break
                if not self._allowed(page_url):
                    processed += 1
                    continue
                if sitemap_item is not None:
                    ordered[index] = sitemap_item
                else:
                    html_jobs.append((index, page_url))
                processed += 1

            if processed == 0:
                break
            html_jobs = [(index, url) for index, url in html_jobs if index < processed]
            if html_jobs:
                urls = [page_url for _, page_url in html_jobs]
                if self.fetch_concurrency == 1 or len(urls) == 1:
                    fetched = [self._fetch_page_item(page_url) for page_url in urls]
                else:
                    with ThreadPoolExecutor(max_workers=min(self.fetch_concurrency, len(urls))) as executor:
                        fetched = list(executor.map(self._fetch_page_item, urls))
                for (index, _), item in zip(html_jobs, fetched):
                    ordered[index] = item

            items.extend(item for item in ordered[:processed] if item is not None)
            consumed += processed

        return items, consumed

    def _collect_sync(self, limit: int) -> list[SearchItem]:
        page_limit = min(max(1, limit), self.max_pages)
        records = self._sitemap_records(self.sitemap_url, page_limit)
        return self._materialize_records(records)

    def _resolve_thumbnail_sync(
        self,
        item: SearchItem,
        *,
        force: bool = False,
    ) -> str | None:
        current = str(item.thumbnail) if item.thumbnail else None
        if not force and not needs_thumbnail_resolution(item):
            return current
        item_host = urlparse(str(item.url)).hostname
        sitemap_host = urlparse(self.sitemap_url).hostname
        if not item_host or item_host != sitemap_host:
            return current
        try:
            html = self._fetch_text(str(item.url))
            parsed = parse_video_metadata(
                html,
                provider=self.name,
                page_url=str(item.url),
            )
        except Exception:
            return current
        if parsed is None or parsed.thumbnail is None:
            return current
        return str(parsed.thumbnail)

    async def resolve_thumbnail(
        self,
        item: SearchItem,
        *,
        force: bool = False,
    ) -> str | None:
        return await asyncio.to_thread(
            self._resolve_thumbnail_sync,
            item,
            force=force,
        )

    async def collect(self, limit: int = 1000) -> list[SearchItem]:
        return await asyncio.to_thread(self._collect_sync, limit)

    def _collect_page_sync(
        self,
        offset: int,
        limit: int,
    ) -> tuple[list[SearchItem], int]:
        start_offset = max(0, int(offset))
        page_limit = min(max(1, limit), self.max_pages)
        records = self._sitemap_records(
            self.sitemap_url,
            page_limit,
            offset=start_offset,
        )
        items = self._materialize_records(records)
        return items, start_offset + len(records)

    async def collect_page(
        self,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[SearchItem], int]:
        return await asyncio.to_thread(self._collect_page_sync, offset, limit)


    def _collect_page_bounded_sync(
        self,
        offset: int,
        limit: int,
        max_seconds: float,
    ) -> tuple[list[SearchItem], int]:
        start_offset = max(0, int(offset))
        page_limit = min(max(1, limit), self.max_pages)
        deadline = time.monotonic() + max(0.0, float(max_seconds))
        records = self._sitemap_records(
            self.sitemap_url,
            page_limit,
            offset=start_offset,
            deadline=deadline,
        )
        items, consumed = self._materialize_records_bounded(records, deadline=deadline)
        return items, start_offset + consumed

    async def collect_page_bounded(
        self,
        *,
        offset: int,
        limit: int,
        max_seconds: float,
    ) -> tuple[list[SearchItem], int]:
        return await asyncio.to_thread(
            self._collect_page_bounded_sync,
            offset,
            limit,
            max_seconds,
        )

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
