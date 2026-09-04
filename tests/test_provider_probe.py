from __future__ import annotations
import unittest
from backend.models import SearchItem
from backend.provider_probe import format_probe, summarize_probe

def item(i: str, *, thumb=True, duration=True, quality=True, tags=True):
    return SearchItem(
        id=i, provider="sample", title=f"Item {i}", url=f"https://example.com/{i}",
        thumbnail=f"https://example.com/{i}.jpg" if thumb else None,
        duration_seconds=60 if duration else None,
        quality="1080p" if quality else None,
        tags=["tag"] if tags else [],
    )

class ProviderProbeTests(unittest.TestCase):
    def test_empty_is_no_results(self):
        self.assertEqual(summarize_probe("sample", []).status, "NO_RESULTS")

    def test_good_metadata_is_generic_ready(self):
        result = summarize_probe("sample", [item("1"), item("2"), item("3")])
        self.assertEqual(result.status, "GENERIC_READY")
        self.assertEqual(result.unique_urls, 3)
        self.assertEqual(result.percentage(result.thumbnails), 100)

    def test_sparse_metadata_requires_custom(self):
        result = summarize_probe("sample", [
            item("1", thumb=False, duration=False, quality=False, tags=False),
            item("2", thumb=False, duration=False, quality=False, tags=False),
            item("3"),
        ])
        self.assertEqual(result.status, "CUSTOM_REQUIRED")

    def test_format_contains_summary_and_sample(self):
        rows = [item("1")]
        text = format_probe(summarize_probe("sample", rows), rows)
        self.assertIn("provider=sample", text)
        self.assertIn("status=GENERIC_READY", text)
        self.assertIn("sample[1]=", text)

if __name__ == "__main__":
    unittest.main()
