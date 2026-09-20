# Phase E — Premium Product Finish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the functional “form + grid” Search frontend with the approved premium, media-first desktop/mobile experience while preserving the existing Search API, filter semantics, thumbnail recovery, manual preview policy, and production deployment discipline.

**Architecture:** Keep the existing vanilla HTML/CSS/JS application and backend contract. Restructure the DOM into a compact premium search shell, one canonical set of filter controls with a mobile sheet presentation, an accessible media card template, and explicit UI-state render helpers. Preserve existing search/prefetch/live-refresh functions and provider media policies; refactor only the presentation and UI orchestration around them.

**Tech Stack:** Vanilla HTML5, CSS, browser JavaScript, service worker/PWA shell, Python `pytest` contract tests.

**Spec:** `docs/superpowers/specs/2026-09-20-premium-product-finish-design.md`

## Global Constraints

- Base feature work on exact deployed code SHA `82a152999e173b8649e4d6dfce5e0003cdf579d0`.
- Work only on branch `feature/premium-product-finish` in its isolated worktree.
- Keep vanilla `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`; do not add React, Vue, Svelte, or another framework.
- Do not change backend API contracts or backend behavior.
- Preserve Provider, Quality, Duration, Age Check, Content Type, sorting, URL state, thumbnail self-healing, provider media policy, prefetch, and live-refresh behavior.
- Preview stays manual only and one-at-a-time; no hover/scroll autoplay.
- Mobile stays one-column with full-width 16:9 media cards.
- Do not add Trending, Favorites, History, Studios/Performers navigation, subscriptions, recommendations, personalization, fabricated counts, or fake navigation.
- Only explicit `amateur` classification gets an Amateur label; never render generic Unknown/Studio badges; real studio label is shown only when present.
- Use the official deploy helper only; never edit production directly.
- Respect the maintenance lock and never kill healthy sync/backfill work to force a deployment.
- Authenticated visual acceptance may be `NOT_VERIFIED` if operator credentials are unavailable; do not bypass authentication.

## Review Focus

1. **Mobile sheet closed with unapplied edits:** pending secondary filter values must stay intact when the sheet closes, and a search must run only when the user presses Apply; reopening must show the same pending values.
2. **Keyboard-only mobile sheet:** Tab/Shift+Tab must stay inside the open sheet, Escape must close it, focus must return to the Filters button, and body scrolling must always be restored.
3. **Recoverable live failure after cached results rendered:** cached/indexed cards must remain visible; only the quiet live-detail notice changes and Retry is not allowed to destroy good results.
4. **Preview failure while another card is available:** failed preview must restore its still image, disable only that item’s preview control, and preserve the one-active-preview invariant for later cards.
5. **Service-worker controller churn:** a controller change may trigger at most one guarded reload per update window; repeated controller changes in the same page session must not loop reloads.

---

### Task 1: Premium semantic shell and accessibility baseline

**Files:**
- Modify: `frontend/index.html`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: existing element IDs `#search-form`, `#q`, `#sort`, `#content-class`, `#provider`, `#quality`, `#duration`, `#age-check`, `#status`, `#live-detail`, `#results`, `#more`, `#clear`.
- Produces: `.search-shell`, `.primary-controls`, `.secondary-filters`, `#filters-open`, `#filter-sheet`, `#filters-apply`, `#filters-close`, `#filters-reset`, `.media-frame`, `.thumb`, sibling `.preview-toggle`, dedicated `#status[role="status"]`.

- [ ] **Step 1: Add failing semantic-contract tests**

Append these tests to `tests/test_frontend_contract.py`:

```python
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
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_frontend_contract.py::test_premium_shell_has_primary_and_secondary_filter_hierarchy \
  tests/test_frontend_contract.py::test_results_grid_is_not_live_region_and_status_is \
  tests/test_frontend_contract.py::test_preview_button_is_not_nested_inside_media_link
```

Expected: FAIL because the premium shell, dedicated status region contract, and corrected media structure do not exist yet.

- [ ] **Step 3: Restructure `frontend/index.html` without changing control IDs**

Use this structural shape:

```html
<header class="topbar">
  <a class="brand" href="/" aria-label="Search home">SEARCH</a>
  <span class="badge">DEV</span>
</header>

<main class="shell">
  <section class="search-shell" aria-label="Search controls">
    <form id="search-form" class="searchbox">
      <label class="sr-only" for="q">Search</label>
      <input id="q" name="q" type="search" maxlength="200" autocomplete="off"
             placeholder="Search videos, creators, topics…" autofocus>
      <button type="submit">Search</button>
    </form>

    <div class="control-row">
      <div class="primary-controls">
        <!-- existing #sort and #content-class selects, unchanged option values -->
      </div>
      <button id="filters-open" class="filters-open" type="button"
              aria-controls="filter-sheet" aria-expanded="false">Filters</button>
    </div>

    <div class="secondary-filters">
      <!-- existing #provider, #quality, #duration, #age-check selects -->
    </div>
  </section>

  <section class="statusbar" aria-label="Search status">
    <div class="status-copy">
      <span id="status" class="result-summary" role="status"
            aria-live="polite" aria-atomic="true">Ready</span>
      <span id="live-detail" class="live-detail"></span>
    </div>
    <button id="clear" class="ghost" type="button">Clear</button>
  </section>

  <section id="results" class="grid"></section>
  <div class="more-row">
    <button id="more" class="more" type="button" hidden>Show more</button>
  </div>
</main>
```

Add the mobile sheet after `</main>`:

```html
<div id="filter-sheet" class="filter-sheet" role="dialog" aria-modal="true"
     aria-labelledby="filter-sheet-title" hidden>
  <button class="filter-sheet-backdrop" type="button" data-filter-close
          aria-label="Close filters"></button>
  <section class="filter-sheet-panel" tabindex="-1">
    <header class="filter-sheet-header">
      <h2 id="filter-sheet-title">Filters</h2>
      <button id="filters-close" type="button" aria-label="Close filters">×</button>
    </header>
    <div id="mobile-secondary-filters" class="mobile-secondary-filters"></div>
    <footer class="filter-sheet-actions">
      <button id="filters-reset" type="button" class="ghost">Reset</button>
      <button id="filters-apply" type="button" class="primary-action">Apply filters</button>
    </footer>
  </section>
</div>
```

Restructure the card media so the preview control is a sibling of the link:

```html
<article class="card">
  <div class="media-frame">
    <a class="thumb">
      <img class="preview" alt="" loading="lazy" decoding="async"
           referrerpolicy="no-referrer" hidden>
      <video class="motion-preview" muted loop playsinline preload="none"
             referrerpolicy="no-referrer" hidden></video>
      <div class="placeholder">Preview</div>
    </a>
    <div class="media-badges">
      <span class="quality"></span>
      <span class="duration"></span>
    </div>
    <button class="preview-toggle" type="button" aria-label="Play preview"
            aria-pressed="false" hidden>▶</button>
  </div>
  <!-- existing metadata hooks retained -->
</article>
```

- [ ] **Step 4: Run Task 1 tests**

Run the three tests from Step 2.

Expected: PASS.

- [ ] **Step 5: Retire only the obsolete v2 markup-hook test and run the full frontend contract suite**

Replace `test_cards_ui_v2_markup_hooks` with the Task 1 premium-shell tests above. Do not change the legacy CSS-layout tests yet; CSS still remains v26 until Task 2.

Run:

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_frontend_contract.py
```

Expected: PASS. Task 1 must end green; do not commit a checkpoint with known frontend-contract failures.

- [ ] **Step 6: Commit semantic shell**

```bash
git add frontend/index.html tests/test_frontend_contract.py
git commit -m "feat: add premium search shell"
```

---

### Task 2: Premium visual system, desktop hierarchy, and 3/2/1 card layout

**Files:**
- Modify: `frontend/styles.css`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: Task 1 class hooks.
- Produces: CSS tokens, premium desktop shell, 3/2/1 grid, focus styles, card/media hierarchy, sheet base styling.

- [ ] **Step 1: Replace obsolete Cards UI v2 CSS assertions with failing Phase E layout tests**

Replace the old `test_cards_ui_v2_desktop_hierarchy_css` and `test_cards_ui_v2_mobile_feed_contract` with:

```python
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
```

- [ ] **Step 2: Run the three Phase E CSS tests and verify RED**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_frontend_contract.py::test_premium_css_uses_tokens_and_three_two_one_grid \
  tests/test_frontend_contract.py::test_premium_mobile_has_no_horizontal_filter_strip \
  tests/test_frontend_contract.py::test_keyboard_focus_is_explicit
```

Expected: FAIL against the existing v26 CSS.

- [ ] **Step 3: Rewrite `frontend/styles.css` around a restrained token system**

Start with these tokens and use them consistently:

```css
:root {
  color-scheme: dark;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --bg-page: #0a0a0c;
  --bg-surface: #111114;
  --bg-elevated: #17171b;
  --bg-control: #19191e;
  --border-subtle: #29292f;
  --border-strong: #3a3a43;
  --text-primary: #f7f7f8;
  --text-secondary: #b7b7c0;
  --text-muted: #7d7d88;
  --focus-ring: #d7d7df;
  --radius-control: 12px;
  --radius-card: 16px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  background: var(--bg-page);
  color: var(--text-primary);
}
```

Required layout rules:

```css
.shell { width: min(1440px, 100%); margin: 0 auto; padding: 24px 24px 64px; }
.search-shell { display: grid; gap: 12px; padding: 18px 0 16px; }
.control-row { display: flex; justify-content: space-between; gap: 12px; align-items: end; }
.primary-controls { display: grid; grid-template-columns: minmax(180px, 240px) minmax(180px, 240px); gap: 10px; }
.secondary-filters { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 22px 18px; }

@media (max-width: 960px) {
  .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 680px) {
  .shell { padding: 10px 8px 40px; }
  .grid { grid-template-columns: 1fr; gap: 18px; }
  .secondary-filters { display: none; }
  .primary-controls { grid-template-columns: 1fr 1fr; }
  .filters-open { display: inline-flex; }
}
```

Required card rules:
- `.card` uses subtle border/surface and no heavy shadow.
- `.media-frame` is `position: relative`.
- `.thumb` is full-width 16:9, `display: block`, and owns the still/video area.
- `.preview-toggle` is positioned over `.media-frame` but remains outside the link in DOM.
- title is two-line clamped with stronger weight than metadata.
- metadata is split into readable groups with muted secondary text, not a dense undifferentiated string.
- all buttons, links, selects, and input get a visible `:focus-visible` outline using `var(--focus-ring)`.

- [ ] **Step 4: Run Task 2 tests**

Expected: PASS.

- [ ] **Step 5: Run full frontend contracts and fix only obsolete visual expectations**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_frontend_contract.py
```

Expected: PASS after old v2 layout assertions are replaced; search/filter/provider/media-policy behavior tests remain unchanged.

- [ ] **Step 6: Commit visual system**

```bash
git add frontend/styles.css tests/test_frontend_contract.py
git commit -m "feat: add premium responsive visual system"
```

---

### Task 3: Mobile filter sheet with one canonical filter state

**Files:**
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: `#filter-sheet`, `#filters-open`, `#filters-close`, `#filters-reset`, `#filters-apply`, `#mobile-secondary-filters`, `.secondary-filters`; existing provider/quality/duration/age-check selects.
- Produces: `openFilterSheet()`, `closeFilterSheet()`, `applyMobileFilters()`, `resetSecondaryFilters()`, `trapFilterSheetFocus(event)`, responsive relocation of the single secondary-filter DOM group.

- [ ] **Step 1: Add failing mobile-sheet behavior contract tests**

```python
def test_mobile_filter_sheet_contract() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    for hook in (
        'id="filters-open"', 'id="filter-sheet"', 'role="dialog"',
        'aria-modal="true"', 'id="filters-close"', 'id="filters-reset"',
        'id="filters-apply"', 'id="mobile-secondary-filters"',
    ):
        assert hook in html
    for fn in (
        "function openFilterSheet()",
        "function closeFilterSheet(",
        "function applyMobileFilters()",
        "function resetSecondaryFilters()",
        "function trapFilterSheetFocus(event)",
    ):
        assert fn in app
    assert 'document.body.classList.add("filter-sheet-open")' in app
    assert 'document.body.classList.remove("filter-sheet-open")' in app
    assert 'event.key === "Escape"' in app
    assert 'event.key !== "Tab"' in app
    assert "filtersOpenBtn.focus()" in app


def test_mobile_secondary_changes_wait_for_apply() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'const mobileQuery = window.matchMedia("(max-width: 680px)")' in app
    assert "function secondaryFilterChanged()" in app
    section = app[app.index("function secondaryFilterChanged()"):app.index("function resetSecondaryFilters()")]
    assert "mobileQuery.matches" in section
    assert "search();" in section
    apply = app[app.index("function applyMobileFilters()"):app.index("function trapFilterSheetFocus")]
    assert "search();" in apply
    assert "closeFilterSheet" in apply
```

- [ ] **Step 2: Run tests and verify RED**

Run the two tests from Step 1.

Expected: FAIL because sheet behavior is not implemented.

- [ ] **Step 3: Add sheet element references and one canonical secondary filter group**

At the top of `frontend/app.js`, add:

```javascript
const filtersOpenBtn = document.querySelector("#filters-open");
const filterSheet = document.querySelector("#filter-sheet");
const filtersCloseBtn = document.querySelector("#filters-close");
const filtersResetBtn = document.querySelector("#filters-reset");
const filtersApplyBtn = document.querySelector("#filters-apply");
const desktopSecondaryFilters = document.querySelector(".secondary-filters");
const mobileSecondaryFilters = document.querySelector("#mobile-secondary-filters");
const filterSheetPanel = document.querySelector(".filter-sheet-panel");
const mobileQuery = window.matchMedia("(max-width: 680px)");
let filterSheetOpen = false;
const secondaryFiltersHome = document.createComment("secondary-filters-home");
desktopSecondaryFilters.after(secondaryFiltersHome);
```

The comment marker stays in the desktop location. Move the same `.secondary-filters` node into the sheet only while mobile and open, and restore it with `secondaryFiltersHome.before(desktopSecondaryFilters)`. Do not duplicate any `<select>`.

- [ ] **Step 4: Implement open/close/apply/reset/focus behavior**

Use these contracts:

```javascript
function openFilterSheet() {
  if (filterSheetOpen) return;
  filterSheetOpen = true;
  mobileSecondaryFilters.append(desktopSecondaryFilters);
  filterSheet.hidden = false;
  filtersOpenBtn.setAttribute("aria-expanded", "true");
  document.body.classList.add("filter-sheet-open");
  window.requestAnimationFrame(() => filterSheetPanel.focus());
}

function closeFilterSheet({ returnFocus = true } = {}) {
  if (!filterSheetOpen) return;
  filterSheetOpen = false;
  secondaryFiltersHome.before(desktopSecondaryFilters);
  filterSheet.hidden = true;
  filtersOpenBtn.setAttribute("aria-expanded", "false");
  document.body.classList.remove("filter-sheet-open");
  if (returnFocus) filtersOpenBtn.focus();
}

function applyMobileFilters() {
  closeFilterSheet();
  search();
}

function resetSecondaryFilters() {
  providerSelect.value = "";
  qualitySelect.value = "";
  durationSelect.value = "";
  ageCheckSelect.value = "";
}

function trapFilterSheetFocus(event) {
  if (!filterSheetOpen) return;
  if (event.key === "Escape") {
    event.preventDefault();
    closeFilterSheet();
    return;
  }
  if (event.key !== "Tab") return;
  const focusable = [...filterSheetPanel.querySelectorAll(
    'button:not([disabled]), select:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )].filter((node) => !node.hidden);
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}
```

`filtersResetBtn` resets only secondary filters and keeps the sheet open. `filtersApplyBtn` applies once. Backdrop and close button close without issuing a search; pending values remain because the canonical selects are not reverted.

- [ ] **Step 5: Stop secondary selects from auto-searching on mobile**

Replace the single loop over all six controls with:

```javascript
for (const el of [sortSelect, contentClassSelect]) {
  el.addEventListener("change", () => search());
}

function secondaryFilterChanged() {
  if (mobileQuery.matches) return;
  search();
}

for (const el of [providerSelect, qualitySelect, durationSelect, ageCheckSelect]) {
  el.addEventListener("change", secondaryFilterChanged);
}
```

Wire sheet buttons and keyboard:

```javascript
filtersOpenBtn.addEventListener("click", openFilterSheet);
filtersCloseBtn.addEventListener("click", () => closeFilterSheet());
filtersResetBtn.addEventListener("click", resetSecondaryFilters);
filtersApplyBtn.addEventListener("click", applyMobileFilters);
filterSheet.querySelector("[data-filter-close]").addEventListener("click", () => closeFilterSheet());
filterSheet.addEventListener("keydown", trapFilterSheetFocus);
mobileQuery.addEventListener("change", (event) => {
  if (!event.matches && filterSheetOpen) closeFilterSheet({ returnFocus: false });
});
```

- [ ] **Step 6: Add sheet CSS**

Required:
- desktop `#filter-sheet` hidden by `[hidden]`;
- mobile `.filter-sheet` fixed to viewport with backdrop and bottom-aligned panel;
- panel max height `min(86vh, 720px)` and internal scrolling;
- `body.filter-sheet-open { overflow: hidden; }`;
- 44px minimum touch targets for sheet actions/controls;
- no horizontal filter strip.

- [ ] **Step 7: Run Task 3 tests and full frontend contracts**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_frontend_contract.py
```

Expected: PASS.

- [ ] **Step 8: Commit mobile filter sheet**

```bash
git add frontend/app.js frontend/styles.css tests/test_frontend_contract.py
git commit -m "feat: add accessible mobile filter sheet"
```

---

### Task 4: Accessible card wiring and resilient manual preview

**Files:**
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: `.media-frame`, `.thumb`, `.preview-toggle`, existing `startMotionPreview`, `stopMotionPreview`, `failMotionPreview`.
- Produces: accessible thumb names, sibling preview control behavior, preview-failure visual state.

- [ ] **Step 1: Add failing accessibility/preview regression tests**

```python
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
```

- [ ] **Step 2: Run tests and verify RED only for new requirements**

Expected: accessible-name and scoped failure tests FAIL; one-active-preview regression remains PASS.

- [ ] **Step 3: Update `resultCard(item)` accessibility wiring**

Immediately after assigning hrefs:

```javascript
thumb.href = item.url;
thumb.setAttribute("aria-label", `View ${item.title}`);
title.href = item.url;
```

Do not add alt text that duplicates the labeled link; keep decorative thumbnail `alt=""`.

- [ ] **Step 4: Mark preview failure on the owning media frame**

In `failMotionPreview(...)`, before hiding the toggle:

```javascript
toggle.closest(".media-frame")?.classList.add("preview-failed");
```

In `startMotionPreview(...)`, remove the stale failure class before starting:

```javascript
toggle.closest(".media-frame")?.classList.remove("preview-failed");
```

CSS may use `.preview-failed .preview-toggle { display: none; }` and must leave the still image visible.

- [ ] **Step 5: Run Task 4 tests plus existing media-policy tests**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_frontend_contract.py::test_card_thumb_gets_accessible_name_from_title \
  tests/test_frontend_contract.py::test_preview_failure_is_scoped_to_its_media_frame \
  tests/test_frontend_contract.py::test_manual_one_active_preview_contract_is_preserved \
  tests/test_frontend_contract.py::test_card_media_is_policy_driven \
  tests/test_frontend_contract.py::test_preview_is_manual_with_play_button
```

Expected: PASS.

- [ ] **Step 6: Commit card accessibility**

```bash
git add frontend/app.js frontend/styles.css tests/test_frontend_contract.py
git commit -m "fix: harden card accessibility and preview recovery"
```

---

### Task 5: Explicit search, empty, loading, partial, and error states

**Files:**
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: `resultsEl`, `search()`, `loadMore()`, `refreshLive()`, `setPrimaryStatus()`, `setLiveDetail()`.
- Produces: `renderSkeletons()`, `clearSkeletons()`, `renderEmptyState()`, `renderErrorState()`, `hasActiveFilters()`, event delegation for Retry/Clear filters.

- [ ] **Step 1: Add failing UI-state tests**

```python
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
    assert 'data-action="retry-search"' in app
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
```

- [ ] **Step 2: Run tests and verify RED**

Expected: FAIL because explicit state helpers do not exist.

- [ ] **Step 3: Add skeleton and state render helpers**

Implement:

```javascript
function renderSkeletons(count = 6, { append = false } = {}) {
  if (!append) resultsEl.replaceChildren();
  for (let index = 0; index < count; index += 1) {
    const skeleton = document.createElement("article");
    skeleton.className = "card skeleton-card";
    skeleton.dataset.uiState = "skeleton";
    skeleton.innerHTML = `
      <div class="skeleton-media"></div>
      <div class="skeleton-copy">
        <span></span><span></span>
      </div>`;
    resultsEl.append(skeleton);
  }
}

function clearSkeletons() {
  for (const node of resultsEl.querySelectorAll('[data-ui-state="skeleton"]')) node.remove();
}

function hasActiveFilters() {
  return Boolean(
    contentClassSelect.value ||
    providerSelect.value ||
    qualitySelect.value ||
    durationSelect.value ||
    ageCheckSelect.value
  );
}

function renderEmptyState({ filtered = hasActiveFilters() } = {}) {
  resultsEl.replaceChildren();
  const state = document.createElement("div");
  state.className = "state-panel";
  state.innerHTML = filtered
    ? '<strong>No results match these filters.</strong><button type="button" data-action="clear-filters">Clear filters</button>'
    : '<strong>No results found.</strong><span>Try a different search.</span>';
  resultsEl.append(state);
}

function renderErrorState(message) {
  resultsEl.replaceChildren();
  const state = document.createElement("div");
  state.className = "state-panel state-error";
  const copy = document.createElement("strong");
  copy.textContent = message || "Search failed";
  const retry = document.createElement("button");
  retry.type = "button";
  retry.dataset.action = "retry-search";
  retry.textContent = "Retry";
  state.append(copy, retry);
  resultsEl.append(state);
}
```

Do not interpolate server error strings through `innerHTML`.

- [ ] **Step 4: Integrate state helpers into initial search and pagination**

At initial search start:
- set status `"Searching…"`
- call `renderSkeletons()`

Before wiring the new states, remove the old `render()` block that creates a generic `.empty` node when `seenIds` is empty. Search orchestration now owns empty/error presentation.

After `fetchLocal` succeed:
- call `clearSkeletons()`
- call existing `render(...)`
- if no real items remain, call `renderEmptyState()`

On initial search catch:
- call `renderErrorState(error.message || "Search failed")`
- status becomes `"Search unavailable"`

During `loadMore()`:
- append 3 skeletons after current cards;
- always `clearSkeletons()` on success/failure before updating status.

- [ ] **Step 5: Preserve cached results on live-refresh failure and expose partial failures**

Add:

```javascript
function liveFailureCount(providers) {
  return (providers || []).filter((item) => Boolean(item?.error)).length;
}
```

In `applyLiveState`, append quiet unavailable-source text when `liveFailureCount(live.providers) > 0`.

In `refreshLive` catch, do not replace results; use:

```javascript
setLiveDetail("Live sources unavailable — showing cached results.");
```

and continue prefetch behavior.

- [ ] **Step 6: Add state-panel event delegation**

```javascript
resultsEl.addEventListener("click", (event) => {
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action === "retry-search") {
    search({ persist: false });
  } else if (action === "clear-filters") {
    contentClassSelect.value = "";
    providerSelect.value = "";
    qualitySelect.value = "";
    durationSelect.value = "";
    ageCheckSelect.value = "";
    search();
  }
});
```

- [ ] **Step 7: Add CSS for skeleton/state panels without layout shift**

Required:
- skeleton `.skeleton-media` uses same 16:9 geometry as cards;
- pulse/opacity animation respects `@media (prefers-reduced-motion: reduce)`;
- `.state-panel` spans full grid width and has a calm elevated surface;
- retry/clear actions meet touch/focus requirements.

- [ ] **Step 8: Run Task 5 tests and full frontend contracts**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_frontend_contract.py
```

Expected: PASS.

- [ ] **Step 9: Commit explicit UI states**

```bash
git add frontend/app.js frontend/styles.css tests/test_frontend_contract.py
git commit -m "feat: add premium search states"
```

---

### Task 6: Safe PWA update path and asset version v27

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`
- Modify: `frontend/sw.js`
- Modify: `frontend/manifest.webmanifest` only if it embeds a versioned start/scope asset that must match
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: existing service-worker registration.
- Produces: frontend shell version 27 and one-time guarded controller reload.

- [ ] **Step 1: Replace obsolete v26 tests with failing v27 guarded-update tests**

Replace both old v26 asset-version tests with:

```python
def test_frontend_assets_are_v27() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    sw = (ROOT / "frontend" / "sw.js").read_text(encoding="utf-8")
    assert "/styles.css?v=27" in html
    assert "/app.js?v=27" in html
    assert 'register("/sw.js?v=27", { updateViaCache: "none" })' in app
    assert 'const CACHE = "search-shell-v27";' in sw
    assert '"/styles.css?v=27"' in sw
    assert '"/app.js?v=27"' in sw


def test_service_worker_reload_is_guarded() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'const SW_RELOAD_GUARD = "search.swReload.v27";' in app
    controller = app[app.index('navigator.serviceWorker.addEventListener("controllerchange"'):]
    assert "sessionStorage.getItem(SW_RELOAD_GUARD)" in controller
    assert "sessionStorage.setItem(SW_RELOAD_GUARD" in controller
    assert "window.location.reload();" in controller
    assert "window.setTimeout" in controller
    assert "sessionStorage.removeItem(SW_RELOAD_GUARD)" in controller
```

- [ ] **Step 2: Run the two tests and verify RED**

Expected: FAIL because assets are v26 and reload is guarded only by an in-memory boolean.

- [ ] **Step 3: Bump shell assets to v27**

Update:
- `index.html`: `/styles.css?v=27`, `/app.js?v=27`;
- `app.js`: `/sw.js?v=27`;
- `sw.js`: `const CACHE = "search-shell-v27";` and pre-cache v27 asset URLs.

Keep existing provider-media bypass and `cache: "no-store"` behavior unchanged.

- [ ] **Step 4: Replace controllerchange reload with a session guard**

Use:

```javascript
const SW_RELOAD_GUARD = "search.swReload.v27";

navigator.serviceWorker.addEventListener("controllerchange", () => {
  try {
    if (sessionStorage.getItem(SW_RELOAD_GUARD) === "1") return;
    sessionStorage.setItem(SW_RELOAD_GUARD, "1");
  } catch (_) {}
  window.location.reload();
});

window.setTimeout(() => {
  try {
    sessionStorage.removeItem(SW_RELOAD_GUARD);
  } catch (_) {}
}, 5000);
```

This permits one reload when a new worker takes control and suppresses repeated controller churn during the reload window.

- [ ] **Step 5: Run asset/update tests plus media-bypass test**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_frontend_contract.py::test_frontend_assets_are_v27 \
  tests/test_frontend_contract.py::test_service_worker_reload_is_guarded \
  tests/test_frontend_contract.py::test_provider_media_bypasses_service_worker
```

Expected: PASS.

- [ ] **Step 6: Commit PWA shell v27**

```bash
git add frontend/index.html frontend/app.js frontend/sw.js frontend/manifest.webmanifest tests/test_frontend_contract.py
git commit -m "fix: guard premium shell updates"
```

If `frontend/manifest.webmanifest` has no content change, omit it from `git add`.

---

### Task 7: Integration gate, handoff, release, deploy, and acceptance

**Files:**
- Modify: `docs/SEARCH_ENGINE_HANDOFF.md`
- No production files edited directly.

**Interfaces:**
- Consumes: complete Phase E branch.
- Produces: verified feature SHA, updated handoff, fast-forwarded release branch, official deployment, explicit visual-smoke status.

- [ ] **Step 1: Run targeted frontend suite**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_frontend_contract.py
```

Expected: all frontend contract tests PASS.

- [ ] **Step 2: Run full Python suite**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q
```

Expected: all tests PASS; only the two pre-existing FastAPI `on_event` deprecation warnings are acceptable.

- [ ] **Step 3: Run syntax and whitespace gates**

```bash
.venv/bin/python -m compileall -q backend
node --check frontend/app.js
git diff --check
git status --short
```

Expected:
- compileall PASS;
- Node syntax PASS;
- diff-check PASS;
- clean tree after final documentation commit.

- [ ] **Step 4: Update handoff with exact Phase E result**

Append an authoritative checkpoint containing:
- branch and exact HEAD;
- tasks completed;
- exact test counts;
- frontend shell v27;
- production still unchanged at this point;
- visual acceptance status `PENDING`;
- next release/deploy steps.

Commit:

```bash
git add docs/SEARCH_ENGINE_HANDOFF.md
git commit -m "docs: record premium product finish gate"
```

Then rerun `git diff --check` and `git status --short`.

- [ ] **Step 5: Push feature branch**

Use the repository’s existing deploy key and verified sandbox known-host file via temporary `GIT_SSH_COMMAND` if the configured `/tmp/search-engine-github-known-hosts` is absent. Do not disable host-key verification.

```bash
git push origin feature/premium-product-finish
```

Expected: exact feature HEAD is present on origin.

- [ ] **Step 6: Fast-forward release branch to exact Phase E code/docs HEAD only after gates PASS**

First verify:

```bash
git fetch origin feature/provider-registry-probe
git merge-base --is-ancestor origin/feature/provider-registry-probe HEAD
```

Expected exit code: `0`.

Then fast-forward remote release without rewriting history:

```bash
git push origin HEAD:refs/heads/feature/provider-registry-probe
```

Expected: fast-forward only.

- [ ] **Step 7: Prepare canonical sandbox for official helper without losing local handoff work**

Inspect `/opt/bs-sandbox/search_engine` first. If it has only local handoff edits, preserve them with a named stash before fast-forwarding canonical to the exact release SHA. If any unrelated app-code changes exist, STOP and report the blocker instead of stashing/overwriting them.

After preservation:

```bash
git -C /opt/bs-sandbox/search_engine fetch origin feature/provider-registry-probe
git -C /opt/bs-sandbox/search_engine merge --ff-only origin/feature/provider-registry-probe
```

Expected: canonical clean on exact release SHA.

- [ ] **Step 8: Run official helper CHECK as `blackserv`**

```bash
/usr/local/bin/search-engine-deploy-client check
```

Expected: `SEARCH_DEPLOY_CHECK=PASS` for the exact Phase E build.

- [ ] **Step 9: Respect maintenance lock**

Check `search-engine-sync.service` and `search-engine-backfill.service`. If either actively holds the maintenance lock, wait for a natural free window; do not stop/kill either job.

- [ ] **Step 10: Deploy with official helper**

```bash
/usr/local/bin/search-engine-deploy-client deploy
```

If the transport times out, do not blindly retry. Verify `/opt/search_engine/.build-id`, `/api/health`, helper status, and service state first.

- [ ] **Step 11: Verify production build and services**

```bash
cat /opt/search_engine/.build-id
curl -fsS http://127.0.0.1:8775/api/health
/usr/local/bin/search-engine-deploy-client status
```

Expected:
- build ID equals the released Phase E SHA prefix;
- API health `status=ok`;
- `search-engine.service` active;
- sync and backfill timers active.

- [ ] **Step 12: Verify production functional contracts**

Using local API only:
- indexed search with query and filters returns HTTP 200;
- live refresh returns HTTP 200;
- invalid content class returns HTTP 422;
- content-class filtering still returns only requested classes;
- provider/media policy endpoint still responds normally.

No authentication bypass is permitted for public browser access.

- [ ] **Step 13: Authenticated desktop/mobile visual smoke**

When operator credentials are available, verify:
- desktop shows compact premium shell and 3-column cards on wide viewport;
- tablet uses 2 columns;
- mobile shows one column and `Sort / Content / Filters`;
- mobile Filters opens a real sheet and Apply triggers one search;
- no horizontal filter strip;
- preview button is visually separate from the link and one-at-a-time behavior works;
- keyboard focus is visible and sheet focus returns to Filters;
- skeleton, empty, and error states render without layout breakage.

If credentials are not available, record visual smoke exactly as `NOT_VERIFIED`, not PASS.

- [ ] **Step 14: Restore/preserve canonical handoff state and write final authoritative checkpoint**

Merge preserved local handoff notes with the deployed Phase E checkpoint without discarding either history. Record:
- production build;
- automated gate results;
- API acceptance;
- visual acceptance PASS or `NOT_VERIFIED`;
- any remaining red flags;
- exact next product task.

Commit and push documentation if it changes the release branch only through a normal fast-forward; do not deploy a docs-only commit unless deployment tooling requires it.

- [ ] **Step 15: Final cleanliness check**

```bash
git status --short
git log -1 --oneline
```

Expected: feature/release working trees clean except any explicitly preserved, documented local handoff state.
