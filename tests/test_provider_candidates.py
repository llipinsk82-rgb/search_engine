from __future__ import annotations
import json
import re
import unittest
from pathlib import Path
from backend.source_policy import is_searchable_provider, trusted_provider_names

ROOT = Path(__file__).resolve().parents[1]

class ProviderCandidateTests(unittest.TestCase):
    def test_sunporno_is_promoted_to_production_catalog(self):
        production = json.loads((ROOT / "deploy" / "search-engine-providers.example.json").read_text())
        row = next(item for item in production if item["name"] == "sunporno")
        self.assertEqual(row["sitemap_url"], "https://www.sunporno.com/sitemap.xml")
        self.assertEqual(row["sync_mode"], "incremental")
        self.assertIn("sunporno", trusted_provider_names())
        self.assertTrue(is_searchable_provider("sunporno"))

    def test_candidate_catalog_tracks_discovery_without_production_enablement(self):
        rows = json.loads((ROOT / "deploy" / "search-engine-provider-candidates.example.json").read_text())
        self.assertEqual({row["name"] for row in rows}, {"porndoe"})
        self.assertTrue(all(row["sync_mode"] == "incremental" for row in rows))

    def test_txxx_is_promoted_to_production_catalog(self):
        production = json.loads((ROOT / "deploy" / "search-engine-providers.example.json").read_text())
        row = next(item for item in production if item["name"] == "txxx")
        self.assertEqual(row["sitemap_url"], "https://txxx.com/sitemap.xml")
        self.assertEqual(row["sitemap_child_order"], "reverse")
        self.assertIn("txxx", trusted_provider_names())
        self.assertTrue(is_searchable_provider("txxx"))

    def test_new_generic_ready_batch_is_promoted(self):
        production = json.loads((ROOT / "deploy" / "search-engine-providers.example.json").read_text())
        names = {item["name"] for item in production}
        for name in {"justporn", "fpo", "bigassporn", "brazzilmoms", "sextubespot", "xcafe", "mypornhere", "pussyspace", "tubev", "xxxbule"}:
            self.assertIn(name, names)
            self.assertIn(name, trusted_provider_names())
            self.assertTrue(is_searchable_provider(name))

    def test_porndig_is_promoted_to_production_catalog(self):
        production = json.loads((ROOT / "deploy" / "search-engine-providers.example.json").read_text())
        row = next(item for item in production if item["name"] == "porndig")
        self.assertTrue(row["sitemap_url"].endswith("/sitemap.xml"))
        self.assertTrue(row["sitemap_include_pattern"].endswith("\\.xml\\.gz$"))
        self.assertIn("porndig", trusted_provider_names())
        self.assertTrue(is_searchable_provider("porndig"))


if __name__ == "__main__":
    unittest.main()
