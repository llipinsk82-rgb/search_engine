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


def test_frontend_assets_are_v20_and_worker_forces_update() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    sw = (ROOT / "frontend" / "sw.js").read_text(encoding="utf-8")
    assert "/styles.css?v=20" in html
    assert "/app.js?v=20" in html
    assert 'register("/sw.js?v=20", { updateViaCache: "none" })' in app
    assert "controllerchange" in app
    assert 'const CACHE = "search-shell-v20";' in sw
    assert 'cache: "no-store"' in sw


def test_provider_media_bypasses_service_worker() -> None:
    sw = (ROOT / "frontend" / "sw.js").read_text(encoding="utf-8")
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "url.origin !== self.location.origin" in sw
    assert 'referrerpolicy="no-referrer"' in html
    assert 'motion.referrerPolicy = "no-referrer"' in app



def test_stale_thumbzilla_and_tube8_thumbnails_self_heal() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'item.provider === "thumbzilla" || item.provider === "tube8"' in app
    assert '`/thumb/${encodeURIComponent(item.id)}?refresh=true&_=${Date.now()}`' in app
    assert 'preview.dataset.healAttempt' in app
    assert 'window.setTimeout(retry, 700)' in app

def test_search_submit_runs_once() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    start = app.index('form.addEventListener("submit"')
    end = app.index("for (const el of", start)
    assert app[start:end].count("search();") == 1
