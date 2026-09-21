import asyncio
from unittest.mock import patch
from backend.app import providers


def test_provider_api_exposes_media_policy():
    with patch("backend.app.indexed_providers", return_value=[]):
        payload = asyncio.run(providers())
    rows = {row["name"]: row for row in payload["media_policies"]}
    assert rows["thumbzilla"]["thumbnail_mode"] == "proxy"
    assert rows["tube8"]["thumbnail_mode"] == "refresh"
    assert rows["milfporn"]["preview_mode"] == "disabled"
    assert ".phncdn.com" in rows["pornhub"]["preview_host_suffixes"]


def test_provider_api_matches_audited_preview_modes():
    import json
    from pathlib import Path
    rules = json.loads((Path(__file__).resolve().parents[1] / "deploy" / "search-engine-preview-rules.json").read_text())
    with patch("backend.app.indexed_providers", return_value=[]):
        payload = asyncio.run(providers())
    rows = {row["name"]: row for row in payload["media_policies"]}
    for rule in rules:
        assert rows[rule["provider"]]["preview_mode"] == rule["playback_mode"]
