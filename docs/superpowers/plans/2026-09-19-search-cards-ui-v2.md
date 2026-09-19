# Search Cards UI v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the existing dark search UI into a cleaner thumbnail-first premium layout without changing search semantics.

**Architecture:** Keep static HTML/CSS/JS and existing result rendering. Restructure only the visual hierarchy: compact sticky search/filter controls, clearer cards and badges, less operational noise, and preserved one-column mobile feed.

**Tech Stack:** HTML5, CSS, vanilla JavaScript, pytest source-contract tests, existing PWA service worker.

**Spec:** `docs/superpowers/specs/2026-09-19-search-ui-preview-sort-design.md`

## Global Constraints

- Phase A media reliability must be deployed/accepted first.
- No search API/schema change in this plan.
- Dark visual identity remains; this is refinement, not rebranding.
- Mobile remains one full-width 16:9 card per row.
- No hover-only functionality and no autoplay.
- Provider refresh/debug detail remains available but visually secondary.
- Existing load-more/prefetch behavior must not regress.
- Execute from a separate clean worktree; do not modify the preserved PornFlip sandbox changes.

## Review Focus

- 320–420 px mobile width: no horizontal card overflow; filters may scroll horizontally.
- Very long titles/providers: two-line title clamp and metadata wrapping must remain readable.
- Missing quality/duration/media metadata: no empty badge boxes or broken layout.
- Desktop 900–1180 px: grid transitions without excessively narrow cards.
- Status/provider-refresh strings: useful result count remains readable while implementation detail stays secondary.

---

### Task 1: Restructure search/header and card markup

**Files:**
- Modify: `frontend/index.html`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Produces: `.search-panel`, `.filter-strip`, `.result-summary`, `.media-badges`, `.card-meta-primary`, `.card-meta-secondary` hooks consumed by CSS/JS.

- [ ] **Step 1: Write failing markup-contract tests**

Assert the new semantic hooks exist, mobile card still contains `.thumb`, `.preview`, `.motion-preview`, `.quality`, `.duration`, `.preview-toggle`, and no sort selector exists yet in Phase B.

- [ ] **Step 2: Run RED**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_frontend_contract.py`

Expected: FAIL on missing new hooks.

- [ ] **Step 3: Update `index.html`**

Keep search input/button first. Place provider/quality/duration/age-check in a single `.filter-strip`. Split status into a primary result summary and secondary live/provider detail. Keep card media first, title second, then compact provider/age/alternates line. Do not add fields that the API does not yet supply.

- [ ] **Step 4: Verify markup tests**

Run the same test; expected PASS for HTML structure assertions.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html tests/test_frontend_contract.py
git commit -m "refactor: simplify search card markup"
```

### Task 2: Desktop visual hierarchy

**Files:**
- Modify: `frontend/styles.css`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: Task 1 markup hooks.
- Produces: responsive 4/3/2/1-column grid, sticky compact search panel, thumbnail-dominant card hierarchy.

- [ ] **Step 1: Add failing CSS contract assertions**

Pin 4-column wide grid, 3-column medium breakpoint, 2-column intermediate breakpoint, one-column mobile, 16:9 media, and muted secondary metadata. Assert no fixed card height that clips title/meta.

- [ ] **Step 2: Run RED**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_frontend_contract.py`

Expected: FAIL on new CSS rules.

- [ ] **Step 3: Implement desktop CSS**

Make the top search/filter block sticky beneath the topbar on desktop, reduce hero vertical space, preserve strong search input prominence, use subtle borders/background elevation, keep provider secondary, and retain duration bottom-right/quality bottom-left overlays.

- [ ] **Step 4: Verify tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/styles.css tests/test_frontend_contract.py
git commit -m "style: refine desktop result hierarchy"
```

### Task 3: Mobile feed and compact filter strip

**Files:**
- Modify: `frontend/styles.css`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: Task 1 markup.
- Produces: mandatory single-column mobile feed and horizontally scrollable compact filters.

- [ ] **Step 1: Extend failing mobile tests**

Assert the `max-width: 680px` section contains `grid-template-columns: 1fr`, full-width card/thumb, 16:9 media, two-line title clamp, horizontally scrollable filter strip, and no hover dependency.

- [ ] **Step 2: Run RED**

Run the frontend contract test; expected FAIL until the new strip hooks are styled.

- [ ] **Step 3: Implement mobile CSS**

Use minimal shell side padding, 44 px minimum search controls, one full-width card, large media, compact metadata line, scrollable filter chips/selects, and a 40 px preview button hit target.

- [ ] **Step 4: Verify**

Run frontend contract; expected PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/styles.css tests/test_frontend_contract.py
git commit -m "style: polish mobile result feed"
```

### Task 4: Reduce operational status noise

**Files:**
- Modify: `frontend/app.js`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Produces: primary result-count text and secondary live/provider refresh detail using existing API fields.

- [ ] **Step 1: Write failing source-contract assertions**

Assert status rendering writes separate primary and secondary nodes, and that provider detail is not concatenated into the main result count string.

- [ ] **Step 2: Run RED**

Expected: FAIL against the current single `statusEl` flow.

- [ ] **Step 3: Implement minimal split status rendering**

Keep current `liveSummary()` information but route it to the secondary element. Primary text should state search/loading/no-results/result-count state. Do not remove observability data.

- [ ] **Step 4: Verify prefetch/search-submit contracts**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_frontend_contract.py`

Expected: PASS including existing prefetch and single-submit tests.

- [ ] **Step 5: Bump assets to v24**

Update stylesheet/app/service-worker references and cache name from v23 to v24.

- [ ] **Step 6: Commit**

```bash
git add frontend/app.js frontend/index.html frontend/styles.css frontend/sw.js tests/test_frontend_contract.py
git commit -m "feat: ship cards ui v2"
```

### Task 5: Verification and release

- [ ] **Step 1:** Run `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q && git diff --check`.
- [ ] **Step 2:** Push exact HEAD; helper CHECK; wait naturally for maintenance lock.
- [ ] **Step 3:** Official deploy and require formal `SEARCH_DEPLOY=PASS` plus matching health build.
- [ ] **Step 4:** Production smoke at desktop and mobile widths: search, filters, one-column mobile, preview button, Show more/prefetch, missing metadata card, long title card.
- [ ] **Step 5:** Append acceptance/build/backup to `docs/SEARCH_ENGINE_HANDOFF.md`; docs-only commit/push.
