import json
from pathlib import Path

import pytest

from backend.content_evidence_rules import (
    CONTENT_EVIDENCE_RULES,
    _load_rules,
    extract_studio_evidence,
    has_content_evidence_rule,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "content_evidence_pages"


@pytest.mark.parametrize(
    ("provider", "fixture", "url", "expected"),
    [
        ("xgroovy", "xgroovy-positive.html", "https://xgroovy.com/videos/117/sample/", "Brazzers"),
        ("xcafe", "xcafe-positive.html", "https://xcafe.com/366143/", "Blacked"),
        ("porndoe", "porndoe-positive.html", "https://porndoe.com/watch/pd6f9o1e7z7v", "Old Nanny"),
    ],
)
def test_confirmed_rule_extracts_explicit_item_bound_studio(provider, fixture, url, expected):
    html = (FIXTURES / fixture).read_text(encoding="utf-8")
    assert extract_studio_evidence(provider, html, url) == expected


@pytest.mark.parametrize(
    ("provider", "fixture", "url"),
    [
        ("xgroovy", "xgroovy-negative.html", "https://xgroovy.com/videos/117/sample/"),
        ("xcafe", "xcafe-negative.html", "https://xcafe.com/366143/"),
        ("porndoe", "porndoe-negative.html", "https://porndoe.com/watch/pd6f9o1e7z7v"),
    ],
)
def test_creator_uploader_channel_and_publisher_are_not_studio(provider, fixture, url):
    html = (FIXTURES / fixture).read_text(encoding="utf-8")
    assert extract_studio_evidence(provider, html, url) is None


def test_unruled_provider_and_malformed_markup_fail_closed():
    assert not has_content_evidence_rule("xvideos")
    assert extract_studio_evidence("xvideos", '<meta name="studio" content="Nope">', "https://www.xvideos.com/video.1/x") is None
    assert extract_studio_evidence("xgroovy", '<script type="application/ld+json">{broken', "https://xgroovy.com/videos/1/x") is None


def test_rule_registry_contains_exact_confirmed_providers():
    assert set(CONTENT_EVIDENCE_RULES) == {"xgroovy", "xcafe", "porndoe"}
    assert has_content_evidence_rule(" XCafe ")


def test_loader_rejects_duplicate_provider_and_unsupported_kind(tmp_path: Path):
    duplicate = [
        {"provider": "a", "rule_kind": "jsonld_path", "jsonld_type": "VideoObject", "path": ["producer", "name"], "canonical_fixture_url": "https://a.example/v/1"},
        {"provider": "A", "rule_kind": "jsonld_path", "jsonld_type": "VideoObject", "path": ["producer", "name"], "canonical_fixture_url": "https://a.example/v/2"},
    ]
    p = tmp_path / "duplicate.json"
    p.write_text(json.dumps(duplicate), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        _load_rules(p)

    p.write_text(json.dumps([{"provider": "a", "rule_kind": "regex", "canonical_fixture_url": "https://a.example/v/1"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        _load_rules(p)
