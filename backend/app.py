from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from backend.index import count_items, indexed_providers, initialize
from backend.models import SearchResponse
from backend.providers import PROVIDERS
from backend.search import search_all

app = FastAPI(
    title="Search Engine API",
    version="0.2.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


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
    }


@app.get("/api/search", response_model=SearchResponse)
async def search(
    q: str = Query(default="", max_length=200),
    provider: str | None = None,
    quality: str | None = None,
    min_duration: int | None = Query(default=None, ge=0),
    max_duration: int | None = Query(default=None, ge=0),
    limit: int = Query(default=40, ge=1, le=100),
) -> SearchResponse:
    if min_duration is not None and max_duration is not None and min_duration > max_duration:
        raise HTTPException(status_code=400, detail="min_duration cannot exceed max_duration")

    known = {item.name for item in PROVIDERS} | set(indexed_providers())
    if provider is not None and provider not in known:
        raise HTTPException(status_code=400, detail="unknown provider")

    items, used = await search_all(
        q,
        provider=provider,
        quality=quality,
        min_duration=min_duration,
        max_duration=max_duration,
        limit=limit,
    )
    return SearchResponse(query=q, total=len(items), providers=used, items=items)
