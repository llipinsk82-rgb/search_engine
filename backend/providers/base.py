from __future__ import annotations

from abc import ABC, abstractmethod

from backend.models import SearchItem


class SearchProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, limit: int = 40) -> list[SearchItem]:
        """Return normalized metadata results for one provider."""
        raise NotImplementedError
