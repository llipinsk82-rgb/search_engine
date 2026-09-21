from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import monotonic

from backend.content_class import classify_content_evidence
from backend.index import (
    get_item,
    list_content_enrichment_candidates,
    record_content_enrichment_attempt,
    update_content_evidence,
    update_preview_url,
)
from backend.media_policy import media_url_allowed
from backend.settings import DB_PATH


@dataclass
class ContentEnrichmentReport:
    attempted: int = 0
    enriched: int = 0
    classified_amateur: int = 0
    classified_studio: int = 0
    conflicts: int = 0
    no_signal: int = 0
    failures: int = 0


def _failure_delay(failure_count: int) -> timedelta:
    hours = 6 * (2 ** max(0, failure_count - 1))
    return min(timedelta(hours=hours), timedelta(days=7))


async def enrich_unknown_content(
    providers,
    *,
    batch_size: int,
    max_seconds: float,
    path: Path = DB_PATH,
    now: datetime | None = None,
) -> ContentEnrichmentReport:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if max_seconds < 0:
        raise ValueError("max_seconds must be non-negative")

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    eligible = {
        provider.name: provider
        for provider in providers
        if getattr(provider, "content_class_enrichment", False)
        and callable(getattr(provider, "enrich_content_evidence", None))
    }
    report = ContentEnrichmentReport()
    if not eligible or max_seconds == 0:
        return report

    candidates = list_content_enrichment_candidates(
        set(eligible),
        limit=batch_size,
        now=now,
        path=path,
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
            fetched = await provider.enrich_content_evidence(item)
        except Exception:
            report.failures += 1
            failure_count = candidate.failure_count + 1
            record_content_enrichment_attempt(
                item.id,
                provider=item.provider,
                status="failure",
                failure_count=failure_count,
                last_attempt_at=now,
                next_attempt_at=now + _failure_delay(failure_count),
                path=path,
            )
            continue

        preview = str(fetched.preview_url) if fetched.preview_url else None
        if (
            preview
            and getattr(provider, "preview_enrichment", False)
            and media_url_allowed(item.provider, "preview", preview)
        ):
            update_preview_url(item.id, preview_url=preview, path=path)

        fetched_tags = list(fetched.tags)
        fetched_studio = fetched.studio
        evidence_improved = (
            fetched_tags != list(item.tags)
            or (fetched_studio or None) != (item.studio or None)
        )

        if not evidence_improved:
            report.no_signal += 1
            record_content_enrichment_attempt(
                item.id,
                provider=item.provider,
                status="no_signal",
                failure_count=0,
                last_attempt_at=now,
                next_attempt_at=now + timedelta(days=30),
                path=path,
            )
            continue

        changed = update_content_evidence(
            item.id,
            tags=fetched_tags,
            studio=fetched_studio,
            path=path,
        )
        if changed:
            report.enriched += 1

        stored = get_item(item.id, path=path)
        if stored is None:
            report.failures += 1
            failure_count = candidate.failure_count + 1
            record_content_enrichment_attempt(
                item.id,
                provider=item.provider,
                status="failure",
                failure_count=failure_count,
                last_attempt_at=now,
                next_attempt_at=now + _failure_delay(failure_count),
                path=path,
            )
            continue

        classification = classify_content_evidence(
            tags=stored.tags,
            studio=stored.studio,
        )
        if classification.content_class == "amateur":
            report.classified_amateur += 1
        elif classification.content_class == "studio":
            report.classified_studio += 1
        elif classification.source == "conflict":
            report.conflicts += 1

        if classification.source == "none":
            report.no_signal += 1
            record_content_enrichment_attempt(
                item.id,
                provider=item.provider,
                status="no_signal",
                failure_count=0,
                last_attempt_at=now,
                next_attempt_at=now + timedelta(days=30),
                path=path,
            )
        else:
            record_content_enrichment_attempt(
                item.id,
                provider=item.provider,
                status="success",
                failure_count=0,
                last_attempt_at=now,
                next_attempt_at=None,
                path=path,
            )

    return report
