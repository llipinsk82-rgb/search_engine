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
    assert '<option value="not_required">No age check</option>' in index
    assert 'item.age_check_status === "not_required"' not in app


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
    end = app.index("});", start) + 3
    assert app[start:end].count("search();") == 1


def test_premium_visual_contract_is_media_first_and_responsive() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    for token in ("--bg-page:", "--surface-soft:", "--text-primary:", "--text-muted:", "--radius-media:"):
        assert token in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css
    tablet = css[css.index("@media (max-width: 960px)"):css.index("@media (max-width: 680px)")]
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in tablet
    mobile = css[css.index("@media (max-width: 680px)"):]
    assert "grid-template-columns: 1fr" in mobile
    card_block = css[css.index(".card {"):css.index("}", css.index(".card {"))]
    assert "border: 1px solid" not in card_block
    assert "aspect-ratio: 16 / 9" in css


def test_hover_motion_is_fine_pointer_only() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert "@media (hover: hover) and (pointer: fine)" in css
    hover = css[css.index("@media (hover: hover) and (pointer: fine)"):]
    assert ".card:hover" in hover
    assert "transform:" in hover


def test_filter_sheet_is_desktop_drawer_and_mobile_bottom_sheet() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert ".filter-sheet-panel {" in css
    assert "width: min(420px, calc(100vw - 32px));" in css
    mobile = css[css.index("@media (max-width: 680px)"):]
    assert ".filter-sheet-panel" in mobile
    assert "width: 100%;" in mobile


def test_mobile_search_zone_is_sticky_and_touch_targets_are_large() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    mobile = css[css.index("@media (max-width: 680px)"):]
    assert ".search-shell" in mobile
    assert "position: sticky" in mobile
    assert "min-height: 44px" in css

def test_premium_mobile_has_no_horizontal_filter_strip() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    mobile = css[css.index("@media (max-width: 680px)"):]
    assert "overflow-x: auto" not in mobile
    assert 'id="filters-open"' in html
    assert 'class="secondary-filters"' not in html

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
    assert 'sortSelect.addEventListener("change", () => search());' in app
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
    assert '<input id="content-class" type="hidden" value="">' in html
    for value in ("", "amateur", "studio"):
        assert f'data-content-class="{value}"' in html
    assert 'data-content-class="unknown"' not in html
    assert '>Production</button>' in html
    assert 'const contentClassInput = document.querySelector("#content-class");' in app
    assert 'if (getContentClassValue()) params.set("content_class", getContentClassValue());' in app
    assert 'setContentClassValue(params.get("content_class") || "");' in app
    assert 'if (payload.content_class) livePayload.content_class = payload.content_class;' in app
    assert app.count('if (stateParams.has("content_class")) payload.content_class = stateParams.get("content_class");') >= 2
    assert 'setContentClassValue("");' in app

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


def test_premium_shell_has_primary_and_secondary_filter_hierarchy() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert 'class="search-shell"' in html
    assert 'class="primary-controls"' in html
    primary = html[html.index('class="primary-controls"'):html.index('</div>', html.index('class="primary-controls"'))]
    assert 'id="sort"' in primary
    assert 'class="content-segment"' in html
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


def test_mobile_filter_sheet_contract() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    for hook in (
        'id="filters-open"', 'id="filter-sheet"', 'role="dialog"',
        'aria-modal="true"', 'id="filters-close"', 'id="filters-reset"',
        'id="filters-apply"', 'class="filter-fields"',
    ):
        assert hook in html
    for fn in (
        "function openFilterSheet()",
        "function closeFilterSheet(",
        "function applyFilterSheet()",
        "function resetSecondaryFilters()",
        "function trapFilterSheetFocus(event)",
    ):
        assert fn in app
    assert 'document.body.classList.add("filter-sheet-open")' in app
    assert 'document.body.classList.remove("filter-sheet-open")' in app
    assert 'event.key === "Escape"' in app
    assert 'event.key !== "Tab"' in app
    assert "filtersOpenBtn.focus()" in app

def test_secondary_filters_wait_for_apply_on_all_viewports() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "function applyFilterSheet()" in app
    assert 'filtersApplyBtn.addEventListener("click", applyFilterSheet);' in app
    assert 'for (const el of [providerSelect, qualitySelect, durationSelect, ageCheckSelect])' in app
    assert 'el.addEventListener("change", updateFilterCount);' in app

def test_card_thumb_gets_accessible_name_from_title() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'thumb.setAttribute("aria-label", `View ${item.title}`);' in app


def test_preview_failure_is_scoped_to_its_media_frame() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'toggle.closest(".media-frame")?.classList.add("preview-failed");' in app
    assert "failedPreviewIds.add(itemId);" in app
    assert "toggle.hidden = true;" in app


def test_manual_one_active_preview_contract_is_preserved() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    start = app[app.index("function startMotionPreview("):app.index("function durationText(")]
    assert "activeMotionPreview?.motion && activeMotionPreview.motion !== motion" in start
    assert "stopMotionPreview(" in start
    assert "IntersectionObserver" not in app
    assert "pointerenter" not in app


def test_explicit_search_state_helpers_exist() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    for fn in (
        "function renderSkeletons(",
        "function clearSkeletons()",
        "function renderEmptyState(",
        "function renderErrorState(",
        "function hasActiveFilters()",
    ):
        assert fn in app
    assert 'retry.dataset.action = "retry-search";' in app
    assert 'data-action="clear-filters"' in app


def test_recoverable_live_failure_keeps_cached_results() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    refresh = app[app.index("async function refreshLive("):app.index("async function loadMore(")]
    catch_section = refresh[refresh.index("catch"): ]
    assert "resultsEl.replaceChildren()" not in catch_section
    assert "Live sources unavailable" in catch_section


def test_partial_provider_failure_is_surfaced_quietly() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "function liveFailureCount(providers)" in app
    assert "liveFailureCount(live.providers)" in app
    assert "live source" in app and "unavailable" in app


def test_load_more_null_page_clears_own_skeletons_without_touching_stale_generation() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    load_more = app[app.index("async function loadMore()"):app.index("async function search(")]
    assert "if (generation !== searchGeneration) return;" in load_more
    null_page = load_more[load_more.index("if (!page) {"):load_more.index("prefetchedPage = null;")]
    assert "clearSkeletons();" in null_page
    assert 'moreBtn.textContent = "Show more";' in null_page

def test_frontend_assets_are_v31() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    sw = (ROOT / "frontend" / "sw.js").read_text(encoding="utf-8")
    assert "/styles.css?v=31" in html
    assert "/app.js?v=31" in html
    assert 'register("/sw.js?v=31", { updateViaCache: "none" })' in app
    assert 'const CACHE = "search-shell-v31";' in sw
    assert '"/styles.css?v=31"' in sw
    assert '"/app.js?v=31"' in sw


def test_service_worker_reload_is_guarded() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'const SW_RELOAD_GUARD = "search.swReload.v31";' in app
    controller = app[app.index('navigator.serviceWorker.addEventListener("controllerchange"'):]
    assert "sessionStorage.getItem(SW_RELOAD_GUARD)" in controller
    assert "sessionStorage.setItem(SW_RELOAD_GUARD" in controller
    assert "window.location.reload();" in controller
    assert "window.setTimeout" in controller
    assert "sessionStorage.removeItem(SW_RELOAD_GUARD)" in controller


def test_filter_sheet_initial_focus_is_trapped_in_panel() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    sheet = html[html.index('id="filter-sheet"'):html.index('</div>', html.index('id="filter-sheet"'))]
    assert 'data-filter-close' in sheet
    assert 'tabindex="-1"' in sheet
    trap = app[app.index("function trapFilterSheetFocus(event)"):app.index("const providerMediaPolicies")]
    assert "document.activeElement === filterSheetPanel" in trap
    assert "!filterSheetPanel.contains(document.activeElement)" in trap

def test_premium_body_selector_applies_page_surface() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert "bwdy {" not in css
    start = css.index("body {")
    body = css[start:css.index("}", start) + 1]
    assert "margin: 0" in body
    assert "min-height: 100vh" in body
    assert "var(--bg-page)" in body


def test_on_demand_preview_resolution_is_click_driven_and_no_store() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'policy.preview_resolution_mode === "on_demand"' in app
    assert 'policy.preview_storage_mode === "ephemeral"' in app
    assert "const needsOnDemand =" in app
    assert 'async function resolvePreviewForPlayback(item)' in app
    assert "/api/preview/" in app
    assert "search.failedPreviewIds.v2" in app
    assert 'cache: "no-store"' in app
    assert 'previewToggle.addEventListener("click", async (event)' in app


def test_on_demand_preview_frontend_bumps_shell_cache() -> None:
    sw = (ROOT / "frontend" / "sw.js").read_text(encoding="utf-8")
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert 'search-shell-v31' in sw
    assert '/app.js?v=31' in sw
    assert '/styles.css?v=31' in sw
    assert 'app.js?v=31' in html
    assert 'styles.css?v=31' in html

def test_premium_polish_removes_dev_badge() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert '<span class="badge">DEV</span>' not in html


def test_premium_polish_uses_compact_live_status() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'function liveSummary(providers)' in app
    assert 'live source' in app
    assert '(item) => !item.error,' in app
    assert 'parts.push(`${item.provider} ${item.total.toLocaleString()}`)' not in app
    assert 'parts.push(`${item.provider} +${item.fetched}`)' not in app


def test_premium_polish_uses_neutral_age_copy() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'Any age check' in html
    assert 'Age check required' in html
    assert 'No age check observed' not in html
    assert 'no age check observed' not in app
    assert '? "18+"' in app


def test_premium_polish_reset_is_secondary_action() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert 'id="filters-reset" type="button" class="secondary-action"' in html
    assert '.secondary-action {' in css
    assert 'border: 1px solid var(--line-soft)' in css


def test_premium_polish_duration_copy_is_correct() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert '10–30 min' in html
    assert '10–0 min' not in html


def test_brandless_shell_uses_segmented_content_control() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "BlackServ" not in html
    assert ">BS<" not in html
    assert 'class="brand"' not in html
    assert '<input id="content-class" type="hidden" value="">' in html
    for value, label in (("", "All"), ("amateur", "Amateur"), ("studio", "Production")):
        assert f'data-content-class="{value}"' in html
        assert f'>{label}</button>' in html
    assert 'const contentClassInput = document.querySelector("#content-class");' in app
    assert 'const contentClassButtons = [...document.querySelectorAll("[data-content-class]")];' in app
    assert "function getContentClassValue()" in app
    assert "function setContentClassValue(value)" in app


def test_segmented_content_state_maps_to_existing_api_values() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'if (getContentClassValue()) params.set("content_class", getContentClassValue());' in app
    assert 'setContentClassValue(params.get("content_class") || "");' in app
    assert '["", "amateur", "studio"].includes(value)' in app
    assert 'button.setAttribute("aria-pressed", String(button.dataset.contentClass === safeValue));' in app


def test_unknown_restored_content_state_fails_closed_to_all() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'const safeValue = ["", "amateur", "studio"].includes(value) ? value : "";' in app


def test_secondary_filters_live_only_in_filter_sheet() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    shell_start = html.index('<section class="search-shell"')
    shell_end = html.index('</section>', shell_start)
    shell = html[shell_start:shell_end]
    assert 'id="provider"' not in shell
    assert 'id="quality"' not in shell
    assert 'id="duration"' not in shell
    assert 'id="age-check"' not in shell
    sheet = html[html.index('id="filter-sheet"'):]
    for hook in ('id="provider"', 'id="quality"', 'id="duration"', 'id="age-check"'):
        assert hook in sheet
    assert 'const desktopSecondaryFilters' not in app
    assert 'const mobileSecondaryFilters' not in app
    assert 'const mobileQuery' not in app


def test_filter_count_tracks_non_default_secondary_filters() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'id="filter-count"' in html
    assert "function activeSecondaryFilterCount()" in app
    assert "function updateFilterCount()" in app
    assert "[providerSelect, qualitySelect, durationSelect, ageCheckSelect]" in app
    assert 'filterCountEl.hidden = count === 0;' in app
    assert 'filterCountEl.textContent = String(count);' in app


def test_card_template_is_media_first_with_two_metadata_levels() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    template = html[html.index('<template id="card-template">'):html.index('</template>')]
    assert 'class="media-frame"' in template
    assert 'class="card-title-row"' in template
    assert 'class="card-meta-primary"' in template
    assert 'class="card-meta-tags"' in template
    assert template.index('class="media-frame"') < template.index('class="card-title-row"')
    assert template.index('class="card-title-row"') < template.index('class="card-meta-primary"')
    assert template.index('class="card-meta-primary"') < template.index('class="card-meta-tags"')


def test_optional_card_metadata_is_hidden_when_empty() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "function setOptionalText(node, value)" in app
    assert "node.hidden = !text;" in app
    for selector in (".published", ".views", ".rating", ".content-class", ".studio", ".age-check", ".alternates"):
        assert f'card.querySelector("{selector}")' in app


def test_preview_button_contract_survives_card_redesign() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'class="preview-toggle"' in html
    assert 'aria-label="Play preview"' in html
    assert 'previewToggle.addEventListener("click"' in app
    assert 'event.stopPropagation();' in app
    assert "IntersectionObserver" not in app


def test_mobile_content_segment_uses_full_width_second_row() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    mobile = css[css.index("@media (max-width: 680px)"): ]
    assert 'grid-template-areas: "sort filters" "segment segment";' in mobile
    assert '.primary-controls { display: contents; }' in mobile
    assert '#sort { grid-area: sort;' in mobile
    assert '.content-segment {' in mobile
    assert 'grid-area: segment;' in mobile
    assert '.filters-open {' in mobile
    assert 'grid-area: filters;' in mobile
    assert 'white-space: nowrap;' in mobile


def test_result_navigation_saves_and_restores_browse_position() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'const RETURN_POSITION_KEY = "search.returnPosition.v1";' in app
    assert 'function saveBrowsePosition(itemId)' in app
    assert 'function readBrowsePosition()' in app
    assert 'async function restoreBrowsePosition()' in app
    assert 'loadedCount: nextOffset' in app
    assert 'scrollY: window.scrollY' in app
    assert 'card.dataset.itemId = item.id;' in app
    assert 'const outbound = event.target.closest("a.thumb, a.title");' in app
    assert 'saveBrowsePosition(outbound.closest(".card")?.dataset.itemId || "");' in app
    assert 'await restoreBrowsePosition();' in app
    assert 'window.scrollTo({ top: saved.scrollY, left: 0, behavior: "auto" });' in app


def test_scroll_restore_reloads_previous_depth_before_scrolling() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    restore = app[app.index("async function restoreBrowsePosition()"):app.index("async function boot()") ]
    assert 'while (nextOffset < saved.loadedCount && (localHasMore || liveHasMore))' in restore
    assert 'await loadMore();' in restore
    assert 'document.querySelector(`[data-item-id="${CSS.escape(saved.itemId)}"]`)' in restore
    assert 'target.scrollIntoView({ block: "center", behavior: "auto" });' in restore


def test_instant_back_restore_uses_session_snapshot_before_network() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'const RETURN_SNAPSHOT_LIMIT = 120;' in app
    assert 'let renderedItems = [];' in app
    assert 'items: renderedItems.slice(0, RETURN_SNAPSHOT_LIMIT)' in app
    assert 'function restoreBrowseSnapshot(saved)' in app
    boot = app[app.index("async function boot()"):app.index('if ("scrollRestoration" in window.history)')]
    assert 'const saved = readBrowsePosition();' in boot
    assert 'const snapshotRestored = restoreBrowseSnapshot(saved);' in boot
    assert boot.index('const snapshotRestored = restoreBrowseSnapshot(saved);') < boot.index('await loadProviders();')


def test_snapshot_restore_renders_without_search_skeleton() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    restore = app[app.index("function restoreBrowseSnapshot(saved)"):app.index("async function refreshBrowseSnapshotInBackground(saved)")]
    assert 'render(saved.items);' in restore
    assert 'renderSkeletons' not in restore
    assert 'fetchLocal' not in restore
    assert 'window.requestAnimationFrame' in restore
    assert 'sessionStorage.removeItem(RETURN_POSITION_KEY)' in restore


def test_snapshot_background_refresh_is_silent_and_depth_bounded() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    refresh = app[app.index("async function refreshBrowseSnapshotInBackground(saved)"):app.index("async function restoreBrowsePosition()") ]
    assert 'const refreshLimit = Math.min(Math.max(saved.items.length, PAGE_SIZE), RETURN_SNAPSHOT_LIMIT);' in refresh
    assert 'await fetchLocal(payload, { limit: refreshLimit })' in refresh
    assert 'renderSkeletons' not in refresh
    assert 'setPrimaryStatus("Searching…")' not in refresh


def test_premium_polish_v2_removes_technical_card_copy() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'card.querySelector(".source").textContent = item.provider;' in app
    assert '`✓ ${item.provider}`' not in app
    assert 'item.age_check_status === "required" ? "18+" : ""' in app
    assert '"18+ gate"' not in app


def test_premium_polish_v2_uses_quieter_search_and_card_typography() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert "--action-soft:" in css
    assert ".searchbox button {" in css
    search_button = css[css.rindex(".searchbox button {"):css.index("}", css.rindex(".searchbox button {")) + 1]
    assert "background: var(--action-soft);" in search_button
    assert "color: var(--text-primary);" in search_button
    title = css[css.rindex(".title {"):css.index("}", css.rindex(".title {")) + 1]
    assert "font-weight: 650;" in title
    assert "line-height: 1.38;" in title


def test_premium_polish_v2_compacts_status_and_card_rhythm() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert ".statusbar {" in css
    status = css[css.rindex(".statusbar {"):css.index("}", css.rindex(".statusbar {")) + 1]
    assert "min-height: 40px;" in status
    assert "padding: 0 2px 10px;" in status
    copy = css[css.rindex(".card-copy {"):css.index("}", css.rindex(".card-copy {")) + 1]
    assert "padding: 9px 2px 0;" in copy
    assert "gap: 5px;" in copy


def test_premium_polish_v2_uses_subtle_media_controls() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    preview = css[css.rindex(".preview-toggle {"):css.index("}", css.rindex(".preview-toggle {")) + 1]
    assert "background: rgba(8,9,11,.52);" in preview
    assert "box-shadow: 0 6px 18px rgba(0,0,0,.18);" in preview
    badge = css[css.rindex(".duration,"):css.index("}", css.rindex(".duration,")) + 1]
    assert "background: rgba(6,7,9,.62);" in badge
