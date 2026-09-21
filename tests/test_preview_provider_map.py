from __future__ import annotations

import importlib

from backend.live import LIVE_ADAPTERS
from backend.providers.sitemap import SitemapProvider


class Fake:
    def __init__(self, name, enabled):
        self.name = name
        self.preview_enrichment = enabled

    async def extract_preview(self, item):
        return None


def _map(index_providers, live_adapters):
    return importlib.import_module("backend.preview_providers").preview_provider_map(
        index_providers, live_adapters
    )


def test_live_only_provider_can_be_eligible():
    live = Fake("tube8", True)
    assert _map([], [live]) == {"tube8": live}


def test_configured_provider_wins_duplicate_when_both_are_eligible():
    index = Fake("same", True)
    live = Fake("same", True)
    assert _map([index], [live])["same"] is index


def test_disabled_provider_is_not_eligible():
    assert _map([Fake("x", False)], []) == {}


def test_real_live_capabilities_follow_audited_rules():
    rules = importlib.import_module("backend.preview_rules").PREVIEW_RULES
    live = {adapter.name: adapter for adapter in LIVE_ADAPTERS}
    for name, adapter in live.items():
        assert adapter.preview_enrichment is (name in rules)


def test_live_search_strategy_does_not_enable_same_named_sitemap_provider():
    rules = importlib.import_module("backend.preview_rules").PREVIEW_RULES
    assert rules["tube8"].kind == "live_search_exact"
    index = SitemapProvider(
        name="tube8",
        sitemap_url="https://example.com/sitemap.xml",
        obey_robots=False,
    )
    live = next(adapter for adapter in LIVE_ADAPTERS if adapter.name == "tube8")
    assert index.preview_enrichment is False
    assert live.preview_enrichment is True
    assert _map([index], [live])["tube8"] is live
