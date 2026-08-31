from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, Request

from backend.index import count_items, indexed_providers, initialize, provider_counts
from backend.models import SearchRequest, SearchResponse
from backend.providers import PROVIDERS
from backend.search import search_all

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


@app.get("/api/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "version": app.version,
        "providers": len(PROVIDERS),
        "indexed_items": count_items(),
    }


@app.get("/api/providers")
async def providers() -> dict[str, list[str]]:
    names = sorted({provider.name for provider in PROVIDERS} | set(indexed_providers()))
    return {"providers": names}


@app.get("/api/stats")
async def stats() -> dict[str, object]:
    return {
        "indexed_items": count_items(),
        "indexed_providers": indexed_providers(),
        "provider_counts": provider_counts(),
    }


async def _search_response(
    *,
    q: str,
    provider: str | None,
    quality: str | None,
    min_duration: int | None,
    max_duration: int | None,
    offset: int,
    limit: int,
) -> SearchResponse:
    if min_duration is not None and max_duration is not None and min_duration > max_duration:
        raise HTTPException(status_code=400, detail="min_duration cannot exceed max_duration")

    known = {item.name for item in PROVIDERS} | set(indexed_providers())
    if provider is not None and provider not in known:
        raise HTTPException(status_code=400, detail="unknown provider")

    items, used, has_more = await search_all(
        q,
        provider=provider,
        quality=quality,
        min_duration=min_duration,
        max_duration=max_duration,
        offset=offset,
        limit=limit,
    )
    return SearchResponse(
        query=q,
        total=len(items),
        offset=offset,
        limit=limit,
        has_more=has_more,
        providers=used,
        items=items,
    )


@app.get("/api/search", response_model=SearchResponse)
async def search_get(
    q: str = Query(default="", max_length=200),
    provider: str | None = None,
    quality: str | None = None,
    min_duration: int | None = Query(default=None, ge=0),
    max_duration: int | None = Query(default=None, ge=0),
    offset: int = Query(default=0, ge=0, le=5000),
    limit: int = Query(default=40, ge=1, le=100),
) -> SearchResponse:
    return await _search_response(
        q=q,
        provider=provider,
        quality=quality,
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
        min_duration=payload.min_duration,
        max_duration=payload.max_duration,
        offset=payload.offset,
        limit=payload.limit,
    )
