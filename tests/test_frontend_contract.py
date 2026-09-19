from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_age_check_frontend_contract_is_consistent() -> None:
    index = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'id="age-check"' in index
    assert 'class="age-check"' in index
    assert 'document.querySelector("#age-check")' in app
    assert 'item.age_check_status === "required"' in app
    assert 'item.age_check_status === "not_required"' in app


def test_preview_is_manual_with_play_button() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert 'class="motion-preview"' in html
    assert 'class="preview-toggle"' in html
    assert 'aria-label="Play preview"' in html
    assert 'previewToggle.addEventListener("click"' in app
    assert "IntersectionObserver" not in app
    assert "pointerenter" not in app
    assert ".preview-toggle {" in css


def test_mobile_feed_is_single_column() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    mobile = css[css.index("@media (max-width: 680px)"):]
    assert "grid-template-columns: 1fr" in mobile
    assert "aspect-ratio: 16 / 9" in mobile
    assert ".quality { left:" in css
    assert ".duration { right:" in css


def test_prefetches_next_page_before_show_more() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "let prefetchedPage = null;" in app
    assert "let prefetchPromise = null;" in app
    assert "async function prepareNextPage(payload, generation)" in app
    assert "function startPrefetch(payload, generation)" in app
    load_more = app[app.index("async function loadMore()"):app.index("async function search(")]
    assert "let page = prefetchedPage;" in load_more
    assert "await prefetchPromise" in load_more
    assert "startPrefetch(payload, generation);" in load_more
    assert "requestLive(payload, generation, nextLivePage, { commit: false })" in app


def test_frontend_assets_are_v22_and_worker_forces_update() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    sw = (ROOT / "frontend" / "sw.js").read_text(encoding="utf-8")
    assert "/styles.css?v=23" in html
    assert "/app.js?v=23" in html
    assert 'register("/sw.js?v=23", { updateViaCache: "none" })' in app
    assert "controllerchange" in app
    assert 'const CACHE = "search-shell-v23";' in sw
    assert 'cache: "no-store"' in sw


def test_provider_media_bypasses_service_worker() -> None:
    sw = (ROOT / "frontend" / "sw.js").read_text(encoding="utf-8")
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "url.origin !== self.location.origin" in sw
    assert 'url.pathname.startsWith("/thumb-proxy")' in sw
    assert 'url.pathname.startsWith("/thumb/")' in sw
    assert 'referrerpolicy="no-referrer"' in html
    assert 'motion.referrerPolicy = "no-referrer"' in app



def test_card_media_is_policy_driven() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'const providerMediaPolicies = new Map();' in app
    assert 'function resolveThumbnailUrl(item)' in app
    assert 'function previewEligible(item)' in app
    assert 'const failedPreviewIds = new Set();' in app
    assert 'sessionStorage' in app
    assert 'item.provider === "thumbzilla" || item.provider === "tube8"' not in app
    assert '`/api/thumb/${encodeURIComponent(item.id)}?refresh=true&_=${Date.now()}`' in app
    assert 'preview.dataset.healAttempt' in app
    assert '4000' in app
    assert '/api/preview-proxy?provider=' in app

def test_search_submit_runs_once() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    start = app.index('form.addEventListener("submit"')
    end = app.index("for (const el of", start)
    assert app[start:end].count("search();") == 1


def test_cards_ui_v2_markup_hooks() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    for hook in (
        'search-panel',
        'filter-strip',
        'result-summary',
        'id="live-detail"',
        'media-badges',
        'card-meta-primary',
        'card-meta-secondary',
    ):
        assert hook in html
    for existing in (
        'class="thumb"', 'class="preview"', 'class="motion-preview"',
        'class="quality"', 'class="duration"', 'class="preview-toggle"',
    ):
        assert existing in html
    assert 'id="sort"' not in html


def test_cards_ui_v2_desktop_hierarchy_css() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert ".search-panel {" in css
    panel = css[css.index(".search-panel {"):css.index("}", css.index(".search-panel {")) + 1]
    assert "position: sticky" in panel
    assert "top: 58px" in panel
    assert "grid-template-columns: repeat(4, minmax(0, 1fr))" in css
    medium = css[css.index("@media (max-width: 1000px)"):css.index("@media (max-width: 820px)")]
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in medium
    intermediate = css[css.index("@media (max-width: 820px)"):css.index("@media (max-width: 680px)")]
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in intermediate
    assert ".card-meta-secondary" in css
    assert "color:" in css[css.index(".card-meta-secondary"):css.index("}", css.index(".card-meta-secondary")) + 1]
    assert "aspect-ratio: 16/9" in css or "aspect-ratio: 16 / 9" in css
    assert ".card { height:" not in css


def test_cards_ui_v2_mobile_feed_contract() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    mobile = css[css.index("@media (max-width: 680px)"):]
    assert "grid-template-columns: 1fr" in mobile
    assert ".card { width: 100%;" in mobile
    assert ".thumb {" in mobile and "width: 100%" in mobile
    assert "aspect-ratio: 16 / 9" in mobile
    assert ".filter-strip" in mobile
    assert "overflow-x: auto" in mobile
    assert "flex: 0 0 auto" in mobile
    assert "min-height: 44px" in mobile
    assert "-webkit-line-clamp: 2" in mobile
    assert "min-width: 0" in mobile
