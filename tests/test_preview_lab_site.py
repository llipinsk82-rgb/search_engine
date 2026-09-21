from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "tools" / "preview_lab_site"


def test_preview_lab_site_is_isolated_and_read_only() -> None:
    html = (SITE / "index.html").read_text(encoding="utf-8")
    app = (SITE / "app.js").read_text(encoding="utf-8")
    assert 'id="search-form"' in html
    assert 'id="provider"' in html
    assert 'id="results"' in html
    assert 'const TEST_PROVIDERS = [' in app
    assert 'fetch(`/test-api/search?' in app
    assert 'fetch(`/test-api/preview/${encodeURIComponent(item.id)}`' in app
    assert 'method: "POST"' not in app
    assert 'method: "PUT"' not in app
    assert 'method: "DELETE"' not in app


def test_preview_lab_contains_verified_candidate_rules_only() -> None:
    app = (SITE / "app.js").read_text(encoding="utf-8")
    for provider in ("xvideos", "xnxx", "xgroovy", "mypornhere", "pussyspace", "porndig"):
        assert provider in app
    assert 'xcafe' not in app
    assert 'sunporno' not in app


def test_preview_lab_uses_external_assets_not_inline_script() -> None:
    html = (SITE / "index.html").read_text(encoding="utf-8")
    assert '<script src="/test/app.js" defer></script>' in html
    assert '<link rel="stylesheet" href="/test/styles.css">' in html
    assert '<script>' not in html


def test_preview_lab_site_exposes_only_verified_new_candidates() -> None:
    app = (SITE / "app.js").read_text(encoding="utf-8")
    for provider in ("sexvid", "pornid", "zbporn"):
        assert provider in app


def test_preview_lab_uses_unauthenticated_test_api_only() -> None:
    app = (SITE / "app.js").read_text(encoding="utf-8")
    assert "/test-api/" in app
    assert "`/api/preview/" not in app
    assert "`/api/search?" not in app
    assert 'fetch("/api/providers"' not in app


def test_preview_cards_have_visible_play_button_and_toggle_contract() -> None:
    app = (SITE / "app.js").read_text(encoding="utf-8")
    css = (SITE / "styles.css").read_text(encoding="utf-8")
    assert 'className = "preview-play"' in app
    assert 'textContent = "▶"' in app
    assert 'setAttribute("aria-label", "Play preview")' in app
    assert 'playButton.addEventListener("click"' in app
    assert 'event.stopPropagation()' in app
    assert ".preview-play" in css

def test_provider_dropdown_is_limited_to_preview_lab_candidates() -> None:
    app = (SITE / "app.js").read_text(encoding="utf-8")
    html = (SITE / "index.html").read_text(encoding="utf-8")
    expected = (
        "xvideos", "xnxx", "xgroovy", "mypornhere", "pussyspace",
        "porndig", "sexvid", "pornid", "zbporn",
    )
    assert 'const TEST_PROVIDERS = [' in app
    for provider in expected:
        assert f'"{provider}"' in app
    assert 'fetch("/test-api/providers"' not in app
    assert '<option value="">All test candidates</option>' in html
    assert 'All providers' not in html


def test_all_candidates_searches_only_test_providers() -> None:
    app = (SITE / "app.js").read_text(encoding="utf-8")
    assert "Promise.all(TEST_PROVIDERS.map" in app
    assert 'params.set("provider", provider)' in app
