from __future__ import annotations

from abc import ABC, abstractmethod

from backend.models import SearchItem


class SearchProvider(ABC):
    name: str
    sync_mode: str = "snapshot"
    backfill_priority: int = 100
    backfill_batch_size: int | None = None
    backfill_max_records: int | None = None

    @abstractmethod
    async def search(self, query: str, limit: int = 40) -> list[SearchItem]:
        """Return normalized metadata results for one provider."""
        raise NotImplementedError

    async def resolve_thumbnail(
        self,
        item: SearchItem,
        *,
        force: bool = False,
    ) -> str | None:
        return str(item.thumbnail) if item.thumbnail else None

    async def collect(self, limit: int = 1000) -> list[SearchItem]:
        """Collect provider metadata for indexing.

        Search-only providers may keep the default behavior. Providers with a
        dedicated catalog/feed endpoint should override this method.
        """
        return await self.search("", limit=limit)
