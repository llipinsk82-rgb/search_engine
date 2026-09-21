from __future__ import annotations

import json
from pathlib import Path

from backend.live import LIVE_ADAPTERS

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "deploy" / "search-engine-providers.example.json"
MANIFEST = ROOT / "tests" / "fixtures" / "preview_audit_manifest.json"
RULES = ROOT / "deploy" / "search-engine-preview-rules.json"

_ALLOWED = {
    "PLAYBACK_CONFIRMED",
    "EXTRACT_CONFIRMED",
    "NO_SIGNAL",
    "AMBIGUOUS",
    "BLOCKED_BY_POLICY",
    "FETCH_UNAVAILABLE",
}


def _rows(path: Path):
    return json.loads(path.read_text())


def test_preview_audit_represents_configured_and_live_provider_universe_once():
    configured = {row["name"] for row in _rows(CATALOG)}
    live = {adapter.name for adapter in LIVE_ADAPTERS}
    audit = _rows(MANIFEST)
    names = [row["provider"] for row in audit]
    assert len(names) == len(set(names))
    assert configured | live <= set(names)
    assert {row["status"] for row in audit} <= _ALLOWED
    assert {row["source_kind"] for row in audit} <= {
        "sitemap", "live", "both", "index-only"
    }


def test_playback_confirmed_rows_have_reduced_fixture_and_policy_evidence():
    for row in _rows(MANIFEST):
        if row["status"] != "PLAYBACK_CONFIRMED":
            continue
        assert row["sample_count"] >= 1
        assert row["rule_kind"] in {"linked_attribute", "page_json", "custom", "live_search_exact"}
        assert row["preview_hosts"]
        assert row["playback_mode"] in {"direct", "proxy"}
        assert row["policy_host_suffixes"]
        assert (ROOT / row["fixture"]).is_file()
        assert (ROOT / row["negative_fixture"]).is_file()


def test_policy_blocked_rows_do_not_claim_playback():
    for row in _rows(MANIFEST):
        if row["status"] == "BLOCKED_BY_POLICY":
            assert row.get("playback_mode") in {None, "disabled"}


def test_runtime_rule_file_is_exact_confirmed_projection():
    audit = _rows(MANIFEST)
    expected = [
        {
            key: value
            for key, value in row.items()
            if key not in {
                "status",
                "sample_count",
                "source_kind",
                "fixture",
                "negative_fixture",
            }
        }
        for row in audit
        if row["status"] == "PLAYBACK_CONFIRMED"
    ]
    assert _rows(RULES) == expected


def test_playback_confirmed_rows_declare_storage_mode():
    confirmed = [row for row in _rows(MANIFEST) if row["status"] == "PLAYBACK_CONFIRMED"]
    assert confirmed
    assert {row["storage_mode"] for row in confirmed} <= {"stable", "ephemeral"}
    modes = {row["provider"]: row["storage_mode"] for row in confirmed}
    assert {name for name, mode in modes.items() if mode == "ephemeral"} == {
        "thumbzilla", "tnaflix", "tube8", "youjizz"
    }
    assert {name for name, mode in modes.items() if mode == "stable"} == {
        "bigfuck", "drtuber", "hqporn", "spankbang", "xhamster"
    }
