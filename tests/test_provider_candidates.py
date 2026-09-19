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

    def test_brazzilmoms_current_video_shards_match_filter(self):
        production = json.loads((ROOT / "deploy" / "search-engine-providers.example.json").read_text())
        row = next(item for item in production if item["name"] == "brazzilmoms")
        pattern = re.compile(row["sitemap_include_pattern"])
        self.assertIsNotNone(pattern.search("https://brazzilmoms.com/sitemap/videos-1.xml"))
        self.assertIsNotNone(pattern.search("https://brazzilmoms.com/sitemap/videos-14.xml"))
        self.assertIsNone(pattern.search("https://brazzilmoms.com/sitemap/tags.xml"))


    def test_voyeurhit_is_promoted_to_production_catalog(self):
        production = json.loads((ROOT / "deploy" / "search-engine-providers.example.json").read_text())
        row = next(item for item in production if item["name"] == "voyeurhit")
        self.assertEqual(row["sitemap_url"], "https://voyeurhit.com/sitemap/")
        self.assertEqual(row["sitemap_include_pattern"], r"/sitemap_vids_[0-9]+/?$")
        self.assertEqual(row["sync_mode"], "incremental")
        self.assertIn("voyeurhit", trusted_provider_names())
        self.assertTrue(is_searchable_provider("voyeurhit"))

    def test_porngo_is_promoted_to_production_catalog(self):
        production = json.loads((ROOT / "deploy" / "search-engine-providers.example.json").read_text())
        row = next(item for item in production if item["name"] == "porngo")
        self.assertEqual(row["sitemap_url"], "https://www.porngo.com/sitemap.xml")
        self.assertEqual(row["sitemap_child_order"], "reverse")
        self.assertIn("type=videos", row["sitemap_include_pattern"])
        self.assertIn("porngo", trusted_provider_names())
        self.assertTrue(is_searchable_provider("porngo"))

    def test_candidate_catalog_tracks_discovery_without_production_enablement(self):
        rows = json.loads((ROOT / "deploy" / "search-engine-provider-candidates.example.json").read_text())
        self.assertEqual(rows, [])
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
        for name in {"justporn", "fpo", "bigassporn", "brazzilmoms", "sextubespot", "xcafe", "mypornhere", "pussyspace", "tubev", "xxxbule", "theyarehuge", "sexvid", "pornid", "zbporn"}:
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


def test_megatube_is_promoted_after_enriched_gate():
    assert "megatube" in trusted_provider_names()
    assert is_searchable_provider("megatube")


def test_freeporn_is_promoted_after_full_gate():
    assert "freeporn" in trusted_provider_names()
    assert is_searchable_provider("freeporn")


def test_enriched_clock_providers_are_promoted():
    for name in ("pornsexvideo", "lexotic"):
        assert name in trusted_provider_names()
        assert is_searchable_provider(name)


def test_porndoe_is_promoted_after_enriched_gate():
    assert "porndoe" in trusted_provider_names()
    assert is_searchable_provider("porndoe")
