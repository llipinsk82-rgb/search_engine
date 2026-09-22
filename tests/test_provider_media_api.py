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
    rule_names = sorted({rule["provider"] for rule in rules})
    with patch("backend.app.indexed_providers", return_value=rule_names):
        payload = asyncio.run(providers())
    rows = {row["name"]: row for row in payload["media_policies"]}
    for rule in rules:
        assert rows[rule["provider"]]["preview_mode"] == rule["playback_mode"]


def test_provider_api_exposes_preview_resolution_storage_modes():
    with patch("backend.app.indexed_providers", return_value=[]):
        payload = asyncio.run(providers())
    rows = {row["name"]: row for row in payload["media_policies"]}
    assert rows["tube8"]["preview_resolution_mode"] == "on_demand"
    assert rows["tube8"]["preview_storage_mode"] == "ephemeral"
    assert rows["bigfuck"]["preview_resolution_mode"] == "stored"
    assert rows["bigfuck"]["preview_storage_mode"] == "stable"
    assert rows["pornhub"]["preview_resolution_mode"] == "stored"
    assert rows["pornhub"]["preview_storage_mode"] == "stable"
    for name in ("thumbzilla", "tnaflix", "tube8", "youjizz"):
        assert rows[name]["preview_resolution_mode"] == "on_demand"
        assert rows[name]["preview_storage_mode"] == "ephemeral"


def test_custom_stable_preview_rules_resolve_on_demand_for_uncached_rows():
    promoted = {"xvideos", "xnxx", "mypornhere", "pussyspace", "porndig", "sexvid", "pornid", "zbporn"}
    with patch("backend.app.indexed_providers", return_value=sorted(promoted)):
        payload = asyncio.run(providers())
    rows = {row["name"]: row for row in payload["media_policies"]}
    for name in promoted:
        assert rows[name]["preview_resolution_mode"] == "on_demand"
        assert rows[name]["preview_storage_mode"] == "stable"
