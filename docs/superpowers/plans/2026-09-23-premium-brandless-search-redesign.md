# Premium Brandless Search Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing generic/admin-like Search frontend with a brandless, premium, media-first UI while preserving all current search, filter, preview, pagination, accessibility, provider, and backend behavior.

**Architecture:** Keep the existing vanilla HTML/CSS/JavaScript frontend and backend contracts. Redesign the public shell, filtering UX, card hierarchy, and responsive styling in-place, using small JavaScript helpers only where the new segmented content control, unified filter sheet, active-filter count, and optional metadata rendering require them. Develop in an isolated worktree, publish the branch frontend only to `test.blackserv.eu`, preserve the existing Preview Lab under `/test/`, and gate all production rollout on owner visual acceptance.

**Tech Stack:** HTML5, CSS3, vanilla JavaScript, pytest frontend contract tests, FastAPI backend unchanged, Nginx test staging, existing service worker/PWA assets.

**Spec:** `docs/superpowers/specs/2026-09-23-premium-brandless-search-redesign-design.md`

## Global Constraints

- Do not add BlackServ or BS branding.
- Do not invent a new consumer product name or decorative logo.
- Keep the UI dark, cinematic, calm, image-led, minimal, and practical.
- Do not add a JavaScript framework or new frontend dependency.
- Do not change backend APIs, provider adapters, preview resolver rules, preview promotion policy, classification semantics, search ranking, database schema, or provider coverage.
- Preserve one-tap/click manual preview; no autoplay feed.
- Preserve three-column desktop, two-column intermediate, one-column mobile result layout.
- Preserve keyboard submission, URL/hash state restoration, Show more/prefetch, preview error handling, and filter accessibility.
- Secondary filters are unified behind one `Filters` sheet on desktop and mobile.
- `Amateur` / `Production` semantics remain unchanged: `amateur` and `studio` API values respectively; `Production` continues to mean non-amateur in current backend semantics.
- Unknown remains an internal evidence state and is not exposed as a public content filter.
- Production SEARCH must remain unchanged until rendered `test.blackserv.eu` receives owner visual approval.
- Use only the official production deploy helper after approval.
- Bump all frontend/service-worker cache versions together during the accepted production release.
- Do not delete preserved git stashes or the existing Preview Lab assets.

## Review Focus

1. **Restored malformed/legacy content-class state** — an unknown hash value must fall back to `All`, while `amateur` and `studio` restore both the hidden state input and the visible segmented buttons consistently.
2. **Secondary-filter staged state** — provider/quality/duration/age-check changes must update the visible active-filter count but must not trigger search until `Apply filters`; Reset must clear all four values and the count.
3. **Sparse card metadata** — missing views/rating/published/studio/age/alternate metadata must disappear cleanly without empty separators, blank pills, or layout gaps.
4. **Preview edge cases** — cards without eligible preview show no Play control; eligible preview remains one click/tap; playback failure still hides/suppresses the broken preview for the session without breaking the card.
5. **Cache/staging isolation** — the test domain must not install a root service worker that can interfere with the preserved Preview Lab, and the production release must move `index.html`, `app.js`, and `sw.js` to the same cache version.

---

## Execution Prerequisite

Before Task 1, invoke `superpowers:using-git-worktrees` and create an isolated worktree at:

- branch: `feature/premium-brandless-redesign`
- path: `/opt/bs-sandbox/search_engine-worktrees/premium-brandless-redesign`
- base: the canonical `feature/provider-registry-probe` commit that contains this spec and plan

Verify the new worktree is clean and points at the intended base. Do not implement redesign code in `/opt/bs-sandbox/search_engine` directly. Preserve existing worktrees and stashes.

## File Map

### Public frontend
- `frontend/index.html` — public shell markup, search control, segmented content control, filter sheet markup, status area, result-card template, and static asset version references.
- `frontend/styles.css` — visual tokens, search hierarchy, segmented control, filter drawer/bottom sheet, media-first cards, responsive grid, state panels, skeletons, hover/touch behavior, and accessibility styling.
- `frontend/app.js` — existing search/data behavior plus small UI adapters for segmented content state, filter count, unified filter sheet, optional metadata visibility, and unchanged preview interactions.
- `frontend/sw.js` — only changes during the final accepted production release to bump the service-worker cache version.

### Tests
- `tests/test_frontend_contract.py` — DOM/CSS/JS contract tests for the redesigned shell, segmented content state, filter count, card hierarchy, responsive layout, manual preview, accessibility, and cache version synchronization.

### Documentation
- `docs/SEARCH_ENGINE_HANDOFF.md` — records test-environment visual acceptance and final production rollout result after the user approves the rendered redesign.

### Test environment outside git
- `/opt/search-engine-premium-test/` — static copy of the branch frontend used only by `test.blackserv.eu`.
- `/opt/search-engine-preview-lab/` — existing Preview Lab; preserve it unchanged and continue serving it through `/test/`.
- `/etc/nginx/sites-available/search-preview-lab` — test-domain-only Nginx vhost. During visual review it serves the premium frontend at `/`, proxies `/api/` to `127.0.0.1:8775`, preserves Preview Lab `/test/` + `/test-api/`, and intentionally returns 404 for `/sw.js`.

### Task 1: Brandless primary shell and segmented content control

**Files:**
- Modify: `frontend/index.html:12-136`
- Modify: `frontend/app.js:1-25, 301-360, 865-925`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: existing `#search-form`, `#q`, `#sort`, provider/quality/duration/age controls, hash-state persistence, and `search()`.
- Produces:
  - hidden state input `#content-class` with values `"" | "amateur" | "studio"`;
  - visible buttons `[data-content-class]`;
  - `getContentClassValue() -> string`;
  - `setContentClassValue(value: string) -> void`;
  - direct segmented-control click behavior that calls existing `search()` exactly once.

- [ ] **Step 1: Add failing shell/segmented-control contract tests**

Append these tests to `tests/test_frontend_contract.py`. In the same RED step, rewrite the existing `test_content_class_filter_state_and_payload_contract`, `test_sort_selector_state_and_payload_contract`, and `test_premium_shell_has_primary_and_secondary_filter_hierarchy` so they no longer require `contentClassSelect`, `<select id="content-class">`, `[sortSelect, contentClassSelect]`, or a visible secondary-filter row. Preserve their API-value and sort-payload assertions.

Use the following new tests:

```python
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
```

- [ ] **Step 2: Run the targeted tests and verify RED**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  tests/test_frontend_contract.py::test_brandless_shell_uses_segmented_content_control \
  tests/test_frontend_contract.py::test_segmented_content_state_maps_to_existing_api_values \
  tests/test_frontend_contract.py::test_unknown_restored_content_state_fails_closed_to_all
```

Expected: FAIL because the current UI still contains `.brand`, the content control is a `<select>`, and the helper functions do not exist.

- [ ] **Step 3: Replace the top chrome and content select markup**

In `frontend/index.html` remove the current `<header class="topbar">...</header>`, keep `<main class="shell">` as the first visible product container, and replace the content-class `<select>` with:

```html
<input id="content-class" type="hidden" value="">
<div class="content-segment" role="group" aria-label="Content type">
  <button type="button" class="content-segment-option is-active"
          data-content-class="" aria-pressed="true">All</button>
  <button type="button" class="content-segment-option"
          data-content-class="amateur" aria-pressed="false">Amateur</button>
  <button type="button" class="content-segment-option"
          data-content-class="studio" aria-pressed="false">Production</button>
</div>
```

Keep `#sort` in the primary control row. Do not add any BlackServ/BS text.

- [ ] **Step 4: Add the segmented-control state helpers**

At the top of `frontend/app.js`, replace the old `contentClassSelect` binding with:

```js
const contentClassInput = document.querySelector("#content-class");
const contentClassButtons = [...document.querySelectorAll("[data-content-class]")];
```

Add before `buildSearchParams()`:

```js
function getContentClassValue() {
  return contentClassInput.value;
}

function setContentClassValue(value) {
  const safeValue = ["", "amateur", "studio"].includes(value) ? value : "";
  contentClassInput.value = safeValue;
  for (const button of contentClassButtons) {
    const active = button.dataset.contentClass === safeValue;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  }
}
```

Change search-param creation to:

```js
if (getContentClassValue()) params.set("content_class", getContentClassValue());
```

Change state restore to:

```js
setContentClassValue(params.get("content_class") || "");
```

Replace every reset/clear assignment to the old select with `setContentClassValue("");`.

Replace the old `[sortSelect, contentClassSelect]` listener with:

```js
sortSelect.addEventListener("change", () => search());
for (const button of contentClassButtons) {
  button.addEventListener("click", () => {
    setContentClassValue(button.dataset.contentClass || "");
    search();
  });
}
```

Do not change payload values `amateur` or `studio`.

- [ ] **Step 5: Run targeted and existing state tests**

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  tests/test_frontend_contract.py::test_brandless_shell_uses_segmented_content_control \
  tests/test_frontend_contract.py::test_segmented_content_state_maps_to_existing_api_values \
  tests/test_frontend_contract.py::test_unknown_restored_content_state_fails_closed_to_all \
  tests/test_frontend_contract.py::test_search_submit_runs_once \
  tests/test_content_class_filter.py
```

Expected: all PASS. Also run `tests/test_frontend_contract.py::test_sort_selector_state_and_payload_contract`, `tests/test_frontend_contract.py::test_content_class_filter_state_and_payload_contract`, and `tests/test_frontend_contract.py::test_premium_shell_has_primary_and_secondary_filter_hierarchy`; all must PASS with the new segmented-control contract.

- [ ] **Step 6: Commit Task 1**

```bash
git add frontend/index.html frontend/app.js tests/test_frontend_contract.py
git commit -m "feat: redesign primary search controls"
```

### Task 2: Unified filter sheet and active-filter count

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js:15-110, 890-910`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: existing provider/quality/duration/age controls and existing filter-sheet focus trap.
- Produces:
  - one always-visible `#filters-open` action on desktop/mobile;
  - secondary controls living permanently inside `#filter-sheet`;
  - `activeSecondaryFilterCount() -> number`;
  - `updateFilterCount() -> void`;
  - `#filter-count` badge;
  - staged secondary-filter changes applied only by `Apply filters`.

- [ ] **Step 1: Add failing unified-filter tests**

Before adding the new tests, replace the old `test_mobile_secondary_changes_wait_for_apply` with the all-viewport staged-apply contract below. Update `test_mobile_filter_sheet_contract` to require `class="filter-fields"` instead of `id="mobile-secondary-filters"`. Update `test_premium_mobile_has_no_horizontal_filter_strip` so it verifies there is no horizontal filter strip and that `#filters-open` remains available, without requiring `.secondary-filters` markup.

```python
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


def test_secondary_filters_wait_for_apply_on_all_viewports() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "function applyFilterSheet()" in app
    assert 'filtersApplyBtn.addEventListener("click", applyFilterSheet);' in app
    assert 'for (const el of [providerSelect, qualitySelect, durationSelect, ageCheckSelect])' in app
    assert 'el.addEventListener("change", updateFilterCount);' in app
```

- [ ] **Step 2: Run the targeted tests and verify RED**

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  tests/test_frontend_contract.py::test_secondary_filters_live_only_in_filter_sheet \
  tests/test_frontend_contract.py::test_filter_count_tracks_non_default_secondary_filters \
  tests/test_frontend_contract.py::test_secondary_filters_wait_for_apply_on_all_viewports
```

Expected: FAIL because secondary filters currently live in the main shell and are moved only on mobile.

- [ ] **Step 3: Move secondary filters permanently into the filter sheet**

Remove `.secondary-filters` from the search shell. Inside `.filter-sheet-panel`, replace `#mobile-secondary-filters` with:

```html
<div class="filter-fields">
  <label><span>Source</span><select id="provider" aria-label="Provider"><option value="">All sources</option></select></label>
  <label><span>Quality</span><select id="quality" aria-label="Quality"><option value="">Any quality</option><option>360p</option><option>480p</option><option>720p</option><option>1080p</option><option>HD</option><option>4K</option></select></label>
  <label><span>Duration</span><select id="duration" aria-label="Duration"><option value="">Any length</option><option value="0:600">Under 10 min</option><option value="600:1800">10–30 min</option><option value="1800:">30+ min</option></select></label>
  <label><span>Age check</span><select id="age-check" aria-label="Age check"><option value="">Any age check</option><option value="required">Age check required</option><option value="not_required">No age check</option><option value="unknown">Unknown</option></select></label>
</div>
```

Change the Filters button to:

```html
<button id="filters-open" class="filters-open" type="button" aria-controls="filter-sheet" aria-expanded="false">
  <span>Filters</span>
  <span id="filter-count" class="filter-count" hidden>0</span>
</button>
```

- [ ] **Step 4: Simplify filter-sheet JavaScript and add filter count**

Delete `desktopSecondaryFilters`, `mobileSecondaryFilters`, `mobileQuery`, DOM move logic, `secondaryFilterChanged()`, and the `mobileQuery` change listener.

Add:

```js
const filterCountEl = document.querySelector("#filter-count");

function activeSecondaryFilterCount() {
  return [providerSelect, qualitySelect, durationSelect, ageCheckSelect]
    .filter((control) => Boolean(control.value))
    .length;
}

function updateFilterCount() {
  const count = activeSecondaryFilterCount();
  filterCountEl.hidden = count === 0;
  filterCountEl.textContent = String(count);
}

function applyFilterSheet() {
  updateFilterCount();
  closeFilterSheet();
  search();
}
```

Call `updateFilterCount();` after state restoration and at the end of `resetSecondaryFilters()`.

Use:

```js
for (const el of [providerSelect, qualitySelect, durationSelect, ageCheckSelect]) {
  el.addEventListener("change", updateFilterCount);
}
filtersApplyBtn.addEventListener("click", applyFilterSheet);
```

Keep focus trap, Escape handling, `aria-expanded`, focus return, and body scroll lock.

- [ ] **Step 5: Run filter/accessibility tests**

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  tests/test_frontend_contract.py::test_secondary_filters_live_only_in_filter_sheet \
  tests/test_frontend_contract.py::test_filter_count_tracks_non_default_secondary_filters \
  tests/test_frontend_contract.py::test_secondary_filters_wait_for_apply_on_all_viewports \
  tests/test_frontend_contract.py::test_mobile_filter_sheet_contract \
  tests/test_frontend_contract.py::test_keyboard_focus_is_explicit
```

Expected: all PASS. Also run the updated `test_premium_mobile_has_no_horizontal_filter_strip`; it must PASS without any `.secondary-filters` dependency.

- [ ] **Step 6: Commit Task 2**

```bash
git add frontend/index.html frontend/app.js tests/test_frontend_contract.py
git commit -m "feat: unify premium filter sheet"
```

### Task 3: Media-first card hierarchy and sparse-metadata handling

**Files:**
- Modify: `frontend/index.html` card template
- Modify: `frontend/app.js:362-455`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: existing card item fields and existing preview eligibility/resolver behavior.
- Produces `.card-title-row`, `.card-meta-primary`, `.card-meta-tags`, and `setOptionalText(node, value)`.

- [ ] **Step 1: Add failing card hierarchy tests**

```python
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
```

- [ ] **Step 2: Run targeted tests and verify RED**

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  tests/test_frontend_contract.py::test_card_template_is_media_first_with_two_metadata_levels \
  tests/test_frontend_contract.py::test_optional_card_metadata_is_hidden_when_empty \
  tests/test_frontend_contract.py::test_preview_button_contract_survives_card_redesign
```

Expected: FAIL for the new hierarchy and helper; preview contract remains present.

- [ ] **Step 3: Replace only the metadata portion of the card template**

Keep the existing media elements/selectors unchanged. Replace the metadata block with:

```html
<div class="card-copy">
  <div class="card-title-row"><a class="title"></a></div>
  <div class="card-meta-primary"><span class="source"></span><span class="views"></span><span class="rating"></span><span class="published"></span></div>
  <div class="card-meta-tags"><span class="content-class"></span><span class="studio"></span><span class="age-check"></span><span class="alternates"></span></div>
</div>
```

Do not alter `.quality`, `.duration`, `.preview`, `.motion-preview`, `.placeholder`, or `.preview-toggle` selectors.

- [ ] **Step 4: Add optional-metadata rendering helper**

Before `resultCard(item)` add:

```js
function setOptionalText(node, value) {
  const text = String(value || "").trim();
  node.textContent = text;
  node.hidden = !text;
}
```

Keep provider visible and render optional metadata with `setOptionalText(...)`; preserve existing formatter functions. Keep the age badge only for `required`. Keep alternate count wording unchanged.

- [ ] **Step 5: Run card/preview regression tests**

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  tests/test_frontend_contract.py::test_card_template_is_media_first_with_two_metadata_levels \
  tests/test_frontend_contract.py::test_optional_card_metadata_is_hidden_when_empty \
  tests/test_frontend_contract.py::test_preview_button_contract_survives_card_redesign \
  tests/test_frontend_contract.py::test_preview_is_manual_with_play_button \
  tests/test_frontend_contract.py::test_card_media_is_policy_driven \
  tests/test_frontend_contract.py::test_preview_button_is_not_nested_inside_media_link
```

Expected: all PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add frontend/index.html frontend/app.js tests/test_frontend_contract.py
git commit -m "feat: make result cards media first"
```

### Task 4: Premium visual system, responsive behavior, and state styling

**Files:**
- Modify: `frontend/styles.css`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: Tasks 1-3 markup/classes.
- Produces: premium visual tokens, 3/2/1 result grid, desktop side-sheet/mobile bottom-sheet, sticky mobile search, image-first cards, fine-pointer-only hover, 44px minimum preview/filter hit targets, redesigned skeleton/empty/error states.

- [ ] **Step 1: Add failing visual-contract tests**

Replace the existing `test_premium_css_uses_tokens_and_three_two_one_grid` with the new token/layout contract below. Update `test_premium_polish_reset_is_secondary_action` to assert `border: 1px solid var(--line-soft)` instead of the retired `--border-subtle` token. Keep `test_mobile_feed_is_single_column`, `test_keyboard_focus_is_explicit`, `test_premium_body_selector_applies_page_surface`, and reduced-motion/state tests intact.

```python
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
```

- [ ] **Step 2: Run the targeted CSS tests and verify RED**

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  tests/test_frontend_contract.py::test_premium_visual_contract_is_media_first_and_responsive \
  tests/test_frontend_contract.py::test_hover_motion_is_fine_pointer_only \
  tests/test_frontend_contract.py::test_filter_sheet_is_desktop_drawer_and_mobile_bottom_sheet \
  tests/test_frontend_contract.py::test_mobile_search_zone_is_sticky_and_touch_targets_are_large
```

Expected: FAIL because the current stylesheet still uses the old heavy card border, topbar/admin control hierarchy, and mobile-only filter-sheet assumptions.

- [ ] **Step 3: Replace the visual token layer**

Use this base token family:

```css
:root {
  color-scheme: dark;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --bg-page: #08090b;
  --surface-soft: #101216;
  --surface-raised: #15181d;
  --surface-control: #171a20;
  --line-soft: rgba(255,255,255,.08);
  --line-strong: rgba(255,255,255,.15);
  --text-primary: #f5f7fa;
  --text-secondary: #b7bec8;
  --text-muted: #7f8792;
  --focus-ring: #dfe5ec;
  --radius-control: 14px;
  --radius-media: 16px;
  --radius-sheet: 22px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;
  background: var(--bg-page);
  color: var(--text-primary);
}
```

Keep system fonts; do not add a CDN font.

- [ ] **Step 4: Restyle the shell and search hierarchy**

Implement no visible topbar, generous desktop spacing, dominant search, compact primary controls, and no permanent secondary-filter row. Use a search shell equivalent to:

```css
.search-shell { display:grid; gap:14px; padding:28px 0 20px; }
.searchbox { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:8px; padding:6px; border:1px solid var(--line-soft); border-radius:18px; background:rgba(18,20,24,.92); box-shadow:0 18px 60px rgba(0,0,0,.18); }
.searchbox input { min-height:56px; border:0; background:transparent; padding:0 14px; font-size:clamp(17px,1.5vw,20px); }
.searchbox button { min-height:48px; border-radius:13px; padding:0 20px; }
```

- [ ] **Step 5: Style segmented content control and filter count**

Use pill-group styling with active state and a compact circular count badge. Keep every interactive control at least 40px high and Preview/Filters effective hit area at least 44px.

- [ ] **Step 6: Style media-first cards**

Required:
- `.card` has no heavy full-card 1px border;
- `.media-frame` is 16:9 with `var(--radius-media)` and restrained shadow;
- `.card-copy` uses spacing instead of a box border;
- `.title` clamps to two lines;
- `.card-meta-primary` and `.card-meta-tags` are distinct levels;
- hidden metadata nodes remain `display:none`;
- `.preview-toggle` is at least 44×44.

- [ ] **Step 7: Put hover effects behind fine-pointer media query only**

Use:

```css
@media (hover: hover) and (pointer: fine) {
  .media-frame img,
  .media-frame video { transition: transform .22s ease, filter .22s ease; }
  .card:hover .media-frame img,
  .card:hover .media-frame video { transform: scale(1.018); }
  .card:hover { transform: translateY(-2px); }
}
```

Do not add hover autoplay.

- [ ] **Step 8: Make the filter sheet a right drawer on desktop and bottom sheet on mobile**

Desktop baseline:

```css
.filter-sheet-panel {
  position:absolute;
  top:16px;
  right:16px;
  bottom:16px;
  width:min(420px, calc(100vw - 32px));
  overflow:auto;
  border:1px solid var(--line-soft);
  border-radius:var(--radius-sheet);
  background:rgba(18,20,24,.98);
  box-shadow:0 24px 80px rgba(0,0,0,.42);
}
```

Mobile override:

```css
@media (max-width: 680px) {
  .filter-sheet-panel { top:auto; right:0; bottom:0; left:0; width:100%; max-height:min(84vh,720px); border-radius:22px 22px 0 0; }
}
```

Keep backdrop, focus-visible, scroll lock, and reduced-motion handling.

- [ ] **Step 9: Preserve 3/2/1 grid and make mobile search sticky**

Use three columns desktop, two under 960px, one under 680px. Inside mobile:

```css
.search-shell { position:sticky; top:0; z-index:12; margin:0 -14px; padding:10px 14px 12px; background:rgba(8,9,11,.92); backdrop-filter:blur(18px); }
.grid { grid-template-columns:1fr; gap:26px; }
```

- [ ] **Step 10: Restyle skeleton, empty/error states, and Show more**

Keep existing JS state contracts. Match skeleton media to 16:9/radius, remove admin-like boxed treatment, preserve retry button keyboard accessibility, and keep Show more visually secondary to Search.

- [ ] **Step 11: Run the full frontend contract suite**

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_frontend_contract.py
node --check frontend/app.js
git diff --check
```

Expected: all frontend tests PASS; JS syntax PASS; diff check PASS.

- [ ] **Step 12: Commit Task 4**

```bash
git add frontend/styles.css tests/test_frontend_contract.py
git commit -m "feat: apply premium media first visual system"
```

### Task 5: Publish branch frontend to isolated `test.blackserv.eu` and obtain visual acceptance

**Files:**
- No production repository code changes required for staging.
- Modify test host only: `/etc/nginx/sites-available/search-preview-lab`, `/opt/search-engine-premium-test/`.
- Preserve `/opt/search-engine-preview-lab/`.
- After owner acceptance, modify `docs/SEARCH_ENGINE_HANDOFF.md`.

**Interfaces:**
- Consumes completed redesign branch frontend files and backend `127.0.0.1:8775`.
- Produces premium redesign at `https://test.blackserv.eu/`, backend API at `/api/`, preserved Preview Lab at `/test/index.html`, no root service worker on test domain, and owner PASS/CHANGES evidence.

- [ ] **Step 1: Verify branch release gate before staging**

```bash
PYTHONPATH=. .venv/bin/pytest -q
python -m compileall backend
node --check frontend/app.js
git diff --check
git status --short --branch
```

Expected: 0 failures, compileall PASS, JS syntax PASS, diff check PASS, clean worktree.

- [ ] **Step 2: Back up the current test-domain Nginx vhost**

```bash
sudo cp -a /etc/nginx/sites-available/search-preview-lab /etc/nginx/sites-available/search-preview-lab.bak-premium-$(date +%Y%m%dT%H%M%S)
```

- [ ] **Step 3: Stage branch frontend into a dedicated test directory**

```bash
sudo install -d -o root -g root -m 0755 /opt/search-engine-premium-test
sudo rsync -a --delete /opt/bs-sandbox/search_engine-worktrees/premium-brandless-redesign/frontend/ /opt/search-engine-premium-test/
```

- [ ] **Step 4: Point the test vhost at the premium frontend while preserving Preview Lab**

Use this test-only contract:

```nginx
server {
    listen 80;
    server_name test.blackserv.eu;
    root /opt/search-engine-premium-test;
    index index.html;
    access_log off;

    location ^~ /api/ {
        proxy_pass http://127.0.0.1:8775;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_read_timeout 30s;
    }

    location = /sw.js { return 404; }

    location ^~ /test-api/ {
        rewrite ^/test-api/(.*)$ /api/$1 break;
        proxy_pass http://127.0.0.1:8775;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_read_timeout 30s;
    }

    location ^~ /test/ {
        alias /opt/search-engine-preview-lab/;
        add_header Cache-Control "no-store";
    }

    location = /preview-lab { return 302 /test/index.html; }

    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-store";
    }

    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy no-referrer always;
    add_header X-Frame-Options SAMEORIGIN always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' https: data:; media-src 'self' https:; object-src 'none'; base-uri 'none'; frame-ancestors 'self'" always;
}
```

CT104 edge proxy remains unchanged.

- [ ] **Step 5: Verify and reload test Nginx only**

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Expected: config test success; reload exit 0.

- [ ] **Step 6: Smoke staged frontend and preserved Preview Lab**

```bash
curl -fsS -H 'Host: test.blackserv.eu' http://127.0.0.1/ | grep -q 'id="search-form"'
curl -fsS -H 'Host: test.blackserv.eu' http://127.0.0.1/api/health | grep -q '"status":"ok"'
curl -fsS -H 'Host: test.blackserv.eu' http://127.0.0.1/test/index.html | grep -q 'Preview Lab'
test "$(curl -sS -o /dev/null -w '%{http_code}' -H 'Host: test.blackserv.eu' http://127.0.0.1/sw.js)" = "404"
```

Expected: all commands exit 0.

- [ ] **Step 7: Owner visual acceptance on real devices**

Do not proceed to Task 6 until the owner reviews the rendered test frontend.

Desktop checks:
1. wide three-column search results;
2. search hierarchy;
3. Amateur / Production segmented control;
4. Filters right drawer;
5. card with preview;
6. card without preview;
7. long title;
8. sparse metadata;
9. loading/empty state if practical.

Mobile checks:
1. one full-width 16:9 card per row;
2. sticky search area;
3. one-tap Play;
4. Filters bottom sheet;
5. no horizontal overflow.

Acceptance must be explicit:
- `PASS` — continue to Task 6;
- `CHANGES` — return to the owning task, add a failing regression/contract test where applicable, implement the change, repeat staging and review.

- [ ] **Step 8: Record visual acceptance only after explicit PASS**

Append a dated checkpoint to `docs/SEARCH_ENGINE_HANDOFF.md` with redesign SHA, test domain, desktop PASS, mobile PASS, one-tap preview PASS, filter sheet PASS, and any accepted limitations.

```bash
git add docs/SEARCH_ENGINE_HANDOFF.md
git commit -m "docs: record premium frontend visual acceptance"
```

### Task 6: Cache v32 production release after owner visual PASS

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`
- Modify: `frontend/sw.js`
- Modify: `tests/test_frontend_contract.py`
- Modify after release: `docs/SEARCH_ENGINE_HANDOFF.md`

**Interfaces:**
- Consumes owner-approved Task 5 branch.
- Produces synchronized frontend asset/cache version 32, exact verified release SHA, official helper deployment, and production health/hash/visual evidence.

- [ ] **Step 1: Add failing cache-version synchronization test**

In the same RED step, update the existing `test_frontend_assets_are_v31`, `test_service_worker_reload_is_guarded`, and `test_on_demand_preview_frontend_bumps_shell_cache` to version 32 expectations (rename the first to `test_frontend_assets_are_v32`). Do not leave duplicate v31 and v32 requirements in the suite. Then add this synchronization test:

```python
def test_frontend_cache_versions_move_together() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    sw = (ROOT / "frontend" / "sw.js").read_text(encoding="utf-8")
    assert '/styles.css?v=32' in html
    assert '/app.js?v=32' in html
    assert 'search-shell-v32' in sw
    assert 'search.swReload.v32' in app
    assert 'navigator.serviceWorker.register("/sw.js?v=32"' in app
```

- [ ] **Step 2: Run cache test and verify RED**

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_frontend_contract.py::test_frontend_cache_versions_move_together
```

Expected: FAIL because the accepted test build is still on production cache version 31.

- [ ] **Step 3: Bump cache version atomically**

Change:
- `frontend/index.html`: `/styles.css?v=31` -> v32 and `/app.js?v=31` -> v32;
- `frontend/app.js`: `search.swReload.v31` -> v32 and `/sw.js?v=31` -> v32;
- `frontend/sw.js`: `search-shell-v31` -> v32.

Do not alter service-worker fetch semantics.

- [ ] **Step 4: Run complete release gate**

```bash
PYTHONPATH=. .venv/bin/pytest -q
python -m compileall backend
node --check frontend/app.js
git diff --check
```

Expected: 0 failures and 0 syntax/diff errors.

- [ ] **Step 5: Commit release cache bump**

```bash
git add frontend/index.html frontend/app.js frontend/sw.js tests/test_frontend_contract.py
git commit -m "chore: bump premium frontend cache v32"
git rev-parse HEAD
```

- [ ] **Step 6: Push redesign branch**

```bash
git push -u origin feature/premium-brandless-redesign
```

Expected: push succeeds; local/origin SHA match.

- [ ] **Step 7: Run official production helper CHECK**

```bash
sudo -u blackserv /usr/local/bin/search-engine-deploy-client status
sudo -u blackserv /usr/local/bin/search-engine-deploy-client check
```

Expected: service healthy and CHECK PASS. Do not deploy on failure.

- [ ] **Step 8: Deploy only the owner-approved exact release**

```bash
sudo -u blackserv /usr/local/bin/search-engine-deploy-client deploy
```

Expected: `SEARCH_DEPLOY=PASS`. No direct `/opt/search_engine` edits.

- [ ] **Step 9: Verify production health and frontend asset truth**

```bash
curl -fsS http://127.0.0.1:8775/api/health
grep -n 'styles.css?v=32\|app.js?v=32' /opt/search_engine/frontend/index.html
grep -n 'search-shell-v32' /opt/search_engine/frontend/sw.js
grep -n 'search.swReload.v32\|/sw.js?v=32' /opt/search_engine/frontend/app.js
```

Expected: health status ok; production build equals release SHA prefix; all v32 assertions present.

- [ ] **Step 10: Verify production file hashes equal the release tree**

```bash
sha256sum /opt/search_engine/frontend/index.html /opt/search_engine/frontend/app.js /opt/search_engine/frontend/styles.css /opt/search_engine/frontend/sw.js
sudo -u blackserv sha256sum /opt/bs-sandbox/search_engine-worktrees/premium-brandless-redesign/frontend/index.html /opt/bs-sandbox/search_engine-worktrees/premium-brandless-redesign/frontend/app.js /opt/bs-sandbox/search_engine-worktrees/premium-brandless-redesign/frontend/styles.css /opt/bs-sandbox/search_engine-worktrees/premium-brandless-redesign/frontend/sw.js
```

Expected: each production hash matches the corresponding release-worktree hash.

- [ ] **Step 11: Run bounded functional smoke**

Verify production backend:
- `/api/health` 200;
- one normal search returns items;
- `content_class=amateur` accepted;
- `content_class=studio` accepted;
- one of the eight promoted preview providers still returns a non-empty `/api/preview/{id}` result.

Do not crawl providers or re-run mass preview audit.

- [ ] **Step 12: Owner post-deploy visual smoke**

On authenticated production verify mobile shell/card/filter sheet, desktop three-column layout, one-tap preview, and no stale old shell. If stale UI appears, inspect loaded v32 assets/service-worker state before changing source.

- [ ] **Step 13: Record final closeout**

Append exact release SHA, CHECK PASS, deploy PASS, health PASS, v32 source/hash PASS, and owner mobile/desktop visual PASS to `docs/SEARCH_ENGINE_HANDOFF.md`.

```bash
git add docs/SEARCH_ENGINE_HANDOFF.md
git commit -m "docs: close premium frontend redesign"
git push
```

Do not redeploy the docs-only closeout commit.

## Final Verification Checklist

Before declaring the redesign complete:

```bash
PYTHONPATH=. .venv/bin/pytest -q
python -m compileall backend
node --check frontend/app.js
git diff --check
git status --short --branch
```

Required evidence:
- full suite: 0 failures;
- compileall: PASS;
- JavaScript syntax: PASS;
- diff check: PASS;
- worktree clean;
- test-domain desktop visual PASS;
- test-domain mobile visual PASS;
- owner explicitly approved production rollout;
- official helper CHECK PASS;
- official helper DEPLOY PASS;
- production `/api/health` PASS;
- production frontend files match exact release worktree;
- production desktop/mobile visual smoke PASS.

Do not claim `PROJECT_DONE` before every required evidence item above is satisfied.
