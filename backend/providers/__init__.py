from __future__ import annotations

import json
import os
from pathlib import Path

from backend.providers.base import SearchProvider
from backend.providers.demo import DemoProvider
from backend.providers.sitemap import SitemapProvider


# Runtime safety caps protect production even when an older provider catalog is
# intentionally preserved across deploys. XVideos/XNXX require HTML page
# materialization and large batches can exceed the systemd maintenance window.
_BACKFILL_BATCH_CAPS: dict[str, int] = {
    # Tube8 is search-disabled but historical rows are intentionally preserved.
    # Keep any legacy/provider config from scheduling a 10k-row SQLite/FTS merge:
    # production showed that such a merge can outlive the 6-minute systemd window
    # even when network collection itself obeys the 180-second wall-clock budget.
    "tube8": 500,
    "xvideos": 100,
    "xnxx": 100,
}


def _backfill_batch_size(name: str, value: object) -> int | None:
    if value is None:
        return None
    configured = max(1, int(value))
    cap = _BACKFILL_BATCH_CAPS.get(name.strip().lower())
    return min(configured, cap) if cap is not None else configured


def _provider_rows() -> list[tuple[str, object]]:
    sources: list[tuple[str, str]] = []

    config_file = os.environ.get("SEARCH_PROVIDER_CONFIG_FILE", "").strip()
    if config_file:
        path = Path(config_file)
        try:
            sources.append((f"provider config file {path}", path.read_text(encoding="utf-8")))
        except OSError as exc:
            raise RuntimeError(f"cannot read provider config file {path}: {exc}") from exc

    inline = os.environ.get("SEARCH_SITEMAP_PROVIDERS_JSON", "").strip()
    if inline:
        sources.append(("SEARCH_SITEMAP_PROVIDERS_JSON", inline))

    rows_with_source: list[tuple[str, object]] = []
    for source, raw in sources:
        try:
            rows = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{source} is not valid JSON") from exc
        if not isinstance(rows, list):
            raise RuntimeError(f"{source} must contain a JSON array")
        rows_with_source.extend((source, row) for row in rows)
    return rows_with_source


def _configured_sitemap_providers() -> list[SearchProvider]:
    providers: list[SearchProvider] = []
    for index, (source, row) in enumerate(_provider_rows()):
        if not isinstance(row, dict):
            raise RuntimeError(f"{source}: provider #{index + 1} must be a JSON object")

        try:
            providers.append(
                SitemapProvider(
                    name=str(row["name"]),
                    sitemap_url=str(row["sitemap_url"]),
                    max_pages=int(row.get("max_pages", 1000)),
                    delay_seconds=float(row.get("delay_seconds", 0.25)),
                    timeout_seconds=float(row.get("timeout_seconds", 15.0)),
                    obey_robots=bool(row.get("obey_robots", True)),
                    sync_mode=str(row.get("sync_mode", "incremental")),
                    sitemap_include_pattern=(
                        str(row["sitemap_include_pattern"])
                        if row.get("sitemap_include_pattern")
                        else None
                    ),
                    sitemap_child_order=str(row.get("sitemap_child_order", "listed")),
                    fetch_concurrency=int(row.get("fetch_concurrency", 1)),
                    backfill_batch_size=_backfill_batch_size(
                        str(row["name"]),
                        row.get("backfill_batch_size"),
                    ),
                    backfill_priority=int(row.get("backfill_priority", 100)),
                    backfill_max_records=(
                        int(row["backfill_max_records"])
                        if row.get("backfill_max_records") is not None
                        else None
                    ),
                    enrich_missing_core_metadata=bool(row.get("enrich_missing_core_metadata", False)),
                )
            )
        except KeyError as exc:
            raise RuntimeError(
                f"{source}: provider #{index + 1} is missing {exc.args[0]!r}"
            ) from exc

    names = [provider.name for provider in providers]
    if len(names) != len(set(names)):
        raise RuntimeError("configured provider names must be unique")
    return providers


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def build_providers() -> list[SearchProvider]:
    configured = _configured_sitemap_providers()
    providers: list[SearchProvider] = list(configured)
    if not configured or _truthy_env("SEARCH_ENABLE_DEMO"):
        providers.insert(0, DemoProvider())
    return providers


PROVIDERS: list[SearchProvider] = build_providers()
