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
