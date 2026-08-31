from __future__ import annotations

import json
import os

from backend.providers.base import SearchProvider
from backend.providers.demo import DemoProvider
from backend.providers.sitemap import SitemapProvider


def _configured_sitemap_providers() -> list[SearchProvider]:
    raw = os.environ.get("SEARCH_SITEMAP_PROVIDERS_JSON", "").strip()
    if not raw:
        return []

    try:
        rows = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("SEARCH_SITEMAP_PROVIDERS_JSON is not valid JSON") from exc

    if not isinstance(rows, list):
        raise RuntimeError("SEARCH_SITEMAP_PROVIDERS_JSON must contain a JSON array")

    providers: list[SearchProvider] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"sitemap provider #{index + 1} must be a JSON object")

        try:
            providers.append(
                SitemapProvider(
                    name=str(row["name"]),
                    sitemap_url=str(row["sitemap_url"]),
                    max_pages=int(row.get("max_pages", 1000)),
                    delay_seconds=float(row.get("delay_seconds", 0.25)),
                    timeout_seconds=float(row.get("timeout_seconds", 15.0)),
                    obey_robots=bool(row.get("obey_robots", True)),
                )
            )
        except KeyError as exc:
            raise RuntimeError(
                f"sitemap provider #{index + 1} is missing {exc.args[0]!r}"
            ) from exc

    names = [provider.name for provider in providers]
    if len(names) != len(set(names)):
        raise RuntimeError("configured provider names must be unique")
    return providers


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


_configured = _configured_sitemap_providers()

PROVIDERS: list[SearchProvider] = list(_configured)
if not _configured or _truthy_env("SEARCH_ENABLE_DEMO"):
    PROVIDERS.insert(0, DemoProvider())
