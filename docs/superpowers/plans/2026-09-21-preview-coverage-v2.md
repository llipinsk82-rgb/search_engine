# Preview Coverage v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Increase the number of indexed result cards with real, policy-playable previews through audited extraction and bounded enrichment, without guessed URLs, full-video substitution, policy weakening, or mass crawling.

**Architecture:** Reuse the existing `SitemapProvider` canonical-page fetch path. A committed audit manifest is the only source of provider capability; extraction is explicit and provider-scoped, persistence changes only `preview_url`, and a dedicated bounded enrichment engine uses durable retry state under the existing maintenance lock. Existing live preview parsing and frontend playback remain unchanged unless a concrete regression is found.

**Tech Stack:** Python 3.11, FastAPI/Pydantic, SQLite/FTS5, urllib-based provider fetching, systemd timers/services, vanilla frontend.

**Spec:** `docs/superpowers/specs/2026-09-21-preview-coverage-v2-design.md`

## Global Constraints

- Never synthesize preview URLs from provider identity, item id, page URL, thumbnail URL, or guessed paths.
- Never use generic Schema.org `contentUrl`, `embedUrl`, first-MP4/WebM scraping, or arbitrary `<video src>` as preview evidence.
- Only providers with a `PLAYBACK_CONFIRMED` canonical-item-bound rule may have `preview_enrichment=True`.
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
3. **Ambiguous/full-video/related-card evidence:** `contentUrl`, `embedUrl`, generic `<video src>`, arbitrary MP4, and a valid preview attached to a different canonical URL must return no preview.
4. **Deadline reached after partial progress:** completed candidates remain committed; unstarted candidates remain eligible on the next run.
5. **Malformed/non-HTTPS canonical candidate:** do not fetch it; candidate selection excludes it without touching the item.
6. **Live-only audited provider:** enrichment must include it even though it is absent from `PROVIDERS`; duplicate names must still prefer the configured sitemap provider.

---

### Task 1: Provider preview evidence audit and machine-readable capability manifest

**Files:**
- Create: `docs/PREVIEW_COVERAGE_V2_PROVIDER_AUDIT.md`
- Create: `tests/fixtures/preview_audit_manifest.json`
- Create: `deploy/search-engine-preview-rules.json`
- Create one positive fixture per `PLAYBACK_CONFIRMED` provider under `tests/fixtures/preview_pages/`, named `${provider}-positive.html`
- Create one negative fixture per `PLAYBACK_CONFIRMED` provider under `tests/fixtures/preview_pages/`, named `${provider}-negative.html`
- Create: `tests/test_preview_provider_audit.py`
- No product-code changes in this task.

**Interfaces:**
- Consumes: configured sitemap providers (`PROVIDERS`), live adapters (`LIVE_ADAPTERS`), the read-only production set of active indexed providers missing preview, real canonical URLs, existing provider-safe fetch behavior, and current `backend/media_policy.py`.
- Produces: (1) a committed audit manifest with one unique row for every provider observed in that union, and (2) `deploy/search-engine-preview-rules.json`, an exact deterministic projection containing only `PLAYBACK_CONFIRMED` canonical-bound rules. Runtime code consumes only the deploy rule file.

Manifest schema:

```json
{
  "provider": "example",
  "status": "PLAYBACK_CONFIRMED",
  "source_kind": "sitemap|live|both|index-only",
  "sample_count": 3,
  "rule_kind": "linked_attribute|page_json|custom",
  "target_attribute": "href",
  "preview_attribute": "data-preview",
  "json_identity_field": null,
  "json_preview_field": null,
  "canonical_fixture_url": "https://example/video/1",
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
RULES = ROOT / "deploy" / "search-engine-preview-rules.json"

from backend.live import LIVE_ADAPTERS

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


def test_preview_audit_represents_configured_and_live_provider_universe_once():
    configured = {row["name"] for row in _rows(CATALOG)}
    live = {adapter.name for adapter in LIVE_ADAPTERS}
    audit = _rows(MANIFEST)
    names = [row["provider"] for row in audit]
    assert len(names) == len(set(names))
    assert configured | live <= set(names)
    assert {row["status"] for row in audit} <= _ALLOWED
    assert {row["source_kind"] for row in audit} <= {
        "sitemap", "live", "both", "index-only"
    }


def test_playback_confirmed_rows_have_reduced_fixture_and_policy_evidence():
    for row in _rows(MANIFEST):
        if row["status"] != "PLAYBACK_CONFIRMED":
            continue
        assert row["sample_count"] >= 1
        assert row["rule_kind"] in {"linked_attribute", "page_json", "custom", "live_search_exact"}
        assert row["preview_hosts"]
        assert row["playback_mode"] in {"direct", "proxy"}
        assert row["policy_host_suffixes"]
        assert (ROOT / row["fixture"]).is_file()
        assert (ROOT / row["negative_fixture"]).is_file()


def test_policy_blocked_rows_do_not_claim_playback():
    for row in _rows(MANIFEST):
        if row["status"] == "BLOCKED_BY_POLICY":
            assert row.get("playback_mode") in {None, "disabled"}

def test_runtime_rule_file_is_exact_confirmed_projection():
    audit = _rows(MANIFEST)
    expected = [
        {k: v for k, v in row.items() if k not in {
            "status", "sample_count", "source_kind", "fixture", "negative_fixture"
        }}
        for row in audit if row["status"] == "PLAYBACK_CONFIRMED"
    ]
    assert _rows(RULES) == expected
```

- [ ] **Step 2: Run the audit test and verify RED**

Run:

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_preview_provider_audit.py
```

Expected: FAIL because the manifest does not exist.

- [ ] **Step 3: Perform the bounded read-only audit**

For every active indexed provider with rows missing preview (including configured sitemap providers, live adapters such as Tube8, overlaps, and index-only names):

1. record `source_kind` and whether a safe canonical fetcher exists;
2. select at most 3 active canonical URLs from the production index read-only;
3. fetch only those canonical pages using the existing provider-safe fetch path; if no safe canonical fetcher exists, mark `FETCH_UNAVAILABLE`;
4. inspect only explicit preview/trailer attributes or provider fields;
5. prove that the candidate belongs to the exact canonical URL. A related/recommended-card preview whose link normalizes to another URL is a required negative fixture;
6. reduce positive markup to a deterministic fixture and reduce full-video/related-card ambiguity fixtures;
7. if an extracted URL exists, verify HTTPS host and current policy;
8. for direct mode, issue a bounded request (`Range: bytes=0-1023` when supported) and require HTTP 200/206 plus a video-compatible Content-Type or provider-proven media response;
9. for proxy mode, exercise the existing bounded proxy fetch path with the same range;
10. record the status/evidence in `docs/PREVIEW_COVERAGE_V2_PROVIDER_AUDIT.md` and the full JSON audit manifest;
11. write `deploy/search-engine-preview-rules.json` as the deterministic projection of only `PLAYBACK_CONFIRMED` rows, excluding audit-only fields exactly as pinned by the test.

Do not write to production DB. Do not add provider configuration in this task.

- [ ] **Step 4: Run manifest validation**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_preview_provider_audit.py
```

Expected: PASS.

- [ ] **Step 5: Commit audit evidence**

```bash
git add docs/PREVIEW_COVERAGE_V2_PROVIDER_AUDIT.md \
  tests/fixtures/preview_audit_manifest.json deploy/search-engine-preview-rules.json \
  tests/fixtures/preview_pages \
  tests/test_preview_provider_audit.py
git commit -m "docs: audit preview provider evidence"
```

---

### Task 2: Central canonical-bound preview rules across sitemap and live providers

**Files:**
- Create: `backend/preview_rules.py`
- Create: `backend/preview_providers.py`
- Modify: `backend/providers/sitemap.py`
- Modify: `backend/live.py`
- Modify: `tests/test_sitemap_crawl.py`
- Create: `tests/test_preview_rules.py`
- Create: `tests/test_preview_provider_map.py`

**Interfaces:**
- Consumes: Task 1 full audit manifest, `deploy/search-engine-preview-rules.json`, and reduced positive/negative fixtures.
- Produces:
  - `PreviewRule` and `PREVIEW_RULES`, containing only `PLAYBACK_CONFIRMED` providers;
  - `extract_preview_url(rule, html, page_url) -> str | None` for canonical-page rules;
  - `select_exact_live_preview(items, canonical_url) -> str | None` for `live_search_exact`, which accepts only a returned card whose normalized URL equals the indexed canonical URL;
  - `preview_enrichment` and `async extract_preview(item)` on `SitemapProvider` and `_HttpLiveAdapter`, derived from `PREVIEW_RULES`;
  - `preview_provider_map(PROVIDERS, LIVE_ADAPTERS)` with configured sitemap providers winning duplicate names;
  - ordinary page-fetch paths that never persist a policy-rejected preview;
  - `_merge_enriched_item()` that fills a missing preview without replacing an existing one.

- [ ] **Step 1: Add failing manifest-to-rule contract tests**

Create `tests/test_preview_rules.py`:

```python
import json
from pathlib import Path

from backend.preview_rules import PREVIEW_RULES, extract_preview_url, select_exact_live_preview

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "preview_audit_manifest.json"


def _confirmed():
    return {
        row["provider"]: row
        for row in json.loads(MANIFEST.read_text())
        if row["status"] == "PLAYBACK_CONFIRMED"
    }


def test_rule_registry_exactly_matches_confirmed_manifest():
    confirmed = _confirmed()
    assert set(PREVIEW_RULES) == set(confirmed)
    for name, rule in PREVIEW_RULES.items():
        row = confirmed[name]
        assert rule.kind == row["rule_kind"]
        assert rule.preview_host_suffixes == tuple(row["policy_host_suffixes"])


def test_confirmed_page_fixtures_bind_to_exact_item():
    for name, row in _confirmed().items():
        if row["rule_kind"] == "live_search_exact":
            continue
        html = (ROOT / row["fixture"]).read_text()
        preview = extract_preview_url(
            PREVIEW_RULES[name], html, row["canonical_fixture_url"]
        )
        assert preview is not None
        assert preview.startswith("https://")


def test_live_search_fixtures_require_exact_canonical_match():
    for name, row in _confirmed().items():
        if row["rule_kind"] != "live_search_exact":
            continue
        positive = json.loads((ROOT / row["fixture"]).read_text())
        negative = json.loads((ROOT / row["negative_fixture"]).read_text())
        assert select_exact_live_preview(
            [positive["result"]], positive["canonical_url"]
        ) == positive["result"]["preview_url"]
        assert select_exact_live_preview(
            [negative["result"]], negative["canonical_url"]
        ) is None
```

- [ ] **Step 2: Add failing ambiguity tests**

```python
def test_full_video_and_unbound_preview_are_not_evidence():
    html = """
      <script type="application/ld+json">
      {"@type":"VideoObject",
       "url":"https://example/video/1",
       "contentUrl":"https://cdn.example/full.mp4",
       "embedUrl":"https://example/embed/1"}
      </script>
      <a href="https://example/video/2"
         data-preview="https://cdn.example/other-preview.mp4">other</a>
    """
    for rule in PREVIEW_RULES.values():
        assert extract_preview_url(
            rule, html, "https://example/video/1"
        ) is None
```

No implementation may fall back to first-MP4, first-preview-attribute, `contentUrl`, or `embedUrl`.

- [ ] **Step 3: Add failing provider-map tests**

Create `tests/test_preview_provider_map.py`:

```python
from backend.preview_providers import preview_provider_map


class Fake:
    def __init__(self, name, enabled):
        self.name = name
        self.preview_enrichment = enabled

    async def extract_preview(self, item):
        return None


def test_live_only_provider_can_be_eligible():
    live = Fake("tube8", True)
    assert preview_provider_map([], [live]) == {"tube8": live}


def test_configured_provider_wins_duplicate_name():
    index = Fake("xnxx", True)
    live = Fake("xnxx", True)
    assert preview_provider_map([index], [live])["xnxx"] is index


def test_disabled_provider_is_not_eligible():
    assert preview_provider_map([Fake("x", False)], []) == {}
```

- [ ] **Step 4: Add failing real capability tests**

Use the committed Task 1 manifest as the oracle:
- every real `SitemapProvider` or `_HttpLiveAdapter` whose name is in `PREVIEW_RULES` reports `preview_enrichment is True`;
- providers absent from `PREVIEW_RULES` report false;
- if Tube8 is not `PLAYBACK_CONFIRMED`, `Tube8LiveAdapter.preview_enrichment` remains false even though its search listing parser already knows `data-mediabook`.

- [ ] **Step 5: Add failing merge and policy-boundary tests**

In `tests/test_sitemap_crawl.py` assert:
- missing base preview can be filled from an allowed fetched preview;
- existing base preview is preserved byte-for-byte;
- if extraction yields a candidate rejected by `media_url_allowed()`, ordinary `_fetch_page_item()` returns a `SearchItem` with `preview_url is None`.

- [ ] **Step 6: Run the Task 2 tests and verify RED**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_preview_provider_audit.py \
  tests/test_preview_rules.py \
  tests/test_preview_provider_map.py \
  tests/test_sitemap_crawl.py \
  tests/test_media_policy.py
```

Expected: FAIL because the shared audited rule registry/provider map do not exist.

- [ ] **Step 7: Implement `backend/preview_rules.py`**

Define:

```python
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

RuleKind = Literal["linked_attribute", "page_json", "custom", "live_search_exact"]


@dataclass(frozen=True)
class PreviewRule:
    provider: str
    kind: RuleKind
    preview_host_suffixes: tuple[str, ...]
    target_attribute: str | None = None
    preview_attribute: str | None = None
    json_identity_field: str | None = None
    json_preview_field: str | None = None


RULE_FILE = Path(__file__).resolve().parents[1] / "deploy" / "search-engine-preview-rules.json"


def _load_rules() -> dict[str, PreviewRule]:
    rows = json.loads(RULE_FILE.read_text())
    return {
        row["provider"]: PreviewRule(
            provider=row["provider"],
            kind=row["rule_kind"],
            preview_host_suffixes=tuple(row["policy_host_suffixes"]),
            target_attribute=row.get("target_attribute"),
            preview_attribute=row.get("preview_attribute"),
            json_identity_field=row.get("json_identity_field"),
            json_preview_field=row.get("json_preview_field"),
        )
        for row in rows
    }


PREVIEW_RULES = _load_rules()
```

Rules are loaded only from the committed deploy rule file. Tests require that file to be the exact `PLAYBACK_CONFIRMED` projection of the audit manifest and that the loaded registry matches it field-for-field.

URL normalization must:
- resolve relative targets against `page_url`;
- require HTTPS item targets;
- lowercase scheme/host;
- drop fragments;
- normalize a trailing slash consistently;
- preserve meaningful query strings unless the Task 1 audit explicitly proves a provider-specific tracking normalization.

For `linked_attribute`, inspect only the audited element/block, capture both target item URL and preview URL, and return preview only when normalized target equals normalized `page_url`.

For `page_json`, require audited identity and preview fields in the same JSON object and require identity to normalize to `page_url`.

For `live_search_exact`, do not parse arbitrary HTML in `preview_rules.py`. `select_exact_live_preview()` receives returned items from the provider's existing live adapter and returns a preview only when one returned item URL normalizes exactly to the indexed canonical URL.

`custom` is permitted only when Task 1 committed a provider-specific positive fixture plus related-card-negative fixture and the generic strategies cannot model the source safely.

Never return the first preview-looking attribute globally.

- [ ] **Step 8: Expose rule-derived capability on sitemap and live fetchers**

`SitemapProvider` and `_HttpLiveAdapter` expose:

```python
@property
def preview_enrichment(self) -> bool:
    return self.name in PREVIEW_RULES
```

Both expose:

```python
async def extract_preview(self, item: SearchItem) -> str | None:
    ...
```

For `SitemapProvider`, canonical-page rules use the existing provider-safe page fetch. For `_HttpLiveAdapter` with `live_search_exact`, call the existing `search(item.title, page=1, limit=40)` and pass its returned items through `select_exact_live_preview()`; never accept a preview from a non-matching URL.

If a provider has neither a safe canonical-page rule nor an audited exact live-search rule, Task 1 leaves it out of `PREVIEW_RULES`; the engine never calls it.

For `SitemapProvider._fetch_page_item()`, when a rule exists, extract the candidate but attach it to the returned `SearchItem` only when:

```python
media_url_allowed(self.name, "preview", candidate)
```

is true. This prevents ordinary sync/core/content-enrichment paths from persisting policy-blocked previews.

Extend `_merge_enriched_item()` with:

```python
"preview_url": base.preview_url or fetched.preview_url,
```

- [ ] **Step 9: Implement `preview_provider_map()`**

Create `backend/preview_providers.py`:

```python
def preview_provider_map(index_providers, live_adapters):
    eligible = {
        adapter.name: adapter
        for adapter in live_adapters
        if getattr(adapter, "preview_enrichment", False)
        and callable(getattr(adapter, "extract_preview", None))
    }
    eligible.update({
        provider.name: provider
        for provider in index_providers
        if getattr(provider, "preview_enrichment", False)
        and callable(getattr(provider, "extract_preview", None))
    })
    return eligible
```

The second update intentionally gives configured index/sitemap providers precedence over duplicate live names.

- [ ] **Step 10: Run Task 2 suites**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_preview_provider_audit.py \
  tests/test_preview_rules.py \
  tests/test_preview_provider_map.py \
  tests/test_sitemap_crawl.py \
  tests/test_media_policy.py
```

Expected: PASS.

- [ ] **Step 11: Commit audited cross-provider extraction**

```bash
git add backend/preview_rules.py backend/preview_providers.py \
  backend/providers/sitemap.py backend/live.py \
  tests/test_preview_rules.py tests/test_preview_provider_map.py \
  tests/test_sitemap_crawl.py tests/test_preview_provider_audit.py
git commit -m "feat: add audited canonical preview rules"
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
- Consume: `backend/preview_providers.py`
- Consume: `backend/live.py::LIVE_ADAPTERS`
- Create: `tests/test_preview_enrichment.py`
- Modify: `tests/test_content_enrichment.py`
- Modify: `tests/test_content_class_cli.py`

**Interfaces:**
- Consumes:
  - `preview_provider_map(PROVIDERS, LIVE_ADAPTERS)`, which returns only audited providers with `preview_enrichment=True` and callable `extract_preview()`;
  - Task 3 candidate/state/update helpers;
  - `media_url_allowed()`.
- Produces:
  - `PreviewEnrichmentReport`
  - `async enrich_missing_previews(index_providers, live_adapters, *, batch_size, max_seconds, path=DB_PATH, now=None) -> PreviewEnrichmentReport`
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

1. build the eligible map with `preview_provider_map(index_providers, live_adapters)`; this deduplicates names and prefers the configured sitemap provider over a live adapter with the same name;
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

`enrich-previews` runs `asyncio.run(enrich_missing_previews(PROVIDERS, LIVE_ADAPTERS, ...))` and prints the deterministic report line. Add a CLI contract test that patches distinct index/live provider lists and asserts both are forwarded unchanged to `enrich_missing_previews()`; live-only inclusion itself is pinned by `preview_provider_map()` tests.

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
- Consumes: ordinary backfill, Content Classification enrichment, `enrich_missing_previews()`, `PROVIDERS`, and `LIVE_ADAPTERS`.
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
- preview enrichment receives both `PROVIDERS` and `LIVE_ADAPTERS`, so live-only audited providers are not silently omitted;
- duplicate provider names are resolved by `preview_provider_map()` rather than by scheduler-specific logic;
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
        LIVE_ADAPTERS,
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

## Execution ruling addendum — TTL discovery and resolver rollout (2026-09-21)

During Task 7 production acceptance, a real stale-token failure invalidated the original assumption that every `PLAYBACK_CONFIRMED` URL could be persisted.

Observed evidence:
- a newly resolved Tube8 preview returned bounded HTTP 206 `video/mp4`;
- an older Tube8 URL with expired `validto` returned HTTP 472;
- old non-signed previews for BigFuck, DrTuber, HQPorn, SpankBang and XHamster still returned bounded HTTP 206;
- Thumbzilla, TNAFlix, Tube8 and YouJizz URLs carry signed/expiring parameters.

Execution was corrected before allowing further mass persistence:

1. Added `storage_mode` to committed audit/runtime rules.
2. Limited `preview_enrichment=True` to stable providers only.
3. Prevented ordinary sitemap page-fetch from attaching ephemeral preview URLs.
4. Added read-only `/api/preview/{item_id}` fresh resolution for audited rules.
5. Exposed frontend `on_demand` only for ephemeral providers.
6. Bumped frontend/PWA shell to v29 and reset the failed-preview session key.
7. Corrected `preview-coverage-stats` so ephemeral stored URLs are not counted as persistently playable.

Final execution semantics:
- stable persistence: BigFuck, DrTuber, HQPorn, SpankBang, XHamster;
- ephemeral on-demand: Thumbzilla, TNAFlix, Tube8, YouJizz;
- policy-disabled remains unchanged: PornHat, PornDr, AnyPorn.

Production E2E acceptance:
- Tube8 fresh direct resolver: HTTP 206 `video/mp4`, 1024-byte bounded probe, DB unchanged;
- Thumbzilla fresh resolver through strict proxy: HTTP 206 `video/mp4`, bounded, DB unchanged;
- TNAFlix direct resolver: PASS after one transient upstream timeout and retry;
- YouJizz direct resolver: PASS;
- two natural stable-only scheduler runs succeeded with zero item failures before final resolver closeout.

The original rollout acceptance item "stored/playable growth for a sparse provider" is superseded for ephemeral providers by "fresh on-demand playback succeeds without persisting the signed URL". Stable providers retain the original stored-growth criterion.
