from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class SearchItem(BaseModel):
    id: str
    provider: str
    title: str
    url: HttpUrl
    thumbnail: HttpUrl | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    quality: str | None = None
    tags: list[str] = Field(default_factory=list)
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
    min_duration: int | None = Field(default=None, ge=0)
    max_duration: int | None = Field(default=None, ge=0)
    offset: int = Field(default=0, ge=0, le=5000)
    limit: int = Field(default=40, ge=1, le=100)


class SearchResponse(BaseModel):
    query: str
    total: int
    offset: int
    limit: int
    has_more: bool
    providers: list[str]
    items: list[SearchItem]
