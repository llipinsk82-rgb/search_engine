from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import monotonic

from backend.index import (
    list_preview_enrichment_candidates,
    record_preview_enrichment_attempt,
    update_preview_url,
)
from backend.media_policy import media_url_allowed
from backend.preview_providers import preview_provider_map
from backend.settings import DB_PATH


@dataclass
class PreviewEnrichmentReport:
    attempted: int = 0
    extracted: int = 0
    stored: int = 0
    playable: int = 0
    no_preview: int = 0
    blocked_policy: int = 0
    failures: int = 0


def _failure_delay(failure_count: int) -> timedelta:
    hours = 6 * (2 ** max(0, failure_count - 1))
    return min(timedelta(hours=hours), timedelta(days=7))


async def enrich_missing_previews(
    index_providers,
    live_adapters,
    *,
    batch_size: int,
    max_seconds: float,
    path: Path = DB_PATH,
    now: datetime | None = None,
) -> PreviewEnrichmentReport:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if max_seconds < 0:
        raise ValueError("max_seconds must be non-negative")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    eligible = preview_provider_map(index_providers, live_adapters)
    report = PreviewEnrichmentReport()
    if not eligible or max_seconds == 0:
        return report

    candidates = list_preview_enrichment_candidates(
        set(eligible), limit=batch_size, now=now, path=path
    )
    deadline = monotonic() + float(max_seconds)

    for candidate in candidates:
        if monotonic() >= deadline:
            break
        item = candidate.item
        provider = eligible.get(item.provider)
        if provider is None:
            continue
        report.attempted += 1
        try:
            preview = await provider.extract_preview(item)
        except Exception:
            report.failures += 1
            failures = candidate.failure_count + 1
            record_preview_enrichment_attempt(
                item.id, provider=item.provider, status="failure",
                failure_count=failures, last_attempt_at=now,
                next_attempt_at=now + _failure_delay(failures), path=path,
            )
            continue

        if not preview:
            report.no_preview += 1
            record_preview_enrichment_attempt(
                item.id, provider=item.provider, status="no_preview",
                failure_count=0, last_attempt_at=now,
                next_attempt_at=now + timedelta(days=30), path=path,
            )
            continue

        report.extracted += 1
        preview = str(preview)
        if not media_url_allowed(item.provider, "preview", preview):
            report.blocked_policy += 1
            record_preview_enrichment_attempt(
                item.id, provider=item.provider, status="blocked_policy",
                failure_count=0, last_attempt_at=now,
                next_attempt_at=now + timedelta(days=30), path=path,
            )
            continue

        changed = update_preview_url(item.id, preview_url=preview, path=path)
        if changed:
            report.stored += 1
            report.playable += 1
        record_preview_enrichment_attempt(
            item.id, provider=item.provider, status="success",
            failure_count=0, last_attempt_at=now, next_attempt_at=None, path=path,
        )

    return report
