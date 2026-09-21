import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "deploy" / "search-engine-providers.example.json"
MANIFEST = ROOT / "tests" / "fixtures" / "content_evidence_audit_manifest.json"
RULES = ROOT / "deploy" / "search-engine-content-evidence-rules.json"

_ALLOWED = {
    "STUDIO_RULE_CONFIRMED",
    "NO_STUDIO_SIGNAL",
    "AMBIGUOUS",
    "FETCH_UNAVAILABLE",
}
_KINDS = {"jsonld_path", "meta_name", "labelled_text"}


def _rows(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_content_evidence_audit_represents_configured_provider_universe_once():
    configured = {row["name"] for row in _rows(CATALOG)}
    audit = _rows(MANIFEST)
    names = [row["provider"] for row in audit]
    assert len(names) == len(set(names))
    assert configured == set(names)
    assert {row["status"] for row in audit} <= _ALLOWED
    assert all(1 <= int(row["sample_count"]) <= 3 for row in audit)


def test_confirmed_rows_have_deterministic_positive_and_negative_fixtures():
    for row in _rows(MANIFEST):
        if row["status"] != "STUDIO_RULE_CONFIRMED":
            continue
        assert row["rule_kind"] in _KINDS
        assert row["canonical_fixture_url"].startswith("https://")
        assert (ROOT / row["fixture"]).is_file()
        assert (ROOT / row["negative_fixture"]).is_file()


def test_runtime_rules_are_exact_confirmed_projection():
    audit = _rows(MANIFEST)
    expected = [
        {
            key: value
            for key, value in row.items()
            if key
            not in {
                "status",
                "sample_count",
                "fixture",
                "negative_fixture",
                "notes",
            }
        }
        for row in audit
        if row["status"] == "STUDIO_RULE_CONFIRMED"
    ]
    assert _rows(RULES) == expected
