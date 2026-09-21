from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from backend.providers import build_providers


class ProviderRegistryTests(unittest.TestCase):
    def test_demo_is_default_when_no_real_provider_is_configured(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SEARCH_SITEMAP_PROVIDERS_JSON": "",
                "SEARCH_ENABLE_DEMO": "",
            },
            clear=False,
        ):
            providers = build_providers()

        self.assertEqual([provider.name for provider in providers], ["demo"])

    def test_demo_is_omitted_when_real_providers_exist(self) -> None:
        config = json.dumps(
            [
                {
                    "name": "real",
                    "sitemap_url": "https://example.com/sitemap.xml",
                }
            ]
        )
        with patch.dict(
            os.environ,
            {
                "SEARCH_SITEMAP_PROVIDERS_JSON": config,
                "SEARCH_ENABLE_DEMO": "",
            },
            clear=False,
        ):
            providers = build_providers()

        self.assertEqual([provider.name for provider in providers], ["real"])
        self.assertEqual(providers[0].sync_mode, "incremental")

    def test_snapshot_mode_can_be_configured_explicitly(self) -> None:
        config = json.dumps(
            [
                {
                    "name": "full",
                    "sitemap_url": "https://example.com/sitemap.xml",
                    "sync_mode": "snapshot",
                }
            ]
        )
        with patch.dict(
            os.environ,
            {
                "SEARCH_SITEMAP_PROVIDERS_JSON": config,
                "SEARCH_ENABLE_DEMO": "",
            },
            clear=False,
        ):
            providers = build_providers()

        self.assertEqual(providers[0].sync_mode, "snapshot")

    def test_demo_can_be_enabled_explicitly(self) -> None:
        config = json.dumps(
            [
                {
                    "name": "real",
                    "sitemap_url": "https://example.com/sitemap.xml",
                }
            ]
        )
        with patch.dict(
            os.environ,
            {
                "SEARCH_SITEMAP_PROVIDERS_JSON": config,
                "SEARCH_ENABLE_DEMO": "1",
            },
            clear=False,
        ):
            providers = build_providers()

        self.assertEqual([provider.name for provider in providers], ["demo", "real"])

    def test_duplicate_provider_names_are_rejected(self) -> None:
        config = json.dumps(
            [
                {"name": "dup", "sitemap_url": "https://example.com/a.xml"},
                {"name": "dup", "sitemap_url": "https://example.com/b.xml"},
            ]
        )
        with patch.dict(
            os.environ,
            {"SEARCH_SITEMAP_PROVIDERS_JSON": config},
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                build_providers()


if __name__ == "__main__":
    unittest.main()
def test_content_class_enrichment_defaults_off(monkeypatch):
    rows = [{"name": "example", "sitemap_url": "https://example.com/sitemap.xml"}]
    monkeypatch.setenv("SEARCH_SITEMAP_PROVIDERS_JSON", json.dumps(rows))
    monkeypatch.setenv("SEARCH_PROVIDER_CONFIG_FILE", "")
    provider = build_providers()[0]
    assert provider.content_class_enrichment is False


def test_content_class_enrichment_can_be_enabled_explicitly(monkeypatch):
    rows = [{
        "name": "example",
        "sitemap_url": "https://example.com/sitemap.xml",
        "content_class_enrichment": True,
    }]
    monkeypatch.setenv("SEARCH_SITEMAP_PROVIDERS_JSON", json.dumps(rows))
    monkeypatch.setenv("SEARCH_PROVIDER_CONFIG_FILE", "")
    provider = build_providers()[0]
    assert provider.content_class_enrichment is True
