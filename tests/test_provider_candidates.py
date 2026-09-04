from __future__ import annotations
import json
import unittest
from pathlib import Path
from backend.source_policy import is_searchable_provider, trusted_provider_names

ROOT = Path(__file__).resolve().parents[1]

class ProviderCandidateTests(unittest.TestCase):
    def test_sunporno_candidate_is_declared_but_disabled(self):
        rows = json.loads((ROOT / "deploy" / "search-engine-provider-candidates.example.json").read_text())
        row = next(item for item in rows if item["name"] == "sunporno")
        self.assertTrue(row["candidate_only"])
        self.assertIn("sunporno", trusted_provider_names())
        self.assertFalse(is_searchable_provider("sunporno"))
        self.assertEqual(row["sitemap_url"], "https://www.sunporno.com/sitemap.xml")

if __name__ == "__main__":
    unittest.main()
