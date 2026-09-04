from __future__ import annotations

import asyncio
import logging
import sqlite3
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request as UrlRequest, build_opener, urlopen

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response

from backend.index import (
    count_items,
    get_item,
    indexed_providers,
    initialize,
    provider_counts,
    update_item_thumbnail,
)
from backend.live import LIVE_ADAPTERS, cache_live_provider_results, refresh_live_search
from backend.models import (
    LiveProviderStatus,
    LiveRefreshRequest,
    LiveRefreshResponse,
    SearchRequest,
    SearchResponse,
)
from backend.providers import PROVIDERS
from backend.search import search_all
from backend.settings import get_build_id
from backend.source_policy import (
    is_searchable_provider,
    provider_policy_rows,
    trusted_provider_names,
)

logger = logging.getLogger(__name__)

_THUMBNAIL_PROXY_RULES: dict[str, tuple[str, str]] = {
    "thumbzilla": (".ypncdn.com", "https://www.thumbzilla.com/"),
}
_THUMBNAIL_PROXY_MAX_BYTES = 2 * 1024 * 1024


class _ThumbnailProxyNoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _thumbnail_proxy_open(request: UrlRequest):
    return build_opener(_ThumbnailProxyNoRedirect()).open(request, timeout=8.0)


def _thumbnail_proxy_fetch(provider: str, url: str) -> tuple[bytes, str]:
    rule = _THUMBNAIL_PROXY_RULES.get(provider)
    if rule is None:
        raise ValueError("thumbnail proxy is not enabled for provider")
    allowed_suffix, referer = rule
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not host.endswith(allowed_suffix)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise ValueError("thumbnail host is not allowed")
    request = UrlRequest(
        url,
        headers={
            "User-Agent": "SearchEngineLive/0.6",
            "Referer": referer,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        },
    )
    with _thumbnail_proxy_open(request) as response:
        content_type = response.headers.get_content_type()
        if not content_type.startswith("image/"):
            raise ValueError("upstream did not return an image")
        body = response.read(_THUMBNAIL_PROXY_MAX_BYTES + 1)
        if len(body) > _THUMBNAIL_PROXY_MAX_BYTES:
            raise ValueError("thumbnail exceeds proxy size limit")
        return body, content_type

app = FastAPI(
    title="Search Engine API",
    version="0.5.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.middleware("http")
async def api_privacy_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@app.on_event("startup")
async def startup() -> None:
    initialize()


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
    return {
        "providers": names,
        "policies": provider_policy_rows(set(names)),
    }


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
    age_check: str | None,
    min_duration: int | None,
    max_duration: int | None,
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
        age_check=age_check,
        min_duration=min_duration,
        max_duration=max_duration,
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


@app.get("/thumb-proxy", include_in_schema=False)
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
async def thumbnail_redirect(
    item_id: str,
    refresh: bool = False,
) -> RedirectResponse:
    item = get_item(item_id)
    if item is None or item.thumbnail is None:
        raise HTTPException(status_code=404, detail="thumbnail not found")

    provider = next(
        (candidate for candidate in PROVIDERS if candidate.name == item.provider),
        None,
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

    # Cache only after the response path has been prepared. The cache function
    # itself has a non-blocking lock and skips instead of queueing.
    background_tasks.add_task(cache_live_provider_results, result.providers)

    fresh_items = []
    max_rows = max((len(item.items) for item in result.providers), default=0)
    seen_live_ids: set[str] = set()
    for position in range(max_rows):
        for provider_result in result.providers:
            if position >= len(provider_result.items):
                continue
            item = provider_result.items[position]
            if item.id in seen_live_ids:
                continue
            seen_live_ids.add(item.id)
            fresh_items.append(item)

    return LiveRefreshResponse(
        query=payload.q,
        cached_items=0,
        indexed_items=count_items(),
        providers=[
            LiveProviderStatus(
                provider=item.provider,
                fetched=len(item.items),
                total=item.total,
                page=item.page,
                elapsed_ms=item.elapsed_ms,
                error=item.error,
            )
            for item in result.providers
        ],
        items=fresh_items,
    )


@app.get("/api/search", response_model=SearchResponse)
async def search_get(
    q: str = Query(default="", max_length=200),
    provider: str | None = None,
    quality: str | None = None,
    age_check: str | None = Query(
        default=None,
        pattern="^(required|not_required|unknown)$",
    ),
    min_duration: int | None = Query(default=None, ge=0),
    max_duration: int | None = Query(default=None, ge=0),
    offset: int = Query(default=0, ge=0, le=5000),
    limit: int = Query(default=40, ge=1, le=100),
) -> SearchResponse:
    return await _search_response(
        q=q,
        provider=provider,
        quality=quality,
        age_check=age_check,
        min_duration=min_duration,
        max_duration=max_duration,
        offset=offset,
        limit=limit,
    )


@app.post("/api/search", response_model=SearchResponse)
async def search_post(payload: SearchRequest) -> SearchResponse:
    return await _search_response(
        q=payload.q,
        provider=payload.provider,
        quality=payload.quality,
        age_check=payload.age_check,
        min_duration=payload.min_duration,
        max_duration=payload.max_duration,
        offset=payload.offset,
        limit=payload.limit,
        exclude_ids=set(payload.exclude_ids),
    )
