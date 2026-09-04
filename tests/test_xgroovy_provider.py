from __future__ import annotations
import json
from pathlib import Path
from backend.source_policy import is_searchable_provider, trusted_provider_names

ROOT=Path(__file__).resolve().parents[1]

def test_xgroovy_is_searchable_sitemap_provider():
    rows=json.loads((ROOT/"deploy"/"search-engine-providers.example.json").read_text())
    row=next(r for r in rows if r["name"]=="xgroovy")
    assert row["sitemap_url"]=="https://xgroovy.com/sitemap/"
    assert "type=videos" in row["sitemap_include_pattern"]
    assert row["obey_robots"] is True
    assert "xgroovy" in trusted_provider_names()
    assert is_searchable_provider("xgroovy")
