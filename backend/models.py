from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class SearchItem(BaseModel):
    id: str
    provider: str
    title: str
    url: HttpUrl
    thumbnail: HttpUrl | None = None
    preview_url: HttpUrl | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    quality: str | None = None
    tags: list[str] = Field(default_factory=list)
    age_check_status: Literal["required", "not_required", "unknown"] = "unknown"
    score: float = 0.0
    alternate_sources: list["SourceVariant"] = Field(default_factory=list)


class SourceVariant(BaseModel):
    provider: str
    url: HttpUrl
    quality: str | None = None


class SearchRequest(BaseModel):
    q: str = Field(default="", max_length=200)
    provider: str | None = None
    quality: str | None = None
    age_check: Literal["required", "not_required", "unknown"] | None = None
    min_duration: int | None = Field(default=None, ge=0)
    max_duration: int | None = Field(default=None, ge=0)
    offset: int = Field(default=0, ge=0, le=5000)
    limit: int = Field(default=40, ge=1, le=100)
    exclude_ids: list[str] = Field(default_factory=list, max_length=800)


class SearchResponse(BaseModel):
    query: str
    total: int
    offset: int
    limit: int
    has_more: bool
    providers: list[str]
    items: list[SearchItem]


class LiveRefreshRequest(BaseModel):
    q: str = Field(min_length=1, max_length=200)
    provider: str | None = None
    quality: str | None = None
    age_check: Literal["required", "not_required", "unknown"] | None = None
    min_duration: int | None = Field(default=None, ge=0)
    max_duration: int | None = Field(default=None, ge=0)
    page: int = Field(default=1, ge=1, le=5000)
    limit_per_provider: int = Field(default=24, ge=1, le=100)


class LiveProviderStatus(BaseModel):
    provider: str
    fetched: int
    total: int | None = None
    page: int
    elapsed_ms: int
    error: str | None = None


class LiveRefreshResponse(BaseModel):
    query: str
    cached_items: int
    indexed_items: int
    providers: list[LiveProviderStatus]
    items: list[SearchItem] = Field(default_factory=list)
