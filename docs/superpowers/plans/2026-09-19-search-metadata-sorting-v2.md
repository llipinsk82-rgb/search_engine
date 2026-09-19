# Search Metadata and Sorting v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add honest Newest/Most viewed/Best rated/Longest/Shortest sorting backed by nullable real metadata, with missing values always after known values.

**Architecture:** Extend `SearchItem` and SQLite additively, enrich RedTube first because its existing public JSON API exposes `publish_date`, `views`, `rating`, and `ratings`, add explicit SQL/in-memory sort helpers, then surface one sort selector through GET/POST/live-refresh and frontend hash state. Existing rows/providers remain valid with null metadata.

**Tech Stack:** Python 3.11, Pydantic, SQLite/FTS5, FastAPI, vanilla JavaScript, pytest/unittest.

**Spec:** `docs/superpowers/specs/2026-09-19-search-ui-preview-sort-design.md`

## Global Constraints

- Media Reliability and Cards/UI v2 should be deployed first.
- Sort modes are exactly: `relevance`, `newest`, `views`, `rating`, `longest`, `shortest`.
- No fabricated dates, views, ratings, or vote counts.
- Missing metadata sorts after known metadata for every non-relevance sort.
- `rating_percent` is normalized to 0–100 only when the source scale is known.
- Live sorting is exact only within the fetched live result pool; UI must not claim global remote-catalog ordering.
- Existing FTS relevance behavior remains the default.
- SQLite migration is additive; no destructive table rebuild.
- Never deploy dirty; use official helper CHECK/maintenance/deploy/acceptance workflow.

## Review Focus

- Mixed known/null metadata: null rows must remain last for both ascending and descending sorts.
- Equal sort values: result order must be stable/deterministic through existing relevance/indexed/source tie-breakers.
- Invalid `sort` query/body value: API must reject it through Pydantic/FastAPI validation rather than silently default.
- RedTube rating string/number variations and malformed metadata: parser must return `None`, not crash or synthesize.
- Pagination under non-relevance sort: offset/limit must preserve global SQL order and not re-rank only the current page.

---

### Task 1: Extend the result model with optional sort metadata

**Files:**
- Modify: `backend/models.py`
- Create: `tests/test_metadata_model.py`

**Interfaces:**
- Produces: `SortMode = Literal["relevance", "newest", "views", "rating", "longest", "shortest"]`.
- Extends `SearchItem` with `published_at: datetime | None`, `views: int | None`, `rating_percent: float | None`, `rating_count: int | None`.
- Extends `SearchRequest` and `LiveRefreshRequest` with `sort: SortMode = "relevance"`.

- [ ] **Step 1: Write failing model tests**

```python
from datetime import datetime, timezone
from backend.models import SearchItem, SearchRequest


def test_sort_metadata_is_optional_and_validated():
    item = SearchItem(
        id="x", provider="demo", title="X", url="https://example.com/x",
        published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        views=123, rating_percent=98.5, rating_count=42,
    )
    assert item.views == 123
    assert SearchRequest(sort="views").sort == "views"
```

Also test negative `views/rating_count` and rating outside 0–100 are rejected with `Field(ge=0)` / `Field(ge=0, le=100)`. Pin accepted rating boundaries `0.0` and `100.0` so normalization limits cannot drift.

- [ ] **Step 2: Run RED**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_metadata_model.py`

Expected: missing fields/SortMode failure.

- [ ] **Step 3: Implement minimal Pydantic fields/types**

Use timezone-aware `datetime | None`, nonnegative integer fields, and `rating_percent` 0–100. Do not add content-class fields in this phase.

- [ ] **Step 4: Verify model tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/models.py tests/test_metadata_model.py
git commit -m "feat: add sortable result metadata"
```

### Task 2: Add SQLite columns, round-trip, and indexes

**Files:**
- Modify: `backend/index.py`
- Modify: `tests/test_index_migrations.py`
- Modify: `tests/test_index_sync.py`
- Create: `tests/test_metadata_roundtrip.py`

**Interfaces:**
- Consumes: Task 1 `SearchItem` fields.
- Produces columns: `published_at TEXT`, `views INTEGER`, `rating_percent REAL`, `rating_count INTEGER`.

- [ ] **Step 1: Write failing migration/round-trip tests**

Create an old-format DB without the new columns, call `initialize(db)`, and assert all four columns appear while existing row data remains. Upsert a `SearchItem` with all fields, call `get_item()` and `search_items()`, and assert exact values round-trip.

- [ ] **Step 2: Run RED**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_index_migrations.py tests/test_metadata_roundtrip.py`

Expected: FAIL on absent columns/select/upsert fields.

- [ ] **Step 3: Implement additive migration and persistence**

Add columns through the existing `PRAGMA table_info` + `ALTER TABLE` loop. Store UTC ISO-8601 text for `published_at`; parse with `datetime.fromisoformat()` on reads. Extend upsert/select/get paths. Add indexes once behind provider-state marker `migration:metadata_sort_indexes_v1`: `idx_items_published_at`, `idx_items_views`, `idx_items_rating_percent`.

- [ ] **Step 4: Verify migration idempotency and snapshot behavior**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_index_migrations.py tests/test_metadata_roundtrip.py tests/test_index_sync.py`

Expected: PASS; existing FTS/snapshot tests unchanged.

- [ ] **Step 5: Commit**

```bash
git add backend/index.py tests/test_index_migrations.py tests/test_index_sync.py tests/test_metadata_roundtrip.py
git commit -m "feat: persist sortable metadata"
```

### Task 3: Enrich RedTube from its existing public JSON API

**Files:**
- Modify: `backend/live.py`
- Modify: `tests/test_redtube_live_parser.py`

**Interfaces:**
- Consumes RedTube public fields already observed on 2026-09-19: `publish_date`, `views`, `rating`, `ratings`.
- Produces `SearchItem.published_at/views/rating_percent/rating_count` for RedTube.

- [ ] **Step 1: Extend RedTube parser fixture and write failing assertions**

Use fixture values:

```python
"publish_date": "2026-02-18 15:45:44",
"views": 787499,
"rating": "98.008",
"ratings": 251,
```

Assert UTC `2026-02-18T15:45:44+00:00`, views `787499`, rating approximately `98.008`, rating_count `251`. Add malformed variants (`"views": "n/a"`, rating `None`) and assert fields become `None` without parser failure.

- [ ] **Step 2: Run RED**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_redtube_live_parser.py`

Expected: new metadata assertions fail.

- [ ] **Step 3: Implement minimal explicit parsing**

Parse `publish_date` with `%Y-%m-%d %H:%M:%S` and attach UTC. Convert numeric view/rating/count fields only when conversion succeeds and values are in model bounds. Do not infer any missing value.

- [ ] **Step 4: Run parser and real one-item gate**

Run targeted tests, then a read-only live RedTube query and print the four fields. Expected: tests PASS and real item has explicit metadata when upstream supplies it.

- [ ] **Step 5: Commit**

```bash
git add backend/live.py tests/test_redtube_live_parser.py
git commit -m "feat: ingest redtube sort metadata"
```

### Task 4: Implement deterministic SQL sort modes

**Files:**
- Modify: `backend/index.py`
- Modify: `backend/search.py`
- Modify: `tests/test_search_ranking.py`
- Create: `tests/test_search_sorting.py`

**Interfaces:**
- Produces: `search_items(..., sort: SortMode = "relevance")` and `search_all(..., sort: SortMode = "relevance")`.

- [ ] **Step 1: Write failing sort-order tests**

Seed rows with known and null values. Pin exact ordering:

```python
assert ids(search_items("", sort="newest")) == ["newer", "older", "missing"]
assert ids(search_items("", sort="views")) == ["1000", "10", "missing"]
assert ids(search_items("", sort="rating")) == ["99_many", "99_few", "80", "missing"]
assert ids(search_items("", sort="longest")) == ["long", "short", "missing"]
assert ids(search_items("", sort="shortest")) == ["short", "long", "missing"]
```

Add a text-query test proving `relevance` still ranks title match above tag-only match.

- [ ] **Step 2: Run RED**

Expected: `sort` argument missing.

- [ ] **Step 3: Implement SQL ORDER BY mapping**

Use exact rules:
- relevance with tokens: `fts_rank ASC, i.indexed_at DESC, i.source_order ASC`;
- relevance empty: `i.indexed_at DESC, i.source_order ASC`;
- newest: `(i.published_at IS NULL) ASC, i.published_at DESC, i.indexed_at DESC, i.source_order ASC`;
- views: `(i.views IS NULL) ASC, i.views DESC, i.indexed_at DESC, i.source_order ASC`;
- rating: `(i.rating_percent IS NULL) ASC, i.rating_percent DESC, (i.rating_count IS NULL) ASC, i.rating_count DESC, i.indexed_at DESC, i.source_order ASC`;
- longest: `(i.duration_seconds IS NULL) ASC, i.duration_seconds DESC, i.indexed_at DESC, i.source_order ASC`;
- shortest: `(i.duration_seconds IS NULL) ASC, i.duration_seconds ASC, i.indexed_at DESC, i.source_order ASC`.

Count query remains sort-independent.

- [ ] **Step 4: Verify ranking and paging**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_search_ranking.py tests/test_search_sorting.py tests/test_search_paging.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/index.py backend/search.py tests/test_search_ranking.py tests/test_search_sorting.py tests/test_search_paging.py
git commit -m "feat: add indexed result sorting"
```

### Task 5: Add API and live-batch sort semantics

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/live.py`
- Create: `tests/test_search_api_sort.py`
- Create: `tests/test_live_sorting.py`

**Interfaces:**
- GET/POST `/api/search` accept `sort`.
- POST `/api/live-refresh` accepts `sort` and sorts the fetched merged batch only.
- Produces `sort_live_items(items: list[SearchItem], sort: SortMode) -> list[SearchItem]` or equivalent stable helper.

- [ ] **Step 1: Write failing API/live tests**

Assert GET and POST pass `sort="views"` to `_search_response/search_all`; invalid sort gets FastAPI/Pydantic 422. For live fixtures, assert known values before nulls while preserving input order among equal/missing values.

- [ ] **Step 2: Run RED**

Expected: API signatures/helper absent.

- [ ] **Step 3: Implement API plumbing**

Add `sort` query parameter pattern/enum to GET, pass payload sort from POST, and propagate through `_search_response()` into `search_all()`.

- [ ] **Step 4: Implement stable live-batch sort**

For `relevance`, preserve current provider round-robin order. For other modes, sort only `fresh_items` after merge, using stable Python keys with a leading missing flag so null is last. Do not claim unseen remote pages are globally sorted.

- [ ] **Step 5: Verify API/live tests**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_search_api_sort.py tests/test_live_sorting.py`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app.py backend/live.py tests/test_search_api_sort.py tests/test_live_sorting.py
git commit -m "feat: expose result sort modes"
```

### Task 6: Frontend sort selector, state, and metadata display

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`
- Modify: `frontend/sw.js`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Produces selector `#sort` values `relevance/newest/views/rating/longest/shortest`.
- Search/hash state adds `sort` only when not default.

- [ ] **Step 1: Write failing frontend tests**

Assert `#sort` exists with six exact values; `buildSearchParams`, restoreState, local search payload, and live payload all carry sort; card metadata renders views/rating/date only when present.

- [ ] **Step 2: Run RED**

Expected: missing selector/state/rendering.

- [ ] **Step 3: Implement selector/state**

Place Sort before secondary filters. Default `relevance`. Persist non-default sort in hash. Filter-change listener includes sort and re-runs one search exactly once.

- [ ] **Step 4: Render optional metadata honestly**

Add compact metadata spans: formatted date when `published_at`, localized integer views when `views`, rating like `98%` and optionally `(251)` when rating/count exist. Do not show placeholders such as `0 views` for null.

- [ ] **Step 5: Bump assets to v25**

Update HTML references, SW registration, and cache name.

- [ ] **Step 6: Verify frontend tests**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_frontend_contract.py tests/test_deploy_assets.py`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html frontend/app.js frontend/styles.css frontend/sw.js tests/test_frontend_contract.py
git commit -m "feat: add search sorting controls"
```

### Task 7: Full verification and production acceptance

- [ ] **Step 1:** Run `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q && git diff --check`.
- [ ] **Step 2:** Push exact HEAD; helper CHECK; wait for maintenance naturally.
- [ ] **Step 3:** Deploy officially and require `SEARCH_DEPLOY=PASS` plus matching health build.
- [ ] **Step 4:** Production cache at least a bounded RedTube batch through normal live-refresh; verify RedTube rows expose date/views/rating without manual DB edits.
- [ ] **Step 5:** For each sort mode, query a bounded provider/result set containing known and null metadata and verify missing-last semantics. Confirm relevance default remains unchanged and pagination keeps order.
- [ ] **Step 6:** Record SHA, backup, RedTube metadata sample and six sort acceptance results in `docs/SEARCH_ENGINE_HANDOFF.md`; docs-only commit/push.
