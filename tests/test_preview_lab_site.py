from pathlib import Path
import re

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


def test_preview_lab_uses_external_assets_not_inline_script() -> None:
    html = (SITE / "index.html").read_text(encoding="utf-8")
    assert '<script src="/test/app.js" defer></script>' in html
    assert '<link rel="stylesheet" href="/test/styles.css">' in html
    assert '<script>' not in html


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


def test_preview_lab_queue_contains_exactly_active_candidates() -> None:
    app = (SITE / "app.js").read_text(encoding="utf-8")
    block = app.split("const TEST_PROVIDERS = [", 1)[1].split("];", 1)[0]
    expected = {"xvideos", "xnxx", "xgroovy", "mypornhere", "pussyspace", "porndig", "sexvid", "pornid", "zbporn"}
    found = set(re.findall(r"\"([a-z0-9]+)\"", block))
    assert found == expected
    assert len(found) == 9


def test_preview_lab_requires_single_provider_selection() -> None:
    app = (SITE / "app.js").read_text(encoding="utf-8")
    html = (SITE / "index.html").read_text(encoding="utf-8")
    assert "Promise.all(TEST_PROVIDERS.map" not in app
    assert "if (!providerSelect.value)" in app
    assert '<option value="" selected>Select provider</option>' in html
    assert 'params.set("provider", provider)' in app


def test_mobile_play_uses_click_only_and_desktop_hover_is_fine_pointer_only() -> None:
    app = (SITE / "app.js").read_text(encoding="utf-8")
    assert 'window.matchMedia("(hover: hover) and (pointer: fine)")' in app
    assert "if (canHover)" in app
    assert 'playButton.addEventListener("click"' in app


def test_xgroovy_is_marked_proxy_required_without_direct_browser_candidate() -> None:
    app = (SITE / "app.js").read_text(encoding="utf-8")
    assert 'provider === "xgroovy"' in app
    assert 'source: "proxy"' in app
    assert 'badge("Proxy required", "none")' in app
