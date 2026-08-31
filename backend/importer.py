from __future__ import annotations

import hashlib
import json
from pathlib import Path

from backend.models import SearchItem


def _stable_id(provider: str, url: str) -> str:
    return hashlib.sha256(f"{provider}:{url}".encode("utf-8")).hexdigest()[:24]


def load_jsonl(
    source: Path,
    *,
    provider_override: str | None = None,
) -> dict[str, list[SearchItem]]:
    """Load normalized metadata from a JSONL file.

    Required fields per row: title, url and provider (unless overridden).
    id is optional and is derived from provider+url when missing.
    """
    groups: dict[str, dict[str, SearchItem]] = {}

    with source.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{source}:{line_number}: invalid JSON: {exc}") from exc

            if not isinstance(payload, dict):
                raise ValueError(f"{source}:{line_number}: row must be a JSON object")

            provider = (provider_override or str(payload.get("provider") or "")).strip()
            title = str(payload.get("title") or "").strip()
            url = str(payload.get("url") or "").strip()

            if not provider:
                raise ValueError(f"{source}:{line_number}: provider is required")
            if not title:
                raise ValueError(f"{source}:{line_number}: title is required")
            if not url:
                raise ValueError(f"{source}:{line_number}: url is required")

            item_id = str(payload.get("id") or "").strip() or _stable_id(provider, url)
            tags = payload.get("tags") or []
            if not isinstance(tags, list):
                raise ValueError(f"{source}:{line_number}: tags must be a list")

            item = SearchItem(
                id=item_id,
                provider=provider,
                title=title,
                url=url,
                thumbnail=payload.get("thumbnail"),
                duration_seconds=payload.get("duration_seconds"),
                quality=payload.get("quality"),
                tags=[str(tag) for tag in tags if str(tag).strip()],
                score=float(payload.get("score") or 0.0),
            )
            groups.setdefault(provider, {})[item.id] = item

    if provider_override and provider_override not in groups:
        groups[provider_override] = {}

    return {
        provider: list(items.values())
        for provider, items in groups.items()
    }
