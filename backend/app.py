from __future__ import annotations

import asyncio
import logging
import re
import sqlite3
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request as UrlRequest, build_opener, urlopen

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response

from backend.content_class import ContentClass
from backend.content_class_live import filter_live_items
from backend.index import (
    count_items,
    get_item,
    indexed_providers,
    initialize,
    provider_counts,
    update_item_thumbnail,
)
from backend.live import LIVE_ADAPTERS, cache_live_provider_results, refresh_live_search, sort_live_items
from backend.media_policy import media_policy_rows, media_url_allowed, provider_media_policy
from backend.models import (
    LiveProviderStatus,
    LiveRefreshRequest,
    LiveRefreshResponse,
    SearchRequest,
    SearchResponse,
    SortMode,
)
from backend.providers import PROVIDERS
from backend.providers.sitemap import SitemapProvider
from backend.preview_rules import PREVIEW_RULES
from backend.search import search_all
from backend.settings import get_build_id
from backend.source_policy import (
    is_searchable_provider,
    provider_policy_rows,
    trusted_provider_names,
)

logger = logging.getLogger(__name__)

_THUMBNAIL_PROXY_MAX_BYTES = 2 * 1024 * 1024
_PREVIEW_PROXY_MAX_BYTES = 2 * 1024 * 1024
_PREVIEW_PROXY_CHUNK_BYTES = 1024 * 1024


class _ThumbnailProxyNoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _thumbnail_proxy_open(request: UrlRequest):
    return build_opener(_ThumbnailProxyNoRedirect()).open(request, timeout=8.0)


def _thumbnail_proxy_fetch(provider: str, url: str) -> tuple[bytes, str]:
    policy = provider_media_policy(provider)
    if policy.thumbnail_mode != "proxy":
        raise ValueError("thumbnail proxy is not enabled for provider")
    if not media_url_allowed(provider, "thumbnail", url):
        raise ValueError("thumbnail host is not allowed")
    headers = {
        "User-Agent": "SearchEngineLive/0.6",
        "Accept": "image/jpeg,image/webp,image/*;q=0.8,*/*;q=0.5",
    }
    if policy.thumbnail_referer:
        headers["Referer"] = policy.thumbnail_referer
    request = UrlRequest(url, headers=headers)
    with _thumbnail_proxy_open(request) as response:
        content_type = response.headers.get_content_type()
        if not content_type.startswith("image/"):
            raise ValueError("upstream did not return an image")
        body = response.read(_THUMBNAIL_PROXY_MAX_BYTES + 1)
        if len(body) > _THUMBNAIL_PROXY_MAX_BYTES:
            raise ValueError("thumbnail exceeds proxy size limit")
        return body, content_type


def _bounded_preview_range(value: str | None) -> str:
    if not value:
        return f"bytes=0-{_PREVIEW_PROXY_CHUNK_BYTES - 1}"
    match = re.fullmatch(r"bytes=(\d+)-(\d*)", value.strip())
    if match is None:
        raise ValueError("invalid preview range")
    start = int(match.group(1))
    raw_end = match.group(2)
    if raw_end:
        requested_end = int(raw_end)
        if requested_end < start:
            raise ValueError("invalid preview range")
        end = min(requested_end, start + _PREVIEW_PROXY_MAX_BYTES - 1)
    else:
        end = start + _PREVIEW_PROXY_CHUNK_BYTES - 1
    return f"bytes={start}-{end}"


def _preview_proxy_fetch(
    provider: str,
    url: str,
    range_header: str | None,
) -> tuple[bytes, str, int, dict[str, str]]:
    policy = provider_media_policy(provider)
    if policy.preview_mode != "proxy":
        raise ValueError("preview proxy is not enabled for provider")
    if not media_url_allowed(provider, "preview", url):
        raise ValueError("preview host is not allowed")
    headers = {
        "User-Agent": "SearchEngineLive/0.6",
        "Accept": "video/*,*/*;q=0.5",
        "Range": _bounded_preview_range(range_header),
    }
    if policy.preview_referer:
        headers["Referer"] = policy.preview_referer
    request = UrlRequest(url, headers=headers)
    with _thumbnail_proxy_open(request) as response:
        content_type = response.headers.get_content_type()
        if not content_type.startswith("video/"):
            raise ValueError("upstream did not return video content")
        body = response.read(_PREVIEW_PROXY_MAX_BYTES + 1)
        if len(body) > _PREVIEW_PROXY_MAX_BYTES:
            raise ValueError("preview range exceeds proxy size limit")
        upstream_headers: dict[str, str] = {}
        for name in ("Content-Range", "Accept-Ranges"):
            value = response.headers.get(name)
            if value:
                upstream_headers[name] = value
        return body, content_type, int(getattr(response, "status", 200)), upstream_headers


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize()
    yield


app = FastAPI(
    title="Search Engine API",
    version="0.5.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


@app.middleware("http")
async def api_privacy_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def _provider_observability() -> dict[str, object]:
    indexed = sorted(set(indexed_providers()))
    configured_index = sorted({provider.name for provider in PROVIDERS})
    live = [adapter.name for adapter in LIVE_ADAPTERS]
    trusted = sorted(trusted_provider_names())
    searchable = {
        name for name in trusted_provider_names() if is_searchable_provider(name)
    }
    available = sorted((set(indexed) | set(configured_index) | set(live)) & searchable)
    return {
        "indexed_provider_count": len(indexed),
        "indexed_providers": indexed,
        "configured_index_provider_count": len(configured_index),
        "configured_index_providers": configured_index,
        "live_provider_count": len(live),
        "live_providers": live,
        "trusted_provider_count": len(trusted),
        "trusted_providers": trusted,
        "available_provider_count": len(available),
        "available_providers": available,
    }


@app.get("/api/health")
async def health() -> dict[str, object]:
    try:
        indexed_items = count_items()
        provider_observability = _provider_observability()
    except sqlite3.OperationalError as exc:
        logger.warning("index database unavailable during health check: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="index database temporarily unavailable",
        ) from exc
    return {
        "status": "ok",
        "version": app.version,
        "build": get_build_id(),
        "indexed_items": indexed_items,
        **provider_observability,
    }


@app.get("/api/providers")
async def providers() -> dict[str, object]:
    available = (
        {provider.name for provider in PROVIDERS}
        | {adapter.name for adapter in LIVE_ADAPTERS}
        | set(indexed_providers())
    )
    searchable = {
        name for name in trusted_provider_names() if is_searchable_provider(name)
    }
    names = sorted(available & searchable)
    media_rows = media_policy_rows(set(names))
    for row in media_rows:
        name = str(row["name"])
        rule = PREVIEW_RULES.get(name)
        row["preview_resolution_mode"] = ("on_demand" if rule is not None and (rule.storage_mode == "ephemeral" or rule.kind == "custom") else "stored")
        row["preview_storage_mode"] = rule.storage_mode if rule is not None else "stable"
    return {
        "providers": names,
        "policies": provider_policy_rows(set(names)),
        "media_policies": media_rows,
    }


@app.get("/api/preview/{item_id}", include_in_schema=False)
async def resolve_preview(item_id: str) -> dict[str, str]:
    item = get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="preview item not found")

    provider = next(
        (
            candidate
            for candidate in [*PROVIDERS, *LIVE_ADAPTERS]
            if candidate.name == item.provider
            and getattr(candidate, "preview_resolution", False)
            and callable(getattr(candidate, "extract_preview", None))
        ),
        None,
    )
    if provider is None:
        raise HTTPException(status_code=404, detail="preview resolution unavailable")

    try:
        candidate = await asyncio.wait_for(provider.extract_preview(item), timeout=6.0)
    except Exception as exc:
        logger.warning("preview resolution upstream failure for %s", item.provider, exc_info=True)
        raise HTTPException(status_code=502, detail="preview upstream unavailable") from exc

    if not candidate:
        raise HTTPException(status_code=404, detail="preview not found")
    value = str(candidate)
    if not media_url_allowed(item.provider, "preview", value):
        raise HTTPException(status_code=502, detail="preview media rejected")
    return {"preview_url": value}


@app.get("/api/stats")
async def stats() -> dict[str, object]:
    return {
        "indexed_items": count_items(),
        "provider_counts": provider_counts(),
        **_provider_observability(),
    }


async def _search_response(
    *,
    q: str,
    provider: str | None,
    quality: str | None,
    content_class: ContentClass | None,
    age_check: str | None,
    min_duration: int | None,
    max_duration: int | None,
    sort: SortMode,
    offset: int,
    limit: int,
    exclude_ids: set[str] | None = None,
) -> SearchResponse:
    if (
        min_duration is not None
        and max_duration is not None
        and min_duration > max_duration
    ):
        raise HTTPException(
            status_code=400,
            detail="min_duration cannot exceed max_duration",
        )

    known = {
        name for name in trusted_provider_names() if is_searchable_provider(name)
    }
    if provider is not None and provider not in known:
        raise HTTPException(status_code=400, detail="unknown provider")

    items, used, has_more, total = await search_all(
        q,
        provider=provider,
        quality=quality,
        content_class=content_class,
        age_check=age_check,
        min_duration=min_duration,
        max_duration=max_duration,
        sort=sort,
        offset=offset,
        limit=limit,
        allowed_providers=known,
        exclude_ids=exclude_ids,
    )
    return SearchResponse(
        query=q,
        total=total,
        offset=offset,
        limit=limit,
        has_more=has_more,
        providers=used,
        items=items,
    )


@app.get("/preview-proxy", include_in_schema=False)
@app.get("/api/preview-proxy", include_in_schema=False)
async def preview_proxy(request: Request, provider: str, url: str) -> Response:
    try:
        body, content_type, status_code, upstream_headers = await asyncio.to_thread(
            _preview_proxy_fetch, provider, url, request.headers.get("range")
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("preview proxy upstream failure for %s", provider, exc_info=True)
        raise HTTPException(status_code=502, detail="preview upstream unavailable") from exc
    headers = {
        "Cache-Control": "private, no-store",
        "X-Robots-Tag": "noindex, nofollow",
        **upstream_headers,
    }
    return Response(
        content=body,
        status_code=status_code,
        media_type=content_type,
        headers=headers,
    )


@app.get("/thumb-proxy", include_in_schema=False)
@app.get("/api/thumb-proxy", include_in_schema=False)
async def thumbnail_proxy(provider: str, url: str) -> Response:
    try:
        body, content_type = await asyncio.to_thread(_thumbnail_proxy_fetch, provider, url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("thumbnail proxy upstream failure for %s", provider, exc_info=True)
        raise HTTPException(status_code=502, detail="thumbnail upstream unavailable") from exc
    return Response(
        content=body,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=21600",
            "X-Robots-Tag": "noindex, nofollow",
        },
    )


@app.get("/thumb/{item_id}", include_in_schema=False)
@app.get("/api/thumb/{item_id}", include_in_schema=False)
async def thumbnail_redirect(
    item_id: str,
    refresh: bool = False,
) -> Response:
    item = get_item(item_id)
    if item is None or item.thumbnail is None:
        raise HTTPException(status_code=404, detail="thumbnail not found")

    provider = next(
        (candidate for candidate in PROVIDERS if candidate.name == item.provider),
        None,
    )
    if provider is None and item.provider in {"thumbzilla", "tube8"}:
        parsed_item = urlparse(str(item.url))
        if parsed_item.scheme == "https" and parsed_item.hostname:
            provider = SitemapProvider(
                name=item.provider,
                sitemap_url=f"https://{parsed_item.hostname}/",
                obey_robots=False,
                delay_seconds=0,
            )
    resolved = str(item.thumbnail)
    if provider is not None:
        try:
            candidate = await provider.resolve_thumbnail(item, force=refresh)
        except Exception:
            logger.warning(
                "thumbnail resolution failed for %s/%s; using indexed thumbnail",
                item.provider,
                item.id,
                exc_info=True,
            )
            candidate = None
        if candidate:
            resolved = candidate
            if resolved != str(item.thumbnail):
                try:
                    update_item_thumbnail(item.id, resolved)
                except Exception:
                    logger.warning(
                        "thumbnail cache update failed for %s/%s",
                        item.provider,
                        item.id,
                        exc_info=True,
                    )

    if item.provider == "thumbzilla":
        try:
            body, content_type = await asyncio.to_thread(
                _thumbnail_proxy_fetch, item.provider, resolved
            )
            return Response(
                content=body,
                media_type=content_type,
                headers={
                    "Cache-Control": "private, max-age=21600",
                    "X-Robots-Tag": "noindex, nofollow",
                },
            )
        except Exception:
            logger.warning(
                "refreshed thumbnail proxy failed for %s/%s",
                item.provider,
                item.id,
                exc_info=True,
            )

    return RedirectResponse(
        url=resolved,
        status_code=302,
        headers={
            "Cache-Control": "private, max-age=21600",
            "X-Robots-Tag": "noindex, nofollow",
        },
    )


@app.post("/api/live-refresh", response_model=LiveRefreshResponse)
async def live_refresh(
    payload: LiveRefreshRequest,
    background_tasks: BackgroundTasks,
) -> LiveRefreshResponse:
    result = await refresh_live_search(
        payload.q,
        page=payload.page,
        limit_per_provider=payload.limit_per_provider,
        deadline_seconds=4.0,
        provider=payload.provider,
        quality=payload.quality,
        age_check=payload.age_check,
        min_duration=payload.min_duration,
        max_duration=payload.max_duration,
    )

    for provider_result in result.providers:
        provider_result.items = filter_live_items(provider_result.items, None)

    # Cache the full classified provider batches. Request-specific content
    # filtering is applied only to the response copy below.
    background_tasks.add_task(cache_live_provider_results, result.providers)

    response_provider_items = [
        (
            provider_result,
            filter_live_items(provider_result.items, payload.content_class),
        )
        for provider_result in result.providers
    ]

    fresh_items = []
    max_rows = max((len(items) for _, items in response_provider_items), default=0)
    seen_live_ids: set[str] = set()
    for position in range(max_rows):
        for _, items in response_provider_items:
            if position >= len(items):
                continue
            item = items[position]
            if item.id in seen_live_ids:
                continue
            seen_live_ids.add(item.id)
            fresh_items.append(item)

    fresh_items = sort_live_items(fresh_items, payload.sort)

    return LiveRefreshResponse(
        query=payload.q,
        cached_items=0,
        indexed_items=count_items(),
        providers=[
            LiveProviderStatus(
                provider=provider_result.provider,
                fetched=len(items),
                total=provider_result.total,
                page=provider_result.page,
                elapsed_ms=provider_result.elapsed_ms,
                error=provider_result.error,
            )
            for provider_result, items in response_provider_items
        ],
        items=fresh_items,
    )


@app.get("/api/search", response_model=SearchResponse)
async def search_get(
    q: str = Query(default="", max_length=200),
    provider: str | None = None,
    quality: str | None = None,
    content_class: ContentClass | None = Query(default=None),
    age_check: str | None = Query(
        default=None,
        pattern="^(required|not_required|unknown)$",
    ),
    min_duration: int | None = Query(default=None, ge=0),
    max_duration: int | None = Query(default=None, ge=0),
    sort: SortMode = Query(default="relevance"),
    offset: int = Query(default=0, ge=0, le=5000),
    limit: int = Query(default=40, ge=1, le=100),
) -> SearchResponse:
    return await _search_response(
        q=q,
        provider=provider,
        quality=quality,
        content_class=content_class,
        age_check=age_check,
        min_duration=min_duration,
        max_duration=max_duration,
        sort=sort,
        offset=offset,
        limit=limit,
    )


@app.post("/api/search", response_model=SearchResponse)
async def search_post(payload: SearchRequest) -> SearchResponse:
    return await _search_response(
        q=payload.q,
        provider=payload.provider,
        quality=payload.quality,
        content_class=payload.content_class,
        age_check=payload.age_check,
        min_duration=payload.min_duration,
        max_duration=payload.max_duration,
        sort=payload.sort,
        offset=payload.offset,
        limit=payload.limit,
        exclude_ids=set(payload.exclude_ids),
    )
