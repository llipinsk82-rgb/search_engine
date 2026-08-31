from __future__ import annotations

from abc import ABC, abstractmethod

from backend.models import SearchItem


class SearchProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, limit: int = 40) -> list[SearchItem]:
        """Return normalized metadata results for one provider."""
        raise NotImplementedError

    async def collect(self, limit: int = 1000) -> list[SearchItem]:
        """Collect a provider snapshot for indexing.

        Search-only providers may keep the default behavior. Providers with a
        dedicated catalog/feed endpoint should override this method.
        """
        return await self.search("", limit=limit)
