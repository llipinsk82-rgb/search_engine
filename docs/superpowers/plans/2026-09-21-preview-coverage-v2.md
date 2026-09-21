# Preview Coverage v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Increase the number of indexed result cards with real, policy-playable previews through audited extraction and bounded enrichment, without guessed URLs, full-video substitution, policy weakening, or mass crawling.

**Architecture:** Reuse the existing `SitemapProvider` canonical-page fetch path. A committed audit manifest is the only source of provider capability; extraction is explicit and provider-scoped, persistence changes only `preview_url`, and a dedicated bounded enrichment engine uses durable retry state under the existing maintenance lock. Existing live preview parsing and frontend playback remain unchanged unless a concrete regression is found.

**Tech Stack:** Python 3.11, FastAPI/Pydantic, SQLite/FTS5, urllib-based provider fetching, systemd timers/services, vanilla frontend.

**Spec:** `docs/superpowers/specs/2026-09-21-preview-coverage-v2-design.md`

## Global Constraints

- Never synthesize preview URLs from provider identity, item id, page URL, thumbnail URL, or guessed paths.
- Never use generic Schema.org `contentUrl`, `embedUrl`, first-MP4/WebM scraping, or arbitrary `<video src>` as preview evidence.
- Only `PLAYBACK_CONFIRMED` providers may have `preview_enrichment=True`.
- Every newly persisted preview must satisfy `media_url_allowed(provider, "preview", url)`.
- Existing non-empty preview URLs are never replaced in v2.
- `pornhat`, `porndr`, and `anyporn` remain policy-disabled unless the audit independently proves a safe delivery mode.
- Preview updates must not change title, canonical URL, thumbnail, tags, studio, content class/source, age-check state, source order, FTS, or provider cursors.
- No public API or frontend contract change.
- No unbounded crawl or parallel DB writer.
- Preview enrichment must run inside the existing `/run/search_engine/maintenance.lock`.
- TDD is required for every behavior change.
- Full test runs use `SHELL=/bin/bash` because the `blackserv` account uses nologin.
- Production changes use the official deploy helper only; never edit `/opt/search_engine` directly.

## Review Focus

1. **Existing preview already present:** extraction/enrichment must preserve it byte-for-byte and must not overwrite it with a newer candidate.
2. **Extracted URL fails media policy:** do not store it; record `blocked_policy` with a 30-day retry time.
3. **Ambiguous/full-video field:** `contentUrl`, `embedUrl`, generic `<video src>`, and an arbitrary MP4 string must return no preview.
4. **Deadline reached after partial progress:** completed candidates remain committed; unstarted candidates remain eligible on the next run.
5. **Malformed/non-HTTPS canonical candidate:** do not fetch it; candidate selection excludes it without touching the item.

---

### Task 1: Provider preview evidence audit and machine-readable capability manifest

**Files:**
- Create: `docs/PREVIEW_COVERAGE_V2_PROVIDER_AUDIT.md`
- Create: `tests/fixtures/preview_audit_manifest.json`
- Create one positive fixture per `PLAYBACK_CONFIRMED` provider under `tests/fixtures/preview_pages/`, named `${provider}-positive.html`
- Create one negative fixture per `PLAYBACK_CONFIRMED` provider under `tests/fixtures/preview_pages/`, named `${provider}-negative.html`
- Create: `tests/test_preview_provider_audit.py`
- No product-code changes in this task.

**Interfaces:**
- Consumes: all rows from `deploy/search-engine-providers.example.json`, real canonical URLs from the current read-only production index, existing provider-safe fetch behavior, and current `backend/media_policy.py`.
- Produces: a committed manifest with one row for every configured sitemap provider. Later tasks consume only manifest rows whose `status == "PLAYBACK_CONFIRMED"`.

Manifest schema:

```json
{
  "provider": "example",
  "status": "PLAYBACK_CONFIRMED",
  "sample_count": 3,
  "attribute_names": ["data-preview"],
  "json_fields": [],
  "preview_hosts": ["cdn.example"],
  "media_type": "video/mp4",
  "playback_mode": "direct",
  "policy_host_suffixes": [".example"],
  "fixture": "tests/fixtures/preview_pages/example-positive.html",
  "negative_fixture": "tests/fixtures/preview_pages/example-negative.html"
}
```

Allowed `status` values:

```text
PLAYBACK_CONFIRMED
EXTRACT_CONFIRMED
NO_SIGNAL
AMBIGUOUS
BLOCKED_BY_POLICY
FETCH_UNAVAILABLE
```

- [ ] **Step 1: Add the manifest validation test first**

Create `tests/test_preview_provider_audit.py`:

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "deploy" / "search-engine-providers.example.json"
MANIFEST = ROOT / "tests" / "fixtures" / "preview_audit_manifest.json"

_ALLOWED = {
    "PLAYBACK_CONFIRMED",
    "EXTRACT_CONFIRMED",
    "NO_SIGNAL",
    "AMBIGUOUS",
    "BLOCKED_BY_POLICY",
    "FETCH_UNAVAILABLE",
}


def _rows(path: Path):
    return json.loads(path.read_text())


def test_preview_audit_represents_every_configured_sitemap_provider_once():
    configured = {row["name"] for row in _rows(CATALOG)}
    audit = _rows(MANIFEST)
    names = [row["provider"] for row in audit]
    assert len(names) == len(set(names))
    assert set(names) == configured
    assert {row["status"] for row in audit} <= _ALLOWED


def test_playback_confirmed_rows_have_reduced_fixture_and_policy_evidence():
    for row in _rows(MANIFEST):
        if row["status"] != "PLAYBACK_CONFIRMED":
            continue
        assert row["sample_count"] >= 1
        assert row["attribute_names"] or row["json_fields"]
        assert row["preview_hosts"]
        assert row["playback_mode"] in {"direct", "proxy"}
        assert row["policy_host_suffixes"]
        assert (ROOT / row["fixture"]).is_file()
        assert (ROOT / row["negative_fixture"]).is_file()


def test_policy_blocked_rows_do_not_claim_playback():
    for row in _rows(MANIFEST):
        if row["status"] == "BLOCKED_BY_POLICY":
            assert row.get("playback_mode") in {None, "disabled"}
```

- [ ] **Step 2: Run the audit test and verify RED**

Run:

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_preview_provider_audit.py
```

Expected: FAIL because the manifest does not exist.

- [ ] **Step 3: Perform the bounded read-only audit**

For each configured sitemap provider:

1. select at most 3 active canonical URLs from the production index read-only;
2. fetch only those canonical pages using the existing provider User-Agent/robots behavior;
3. inspect only explicit preview/trailer attributes or provider fields;
4. reduce positive markup to a deterministic fixture containing only the relevant element/field;
5. reduce an ambiguity/negative case when the page exposes full-video or unrelated media fields;
6. if an extracted URL exists, verify HTTPS host and current policy;
7. for direct mode, issue a bounded request (`Range: bytes=0-1023` when supported) and require HTTP 200/206 plus a video-compatible Content-Type or provider-proven media response;
8. for proxy mode, exercise the existing bounded proxy fetch path with the same range;
9. record the status and evidence in `docs/PREVIEW_COVERAGE_V2_PROVIDER_AUDIT.md` and the JSON manifest.

Do not write to production DB. Do not add provider configuration in this task.

- [ ] **Step 4: Run manifest validation**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_preview_provider_audit.py
```

Expected: PASS.

- [ ] **Step 5: Commit audit evidence**

```bash
git add docs/PREVIEW_COVERAGE_V2_PROVIDER_AUDIT.md \
  tests/fixtures/preview_audit_manifest.json \
  tests/fixtures/preview_pages \
  tests/test_preview_provider_audit.py
git commit -m "docs: audit preview provider evidence"
```

---

### Task 2: Audited provider capability, explicit extraction, and non-destructive merge

**Files:**
- Create: `backend/preview_extraction.py`
- Modify: `backend/providers/sitemap.py`
- Modify: `backend/providers/__init__.py`
- Modify: `deploy/search-engine-providers.example.json`
- Modify: `tests/test_provider_registry.py`
- Modify: `tests/test_sitemap_crawl.py`
- Create: `tests/test_preview_extraction.py`

**Interfaces:**
- Consumes: Task 1 manifest and reduced fixtures.
- Produces:
  - `extract_preview_url(html: str, page_url: str, *, attribute_names: tuple[str, ...], json_fields: tuple[str, ...]) -> str | None`
  - `SitemapProvider.preview_enrichment: bool`
  - `SitemapProvider.preview_attribute_names: tuple[str, ...]`
  - `SitemapProvider.preview_json_fields: tuple[str, ...]`
  - `async SitemapProvider.extract_preview(item: SearchItem) -> str | None`
  - `_fetch_page_item()` that strips any extracted preview rejected by media policy before returning a `SearchItem`
  - `_merge_enriched_item()` that preserves an existing preview and fills a missing policy-allowed preview from fetched evidence.

- [ ] **Step 1: Add failing capability tests**

Append to `tests/test_provider_registry.py`:

```python
def test_preview_enrichment_defaults_off(monkeypatch):
    rows = [{"name": "example", "sitemap_url": "https://example.com/sitemap.xml"}]
    monkeypatch.setenv("SEARCH_SITEMAP_PROVIDERS_JSON", json.dumps(rows))
    monkeypatch.setenv("SEARCH_PROVIDER_CONFIG_FILE", "")
    provider = build_providers()[0]
    assert provider.preview_enrichment is False


def test_preview_enrichment_can_be_enabled_explicitly(monkeypatch):
    rows = [{
        "name": "example",
        "sitemap_url": "https://example.com/sitemap.xml",
        "preview_enrichment": True,
    }]
    monkeypatch.setenv("SEARCH_SITEMAP_PROVIDERS_JSON", json.dumps(rows))
    monkeypatch.setenv("SEARCH_PROVIDER_CONFIG_FILE", "")
    provider = build_providers()[0]
    assert provider.preview_enrichment is True
```

Add a production-catalog contract test to `tests/test_preview_provider_audit.py`:

```python
def test_production_preview_capabilities_equal_playback_confirmed_audit():
    audit = _rows(MANIFEST)
    configured = _rows(CATALOG)
    expected = {
        row["provider"]: (
            tuple(row["attribute_names"]),
            tuple(row["json_fields"]),
        )
        for row in audit
        if row["status"] == "PLAYBACK_CONFIRMED"
    }
    enabled = {
        row["name"]: (
            tuple(row.get("preview_attribute_names", [])),
            tuple(row.get("preview_json_fields", [])),
        )
        for row in configured
        if row.get("preview_enrichment") is True
    }
    assert enabled == expected
```

- [ ] **Step 2: Add failing extraction tests from the audit fixtures**

Create `tests/test_preview_extraction.py`:

```python
import json
from pathlib import Path

from backend.preview_extraction import extract_preview_url

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "preview_audit_manifest.json"


def _audit():
    return json.loads(MANIFEST.read_text())


def test_every_playback_confirmed_fixture_extracts_exact_audited_preview():
    for row in _audit():
        if row["status"] != "PLAYBACK_CONFIRMED":
            continue
        html = (ROOT / row["fixture"]).read_text()
        preview = extract_preview_url(
            html,
            f"https://{row['provider']}.invalid/video/1",
            attribute_names=tuple(row["attribute_names"]),
            json_fields=tuple(row["json_fields"]),
        )
        assert preview is not None
        assert preview.startswith("https://")


def test_negative_fixtures_do_not_extract_preview():
    for row in _audit():
        path = row.get("negative_fixture")
        if not path:
            continue
        html = (ROOT / path).read_text()
        assert extract_preview_url(
            html,
            f"https://{row['provider']}.invalid/video/1",
            attribute_names=tuple(row["attribute_names"]),
            json_fields=tuple(row["json_fields"]),
        ) is None


def test_generic_full_video_fields_are_not_preview_evidence():
    html = """
      <script type="application/ld+json">
      {"@type":"VideoObject",
       "contentUrl":"https://cdn.example/full.mp4",
       "embedUrl":"https://example/embed/1"}
      </script>
      <video src="https://cdn.example/arbitrary.mp4"></video>
    """
    assert extract_preview_url(
        html,
        "https://example/video/1",
        attribute_names=(),
        json_fields=(),
    ) is None
```

The extraction implementation must use only exact attribute/field names recorded in the Task 1 manifest. It must not search arbitrary media URLs.

- [ ] **Step 3: Add failing merge tests**

In `tests/test_sitemap_crawl.py` add:

```python
def test_merge_fills_missing_preview_without_replacing_existing_preview():
    base = SearchItem(
        id="1", provider="example", title="X",
        url="https://example/video/1",
        preview_url=None,
    )
    fetched = base.model_copy(
        update={"preview_url": "https://cdn.example/new.mp4"}
    )
    merged = SitemapProvider._merge_enriched_item(base, fetched)
    assert str(merged.preview_url) == "https://cdn.example/new.mp4"

    existing = base.model_copy(
        update={"preview_url": "https://cdn.example/original.mp4"}
    )
    merged_existing = SitemapProvider._merge_enriched_item(existing, fetched)
    assert str(merged_existing.preview_url) == "https://cdn.example/original.mp4"
```

Add a page-fetch policy test:

```python
def test_page_fetch_strips_preview_rejected_by_media_policy(monkeypatch):
    provider = SitemapProvider(
        name="example",
        sitemap_url="https://example.com/sitemap.xml",
        obey_robots=False,
        preview_attribute_names=("data-preview",),
    )
    monkeypatch.setattr(
        provider,
        "_fetch_text",
        lambda _url: (
            '<meta property="og:title" content="X">'
            '<meta property="og:image" content="https://example.com/x.jpg">'
            '<div data-preview="https://evil.example/preview.mp4"></div>'
        ),
    )
    monkeypatch.setattr(
        "backend.providers.sitemap.media_url_allowed",
        lambda *_args: False,
    )
    fetched = provider._fetch_page_item("https://example.com/video/1")
    assert fetched is not None
    assert fetched.preview_url is None
```

- [ ] **Step 4: Run tests and verify RED**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_preview_provider_audit.py \
  tests/test_provider_registry.py \
  tests/test_preview_extraction.py \
  tests/test_sitemap_crawl.py
```

Expected: FAIL because capability/extraction/merge support is absent.

- [ ] **Step 5: Implement `backend/preview_extraction.py`**

The extractor receives only the exact rule names supplied by the audited provider configuration; it has no provider-name fallback and no broad media scan.

```python
from __future__ import annotations

import html
import json
import re
from urllib.parse import urljoin


def _attribute_url(source: str, name: str) -> str | None:
    pattern = re.compile(
        rf"\b{re.escape(name)}\s*=\s*[\"'](?P<url>[^\"']+)[\"']",
        re.IGNORECASE,
    )
    match = pattern.search(source)
    return html.unescape(match.group("url")).strip() if match else None


def _json_field_url(source: str, field_names: tuple[str, ...]) -> str | None:
    if not field_names:
        return None
    script_re = re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    for raw in script_re.findall(source):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        stack = payload if isinstance(payload, list) else [payload]
        for obj in stack:
            if not isinstance(obj, dict):
                continue
            for field in field_names:
                value = obj.get(field)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return None


def extract_preview_url(
    html_source: str,
    page_url: str,
    *,
    attribute_names: tuple[str, ...],
    json_fields: tuple[str, ...],
) -> str | None:
    values = [
        *(
            value
            for name in attribute_names
            if (value := _attribute_url(html_source, name))
        ),
        _json_field_url(html_source, json_fields),
    ]
    for value in values:
        if not value:
            continue
        resolved = urljoin(page_url, value)
        if resolved.startswith("https://"):
            return resolved
    return None
```

The caller supplies only Task 1 audited names. Therefore `contentUrl`, `embedUrl`, arbitrary `<video src>`, and unlisted JSON keys are invisible to this function.

- [ ] **Step 6: Wire provider capability and extraction**

In `SitemapProvider.__init__()` add:

```python
preview_enrichment: bool = False
preview_attribute_names: tuple[str, ...] = ()
preview_json_fields: tuple[str, ...] = ()

self.preview_enrichment = bool(preview_enrichment)
self.preview_attribute_names = tuple(preview_attribute_names)
self.preview_json_fields = tuple(preview_json_fields)
```

Pass from `backend/providers/__init__.py`:

```python
preview_enrichment=bool(row.get("preview_enrichment", False)),
preview_attribute_names=tuple(row.get("preview_attribute_names", [])),
preview_json_fields=tuple(row.get("preview_json_fields", [])),
```

Extend `parse_video_metadata()` with keyword-only `preview_attribute_names` and `preview_json_fields`, call:

```python
preview_url = extract_preview_url(
    html,
    page_url,
    attribute_names=preview_attribute_names,
    json_fields=preview_json_fields,
)
```

and pass the raw explicit candidate as `preview_url` to `SearchItem`.

In `SitemapProvider._fetch_page_item()`, pass `self.preview_attribute_names` and `self.preview_json_fields` into `parse_video_metadata()`. Before returning the parsed item, enforce the storage invariant:

```python
if (
    parsed is not None
    and parsed.preview_url is not None
    and not media_url_allowed(self.name, "preview", str(parsed.preview_url))
):
    parsed = parsed.model_copy(update={"preview_url": None})
```

Thus ordinary sync/core/content page-fetch paths can only persist policy-playable previews.

In `_merge_enriched_item()` add:

```python
"preview_url": base.preview_url or fetched.preview_url,
```

Add a raw preview-only fetch path for the dedicated enrichment engine so it can distinguish `blocked_policy` from `no_preview`:

```python
def _extract_preview_sync(self, page_url: str) -> str | None:
    try:
        html_source = self._fetch_text(page_url)
        return extract_preview_url(
            html_source,
            page_url,
            attribute_names=self.preview_attribute_names,
            json_fields=self.preview_json_fields,
        )
    finally:
        if self.delay_seconds:
            time.sleep(self.delay_seconds)


async def extract_preview(self, item: SearchItem) -> str | None:
    return await asyncio.to_thread(self._extract_preview_sync, str(item.url))
```

- [ ] **Step 7: Enable only audited production providers**

In `deploy/search-engine-providers.example.json`, for every Task 1 row whose status is exactly `PLAYBACK_CONFIRMED`:
- set `preview_enrichment` to `true`;
- set `preview_attribute_names` to the exact `attribute_names` array from that manifest row;
- set `preview_json_fields` to the exact `json_fields` array from that manifest row.

The catalog-contract test compares these values byte-for-byte with the committed manifest, so execution cannot invent or broaden a rule. Providers with any other audit status have no `preview_enrichment: true` flag.

- [ ] **Step 8: Run extraction/capability suites**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_preview_provider_audit.py \
  tests/test_provider_registry.py \
  tests/test_preview_extraction.py \
  tests/test_sitemap_crawl.py \
  tests/test_media_policy.py
```

Expected: PASS.

- [ ] **Step 9: Commit audited extraction**

```bash
git add backend/preview_extraction.py backend/providers/sitemap.py \
  backend/providers/__init__.py deploy/search-engine-providers.example.json \
  tests/test_provider_registry.py tests/test_sitemap_crawl.py \
  tests/test_preview_extraction.py tests/test_preview_provider_audit.py
git commit -m "feat: extract audited preview metadata"
```

---

### Task 3: Preview-only persistence, retry state, candidate selection, and coverage stats

**Files:**
- Modify: `backend/index.py`
- Create: `backend/preview_stats.py`
- Modify: `tests/test_index_migrations.py`
- Create: `tests/test_preview_update.py`
- Create: `tests/test_preview_candidates.py`
- Create: `tests/test_preview_stats.py`

**Interfaces:**
- Consumes: `media_url_allowed()` and the current `items.preview_url`.
- Produces:
  - table `preview_enrichment_state`
  - `PreviewEnrichmentCandidate(item: SearchItem, failure_count: int)`
  - `update_preview_url(item_id: str, *, preview_url: str, path: Path = DB_PATH) -> bool`
  - `record_preview_enrichment_attempt(...)`
  - `list_preview_enrichment_candidates(provider_names, *, limit, now, path=DB_PATH)`
  - `preview_coverage_stats(path=DB_PATH) -> PreviewCoverageStats`.

- [ ] **Step 1: Add failing additive migration test**

Extend `tests/test_index_migrations.py`:

```python
def test_preview_enrichment_state_schema_is_additive(tmp_path):
    db = tmp_path / "preview.db"
    index._initialized_paths.discard(str(db.resolve()))
    index.initialize(db)
    with sqlite3.connect(db) as conn:
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(preview_enrichment_state)"
            )
        }
        assert columns == {
            "item_id", "provider", "status", "failure_count",
            "last_attempt_at", "next_attempt_at",
        }
        pk = [
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(preview_enrichment_state)"
            )
            if row[5] == 1
        ]
        assert pk == ["item_id"]
```

- [ ] **Step 2: Add failing preview-only update safety test**

Create `tests/test_preview_update.py` with a full item, snapshot all non-preview columns plus FTS and provider state, call:

```python
changed = update_preview_url(
    item.id,
    preview_url="https://cdn.example/preview.mp4",
    path=db,
)
```

Assert:
- first call returns `True`;
- same call again returns `False`;
- an existing different preview is not replaced;
- only `preview_url` changes in the item row;
- `indexed_at`, FTS, content class/source, source order, age state, tags, studio, thumbnail, title and URL remain unchanged.

Also assert empty/non-HTTPS input raises `ValueError`, and an HTTPS URL rejected by `media_url_allowed(stored_provider, "preview", url)` raises `ValueError` without changing the row.

- [ ] **Step 3: Add failing candidate-selection tests**

Create `tests/test_preview_candidates.py`:

- active row without preview + audited provider + HTTPS URL => included;
- existing preview => excluded;
- inactive row => excluded;
- HTTP canonical URL => excluded;
- provider outside the supplied set => excluded;
- future `next_attempt_at` => excluded;
- same candidate becomes eligible once deterministic `now` reaches the retry time.

- [ ] **Step 4: Add failing coverage reconciliation test**

Create `tests/test_preview_stats.py` with:
- one policy-playable stored preview,
- one stored preview rejected by policy,
- two rows without preview.

Assert:

```python
stats.total == 4
stats.stored == 2
stats.playable == 1
stats.stored_percent == 50.0
stats.playable_percent == 25.0
```

and per-provider counts reconcile to total.

- [ ] **Step 5: Run DB/stats tests and verify RED**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_index_migrations.py \
  tests/test_preview_update.py \
  tests/test_preview_candidates.py \
  tests/test_preview_stats.py
```

Expected: FAIL because preview enrichment persistence/state/stats are absent.

- [ ] **Step 6: Implement additive state schema**

In `initialize()` create:

```sql
CREATE TABLE IF NOT EXISTS preview_enrichment_state (
    item_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    failure_count INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT NOT NULL,
    next_attempt_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_preview_enrichment_next_attempt
ON preview_enrichment_state(next_attempt_at);
```

Follow the existing migration-marker pattern so large production startup does not contend repeatedly on index creation.

- [ ] **Step 7: Implement narrow preview update**

```python
def update_preview_url(
    item_id: str,
    *,
    preview_url: str,
    path: Path = DB_PATH,
) -> bool:
```

Rules:
- trim the URL;
- require `https://`;
- select the active row including its stored provider;
- return `False` when row is missing or already has any non-empty preview;
- require `media_url_allowed(row["provider"], "preview", preview_url)` before any write;
- raise `ValueError` on a rejected candidate so policy cannot be bypassed by a future caller;
- update only `preview_url`;
- do not modify `indexed_at` or FTS.

- [ ] **Step 8: Implement retry/candidate helpers**

Use the same timezone-aware ISO format as Content Classification v2.

Candidate SQL:

```sql
SELECT i.id, COALESCE(s.failure_count, 0) AS failure_count
FROM items i
LEFT JOIN preview_enrichment_state s ON s.item_id = i.id
WHERE i.active = 1
  AND (i.preview_url IS NULL OR i.preview_url = '')
  AND i.url LIKE 'https://%'
  AND i.provider IN (...)
  AND (s.next_attempt_at IS NULL OR s.next_attempt_at <= ?)
ORDER BY i.id
LIMIT ?
```

- [ ] **Step 9: Implement coverage stats**

In `backend/preview_stats.py` define:

```python
@dataclass
class ProviderPreviewStats:
    total: int
    stored: int
    playable: int


@dataclass
class PreviewCoverageStats:
    total: int
    stored: int
    playable: int
    stored_percent: float
    playable_percent: float
    providers: dict[str, ProviderPreviewStats]
    states: dict[str, int]
```

Count totals/stored in SQL. For rows with stored preview, compute `playable` through `media_url_allowed(provider, "preview", url)`; the current preview population is small enough for this read-only validation path.

- [ ] **Step 10: Run DB/stats suites**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_index_migrations.py \
  tests/test_preview_update.py \
  tests/test_preview_candidates.py \
  tests/test_preview_stats.py \
  tests/test_preview_metadata.py
```

Expected: PASS.

- [ ] **Step 11: Commit preview persistence/state**

```bash
git add backend/index.py backend/preview_stats.py \
  tests/test_index_migrations.py tests/test_preview_update.py \
  tests/test_preview_candidates.py tests/test_preview_stats.py
git commit -m "feat: persist bounded preview enrichment state"
```

---

### Task 4: Bounded preview enrichment engine and reuse of existing page fetches

**Files:**
- Create: `backend/preview_enrichment.py`
- Modify: `backend/content_enrichment.py`
- Modify: `backend/cli.py`
- Create: `tests/test_preview_enrichment.py`
- Modify: `tests/test_content_enrichment.py`
- Modify: `tests/test_content_class_cli.py`

**Interfaces:**
- Consumes:
  - providers with `preview_enrichment=True` and callable `extract_preview()`;
  - Task 3 candidate/state/update helpers;
  - `media_url_allowed()`.
- Produces:
  - `PreviewEnrichmentReport`
  - `async enrich_missing_previews(providers, *, batch_size, max_seconds, path=DB_PATH, now=None) -> PreviewEnrichmentReport`
  - CLI `enrich-previews`
  - CLI `preview-coverage-stats`
  - opportunistic persistence of a policy-playable preview already returned by Content Classification page enrichment, without a second page request.

- [ ] **Step 1: Add failing preview-engine tests**

Create `tests/test_preview_enrichment.py` covering:

```text
explicit preview + allowed policy -> stored + success
explicit preview + rejected policy -> not stored + blocked_policy
no preview -> no_preview + 30d
fetch exception -> failure + exponential backoff
provider capability false -> never called
existing preview -> never selected/overwritten
deadline reached -> unstarted candidate remains eligible
one failure does not abort later candidates
```

Use a deterministic timezone-aware `now`.

Retry policy:
- failure 1: +6h
- failure n: `6h * 2**(n-1)`, capped at 7d
- no_preview: +30d
- blocked_policy: +30d
- success: no next retry.

- [ ] **Step 2: Add failing opportunistic-reuse test**

In `tests/test_content_enrichment.py`, use a fake provider with both:
- `content_class_enrichment=True`
- `preview_enrichment=True`

and one canonical fetch that returns improved content evidence plus a preview URL.

Assert:
- provider page enrichment is called exactly once;
- content evidence is updated;
- if policy allows the preview, `preview_url` is persisted by the same run;
- no preview-specific second fetch occurs.

This pins the spec requirement that existing page fetches are reused rather than duplicated.

- [ ] **Step 3: Add failing CLI test**

In `tests/test_content_class_cli.py`, patch `enrich_missing_previews()` and run:

```text
search-engine enrich-previews --batch-size 10 --max-seconds 30
```

Assert exact arguments and one summary line containing:

```text
preview-enrichment: attempted=... extracted=... stored=... playable=... no_preview=... blocked_policy=... failures=...
```

Add a second CLI test for:

```text
search-engine preview-coverage-stats
```

Patch `preview_coverage_stats()` and assert output includes total/stored/playable percentages plus provider/state summaries.

- [ ] **Step 4: Run tests and verify RED**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_preview_enrichment.py \
  tests/test_content_enrichment.py \
  tests/test_content_class_cli.py
```

Expected: FAIL because the preview engine/CLI/reuse path do not exist.

- [ ] **Step 5: Implement `PreviewEnrichmentReport` and backoff**

```python
@dataclass
class PreviewEnrichmentReport:
    attempted: int = 0
    extracted: int = 0
    stored: int = 0
    playable: int = 0
    no_preview: int = 0
    blocked_policy: int = 0
    failures: int = 0
```

Use the same `_failure_delay()` formula as content enrichment.

- [ ] **Step 6: Implement sequential bounded preview enrichment**

Algorithm:

1. build eligible map from providers with `preview_enrichment=True` and callable `extract_preview`;
2. list at most `batch_size` eligible candidates;
3. stop before starting a request once monotonic deadline is reached;
4. call `await provider.extract_preview(item)`;
5. if it returns no URL, record `no_preview` +30d;
6. increment `extracted` when an explicit candidate URL exists;
7. validate `media_url_allowed(item.provider, "preview", url)`;
8. if rejected, record `blocked_policy` +30d and do not write;
9. if allowed, call `update_preview_url`;
10. on write success increment `stored` and `playable`;
11. record success with no next retry;
12. on one exception, record failure/backoff and continue.

- [ ] **Step 7: Reuse content-enrichment fetch results**

After `provider.enrich_content_evidence(item)` returns in `backend/content_enrichment.py`, before classification persistence:

```python
preview = str(fetched.preview_url) if fetched.preview_url else None
if (
    preview
    and getattr(provider, "preview_enrichment", False)
    and media_url_allowed(item.provider, "preview", preview)
):
    update_preview_url(item.id, preview_url=preview, path=path)
```

Do not mark preview retry state from this opportunistic path; successful stored previews are naturally excluded. A rejected preview remains for the dedicated preview engine to classify as `blocked_policy`.

- [ ] **Step 8: Add CLI commands**

`backend/cli.py`:

```text
enrich-previews
  --batch-size 10
  --max-seconds 30

preview-coverage-stats
```

`enrich-previews` runs `asyncio.run(enrich_missing_previews(PROVIDERS, ...))` and prints the deterministic report line.

`preview-coverage-stats` calls `preview_coverage_stats()` and prints:
- one global `total/stored/playable/stored_percent/playable_percent` line;
- one `states=` JSON line;
- one deterministic provider line per provider.

- [ ] **Step 9: Run enrichment/CLI suites**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_preview_enrichment.py \
  tests/test_content_enrichment.py \
  tests/test_content_class_cli.py \
  tests/test_preview_update.py \
  tests/test_media_policy.py
```

Expected: PASS.

- [ ] **Step 10: Commit bounded preview enrichment**

```bash
git add backend/preview_enrichment.py backend/content_enrichment.py backend/cli.py \
  tests/test_preview_enrichment.py tests/test_content_enrichment.py \
  tests/test_content_class_cli.py
git commit -m "feat: add bounded preview enrichment"
```

---

### Task 5: Media-policy acceptance and regression protection

**Files:**
- Modify only if Task 1 proves a new playable host/mode: `backend/media_policy.py`
- Modify: `tests/test_media_policy.py`
- Modify: `tests/test_provider_media_api.py`
- Existing provider live parser tests remain unchanged except for necessary regression assertions.

**Interfaces:**
- Consumes: exact `policy_host_suffixes` and `playback_mode` from Task 1 `PLAYBACK_CONFIRMED` rows.
- Produces: the minimal allowlist/mode changes required for newly enabled providers.

- [ ] **Step 1: Add failing policy tests from audit manifest**

Parameterize over Task 1 `PLAYBACK_CONFIRMED` rows and assert:
- exact audited HTTPS host is allowed;
- `evil.example` is rejected;
- `http://` equivalent is rejected;
- embedded credentials are rejected;
- port 8443 is rejected.

Also retain:

```python
for name in ("pornhat", "porndr", "anyporn"):
    assert provider_media_policy(name).preview_mode == "disabled"
```

unless Task 1 independently produced `PLAYBACK_CONFIRMED` for that provider. In that case the manifest, audit doc, positive range/playback evidence, and test must all change in the same commit.

- [ ] **Step 2: Run policy tests and verify RED only when policy expansion is required**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_media_policy.py \
  tests/test_provider_media_api.py \
  tests/test_preview_provider_audit.py
```

Expected:
- PASS immediately if every enabled provider is already covered;
- otherwise FAIL only for the exact newly audited host/mode.

- [ ] **Step 3: Apply the minimal policy delta**

For each newly confirmed provider:
- add only the exact suffix from the manifest;
- use `direct` only for audit rows with `playback_mode == "direct"`;
- use `proxy` only for audit rows with `playback_mode == "proxy"` and preserve referer requirements;
- do not add broad wildcard suffixes.

- [ ] **Step 4: Run policy and proxy suites**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_media_policy.py \
  tests/test_provider_media_api.py \
  tests/test_preview_proxy.py \
  tests/test_thumbnail_proxy.py
```

Expected: PASS.

- [ ] **Step 5: Commit media-policy delta**

If files changed:

```bash
git add backend/media_policy.py tests/test_media_policy.py tests/test_provider_media_api.py
git commit -m "feat: allow audited preview media hosts"
```

If no policy code changed, record `NO_POLICY_DELTA` in the execution ledger and do not create an empty commit.

---

### Task 6: Scheduler integration and production-safe defaults

**Files:**
- Modify: `backend/cli.py`
- Modify: `deploy/search-engine-backfill.service`
- Modify: `deploy/search-engine.env.example`
- Modify: `tests/test_deploy_units.py`
- Modify: `tests/test_backfill_enrichment_handoff.py`

**Interfaces:**
- Consumes: ordinary backfill, Content Classification enrichment, `enrich_missing_previews()`.
- Produces:
  - `backfill-all --enrich-preview-batch-size N --enrich-preview-seconds S`
  - systemd defaults `SEARCH_PREVIEW_ENRICH_BATCH_SIZE=10`
  - systemd defaults `SEARCH_PREVIEW_ENRICH_MAX_SECONDS=30`
  - one maintenance lock only.

- [ ] **Step 1: Add failing scheduler handoff tests**

Extend `tests/test_backfill_enrichment_handoff.py` to assert order:

```text
backfill_many
enrich_unknown_content
enrich_missing_previews
```

Cases:
- successful backfill + both budgets > 0 => both enrichers run once in order;
- backfill provider error => neither enrichment runs;
- content enrichment item failures do not suppress preview enrichment;
- preview enrichment item failures do not fail the unit;
- preview seconds 0 => preview enrichment skipped;
- preview batch 0 => preview enrichment skipped.

- [ ] **Step 2: Add failing deploy-unit contract**

In `tests/test_deploy_units.py` require both unit and env file contain:

```text
SEARCH_PREVIEW_ENRICH_BATCH_SIZE=10
SEARCH_PREVIEW_ENRICH_MAX_SECONDS=30
```

and `ExecStart` contains:

```text
--enrich-preview-batch-size "$SEARCH_PREVIEW_ENRICH_BATCH_SIZE"
--enrich-preview-seconds "$SEARCH_PREVIEW_ENRICH_MAX_SECONDS"
```

Also assert:

```python
assert unit.count("run-maintenance.sh /run/search_engine/maintenance.lock") == 1
assert "TimeoutStartSec=6min" in unit
```

The worst configured budget remains 180s backfill + 45s content enrichment + 30s preview enrichment = 255s, below 360s.

- [ ] **Step 3: Run scheduler tests and verify RED**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_backfill_enrichment_handoff.py \
  tests/test_deploy_units.py
```

Expected: FAIL because preview handoff/env flags are absent.

- [ ] **Step 4: Extend `_backfill_all()`**

Signature:

```python
async def _backfill_all(
    batch_size: int,
    batches_per_provider: int,
    max_seconds: float | None,
    *,
    enrich_unknown_batch_size: int = 0,
    enrich_unknown_seconds: float = 0.0,
    enrich_preview_batch_size: int = 0,
    enrich_preview_seconds: float = 0.0,
) -> None:
```

After successful content enrichment:

```python
if enrich_preview_seconds > 0 and enrich_preview_batch_size > 0:
    report = await enrich_missing_previews(
        PROVIDERS,
        batch_size=enrich_preview_batch_size,
        max_seconds=enrich_preview_seconds,
    )
```

Print the deterministic `preview-enrichment:` summary.

- [ ] **Step 5: Add CLI flags and systemd/env defaults**

Add `backfill-all` args:

```text
--enrich-preview-batch-size
--enrich-preview-seconds
```

Default CLI values are 0/0.0; systemd/env opt in with 10/30.

Append both flags to the existing single `run-maintenance.sh` invocation.

- [ ] **Step 6: Run full maintenance tests**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_backfill_enrichment_handoff.py \
  tests/test_deploy_units.py \
  tests/test_maintenance_runner.py \
  tests/test_backfill.py \
  tests/test_backfill_many.py \
  tests/test_backfill_deadline.py
```

Expected: PASS.

- [ ] **Step 7: Commit scheduler integration**

```bash
git add backend/cli.py deploy/search-engine-backfill.service \
  deploy/search-engine.env.example tests/test_deploy_units.py \
  tests/test_backfill_enrichment_handoff.py
git commit -m "feat: schedule bounded preview enrichment"
```

---

### Task 7: Integration gate, rollout, measurement, and authoritative handoff

**Files:**
- Modify: `docs/SEARCH_ENGINE_HANDOFF.md`
- No direct production edits.

**Interfaces:**
- Consumes: Tasks 1–6.
- Produces: verified release SHA, production preview schema/state, exact before/after stored/playable coverage, natural scheduler acceptance, and closeout handoff.

- [ ] **Step 1: Run targeted Preview Coverage v2 gate**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_preview_provider_audit.py \
  tests/test_preview_extraction.py \
  tests/test_provider_registry.py \
  tests/test_sitemap_crawl.py \
  tests/test_index_migrations.py \
  tests/test_preview_update.py \
  tests/test_preview_candidates.py \
  tests/test_preview_stats.py \
  tests/test_preview_enrichment.py \
  tests/test_media_policy.py \
  tests/test_preview_proxy.py \
  tests/test_provider_media_api.py \
  tests/test_backfill_enrichment_handoff.py \
  tests/test_deploy_units.py
```

Expected: PASS.

- [ ] **Step 2: Run complete verification gate**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q backend
node --check frontend/app.js
git diff --check
git status --short
```

Expected: all tests PASS; only previously documented deprecation warnings are acceptable; tree clean after commits.

- [ ] **Step 3: Capture read-only production baseline**

Record:
- production code build;
- active total;
- stored preview count/percentage;
- playable preview count/percentage using current policy;
- per-provider stored/playable coverage;
- preview state table absent before deploy;
- service/sync/backfill timer state.

Use the same stats implementation after deploy so before/after comparison uses identical definitions.

- [ ] **Step 4: Update pre-release handoff and commit docs**

Record exact feature SHA, enabled audited providers, test counts, policy delta, rollout sequence, and `PRODUCTION_UNCHANGED`.

```bash
git add docs/SEARCH_ENGINE_HANDOFF.md
git commit -m "docs: record preview coverage v2 gate"
```

- [ ] **Step 5: Push feature and fast-forward release**

Verify release ancestry and push without force using the repository deploy key/known-hosts override.

- [ ] **Step 6: Fast-forward canonical and run official helper CHECK**

Require canonical tree clean or preserve only the known handoff-only safety condition. Stop on unrelated app-code dirt.

Run:

```bash
/usr/local/bin/search-engine-deploy-client check
```

Expected: `SEARCH_DEPLOY_CHECK=PASS`.

- [ ] **Step 7: Deploy only in a natural free maintenance window**

Do not kill sync/backfill. After lock is free:

```bash
/usr/local/bin/search-engine-deploy-client deploy
```

If transport times out, do not retry blindly. Verify helper status, `/api/health`, deployed build and deployed source first.

- [ ] **Step 8: Verify schema/runtime before enrichment**

Confirm:
- health `status=ok`;
- production build equals release code SHA prefix;
- `preview_enrichment_state` exists;
- audited providers have exact capability flags;
- media policy rows match audit;
- service/timers active;
- existing search and preview-proxy smoke remain valid.

- [ ] **Step 9: Run stats and one tiny manual enrichment batch**

Under the maintenance lock:

```bash
SEARCH_DB_PATH=/var/lib/search_engine/search.db \
  /opt/search_engine/.venv/bin/python -m backend.cli preview-coverage-stats

SEARCH_DB_PATH=/var/lib/search_engine/search.db \
  /opt/search_engine/.venv/bin/python -m backend.cli enrich-previews \
  --batch-size 3 --max-seconds 20
```

Do not run a mass manual preview crawl.

- [ ] **Step 10: Manually verify newly stored previews**

For every provider changed by the tiny batch:
- confirm stored URL host matches audit/policy;
- confirm preview is not the canonical/full-video asset;
- confirm direct/proxy playback path returns bounded media successfully;
- confirm card/search fallback remains intact if preview fails.

If any provider fails this gate, disable only that provider capability before allowing scheduler enrichment.

- [ ] **Step 11: Observe two natural backfill+preview-enrichment runs**

Require journal evidence for two separate successful natural runs:
- one maintenance lock;
- ordinary backfill summary;
- content enrichment summary when enabled;
- preview enrichment summary;
- unit result success / exit 0;
- individual preview failures counted without failing the unit.

- [ ] **Step 12: Measure outcome**

Run `preview-coverage-stats` and record exact:
- active total;
- stored previews and percentage;
- playable previews and percentage;
- per-provider before/after;
- state counts (`success`, `no_preview`, `blocked_policy`, `failure`);
- natural run counters.

Acceptance requires measurable playable growth for at least one previously sparse indexed provider, not an arbitrary global percentage.

- [ ] **Step 13: Regression-check existing high-coverage providers**

Confirm no coverage/playback regression for:
`beeg`, `youjizz`, `tnaflix`, `thumbzilla`, `drtuber`, `xhamster`, `pornhub`, `hqporn`, `bigfuck`.

Confirm `pornhat`, `porndr`, `anyporn` remain disabled unless Task 1 independently proved and committed a safe policy change.

- [ ] **Step 14: Final handoff and docs-only closeout**

Update `docs/SEARCH_ENGINE_HANDOFF.md` with:
- deployed code SHA;
- audit-enabled providers;
- exact tests;
- schema/runtime verification;
- tiny batch result;
- two natural scheduler runs;
- before/after stored and playable coverage;
- provider-level gaps/cooldowns/failures;
- exact next product task.

Commit/push docs-only by normal fast-forward, but do not redeploy the later docs-only SHA.

- [ ] **Step 15: Final cleanliness gate**

```bash
git status --short
git log -1 --oneline
```

Require feature and canonical trees clean. Production should remain on the exact Preview Coverage v2 code build, not the later docs-only commit.
