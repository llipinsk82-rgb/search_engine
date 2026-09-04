from __future__ import annotations

from dataclasses import dataclass

from backend.models import SearchItem
from backend.providers.base import SearchProvider


@dataclass(frozen=True)
class ProviderProbeResult:
    provider: str
    fetched: int
    unique_urls: int
    thumbnails: int
    durations: int
    qualities: int
    tagged: int
    status: str

    def percentage(self, value: int) -> int:
        if self.fetched <= 0:
            return 0
        return round((value / self.fetched) * 100)


def summarize_probe(provider: str, items: list[SearchItem]) -> ProviderProbeResult:
    fetched = len(items)
    unique_urls = len({str(item.url) for item in items})
    thumbnails = sum(item.thumbnail is not None for item in items)
    durations = sum(item.duration_seconds is not None for item in items)
    qualities = sum(bool(item.quality) for item in items)
    tagged = sum(bool(item.tags) for item in items)

    if fetched == 0:
        status = "NO_RESULTS"
    else:
        thumbnail_ratio = thumbnails / fetched
        duration_ratio = durations / fetched
        unique_ratio = unique_urls / fetched
        if thumbnail_ratio >= 0.5 and duration_ratio >= 0.5 and unique_ratio >= 0.8:
            status = "GENERIC_READY"
        else:
            status = "CUSTOM_REQUIRED"

    return ProviderProbeResult(
        provider=provider,
        fetched=fetched,
        unique_urls=unique_urls,
        thumbnails=thumbnails,
        durations=durations,
        qualities=qualities,
        tagged=tagged,
        status=status,
    )


async def probe_provider(
    provider: SearchProvider,
    *,
    limit: int = 5,
) -> tuple[ProviderProbeResult, list[SearchItem]]:
    items = await provider.collect(limit=max(1, limit))
    return summarize_probe(provider.name, items), items


def format_probe(
    result: ProviderProbeResult,
    items: list[SearchItem],
    *,
    sample_limit: int = 3,
) -> str:
    lines = [
        f"provider={result.provider}",
        f"status={result.status}",
        f"fetched={result.fetched}",
        f"unique_urls={result.unique_urls}",
        (
            "metadata="
            f"thumbnail:{result.thumbnails}/{result.fetched}({result.percentage(result.thumbnails)}%) "
            f"duration:{result.durations}/{result.fetched}({result.percentage(result.durations)}%) "
            f"quality:{result.qualities}/{result.fetched}({result.percentage(result.qualities)}%) "
            f"tags:{result.tagged}/{result.fetched}({result.percentage(result.tagged)}%)"
        ),
    ]

    for index, item in enumerate(items[:sample_limit], start=1):
        lines.append(
            f"sample[{index}]="
            f"url={str(item.url)} | "
            f"duration={item.duration_seconds!r} | "
            f"quality={item.quality!r} | "
            f"thumbnail={'yes' if item.thumbnail else 'no'} | "
            f"title={item.title[:120]!r}"
        )
    return "\n".join(lines)
