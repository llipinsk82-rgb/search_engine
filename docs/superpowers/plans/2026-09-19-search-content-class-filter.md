# Search Content Class Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add honest All/Amateur/Studio/Unknown filtering based only on explicit metadata, never title guesses.

**Architecture:** Add nullable/explicit `studio` plus normalized `content_class` to `SearchItem` and SQLite, centralize conservative classification from explicit tags/categories/studio metadata, add API/live/index filtering, and expose a compact frontend filter. Existing records default to `unknown` until refreshed or explicitly classifiable from their stored tags.

**Tech Stack:** Python 3.11, Pydantic, SQLite, FastAPI, vanilla JavaScript, pytest/unittest.

**Spec:** `docs/superpowers/specs/2026-09-19-search-ui-preview-sort-design.md`

## Global Constraints

- Metadata + Sorting v2 must be deployed first.
- Values are exactly `amateur`, `studio`, `unknown`.
- Never infer content class from title/free-form description.
- Explicit `studio` field wins only when it is truly supplied by the provider/source metadata.
- Explicit tags/categories may classify only through a small audited exact-token mapping; conflicting amateur/studio signals become `unknown`.
- Existing rows remain valid and default to `unknown`.
- Filter is not a ranking signal.
- Never deploy dirty; preserve provider/no-bypass/deploy rules.

## Review Focus

- Title contains “amateur” but tags/studio are empty: must remain `unknown`.
- Explicit amateur and studio signals both present: must return `unknown`, not arbitrarily choose.
- `studio` string present with no tags: classify `studio` and preserve the studio label.
- Existing DB row predating migration: reads as `unknown`, not null/error.
- API `content_class=unknown` must select only unknown rows; empty/null means all rows.

---

### Task 1: Conservative content-class classifier

**Files:**
- Create: `backend/content_class.py`
- Create: `tests/test_content_class.py`

**Interfaces:**
- Produces: `ContentClass = Literal["amateur", "studio", "unknown"]` and `classify_content(*, tags: list[str], studio: str | None) -> ContentClass`.

- [ ] **Step 1: Write failing classifier tests**

```python
from backend.content_class import classify_content


def test_explicit_amateur_tag():
    assert classify_content(tags=["Amateur"], studio=None) == "amateur"


def test_explicit_studio_label():
    assert classify_content(tags=[], studio="Example Studio") == "studio"


def test_title_is_not_an_input_and_unrelated_tags_stay_unknown():
    assert classify_content(tags=["stepmom", "hd"], studio=None) == "unknown"


def test_conflicting_signals_are_unknown():
    assert classify_content(tags=["amateur", "professional"], studio="Example Studio") == "unknown"
```

Token mapping starts conservatively with normalized exact metadata values: amateur side `amateur`, `homemade`, `user generated`, `user-generated`; studio side `studio`, `professional`, `production`. Do not substring-match longer labels.

- [ ] **Step 2: Run RED**

Expected: module missing.

- [ ] **Step 3: Implement exact-token classifier**

Normalize case/whitespace/hyphen only; compare whole normalized tokens. Studio label is one explicit studio signal. If both sides signal, return `unknown`.

- [ ] **Step 4: Verify**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_content_class.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/content_class.py tests/test_content_class.py
git commit -m "feat: add explicit content classifier"
```

### Task 2: Model and SQLite persistence

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/index.py`
- Modify: `tests/test_index_migrations.py`
- Create: `tests/test_content_class_roundtrip.py`

**Interfaces:**
- Extends `SearchItem` with `content_class: ContentClass = "unknown"`, `studio: str | None = None`.
- Adds SQLite columns `content_class TEXT NOT NULL DEFAULT 'unknown'`, `studio TEXT`.

- [ ] **Step 1: Write failing old-DB migration and round-trip tests**

Assert migration preserves an old row and returns `content_class == "unknown"`; new upsert/get/search retains explicit `amateur` and `studio` values.

- [ ] **Step 2: Run RED**

Expected: absent fields/columns.

- [ ] **Step 3: Implement additive columns and index**

Use existing migration loop. Add `idx_items_content_class` once under provider-state marker `migration:content_class_index_v1`. Extend upsert/select/get paths. Do not rewrite old rows beyond default `unknown`.

- [ ] **Step 4: Derive classification only at ingestion boundary when safe**

Before persistence, if an incoming item has `content_class="unknown"`, call `classify_content(tags=item.tags, studio=item.studio)`. Never inspect title. Preserve an explicit provider-supplied non-unknown class.

- [ ] **Step 5: Verify**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_content_class.py tests/test_index_migrations.py tests/test_content_class_roundtrip.py tests/test_index_sync.py`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/models.py backend/index.py backend/content_class.py tests/test_index_migrations.py tests/test_content_class_roundtrip.py tests/test_index_sync.py
git commit -m "feat: persist explicit content class"
```

### Task 3: Search/API/live filtering

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/index.py`
- Modify: `backend/search.py`
- Modify: `backend/live.py`
- Modify: `backend/app.py`
- Create: `tests/test_content_class_filter.py`

**Interfaces:**
- `SearchRequest.content_class: ContentClass | None`.
- `LiveRefreshRequest.content_class: ContentClass | None`.
- `search_items/search_all/count_search_items(..., content_class: str | None = None)`.

- [ ] **Step 1: Write failing filter tests**

Seed amateur/studio/unknown rows and assert `None` returns all while each explicit filter returns only that class. Add GET/POST/live request coverage and invalid value 422.

- [ ] **Step 2: Run RED**

Expected: arguments/fields absent.

- [ ] **Step 3: Implement index/search filter**

Add `i.content_class = ?` only when filter is not null. Count and search paths receive identical filter semantics.

- [ ] **Step 4: Implement API/live plumbing**

GET pattern accepts `amateur|studio|unknown`; POST Pydantic uses the literal. Live refresh filters each normalized provider result before merge/cache/render.

- [ ] **Step 5: Verify**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_content_class_filter.py tests/test_search_paging.py`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/models.py backend/index.py backend/search.py backend/live.py backend/app.py tests/test_content_class_filter.py
git commit -m "feat: filter results by content class"
```

### Task 4: Frontend content-class filter and studio display

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`
- Modify: `frontend/sw.js`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Produces `#content-class` options: empty/All, `amateur`, `studio`, `unknown`.
- Hash/search state key: `content_class`.

- [ ] **Step 1: Write failing frontend tests**

Assert selector/options exist; build/restore state carries `content_class`; both local and live payloads include it; studio label renders only when non-null; title text is never inspected for classification in JavaScript.

- [ ] **Step 2: Run RED**

Expected: missing selector/state.

- [ ] **Step 3: Implement filter/state**

Place Content type with the secondary filters. Empty means all. Persist explicit values in hash. Re-run search once on change.

- [ ] **Step 4: Render class/studio minimally**

Show `Amateur` or studio label as small secondary metadata only when explicit. For `unknown`, do not clutter every card with an “Unknown” badge; the filter can still select it.

- [ ] **Step 5: Bump assets to v26**

Update HTML app/styles references, SW registration and cache name.

- [ ] **Step 6: Verify**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_frontend_contract.py tests/test_deploy_assets.py`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html frontend/app.js frontend/styles.css frontend/sw.js tests/test_frontend_contract.py
git commit -m "feat: add amateur studio filtering"
```

### Task 5: Full verification and production acceptance

- [ ] **Step 1:** Run `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q && git diff --check`.
- [ ] **Step 2:** Push exact HEAD; helper CHECK; wait naturally for maintenance.
- [ ] **Step 3:** Official deploy; require `SEARCH_DEPLOY=PASS` and matching health build.
- [ ] **Step 4:** Refresh/cache a bounded set of providers with explicit tags; verify existing rows without signals remain `unknown`, explicit amateur tags classify only as amateur, and no title-only case is classified.
- [ ] **Step 5:** Query All/Amateur/Studio/Unknown through API and UI; verify each result class and confirm Studio may legitimately be sparse until more providers expose explicit studio metadata.
- [ ] **Step 6:** Record coverage caveat, build SHA, backup path and acceptance in `docs/SEARCH_ENGINE_HANDOFF.md`; docs-only commit/push.
