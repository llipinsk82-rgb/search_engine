from __future__ import annotations


def preview_provider_map(index_providers, live_adapters):
    eligible = {
        adapter.name: adapter
        for adapter in live_adapters
        if getattr(adapter, "preview_enrichment", False)
        and callable(getattr(adapter, "extract_preview", None))
    }
    eligible.update({
        provider.name: provider
        for provider in index_providers
        if getattr(provider, "preview_enrichment", False)
        and callable(getattr(provider, "extract_preview", None))
    })
    return eligible
