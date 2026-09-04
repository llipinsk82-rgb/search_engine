from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import html
import json
import logging
import re
import threading
import time
from typing import Protocol
from urllib.parse import quote, quote_plus, urlencode, urljoin
from urllib.request import Request, urlopen

try:
    from websockets.sync.client import connect as websocket_connect
except ImportError:
    websocket_connect = None

from backend.index import merge_provider_batches
from backend.models import SearchItem
from backend.settings import DB_PATH
from backend.source_policy import normalize_trusted_live_item

logger = logging.getLogger(__name__)
_LIVE_CACHE_LOCK = threading.Lock()
_USER_AGENT = "SearchEngineLive/0.6"

_RESULTS_RE = re.compile(r"([\d][\d,.\s]*)\s+results\b", re.IGNORECASE)
_CARD_RE = re.compile(
    r'<div\s+id="video_[^"]+"(?P<body>.*?)'
    r'<script[^>]*>\s*xv\.thumbs\.prepareVideo\([^)]*\);\s*</script>',
    re.IGNORECASE | re.DOTALL,
)
_HREF_RE = re.compile(r'href="(?P<url>/video(?:[.-])[^"]+)"', re.IGNORECASE)
_TITLE_RE = re.compile(r'\btitle="(?P<title>[^"]+)"', re.IGNORECASE)
_THUMB_RE = re.compile(r'\bdata-src="(?P<thumb>https?://[^"]+)"', re.IGNORECASE)
_DURATION_RE = re.compile(r"\b(?P<minutes>\d{1,5})\s*min\b", re.IGNORECASE)
_QUALITY_RE = re.compile(
    r"\b(?P<quality>8k|4k|4320p|2160p|1440p|1080p|720p|480p|360p)\b",
    re.IGNORECASE,
)

_PORNHUB_CARD_RE = re.compile(
    r'<li\s+class="pcVideoListItem[^"]*"(?P<body>.*?)</li>',
    re.IGNORECASE | re.DOTALL,
)
_PORNHUB_URL_RE = re.compile(
    r'href="(?P<url>/view_video\.php\?viewkey=[^"]+)"', re.IGNORECASE
)
_PORNHUB_TITLE_RE = re.compile(
    r'<a[^>]+href="/view_video\.php\?viewkey=[^"]+"[^>]+title="(?P<title>[^"]+)"',
    re.IGNORECASE | re.DOTALL,
)
_PORNHUB_THUMB_RE = re.compile(
    r'<img[^>]+src="(?P<thumb>https?://[^"]+)"', re.IGNORECASE | re.DOTALL
)
_PORNHUB_DURATION_RE = re.compile(
    r'<var[^>]+class="[^"]*duration[^"]*"[^>]*>(?P<duration>\d{1,3}:\d{2}(?::\d{2})?)</var>',
    re.IGNORECASE,
)
_PORNHUB_PREVIEW_RE = re.compile(
    r'data-mediabook="(?P<preview>https?://[^"]+)"', re.IGNORECASE
)

_SPANK_CARD_RE = re.compile(
    r'data-testid="video-item"(?P<body>.*?)(?=data-testid="video-item"|\Z)',
    re.IGNORECASE | re.DOTALL,
)
_SPANK_URL_RE = re.compile(r'href="(?P<url>/[^"]+/video/[^"]+)"', re.IGNORECASE)
_SPANK_THUMB_RE = re.compile(
    r'<img[^>]+src="(?P<thumb>https?://[^"]+)"[^>]+alt="(?P<title>[^"]+)"',
    re.IGNORECASE | re.DOTALL,
)
_SPANK_PREVIEW_RE = re.compile(
    r'<source[^>]+data-src="(?P<preview>https?://[^"]+\.mp4[^"]*)"',
    re.IGNORECASE | re.DOTALL,
)
_SPANK_LENGTH_RE = re.compile(
    r'data-testid="video-item-length"[^>]*>\s*(?P<duration>\d{1,4})m\s*<',
    re.IGNORECASE | re.DOTALL,
)
_SPANK_RES_RE = re.compile(
    r'data-testid="video-item-resolution"[^>]*>\s*(?P<quality>[^<]+?)\s*<',
    re.IGNORECASE | re.DOTALL,
)

_XHAMSTER_ANCHOR_RE = re.compile(
    r'<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>', re.IGNORECASE | re.DOTALL
)
_XHAMSTER_URL_RE = re.compile(
    r'\bhref="(?P<url>https://(?:www\.)?xhamster\.com/videos/[^"]+)"', re.IGNORECASE
)
_XHAMSTER_PREVIEW_RE = re.compile(
    r'\bdata-previewvideo="(?P<preview>https://[^"]+\.mp4[^"]*)"', re.IGNORECASE
)
_XHAMSTER_TITLE_RE = re.compile(r'\baria-label="(?P<title>[^"]+)"', re.IGNORECASE)
_XHAMSTER_THUMB_RE = re.compile(
    r'<img[^>]+\bsrc="(?P<thumb>https://[^"]+)"', re.IGNORECASE | re.DOTALL
)

_YOUJIZZ_CARD_RE = re.compile(
    r'<div\b[^>]*class="[^"]*\bvideo-item\b[^"]*"[^>]*>(?P<body>.*?)'
    r'(?=<div\b[^>]*class="[^"]*\bvideo-item\b[^"]*"|\Z)',
    re.IGNORECASE | re.DOTALL,
)
_YOUJIZZ_FRAME_RE = re.compile(
    r'<a\b(?P<attrs>[^>]*class="[^"]*\bframe\b[^"]*\bvideo\b[^"]*"[^>]*)>',
    re.IGNORECASE | re.DOTALL,
)
_YOUJIZZ_URL_RE = re.compile(r'\bhref="(?P<url>/videos/[^"]+)"', re.IGNORECASE)
_YOUJIZZ_PREVIEW_RE = re.compile(r'\bdata-clip="(?P<preview>[^"]+)"', re.IGNORECASE)
_YOUJIZZ_THUMB_RE = re.compile(
    r'<img[^>]+\bdata-original="(?P<thumb>[^"]+)"', re.IGNORECASE | re.DOTALL
)
_YOUJIZZ_TITLE_RE = re.compile(
    r'<div[^>]+class="[^"]*\bvideo-title\b[^"]*"[^>]*>\s*'
    r'(?:<a[^>]*>)?(?P<title>.*?)(?:</a>)?\s*</div>',
    re.IGNORECASE | re.DOTALL,
)
_YOUJIZZ_DURATION_RE = re.compile(
    r'<span[^>]+class="[^"]*\btime\b[^"]*"[^>]*>(?:.*?&nbsp;)?\s*'
    r'(?P<duration>\d{1,3}:\d{2}(?::\d{2})?)\s*</span>',
    re.IGNORECASE | re.DOTALL,
)

_PORNONE_CARD_RE = re.compile(
    r'<a\b(?P<attrs>[^>]*class="[^"]*\bvideocard\b[^"]*"[^>]*)>(?P<body>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_PORNONE_URL_RE = re.compile(
    r'\bhref="(?P<url>https://(?:www\.)?pornone\.com/[^"]+)"', re.IGNORECASE
)
_PORNONE_TITLE_RE = re.compile(
    r'<div[^>]+class="[^"]*\bvideotitle\b[^"]*"[^>]*>(?P<title>.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)
_PORNONE_THUMB_TAG_RE = re.compile(
    r'<img\b(?P<attrs>[^>]*class="[^"]*\bthumbimg\b[^"]*"[^>]*)>',
    re.IGNORECASE | re.DOTALL,
)
_PORNONE_DATA_SRC_RE = re.compile(r'\bdata-src="(?P<src>https?://[^"]+)"', re.IGNORECASE)
_PORNONE_SRC_RE = re.compile(r'\bsrc="(?P<src>https?://[^"]+)"', re.IGNORECASE)
_PORNONE_DURATION_RE = re.compile(
    r'class="[^"]*\bdurlabel\b[^"]*"[^>]*>(?:\s*<[^>]+>)*\s*'
    r'(?P<duration>\d{1,3}:\d{2}(?::\d{2})?)',
    re.IGNORECASE | re.DOTALL,
)

_HQ_CARD_RE = re.compile(
    r'<section\b[^>]*class="[^"]*\bbox\b[^"]*\bfeature\b[^"]*"[^>]*>(?P<body>.*?)</section>',
    re.IGNORECASE | re.DOTALL,
)
_HQ_URL_RE = re.compile(r'href="(?P<url>/hdporn/[^"]+\.html)"', re.IGNORECASE)
_HQ_IMG_RE = re.compile(
    r'<img[^>]+\bsrc="(?P<thumb>(?://|https?://)[^"]+_main\.jpg)"[^>]+\balt="(?P<title>[^"]+)"',
    re.IGNORECASE | re.DOTALL,
)
_HQ_DURATION_RE = re.compile(
    r'<span[^>]+class="[^"]*\bfa-clock-o\b[^"]*"[^>]*>\s*'
    r'(?:(?P<h>\d+)h\s*)?(?:(?P<m>\d+)m\s*)?(?:(?P<s>\d+)s)?\s*</span>',
    re.IGNORECASE,
)

_THUMBZILLA_CARD_RE = re.compile(
    r'<article\b(?P<attrs>[^>]*class=["\'][^"\']*\bvideo-box\b[^"\']*["\'][^>]*)>(?P<body>.*?)</article>',
    re.IGNORECASE | re.DOTALL,
)
_THUMBZILLA_URL_RE = re.compile(r'\bhref=["\'](?P<url>/watch/[0-9]+/)["\']', re.IGNORECASE)
_THUMBZILLA_TITLE_RE = re.compile(r'\baria-label=["\'](?P<title>[^"\']+)["\']', re.IGNORECASE)
_THUMBZILLA_IMG_RE = re.compile(r'<img\b(?P<attrs>[^>]*)>', re.IGNORECASE | re.DOTALL)
_THUMBZILLA_DATA_SRC_RE = re.compile(r'\bdata-src=["\'](?P<src>https?://[^"\']+)["\']', re.IGNORECASE)
_THUMBZILLA_POSTER_RE = re.compile(r'\bdata-poster=["\'](?P<src>https?://[^"\']+)["\']', re.IGNORECASE)
_THUMBZILLA_PREVIEW_RE = re.compile(r'\bdata-mediabook=["\'](?P<preview>https?://[^"\']+)["\']', re.IGNORECASE)
_THUMBZILLA_DURATION_RE = re.compile(r'\b(?P<duration>\d{1,3}:\d{2}(?::\d{2})?)\b')

_TUBE8_CARD_RE = re.compile(
    r'<article\s+class="video-box[^"]*"(?P<body>.*?)</article>', re.IGNORECASE | re.DOTALL
)
_TUBE8_URL_RE = re.compile(r'href="(?P<url>/porn-video/[0-9]+/)"', re.IGNORECASE)
_TUBE8_TITLE_RE = re.compile(
    r'class="video-title-text[^"]*"[^>]*>\s*<span>(?P<title>.*?)</span>',
    re.IGNORECASE | re.DOTALL,
)
_TUBE8_THUMB_RE = re.compile(
    r'<img[^>]+(?:data-src|data-poster)="(?P<thumb>https?://[^"]+)"',
    re.IGNORECASE | re.DOTALL,
)
_TUBE8_PREVIEW_RE = re.compile(r'data-mediabook="(?P<preview>https?://[^"]+)"', re.IGNORECASE)
_TUBE8_DURATION_RE = re.compile(
    r'class="video-duration[^"]*"[^>]*>.*?<span>\s*(?P<duration>\d{1,3}:\d{2}(?::\d{2})?)\s*</span>',
    re.IGNORECASE | re.DOTALL,
)
_TUBE8_QUALITY_RE = re.compile(
    r'class="[^"]*(?:max-quality|video-hd-mark)[^"]*"[^>]*>\s*(?P<quality>4K|8K|[0-9]{3,4}p|HD)\s*<',
    re.IGNORECASE | re.DOTALL,
)
_TUBE8_TOTAL_RE = re.compile(r'\bsearchCount\s*:\s*(?P<total>[0-9]+)', re.IGNORECASE)

_TNA_CARD_RE = re.compile(
    r'<div\s+data-vid="(?P<vid>[0-9]+)"(?P<body>.*?)(?=<div\s+data-vid="|\Z)',
    re.IGNORECASE | re.DOTALL,
)
_TNA_URL_RE = re.compile(
    r'<a[^>]+class="[^"]*\bvideo-thumb\b[^"]*"[^>]+href="(?P<url>https://www\.tnaflix\.com/[^"]+/video[0-9]+)"[^>]*>',
    re.IGNORECASE | re.DOTALL,
)
_TNA_PREVIEW_RE = re.compile(r'\bdata-trailer="(?P<preview>https?://[^"]+)"', re.IGNORECASE)
_TNA_THUMB_RE = re.compile(
    r'<img[^>]+(?:data-src|src)="(?P<thumb>https?://[^"]+)"[^>]+alt="(?P<title>[^"]+)"',
    re.IGNORECASE | re.DOTALL,
)
_TNA_DURATION_RE = re.compile(
    r'class="thumb-icon\s+video-duration"[^>]*>\s*(?P<duration>[0-9]{1,3}:[0-9]{2}(?::[0-9]{2})?)\s*<',
    re.IGNORECASE,
)
_TNA_QUALITY_RE = re.compile(
    r'class="thumb-icon\s+max-quality"[^>]*>\s*(?P<quality>4K|8K|[0-9]{3,4}p|HD)\s*<',
    re.IGNORECASE,
)


@dataclass(slots=True)
class LiveProviderResult:
    provider: str
    items: list[SearchItem]
    total: int | None
    page: int
    elapsed_ms: int
    error: str | None = None


@dataclass(slots=True)
class LiveRefreshResult:
    providers: list[LiveProviderResult]
    cached_items: int


class LiveAdapter(Protocol):
    name: str

    async def search(
        self, query: str, *, page: int = 1, limit: int = 24
    ) -> LiveProviderResult: ...


def _clean_text(value: object) -> str:
    text = str(value or "")
    text = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
    if any(marker in text for marker in ("â", "Ã", "Â")):
        try:
            text = text.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _item_id(provider: str, page_url: str) -> str:
    return hashlib.sha256(f"{provider}:{page_url}".encode("utf-8")).hexdigest()[:24]


def _duration_minutes(raw: str) -> int | None:
    match = _DURATION_RE.search(raw)
    return int(match.group("minutes")) * 60 if match else None


def _duration_clock(raw: str) -> int | None:
    parts = raw.strip().split(":")
    if len(parts) not in {2, 3} or not all(part.isdigit() for part in parts):
        return None
    values = [int(part) for part in parts]
    if len(values) == 2:
        return values[0] * 60 + values[1]
    return values[0] * 3600 + values[1] * 60 + values[2]


def _normalize_quality(value: str | None) -> str | None:
    if not value:
        return None
    value = _clean_text(value)
    if not value:
        return None
    upper = value.upper()
    if upper in {"HD", "4K", "8K"}:
        return upper
    return value.lower()


def _https_media_url(value: str) -> str:
    resolved = html.unescape(value).strip()
    return f"https:{resolved}" if resolved.startswith("//") else resolved


def parse_reported_total(raw_html: str) -> int | None:
    match = _RESULTS_RE.search(raw_html)
    if match is None:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    return int(digits) if digits else None


def parse_xv_family_listing(
    raw_html: str, *, provider: str, base_url: str, limit: int
) -> list[SearchItem]:
    items: list[SearchItem] = []
    seen: set[str] = set()
    for match in _CARD_RE.finditer(raw_html):
        block = match.group("body")
        href = _HREF_RE.search(block)
        title = _TITLE_RE.search(block)
        thumb = _THUMB_RE.search(block)
        if href is None or title is None:
            continue
        page_url = urljoin(base_url, html.unescape(href.group("url")))
        if page_url in seen:
            continue
        seen.add(page_url)
        quality_match = _QUALITY_RE.search(block)
        items.append(
            SearchItem(
                id=_item_id(provider, page_url),
                provider=provider,
                title=_clean_text(title.group("title"))[:500],
                url=page_url,
                thumbnail=html.unescape(thumb.group("thumb")) if thumb else None,
                duration_seconds=_duration_minutes(block),
                quality=_normalize_quality(quality_match.group("quality") if quality_match else None),
                tags=[],
                score=1.0,
            )
        )
        if len(items) >= limit:
            break
    return items


def parse_xhamster_listing(raw_html: str, *, limit: int) -> list[SearchItem]:
    items: list[SearchItem] = []
    seen: set[str] = set()
    for match in _XHAMSTER_ANCHOR_RE.finditer(raw_html):
        attrs = match.group("attrs")
        if "video-thumb__image-container" not in attrs or 'data-role="thumb-link"' not in attrs:
            continue
        href = _XHAMSTER_URL_RE.search(attrs)
        title = _XHAMSTER_TITLE_RE.search(attrs)
        if href is None:
            continue
        body = match.group("body")
        thumb = _XHAMSTER_THUMB_RE.search(body)
        if title is None:
            title = re.search(r'<img[^>]+\balt="(?P<title>[^"]+)"', body, re.IGNORECASE)
        plain = re.sub(r"<!--.*?-->|<[^>]+>", " ", body, flags=re.DOTALL)
        duration = re.search(r"\b(?:[0-9]{1,3}:)?[0-9]{1,2}:[0-9]{2}\b", plain)
        if title is None or thumb is None or duration is None:
            continue
        page_url = html.unescape(href.group("url"))
        if page_url in seen:
            continue
        seen.add(page_url)
        preview = _XHAMSTER_PREVIEW_RE.search(attrs)
        items.append(
            SearchItem(
                id=_item_id("xhamster", page_url),
                provider="xhamster",
                title=_clean_text(title.group("title"))[:500],
                url=page_url,
                thumbnail=html.unescape(thumb.group("thumb")),
                preview_url=html.unescape(preview.group("preview")) if preview else None,
                duration_seconds=_duration_clock(duration.group(0)),
                quality=None,
                tags=[],
                score=1.0,
            )
        )
        if len(items) >= limit:
            break
    return items


def parse_youjizz_listing(raw_html: str, *, limit: int) -> list[SearchItem]:
    items: list[SearchItem] = []
    seen: set[str] = set()
    base_url = "https://www.youjizz.com/"
    for match in _YOUJIZZ_CARD_RE.finditer(raw_html):
        block = match.group("body")
        frame = _YOUJIZZ_FRAME_RE.search(block)
        if frame is None:
            continue
        attrs = frame.group("attrs")
        href = _YOUJIZZ_URL_RE.search(attrs)
        thumb = _YOUJIZZ_THUMB_RE.search(block)
        title = _YOUJIZZ_TITLE_RE.search(block)
        duration = _YOUJIZZ_DURATION_RE.search(block)
        if href is None or thumb is None or title is None or duration is None:
            continue
        page_url = urljoin(base_url, html.unescape(href.group("url")))
        if page_url in seen:
            continue
        seen.add(page_url)
        preview = _YOUJIZZ_PREVIEW_RE.search(attrs)
        items.append(
            SearchItem(
                id=_item_id("youjizz", page_url),
                provider="youjizz",
                title=_clean_text(title.group("title"))[:500],
                url=page_url,
                thumbnail=_https_media_url(thumb.group("thumb")),
                preview_url=_https_media_url(preview.group("preview")) if preview else None,
                duration_seconds=_duration_clock(duration.group("duration")),
                quality="HD" if re.search(r'class="[^"]*\bi-hd\b', block, re.IGNORECASE) else None,
                tags=[],
                score=1.0,
            )
        )
        if len(items) >= limit:
            break
    return items


def parse_pornone_listing(raw_html: str, *, limit: int) -> list[SearchItem]:
    items: list[SearchItem] = []
    seen: set[str] = set()
    for match in _PORNONE_CARD_RE.finditer(raw_html):
        attrs = match.group("attrs")
        body = match.group("body")
        href = _PORNONE_URL_RE.search(attrs)
        title = _PORNONE_TITLE_RE.search(body)
        image = _PORNONE_THUMB_TAG_RE.search(body)
        duration = _PORNONE_DURATION_RE.search(body)
        if href is None or title is None or image is None or duration is None:
            continue
        page_url = html.unescape(href.group("url"))
        if page_url in seen:
            continue
        seen.add(page_url)
        image_attrs = image.group("attrs")
        thumb = _PORNONE_DATA_SRC_RE.search(image_attrs) or _PORNONE_SRC_RE.search(image_attrs)
        if thumb is None:
            continue
        items.append(
            SearchItem(
                id=_item_id("pornone", page_url),
                provider="pornone",
                title=_clean_text(title.group("title"))[:500],
                url=page_url,
                thumbnail=html.unescape(thumb.group("src")),
                preview_url=None,
                duration_seconds=_duration_clock(duration.group("duration")),
                quality=None,
                tags=[],
                score=1.0,
            )
        )
        if len(items) >= limit:
            break
    return items


def parse_hqporner_listing(raw_html: str, *, limit: int) -> list[SearchItem]:
    items: list[SearchItem] = []
    seen: set[str] = set()
    base_url = "https://hqporner.com/"
    for match in _HQ_CARD_RE.finditer(raw_html):
        block = match.group("body")
        href = _HQ_URL_RE.search(block)
        image = _HQ_IMG_RE.search(block)
        duration = _HQ_DURATION_RE.search(block)
        if href is None or image is None or duration is None:
            continue
        page_url = urljoin(base_url, html.unescape(href.group("url")))
        if page_url in seen:
            continue
        seen.add(page_url)
        seconds = (
            int(duration.group("h") or 0) * 3600
            + int(duration.group("m") or 0) * 60
            + int(duration.group("s") or 0)
        )
        items.append(
            SearchItem(
                id=_item_id("hqporner", page_url),
                provider="hqporner",
                title=_clean_text(image.group("title"))[:500],
                url=page_url,
                thumbnail=_https_media_url(image.group("thumb")),
                preview_url=None,
                duration_seconds=seconds or None,
                quality=None,
                tags=[],
                score=1.0,
            )
        )
        if len(items) >= limit:
            break
    return items


def parse_thumbzilla_listing(raw_html: str, *, limit: int) -> list[SearchItem]:
    items: list[SearchItem] = []
    seen: set[str] = set()
    base_url = "https://www.thumbzilla.com/"
    for match in _THUMBZILLA_CARD_RE.finditer(raw_html):
        attrs, body = match.group("attrs"), match.group("body")
        href = _THUMBZILLA_URL_RE.search(attrs + body)
        title = _THUMBZILLA_TITLE_RE.search(attrs)
        image = _THUMBZILLA_IMG_RE.search(body)
        duration = _THUMBZILLA_DURATION_RE.search(body)
        if href is None or title is None or image is None or duration is None:
            continue
        image_attrs = image.group("attrs")
        thumb = _THUMBZILLA_DATA_SRC_RE.search(image_attrs) or _THUMBZILLA_POSTER_RE.search(image_attrs)
        if thumb is None:
            continue
        page_url = urljoin(base_url, html.unescape(href.group("url")))
        if page_url in seen:
            continue
        seen.add(page_url)
        preview = _THUMBZILLA_PREVIEW_RE.search(image_attrs)
        items.append(
            SearchItem(
                id=_item_id("thumbzilla", page_url),
                provider="thumbzilla",
                title=_clean_text(title.group("title"))[:500],
                url=page_url,
                thumbnail=html.unescape(thumb.group("src")),
                preview_url=html.unescape(preview.group("preview")) if preview else None,
                duration_seconds=_duration_clock(duration.group("duration")),
                quality=None,
                tags=[],
                score=1.0,
            )
        )
        if len(items) >= limit:
            break
    return items


def parse_pornhub_listing(raw_html: str, *, limit: int) -> list[SearchItem]:
    items: list[SearchItem] = []
    seen: set[str] = set()
    base_url = "https://www.pornhub.com/"
    for match in _PORNHUB_CARD_RE.finditer(raw_html):
        block = match.group("body")
        href = _PORNHUB_URL_RE.search(block)
        title = _PORNHUB_TITLE_RE.search(block)
        if href is None or title is None:
            continue
        page_url = urljoin(base_url, html.unescape(href.group("url")))
        if page_url in seen:
            continue
        seen.add(page_url)
        thumb = _PORNHUB_THUMB_RE.search(block)
        duration = _PORNHUB_DURATION_RE.search(block)
        preview = _PORNHUB_PREVIEW_RE.search(block)
        items.append(
            SearchItem(
                id=_item_id("pornhub", page_url),
                provider="pornhub",
                title=_clean_text(title.group("title"))[:500],
                url=page_url,
                thumbnail=html.unescape(thumb.group("thumb")) if thumb else None,
                preview_url=html.unescape(preview.group("preview")) if preview else None,
                duration_seconds=_duration_clock(duration.group("duration")) if duration else None,
                quality=None,
                tags=[],
                score=1.0,
            )
        )
        if len(items) >= limit:
            break
    return items


def parse_spankbang_listing(raw_html: str, *, limit: int) -> list[SearchItem]:
    items: list[SearchItem] = []
    seen: set[str] = set()
    base_url = "https://spankbang.com/"
    for match in _SPANK_CARD_RE.finditer(raw_html):
        block = match.group("body")
        href = _SPANK_URL_RE.search(block)
        thumb = _SPANK_THUMB_RE.search(block)
        if href is None or thumb is None:
            continue
        page_url = urljoin(base_url, html.unescape(href.group("url")))
        if page_url in seen:
            continue
        seen.add(page_url)
        preview = _SPANK_PREVIEW_RE.search(block)
        length = _SPANK_LENGTH_RE.search(block)
        quality = _SPANK_RES_RE.search(block)
        items.append(
            SearchItem(
                id=_item_id("spankbang", page_url),
                provider="spankbang",
                title=_clean_text(thumb.group("title"))[:500],
                url=page_url,
                thumbnail=html.unescape(thumb.group("thumb")),
                preview_url=html.unescape(preview.group("preview")) if preview else None,
                duration_seconds=int(length.group("duration")) * 60 if length else None,
                quality=_normalize_quality(quality.group("quality") if quality else None),
                tags=[],
                score=1.0,
            )
        )
        if len(items) >= limit:
            break
    return items


def parse_tube8_listing(raw_html: str, *, limit: int) -> list[SearchItem]:
    items: list[SearchItem] = []
    seen: set[str] = set()
    base_url = "https://www.tube8.com/"
    for match in _TUBE8_CARD_RE.finditer(raw_html):
        block = match.group("body")
        href = _TUBE8_URL_RE.search(block)
        title = _TUBE8_TITLE_RE.search(block)
        if href is None or title is None:
            continue
        page_url = urljoin(base_url, html.unescape(href.group("url")))
        if page_url in seen:
            continue
        seen.add(page_url)
        thumb = _TUBE8_THUMB_RE.search(block)
        preview = _TUBE8_PREVIEW_RE.search(block)
        duration = _TUBE8_DURATION_RE.search(block)
        quality = _TUBE8_QUALITY_RE.search(block)
        items.append(
            SearchItem(
                id=_item_id("tube8", page_url),
                provider="tube8",
                title=_clean_text(title.group("title"))[:500],
                url=page_url,
                thumbnail=html.unescape(thumb.group("thumb")) if thumb else None,
                preview_url=html.unescape(preview.group("preview")) if preview else None,
                duration_seconds=_duration_clock(duration.group("duration")) if duration else None,
                quality=_normalize_quality(quality.group("quality") if quality else None),
                tags=[],
                score=1.0,
            )
        )
        if len(items) >= limit:
            break
    return items


def parse_tube8_total(raw_html: str) -> int | None:
    match = _TUBE8_TOTAL_RE.search(raw_html)
    return int(match.group("total")) if match else None


def parse_tnaflix_listing(raw_html: str, *, limit: int) -> list[SearchItem]:
    items: list[SearchItem] = []
    seen: set[str] = set()
    for match in _TNA_CARD_RE.finditer(raw_html):
        block = match.group("body")
        href = _TNA_URL_RE.search(block)
        thumb = _TNA_THUMB_RE.search(block)
        if href is None or thumb is None:
            continue
        page_url = html.unescape(href.group("url"))
        if page_url in seen:
            continue
        seen.add(page_url)
        preview = _TNA_PREVIEW_RE.search(block)
        duration = _TNA_DURATION_RE.search(block)
        quality = _TNA_QUALITY_RE.search(block)
        items.append(
            SearchItem(
                id=_item_id("tnaflix", page_url),
                provider="tnaflix",
                title=_clean_text(thumb.group("title"))[:500],
                url=page_url,
                thumbnail=html.unescape(thumb.group("thumb")),
                preview_url=html.unescape(preview.group("preview")) if preview else None,
                duration_seconds=_duration_clock(duration.group("duration")) if duration else None,
                quality=_normalize_quality(quality.group("quality") if quality else None),
                tags=[],
                score=1.0,
            )
        )
        if len(items) >= limit:
            break
    return items


class _HttpLiveAdapter:
    name: str

    def __init__(self, *, timeout_seconds: float = 4.0) -> None:
        self.timeout_seconds = max(0.5, float(timeout_seconds))

    def _fetch_text(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return response.read().decode("utf-8", "replace")

    def _fetch_json(self, url: str) -> dict[str, object]:
        request = Request(
            url,
            headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
        if not isinstance(payload, dict):
            raise ValueError("live provider returned a non-object JSON response")
        return payload


class XVideosLiveAdapter(_HttpLiveAdapter):
    name = "xvideos"
    base_url = "https://www.xvideos.com/"

    def _search_sync(self, query: str, *, page: int, limit: int) -> LiveProviderResult:
        started = time.monotonic()
        encoded = quote(query.strip(), safe="")
        raw = self._fetch_text(f"{self.base_url}?k={encoded}&p={max(0, page - 1)}")
        return LiveProviderResult(
            provider=self.name,
            items=parse_xv_family_listing(raw, provider=self.name, base_url=self.base_url, limit=limit),
            total=parse_reported_total(raw),
            page=page,
            elapsed_ms=round((time.monotonic() - started) * 1000),
        )

    async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
        return await asyncio.to_thread(self._search_sync, query, page=max(1, page), limit=max(1, limit))


class XNXXLiveAdapter(_HttpLiveAdapter):
    name = "xnxx"
    base_url = "https://www.xnxx.com/"

    def _search_sync(self, query: str, *, page: int, limit: int) -> LiveProviderResult:
        started = time.monotonic()
        encoded = quote(query.strip(), safe="")
        raw = self._fetch_text(f"{self.base_url}search/{encoded}/{max(0, page - 1)}")
        return LiveProviderResult(
            provider=self.name,
            items=parse_xv_family_listing(raw, provider=self.name, base_url=self.base_url, limit=limit),
            total=parse_reported_total(raw),
            page=page,
            elapsed_ms=round((time.monotonic() - started) * 1000),
        )

    async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
        return await asyncio.to_thread(self._search_sync, query, page=max(1, page), limit=max(1, limit))


class XHamsterLiveAdapter(_HttpLiveAdapter):
    name = "xhamster"
    base_url = "https://xhamster.com/"
    max_robots_page = 10

    def _search_sync(self, query: str, *, page: int, limit: int) -> LiveProviderResult:
        started = time.monotonic()
        page = max(1, int(page))
        if page > self.max_robots_page:
            return LiveProviderResult(
                self.name, [], None, page,
                round((time.monotonic() - started) * 1000),
            )
        encoded = quote(query.strip(), safe="")
        url = f"{self.base_url}search/{encoded}"
        if page > 1:
            url = f"{url}?page={page}"
        raw = self._fetch_text(url)
        return LiveProviderResult(
            self.name, parse_xhamster_listing(raw, limit=limit), None, page,
            round((time.monotonic() - started) * 1000),
        )

    async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
        return await asyncio.to_thread(self._search_sync, query, page=max(1, page), limit=max(1, limit))


class YouJizzLiveAdapter(_HttpLiveAdapter):
    name = "youjizz"
    base_url = "https://www.youjizz.com/"

    def _search_sync(self, query: str, *, page: int, limit: int) -> LiveProviderResult:
        started = time.monotonic()
        page = max(1, int(page))
        encoded = quote(query.strip(), safe="")
        raw = self._fetch_text(f"{self.base_url}search/{encoded}-{page}.html")
        return LiveProviderResult(
            self.name, parse_youjizz_listing(raw, limit=limit), None, page,
            round((time.monotonic() - started) * 1000),
        )

    async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
        return await asyncio.to_thread(self._search_sync, query, page=max(1, page), limit=max(1, limit))


class PornOneLiveAdapter(_HttpLiveAdapter):
    name = "pornone"
    base_url = "https://pornone.com/"

    def _search_sync(self, query: str, *, page: int, limit: int) -> LiveProviderResult:
        started = time.monotonic()
        page = max(1, int(page))
        params = {"q": query.strip()}
        if page > 1:
            params["page"] = str(page)
        raw = self._fetch_text(f"{self.base_url}search?{urlencode(params)}")
        return LiveProviderResult(
            self.name, parse_pornone_listing(raw, limit=limit), None, page,
            round((time.monotonic() - started) * 1000),
        )

    async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
        return await asyncio.to_thread(self._search_sync, query, page=max(1, page), limit=max(1, limit))


class HQPornerLiveAdapter(_HttpLiveAdapter):
    name = "hqporner"
    base_url = "https://hqporner.com/"

    def _search_sync(self, query: str, *, page: int, limit: int) -> LiveProviderResult:
        started = time.monotonic()
        page = max(1, int(page))
        params = {"q": query.strip()}
        if page > 1:
            params["p"] = str(page)
        raw = self._fetch_text(f"{self.base_url}?{urlencode(params)}")
        return LiveProviderResult(
            self.name, parse_hqporner_listing(raw, limit=limit), None, page,
            round((time.monotonic() - started) * 1000),
        )

    async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
        return await asyncio.to_thread(self._search_sync, query, page=max(1, page), limit=max(1, limit))


class ThumbzillaLiveAdapter(_HttpLiveAdapter):
    name = "thumbzilla"
    base_url = "https://www.thumbzilla.com/"

    def _search_sync(self, query: str, *, page: int, limit: int) -> LiveProviderResult:
        started = time.monotonic()
        page = max(1, int(page))
        if page > 1:
            return LiveProviderResult(
                self.name, [], None, page,
                round((time.monotonic() - started) * 1000),
            )
        raw = self._fetch_text(
            f"{self.base_url}search/?{urlencode({'query': query.strip()})}"
        )
        return LiveProviderResult(
            self.name, parse_thumbzilla_listing(raw, limit=limit), None, page,
            round((time.monotonic() - started) * 1000),
        )

    async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
        return await asyncio.to_thread(self._search_sync, query, page=max(1, page), limit=max(1, limit))


class PornhubLiveAdapter(_HttpLiveAdapter):
    name = "pornhub"
    base_url = "https://www.pornhub.com/"

    def _search_sync(self, query: str, *, page: int, limit: int) -> LiveProviderResult:
        started = time.monotonic()
        params = urlencode({"search": query, "page": max(1, page)})
        raw = self._fetch_text(f"{self.base_url}video/search?{params}")
        return LiveProviderResult(
            self.name, parse_pornhub_listing(raw, limit=limit), parse_reported_total(raw),
            page, round((time.monotonic() - started) * 1000),
        )

    async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
        return await asyncio.to_thread(self._search_sync, query, page=max(1, page), limit=max(1, limit))


class SpankBangLiveAdapter(_HttpLiveAdapter):
    name = "spankbang"
    base_url = "https://spankbang.com/"

    def _search_sync(self, query: str, *, page: int, limit: int) -> LiveProviderResult:
        started = time.monotonic()
        encoded = quote_plus(query.strip().lower(), safe="")
        suffix = f"{page}/" if page > 1 else ""
        raw = self._fetch_text(f"{self.base_url}s/{encoded}/{suffix}")
        parse_limit = limit + 8 if page > 1 else limit
        parsed = parse_spankbang_listing(raw, limit=parse_limit)
        items = parsed[8:8 + limit] if page > 1 and len(parsed) > 8 else parsed[:limit]
        return LiveProviderResult(
            self.name, items, parse_reported_total(raw), page,
            round((time.monotonic() - started) * 1000),
        )

    async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
        return await asyncio.to_thread(self._search_sync, query, page=max(1, page), limit=max(1, limit))


class Tube8LiveAdapter(_HttpLiveAdapter):
    name = "tube8"
    base_url = "https://www.tube8.com/"

    def _search_sync(self, query: str, *, page: int, limit: int) -> LiveProviderResult:
        started = time.monotonic()
        params = urlencode({"q": query, "page": max(1, page)})
        raw = self._fetch_text(f"{self.base_url}searches.html/?{params}")
        parsed = parse_tube8_listing(raw, limit=limit + (8 if page > 1 else 0))
        items = parsed[8:8 + limit] if page > 1 and len(parsed) > 8 else parsed[:limit]
        return LiveProviderResult(
            self.name, items, parse_tube8_total(raw), page,
            round((time.monotonic() - started) * 1000),
        )

    async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
        return await asyncio.to_thread(self._search_sync, query, page=max(1, page), limit=max(1, limit))


class TNAFlixLiveAdapter(_HttpLiveAdapter):
    name = "tnaflix"
    base_url = "https://www.tnaflix.com/"

    def _search_sync(self, query: str, *, page: int, limit: int) -> LiveProviderResult:
        started = time.monotonic()
        raw = self._fetch_text(
            f"{self.base_url}search?{urlencode({'what': query, 'page': max(1, page)})}"
        )
        return LiveProviderResult(
            self.name, parse_tnaflix_listing(raw, limit=limit), None, page,
            round((time.monotonic() - started) * 1000),
        )

    async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
        return await asyncio.to_thread(self._search_sync, query, page=max(1, page), limit=max(1, limit))


def _beeg_title(row: dict[str, object]) -> str | None:
    file_obj = row.get("file")
    if not isinstance(file_obj, dict):
        return None
    data = file_obj.get("data")
    if not isinstance(data, list):
        return None
    for entry in data:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("cd_column") or "") != "sf_name":
            continue
        title = _clean_text(entry.get("cd_value"))
        if title:
            return title[:500]
    return None


def _beeg_quality(file_obj: dict[str, object]) -> str | None:
    heights: list[int] = []
    try:
        source_height = int(file_obj.get("fl_height") or 0)
    except (TypeError, ValueError):
        source_height = 0
    if source_height:
        heights.append(source_height)
    qualities = file_obj.get("qualities")
    if isinstance(qualities, dict):
        for variants in qualities.values():
            if not isinstance(variants, list):
                continue
            for variant in variants:
                if not isinstance(variant, dict):
                    continue
                try:
                    heights.append(int(variant.get("quality") or 0))
                except (TypeError, ValueError):
                    pass
    height = max(heights or [0])
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
    if height >= 480:
        return "480p"
    if height >= 360:
        return "360p"
    return None


def parse_beeg_video(row: object) -> SearchItem | None:
    if not isinstance(row, dict):
        return None
    file_obj = row.get("file")
    if not isinstance(file_obj, dict):
        return None
    file_id = str(file_obj.get("id") or "").strip()
    title = _beeg_title(row)
    if not file_id or not title:
        return None

    legacy_id_url = f"https://beeg.com/-0/{file_id}"
    page_url = f"https://beeg.com/-0{file_id}"
    offset = 0
    facts = row.get("fc_facts")
    if isinstance(facts, list) and facts and isinstance(facts[0], dict):
        thumbs = facts[0].get("fc_thumbs")
        if isinstance(thumbs, list) and thumbs:
            try:
                offset = max(0, int(thumbs[0]))
            except (TypeError, ValueError):
                pass
    try:
        duration = int(file_obj.get("fl_duration") or 0) or None
    except (TypeError, ValueError):
        duration = None

    tags: list[str] = []
    raw_tags = row.get("tags")
    if isinstance(raw_tags, list):
        for tag in raw_tags:
            if isinstance(tag, dict):
                name = _clean_text(tag.get("tg_name"))
                if name and name not in tags:
                    tags.append(name)

    return SearchItem(
        id=_item_id("beeg", legacy_id_url),
        provider="beeg",
        title=title,
        url=page_url,
        thumbnail=f"https://thumbs.externulls.com/videos/{file_id}/{offset}.webp?w=640",
        preview_url=f"https://vp.externulls.com/{file_id}/0-0.mp4",
        duration_seconds=duration,
        quality=_beeg_quality(file_obj),
        tags=tags[:80],
        score=1.0,
    )


class BeegLiveAdapter(_HttpLiveAdapter):
    name = "beeg"
    search_url = "wss://search.externulls.com"
    store_url = "https://store.externulls.com"

    def _resolve_tag_sync(self, query: str) -> tuple[str, int | None] | None:
        if websocket_connect is None:
            raise RuntimeError("websockets support unavailable")
        payload = {
            "type": "search",
            "ignore_stats": True,
            "payload": {"Search_string": query, "offset": 0, "limit": 10},
        }
        with websocket_connect(
            self.search_url,
            origin="https://beeg.com",
            open_timeout=self.timeout_seconds,
            close_timeout=1.0,
        ) as socket:
            socket.send(json.dumps(payload))
            raw = socket.recv(timeout=self.timeout_seconds)
        rows = json.loads(raw)
        if not isinstance(rows, list):
            return None
        for row in rows:
            if not isinstance(row, dict):
                continue
            slug = str(row.get("tg_slug") or "").strip()
            if not slug:
                continue
            try:
                total = int(row.get("tg_videos_count") or 0) or None
            except (TypeError, ValueError):
                total = None
            if total != 0:
                return slug, total
        return None

    def _fetch_rows_sync(self, slug: str, *, page: int, limit: int) -> list[object]:
        upstream_limit = min(100, max(10, limit))
        offset = max(0, page - 1) * upstream_limit
        params = urlencode({"limit": upstream_limit, "offset": offset})
        request = Request(
            f"{self.store_url}/tag/videos/{quote(slug.lower(), safe='')}?{params}",
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "application/json",
                "Origin": "https://beeg.com",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
        return payload if isinstance(payload, list) else []

    def _search_sync(self, query: str, *, page: int, limit: int) -> LiveProviderResult:
        started = time.monotonic()
        resolved = self._resolve_tag_sync(query)
        if resolved is None:
            return LiveProviderResult(
                self.name, [], 0, page,
                round((time.monotonic() - started) * 1000),
            )
        slug, total = resolved
        items: list[SearchItem] = []
        for row in self._fetch_rows_sync(slug, page=page, limit=limit):
            item = parse_beeg_video(row)
            if item is not None:
                items.append(item)
            if len(items) >= limit:
                break
        return LiveProviderResult(
            self.name, items, total, page,
            round((time.monotonic() - started) * 1000),
        )

    async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
        return await asyncio.to_thread(
            self._search_sync, query, page=max(1, page), limit=max(1, limit)
        )


class EpornerLiveAdapter(_HttpLiveAdapter):
    name = "eporner"
    api_url = "https://www.eporner.com/api/v2/video/search/"

    @staticmethod
    def _video_item(row: object) -> SearchItem | None:
        if not isinstance(row, dict):
            return None
        page_url = str(row.get("url") or "").strip()
        title = _clean_text(row.get("title"))
        if not page_url or not title:
            return None

        default_thumb = row.get("default_thumb")
        thumbnail = (
            str(default_thumb.get("src") or "").strip()
            if isinstance(default_thumb, dict)
            else ""
        ) or None

        keywords = _clean_text(row.get("keywords"))
        tags = [
            value.strip()
            for value in keywords.split(",")
            if value.strip() and value.strip().lower() != title.lower()
        ]
        try:
            duration = int(row.get("length_sec") or 0) or None
        except (TypeError, ValueError):
            duration = None

        return SearchItem(
            id=_item_id("eporner", page_url),
            provider="eporner",
            title=title[:500],
            url=page_url,
            thumbnail=thumbnail,
            duration_seconds=duration,
            quality=None,
            tags=tags[:80],
            score=1.0,
        )

    def _search_sync(self, query: str, *, page: int, limit: int) -> LiveProviderResult:
        started = time.monotonic()
        params = urlencode(
            {
                "query": query,
                "per_page": min(max(1, limit), 1000),
                "page": max(1, page),
                "thumbsize": "medium",
                "lq": 1,
                "format": "json",
            }
        )
        payload = self._fetch_json(f"{self.api_url}?{params}")
        items: list[SearchItem] = []
        videos = payload.get("videos")
        if isinstance(videos, list):
            for row in videos:
                item = self._video_item(row)
                if item is not None:
                    items.append(item)
        raw_total = payload.get("total_count")
        try:
            total = int(str(raw_total)) if raw_total is not None else None
        except ValueError:
            total = None

        return LiveProviderResult(
            self.name, items[:limit], total, page,
            round((time.monotonic() - started) * 1000),
        )

    async def search(self, query: str, *, page: int = 1, limit: int = 24) -> LiveProviderResult:
        return await asyncio.to_thread(
            self._search_sync, query, page=max(1, page), limit=max(1, limit)
        )


# Production d054 baseline. Inactive adapters above are intentionally retained
# for later behavior-oriented re-audit; popup/ad capability alone is not a
# rejection criterion.
LIVE_ADAPTERS: list[LiveAdapter] = [
    BeegLiveAdapter(),
    XNXXLiveAdapter(),
    YouJizzLiveAdapter(),
    PornOneLiveAdapter(),
    HQPornerLiveAdapter(),
    EpornerLiveAdapter(),
    TNAFlixLiveAdapter(),
]


def cache_live_provider_results(
    results: list[LiveProviderResult],
    *,
    path=DB_PATH,
) -> int:
    """Best-effort live metadata cache that never queues behind itself."""
    batches = {
        result.provider: list(result.items)
        for result in results
        if result.items
    }
    if not batches or not _LIVE_CACHE_LOCK.acquire(blocking=False):
        return 0
    try:
        return merge_provider_batches(batches, path=path)
    except Exception:
        logger.warning("live metadata cache write failed", exc_info=True)
        return 0
    finally:
        _LIVE_CACHE_LOCK.release()


async def refresh_live_search(
    query: str,
    *,
    page: int = 1,
    limit_per_provider: int = 24,
    deadline_seconds: float = 4.0,
    adapters: list[LiveAdapter] | None = None,
    provider: str | None = None,
    quality: str | None = None,
    age_check: str | None = None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    path=DB_PATH,
) -> LiveRefreshResult:
    query = query.strip()
    if not query:
        return LiveRefreshResult(providers=[], cached_items=0)

    enforce_trust = adapters is None
    selected = list(adapters if adapters is not None else LIVE_ADAPTERS)
    if provider is not None:
        selected = [adapter for adapter in selected if adapter.name == provider]

    async def run(adapter: LiveAdapter) -> LiveProviderResult:
        started = time.monotonic()
        try:
            return await asyncio.wait_for(
                adapter.search(
                    query,
                    page=max(1, page),
                    limit=max(1, limit_per_provider),
                ),
                timeout=max(0.1, deadline_seconds),
            )
        except Exception as exc:
            return LiveProviderResult(
                provider=adapter.name,
                items=[],
                total=None,
                page=max(1, page),
                elapsed_ms=round((time.monotonic() - started) * 1000),
                error=type(exc).__name__,
            )

    results = await asyncio.gather(*(run(adapter) for adapter in selected))

    for result in results:
        items = (
            [
                normalized
                for item in result.items
                if (normalized := normalize_trusted_live_item(item)) is not None
            ]
            if enforce_trust
            else list(result.items)
        )
        if age_check:
            items = [item for item in items if item.age_check_status == age_check]
        if quality:
            items = [
                item
                for item in items
                if (item.quality or "").lower() == quality.lower()
            ]
        if min_duration is not None:
            items = [
                item
                for item in items
                if (item.duration_seconds or 0) >= min_duration
            ]
        if max_duration is not None:
            items = [
                item
                for item in items
                if item.duration_seconds is not None
                and item.duration_seconds <= max_duration
            ]
        result.items = items

    # Since 2c33510 the HTTP response is intentionally decoupled from FTS writes.
    return LiveRefreshResult(providers=results, cached_items=0)
