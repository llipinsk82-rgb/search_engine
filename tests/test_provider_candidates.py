from __future__ import annotations
import json
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

    def test_candidate_catalog_is_empty_after_promotion(self):
        rows = json.loads((ROOT / "deploy" / "search-engine-provider-candidates.example.json").read_text())
        self.assertEqual(rows, [])

if __name__ == "__main__":
    unittest.main()
