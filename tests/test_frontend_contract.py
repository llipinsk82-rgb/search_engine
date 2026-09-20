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


def test_frontend_assets_are_v26_and_worker_forces_update() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    sw = (ROOT / "frontend" / "sw.js").read_text(encoding="utf-8")
    assert "/styles.css?v=26" in html
    assert "/app.js?v=26" in html
    assert 'register("/sw.js?v=26", { updateViaCache: "none" })' in app
    assert "controllerchange" in app
    assert 'const CACHE = "search-shell-v26";' in sw
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


def test_premium_css_uses_tokens_and_three_two_one_grid() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    for token in (
        "--bg-page:", "--bg-surface:", "--bg-elevated:", "--border-subtle:",
        "--text-primary:", "--text-secondary:", "--text-muted:", "--focus-ring:",
        "--radius-card:", "--space-2:", "--space-4:",
    ):
        assert token in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css
    tablet = css[css.index("@media (max-width: 960px)"):css.index("@media (max-width: 680px)")]
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in tablet
    mobile = css[css.index("@media (max-width: 680px)"):]
    assert "grid-template-columns: 1fr" in mobile
    assert "aspect-ratio: 16 / 9" in css or "aspect-ratio: 16/9" in css


def test_premium_mobile_has_no_horizontal_filter_strip() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    mobile = css[css.index("@media (max-width: 680px)"):]
    assert "overflow-x: auto" not in mobile
    assert ".filters-open" in mobile
    assert ".secondary-filters" in mobile
    assert "display: none" in mobile[mobile.index(".secondary-filters"):]


def test_keyboard_focus_is_explicit() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert ":focus-visible" in css
    assert "var(--focus-ring)" in css


def test_cards_ui_v2_separates_primary_and_live_status() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'const liveDetailEl = document.querySelector("#live-detail");' in app
    assert 'function setPrimaryStatus(text)' in app
    assert 'function setLiveDetail(text)' in app
    assert 'liveDetailEl.textContent = text || "";' in app
    assert 'statusEl.textContent = liveStatusText' not in app
    assert 'cached matches · live:' not in app


def test_sort_selector_state_and_payload_contract() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    expected_values = ["relevance", "newest", "views", "rating", "longest", "shortest"]
    sort_start = html.index('id="sort"')
    sort_end = html.index('</select>', sort_start)
    sort_html = html[sort_start:sort_end]
    for value in expected_values:
        assert f'value="{value}"' in sort_html
    assert 'const sortSelect = document.querySelector("#sort");' in app
    assert 'if (sortSelect.value !== "relevance") params.set("sort", sortSelect.value);' in app
    assert 'const sort = params.get("sort") || "relevance";' in app
    assert 'if (payload.sort) livePayload.sort = payload.sort;' in app
    assert app.count('if (stateParams.has("sort")) payload.sort = stateParams.get("sort");') >= 2
    assert '[sortSelect, contentClassSelect, providerSelect, qualitySelect, durationSelect, ageCheckSelect]' in app
    assert 'sortSelect.value = "relevance";' in app


def test_optional_sort_metadata_is_rendered_without_fake_placeholders() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    for hook in ('class="published"', 'class="views"', 'class="rating"'):
        assert hook in html
    assert 'function publishedText(value)' in app
    assert 'function viewsText(value)' in app
    assert 'function ratingText(percent, count)' in app
    assert 'item.published_at' in app
    assert 'item.views' in app
    assert 'item.rating_percent' in app
    assert 'item.rating_count' in app
    assert '0 views' not in app


def test_non_relevance_visible_pool_is_not_round_robin_blended() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'function sortVisibleItems(items, sort)' in app
    assert 'function mergeLiveAndLocal(liveItems, localItems, sort, limit = PAGE_SIZE)' in app
    assert 'if (sort === "relevance") return blendLiveAndLocal(liveItems, localItems, limit);' in app
    assert app.count('mergeLiveAndLocal(') >= 3


def test_content_class_filter_state_and_payload_contract() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    start = html.index('id="content-class"')
    end = html.index('</select>', start)
    selector = html[start:end]
    for value in ("", "amateur", "studio", "unknown"):
        assert f'value="{value}"' in selector
    assert 'const contentClassSelect = document.querySelector("#content-class");' in app
    assert 'if (contentClassSelect.value) params.set("content_class", contentClassSelect.value);' in app
    assert 'const contentClass = params.get("content_class") || "";' in app
    assert 'if (payload.content_class) livePayload.content_class = payload.content_class;' in app
    assert app.count('if (stateParams.has("content_class")) payload.content_class = stateParams.get("content_class");') >= 2
    assert 'contentClassSelect.value = "";' in app


def test_content_class_metadata_is_minimal_and_never_title_inferred() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'class="content-class"' in html
    assert 'class="studio"' in html
    assert 'item.content_class === "amateur" ? "Amateur" : ""' in app
    assert 'item.studio || ""' in app
    assert 'Unknown' not in app
    assert 'item.title.toLowerCase' not in app
    assert 'item.title.includes' not in app


def test_frontend_assets_are_v26_after_content_class_filter() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    sw = (ROOT / "frontend" / "sw.js").read_text(encoding="utf-8")
    assert "/styles.css?v=26" in html
    assert "/app.js?v=26" in html
    assert 'register("/sw.js?v=26", { updateViaCache: "none" })' in app
    assert 'const CACHE = "search-shell-v26";' in sw
    assert '"/styles.css?v=26"' in sw and '"/app.js?v=26"' in sw
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css


def test_premium_shell_has_primary_and_secondary_filter_hierarchy() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert 'class="search-shell"' in html
    assert 'class="primary-controls"' in html
    assert 'class="secondary-filters"' in html
    primary = html[html.index('class="primary-controls"'):html.index('</div>', html.index('class="primary-controls"'))]
    assert 'id="sort"' in primary
    assert 'id="content-class"' in primary
    assert 'id="provider"' not in primary
    assert 'id="quality"' not in primary
    assert 'id="duration"' not in primary


def test_results_grid_is_not_live_region_and_status_is() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    results_start = html.index('id="results"')
    results_tag = html[results_start:html.index('>', results_start) + 1]
    assert "aria-live" not in results_tag
    status_start = html.index('id="status"')
    status_tag = html[status_start:html.index('>', status_start) + 1]
    assert 'role="status"' in status_tag
    assert 'aria-live="polite"' in status_tag
    assert 'aria-atomic="true"' in status_tag


def test_preview_button_is_not_nested_inside_media_link() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    template = html[html.index('<template id="card-template">'):html.index('</template>')]
    media = template[template.index('class="media-frame"'):]
    thumb_start = media.index('class="thumb"')
    thumb_end = media.index('</a>', thumb_start)
    assert 'class="preview-toggle"' not in media[thumb_start:thumb_end]
    assert media.index('class="preview-toggle"') > thumb_end
