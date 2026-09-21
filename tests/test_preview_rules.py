from __future__ import annotations

import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "preview_audit_manifest.json"


def _module():
    return importlib.import_module("backend.preview_rules")


def _confirmed():
    return {
        row["provider"]: row
        for row in json.loads(MANIFEST.read_text())
        if row["status"] == "PLAYBACK_CONFIRMED"
    }


def test_rule_registry_exactly_matches_confirmed_manifest():
    m = _module()
    confirmed = _confirmed()
    assert set(m.PREVIEW_RULES) == set(confirmed)
    for name, rule in m.PREVIEW_RULES.items():
        row = confirmed[name]
        assert rule.kind == row["rule_kind"]
        assert rule.preview_host_suffixes == tuple(row["policy_host_suffixes"])


def test_live_search_fixtures_require_exact_canonical_match():
    m = _module()
    for row in _confirmed().values():
        if row["rule_kind"] != "live_search_exact":
            continue
        positive = json.loads((ROOT / row["fixture"]).read_text())
        negative = json.loads((ROOT / row["negative_fixture"]).read_text())
        assert m.select_exact_live_preview(
            [positive["result"]], positive["canonical_url"]
        ) == positive["result"]["preview_url"]
        assert m.select_exact_live_preview(
            [negative["result"]], negative["canonical_url"]
        ) is None


def test_linked_attribute_requires_exact_target_url():
    m = _module()
    rule = m.PreviewRule(
        provider="example",
        kind="linked_attribute",
        preview_host_suffixes=("cdn.example",),
        target_attribute="href",
        preview_attribute="data-preview",
    )
    exact = '<a href="/video/1" data-preview="https://cdn.example/p.mp4">x</a>'
    other = '<a href="/video/2" data-preview="https://cdn.example/p.mp4">x</a>'
    assert m.extract_preview_url(rule, exact, "https://example.com/video/1/") == "https://cdn.example/p.mp4"
    assert m.extract_preview_url(rule, other, "https://example.com/video/1/") is None


def test_page_json_requires_identity_match_and_ignores_full_video_fields():
    m = _module()
    rule = m.PreviewRule(
        provider="example",
        kind="page_json",
        preview_host_suffixes=("cdn.example",),
        json_identity_field="url",
        json_preview_field="previewUrl",
    )
    exact = '<script type="application/ld+json">{"url":"https://example.com/video/1","previewUrl":"https://cdn.example/p.mp4","contentUrl":"https://cdn.example/full.mp4"}</script>'
    other = '<script type="application/ld+json">{"url":"https://example.com/video/2","previewUrl":"https://cdn.example/p.mp4"}</script>'
    full_only = '<script type="application/ld+json">{"url":"https://example.com/video/1","contentUrl":"https://cdn.example/full.mp4","embedUrl":"https://example.com/embed/1"}</script>'
    assert m.extract_preview_url(rule, exact, "https://example.com/video/1") == "https://cdn.example/p.mp4"
    assert m.extract_preview_url(rule, other, "https://example.com/video/1") is None
    assert m.extract_preview_url(rule, full_only, "https://example.com/video/1") is None


def test_rule_storage_mode_matches_audit_manifest():
    m = _module()
    for name, row in _confirmed().items():
        assert m.PREVIEW_RULES[name].storage_mode == row["storage_mode"]
