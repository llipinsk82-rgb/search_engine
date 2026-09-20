# Content Classification v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `Amateur / Studio / Unknown` reflect trusted metadata evidence across new and existing indexed rows, without title/provider/domain/image inference.

**Architecture:** Preserve the public enum/filter/API exactly as-is. Add an internal evidence/provenance classifier, extract only explicit trusted studio/production metadata, persist derived class provenance in SQLite, reclassify stored evidence offline, then run a bounded/resumable unknown-content enrichment pass inside the existing maintenance lock. Existing page-fetch behavior is reused; no parallel crawler or UI rewrite is introduced.

**Tech Stack:** Python 3.11, FastAPI/Pydantic, SQLite/FTS5, `urllib` + `xml.etree.ElementTree`, existing systemd maintenance runner, pytest/unittest.

**Spec:** `docs/superpowers/specs/2026-09-21-content-classification-v2-design.md`

## Global Constraints

- Keep public values exactly `amateur`, `studio`, `unknown`.
- No title/provider/domain/image inference.
- No substring matching.
- Missing evidence stays `unknown`.
- Amateur + studio evidence stays `unknown` as conflict.
- No direct production edits.
- All data work must be bounded, resumable, observable, and respect the existing maintenance lock.
- `publisher`, `creator`, `author`, site name, uploader/channel, performer/model name are not studio evidence.
- Preview Coverage, ML/image classification, title NLP, public enum changes, UI redesign, removing Unknown, and age-check classification are out of scope.
- `content_class` remains derived/recomputable; source tags/studio remain authoritative evidence.
- Reclassification must not modify URLs, titles, thumbnails, previews, age-check state, provider cursors, or FTS.
- Unknown-content enrichment may update tags/studio plus the derived class/source only, and must preserve unrelated row fields.

## File Structure

- Modify `backend/content_class.py` — internal evidence result and provenance-aware deterministic classifier.
- Modify `backend/providers/sitemap.py` — trusted `productionCompany` extraction and reusable page-evidence merge/fetch path.
- Modify `backend/providers/__init__.py` — explicit provider capability flag for content-class enrichment.
- Modify `backend/index.py` — additive provenance/enrichment-state migrations, evidence-safe DB helpers, stats helpers.
- Create `backend/content_reclassify.py` — bounded dry-run/apply reclassification engine.
- Create `backend/content_enrichment.py` — bounded unknown-content enrichment engine with retry/backoff.
- Modify `backend/cli.py` — `reclassify-content`, `content-class-stats`, `enrich-content`; scheduler handoff from `backfill-all`.
- Modify `deploy/search-engine-backfill.service` — invoke bounded enrichment after ordinary backfill inside the existing maintenance lock.
- Modify `deploy/search-engine.env.example` — enrichment budget defaults.
- Modify `deploy/search-engine-providers.example.json` — explicit `content_class_enrichment` only for providers verified by the audit.
- Create `docs/CONTENT_CLASSIFICATION_V2_PROVIDER_AUDIT.md` — evidence/capability audit from read-only probes.
- Modify tests under `tests/` listed per task.

## Review Focus

1. **Conflicting evidence** — an item with an amateur tag plus explicit studio label must stay `unknown/conflict`, including after DB reclassify and page enrichment.
2. **Untrusted JSON-LD identities** — `publisher`, `creator`, and `author` objects/strings must never populate `studio` or produce `studio` class.
3. **Idempotency and stale provenance** — changing stored tags/studio and rerunning reclassify must recompute both class and source; old source values must never survive changed evidence.
4. **Interrupted/bounded maintenance** — reclassify/enrichment must stop at batch/time bounds and be safe to rerun without skipping or duplicating state transitions.
5. **Evidence merge safety** — enrichment may add deduplicated tags or fill a missing explicit studio label, but must not replace an existing studio label, URL, title, thumbnail, preview, age-check state, or provider cursor.

---

### Task 1: Read-only provider evidence audit and explicit enrichment capability

**Files:**
- Create: `docs/CONTENT_CLASSIFICATION_V2_PROVIDER_AUDIT.md`
- Modify: `backend/providers/sitemap.py`
- Modify: `backend/providers/__init__.py`
- Modify: `deploy/search-engine-providers.example.json`
- Modify: `tests/test_provider_registry.py`
- Modify: `tests/test_provider_candidates.py`

**Interfaces:**
- Consumes: existing configured `SitemapProvider` catalog and current `_fetch_page_item()` / `parse_video_metadata()` behavior.
- Produces: `SitemapProvider.content_class_enrichment: bool`; configuration key `content_class_enrichment`; a committed audit naming exactly which providers may participate in unknown enrichment.

- [ ] **Step 1: Capture the current configured provider evidence surface read-only**

Run from the isolated worktree with the existing provider config available to the sandbox. For every configured sitemap provider, sample at most 3 current page URLs using its normal sitemap/page parser and record only observed explicit evidence:

```bash
SHELL=/bin/bash .venv/bin/python -m backend.cli providers
```

Use a temporary read-only probe script that prints, per provider:

```text
provider | source | sample_count | explicit_tags | productionCompany | page_fetch_ok | notes
```

The script must not write SQLite, provider state, config, or production. Inspect raw fields only when needed to prove a field is explicit. Record `none observed` instead of inferring from brand/site identity.

- [ ] **Step 2: Write the audit document from observed evidence**

Create `docs/CONTENT_CLASSIFICATION_V2_PROVIDER_AUDIT.md` with one row per configured sitemap provider and these columns:

```markdown
| Provider | Samples | Explicit amateur tag | Explicit studio tag | Explicit productionCompany/studio label | Page enrichment safe | Enabled for v2 enrichment |
```

Rules for `Enabled for v2 enrichment = yes`:
- page fetch succeeds through the provider's existing safe fetch path;
- at least one sample exposes explicit tags or a trusted production-company/studio field that the generic parser can consume;
- provider identity alone is never evidence.

- [ ] **Step 3: Add failing provider-capability tests**

In `tests/test_provider_registry.py`, add:

```python
def test_content_class_enrichment_defaults_off(monkeypatch):
    rows = [{"name": "example", "sitemap_url": "https://example.com/sitemap.xml"}]
    monkeypatch.setenv("SEARCH_SITEMAP_PROVIDERS_JSON", json.dumps(rows))
    provider = build_providers()[0]
    assert provider.content_class_enrichment is False


def test_content_class_enrichment_can_be_enabled_explicitly(monkeypatch):
    rows = [{
        "name": "example",
        "sitemap_url": "https://example.com/sitemap.xml",
        "content_class_enrichment": True,
    }]
    monkeypatch.setenv("SEARCH_SITEMAP_PROVIDERS_JSON", json.dumps(rows))
    provider = build_providers()[0]
    assert provider.content_class_enrichment is True
```

Also add a contract assertion in `tests/test_provider_candidates.py` for every provider marked `Enabled for v2 enrichment = yes` in the audit: its row in `deploy/search-engine-providers.example.json` must contain `"content_class_enrichment": true`.

- [ ] **Step 4: Run the capability tests and verify RED**

Run:

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_provider_registry.py \
  tests/test_provider_candidates.py
```

Expected: FAIL because `SitemapProvider` does not yet expose `content_class_enrichment` and config rows ignore it.

- [ ] **Step 5: Implement the explicit capability flag**

Extend `SitemapProvider.__init__`:

```python
content_class_enrichment: bool = False,
```

and store:

```python
self.content_class_enrichment = bool(content_class_enrichment)
```

In `backend/providers/__init__.py`, pass:

```python
content_class_enrichment=bool(row.get("content_class_enrichment", False)),
```

Set `"content_class_enrichment": true` in `deploy/search-engine-providers.example.json` only for providers proven eligible by the committed audit. Do not enable a provider merely because it is a known studio site or because its name/domain looks professional.

- [ ] **Step 6: Run provider tests and full provider catalog gate**

Run:

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_provider_registry.py \
  tests/test_provider_candidates.py \
  tests/test_deploy_artifacts.py
```

Expected: PASS.

- [ ] **Step 7: Commit the audited capability boundary**

```bash
git add docs/CONTENT_CLASSIFICATION_V2_PROVIDER_AUDIT.md \
  backend/providers/sitemap.py backend/providers/__init__.py \
  deploy/search-engine-providers.example.json \
  tests/test_provider_registry.py tests/test_provider_candidates.py
git commit -m "docs: audit content classification evidence"
```

---

### Task 2: Provenance-aware deterministic classifier

**Files:**
- Modify: `backend/content_class.py`
- Modify: `tests/test_content_class.py`

**Interfaces:**
- Consumes: `tags: list[str]`, `studio: str | None`.
- Produces:
  - `ContentClassSource = Literal["none", "tag_amateur", "tag_studio", "studio_label", "explicit_provider", "conflict"]`
  - `ContentClassification(content_class: ContentClass, source: ContentClassSource)`
  - `classify_content_evidence(*, tags: list[str], studio: str | None) -> ContentClassification`
  - compatibility wrapper `classify_content(*, tags: list[str], studio: str | None) -> ContentClass`.

- [ ] **Step 1: Add failing provenance tests**

Append to `tests/test_content_class.py`:

```python
from backend.content_class import ContentClassification, classify_content_evidence


def test_no_signal_reports_none_source() -> None:
    assert classify_content_evidence(tags=["hd"], studio=None) == ContentClassification("unknown", "none")


def test_amateur_tag_reports_tag_amateur() -> None:
    assert classify_content_evidence(tags=[" User-Generated "], studio=None) == ContentClassification("amateur", "tag_amateur")


def test_studio_tag_reports_tag_studio() -> None:
    assert classify_content_evidence(tags=["production"], studio=None) == ContentClassification("studio", "tag_studio")


def test_explicit_studio_label_has_source_priority() -> None:
    assert classify_content_evidence(tags=["hd"], studio="Example Studio") == ContentClassification("studio", "studio_label")


def test_conflict_reports_conflict_source() -> None:
    assert classify_content_evidence(tags=["homemade", "professional"], studio="Example Studio") == ContentClassification("unknown", "conflict")


def test_title_is_not_an_input_to_classifier() -> None:
    result = classify_content_evidence(tags=["stepmom", "hd"], studio=None)
    assert result == ContentClassification("unknown", "none")
```

Keep all existing normalization/no-substring tests.

- [ ] **Step 2: Run classifier tests and verify RED**

Run:

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_content_class.py
```

Expected: FAIL because provenance types/functions do not exist.

- [ ] **Step 3: Implement the classifier result without changing public semantics**

In `backend/content_class.py`, add:

```python
from dataclasses import dataclass

ContentClassSource = Literal[
    "none",
    "tag_amateur",
    "tag_studio",
    "studio_label",
    "explicit_provider",
    "conflict",
]


@dataclass(frozen=True)
class ContentClassification:
    content_class: ContentClass
    source: ContentClassSource
```

Implement:

```python
def classify_content_evidence(*, tags: list[str], studio: str | None) -> ContentClassification:
    normalized_tags = {_normalize_token(tag) for tag in tags if tag.strip()}
    amateur_tag = bool(normalized_tags & _AMATEUR_TOKENS)
    studio_tag = bool(normalized_tags & _STUDIO_TOKENS)
    studio_label = bool(studio and studio.strip())

    if amateur_tag and (studio_tag or studio_label):
        return ContentClassification("unknown", "conflict")
    if amateur_tag:
        return ContentClassification("amateur", "tag_amateur")
    if studio_label:
        return ContentClassification("studio", "studio_label")
    if studio_tag:
        return ContentClassification("studio", "tag_studio")
    return ContentClassification("unknown", "none")
```

Keep compatibility:

```python
def classify_content(*, tags: list[str], studio: str | None) -> ContentClass:
    return classify_content_evidence(tags=tags, studio=studio).content_class
```

Do not assign `explicit_provider` anywhere in this task. It is reserved for a future explicit provider field proven by fixture/audit, never provider identity.

- [ ] **Step 4: Run classifier and existing filter tests**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_content_class.py \
  tests/test_content_class_filter.py
```

Expected: PASS.

- [ ] **Step 5: Commit classifier provenance**

```bash
git add backend/content_class.py tests/test_content_class.py
git commit -m "feat: add content classification provenance"
```

---

### Task 3: Trusted page metadata extraction and evidence-safe merge

**Files:**
- Modify: `backend/providers/sitemap.py`
- Modify: `tests/test_sitemap_crawl.py`

**Interfaces:**
- Consumes: Schema.org `VideoObject.productionCompany`, explicit keywords/tags, existing page fetch path.
- Produces:
  - `_production_company_name(value: Any) -> str | None`
  - `parse_video_metadata(...).studio`
  - `_merge_enriched_item(base, fetched)` that unions tags and fills only missing studio/core values
  - `async SitemapProvider.enrich_content_evidence(item: SearchItem) -> SearchItem`.

- [ ] **Step 1: Add failing JSON-LD studio tests**

Add to `tests/test_sitemap_crawl.py`:

```python
def test_jsonld_production_company_string_sets_studio() -> None:
    item = parse_video_metadata(
        '<script type="application/ld+json">'
        '{"@type":"VideoObject","name":"X","thumbnailUrl":"https://e/x.jpg",'
        '"productionCompany":"Example Studio"}'
        '</script>',
        provider="example",
        page_url="https://example.com/v/1",
    )
    assert item is not None
    assert item.studio == "Example Studio"


def test_jsonld_production_company_object_or_list_sets_studio() -> None:
    for value in (
        '{"name":"Object Studio"}',
        '[{"name":"List Studio"}]',
    ):
        item = parse_video_metadata(
            '<script type="application/ld+json">'
            f'{{"@type":"VideoObject","name":"X","thumbnailUrl":"https://e/x.jpg","productionCompany":{value}}}'
            '</script>',
            provider="example",
            page_url="https://example.com/v/1",
        )
        assert item is not None
        assert item.studio in {"Object Studio", "List Studio"}


def test_publisher_creator_author_do_not_set_studio() -> None:
    item = parse_video_metadata(
        '<script type="application/ld+json">'
        '{"@type":"VideoObject","name":"X","thumbnailUrl":"https://e/x.jpg",'
        '"publisher":{"name":"Publisher"},"creator":{"name":"Creator"},"author":"Author"}'
        '</script>',
        provider="example",
        page_url="https://example.com/v/1",
    )
    assert item is not None
    assert item.studio is None
```

- [ ] **Step 2: Add failing merge-safety tests**

```python
def test_enriched_evidence_unions_tags_and_does_not_replace_existing_studio() -> None:
    base = SearchItem(
        id="1", provider="example", title="Base", url="https://example.com/v/1",
        thumbnail="https://example.com/base.jpg", preview_url="https://example.com/p.mp4",
        tags=["hd"], studio="Original Studio",
    )
    fetched = base.model_copy(update={
        "thumbnail": "https://example.com/new.jpg",
        "tags": ["professional", "hd"],
        "studio": "Fetched Studio",
    })
    merged = SitemapProvider._merge_enriched_item(base, fetched)
    assert merged.tags == ["hd", "professional"]
    assert merged.studio == "Original Studio"
    assert str(merged.thumbnail) == "https://example.com/base.jpg"
    assert str(merged.preview_url) == "https://example.com/p.mp4"
```

Add an async test proving `enrich_content_evidence()` returns the original item when page fetch fails rather than raising.

- [ ] **Step 3: Run targeted tests and verify RED**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_sitemap_crawl.py -k 'production_company or publisher_creator_author or enriched_evidence'
```

Expected: FAIL because studio extraction/evidence merge are not implemented.

- [ ] **Step 4: Implement conservative `productionCompany` parsing**

Add:

```python
def _production_company_name(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, dict):
        return _first_string(value.get("name"))
    if isinstance(value, list):
        for item in value:
            name = _production_company_name(item)
            if name:
                return name
    return None
```

In `parse_video_metadata()`:

```python
studio = _production_company_name(video.get("productionCompany")) if video else None
```

and pass `studio=studio` to `SearchItem`. Do not read `publisher`, `creator`, or `author` for this field.

- [ ] **Step 5: Make evidence merge additive and reusable**

Replace the current `tags=base.tags or fetched.tags` behavior with stable deduplicated union preserving base order:

```python
merged_tags = list(dict.fromkeys([*base.tags, *fetched.tags]))
```

Set:

```python
"tags": merged_tags,
"studio": base.studio or fetched.studio,
```

while keeping current non-destructive thumbnail/duration/quality behavior.

Add:

```python
async def enrich_content_evidence(self, item: SearchItem) -> SearchItem:
    fetched = await asyncio.to_thread(self._fetch_page_item, str(item.url))
    return self._merge_enriched_item(item, fetched)
```

- [ ] **Step 6: Run sitemap and classifier suites**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_sitemap_crawl.py \
  tests/test_content_class.py
```

Expected: PASS.

- [ ] **Step 7: Commit trusted metadata extraction**

```bash
git add backend/providers/sitemap.py tests/test_sitemap_crawl.py
git commit -m "feat: extract trusted studio metadata"
```

---

### Task 4: SQLite provenance migration and atomic evidence persistence

**Files:**
- Modify: `backend/index.py`
- Modify: `tests/test_index_migrations.py`
- Modify: `tests/test_content_class_roundtrip.py`
- Create: `tests/test_content_evidence_update.py`

**Interfaces:**
- Consumes: `classify_content_evidence()`.
- Produces:
  - column `items.content_class_source TEXT NOT NULL DEFAULT 'none'`
  - table `content_enrichment_state`
  - `update_content_evidence(item_id: str, *, tags: list[str], studio: str | None, path: Path = DB_PATH) -> bool`
  - `record_content_enrichment_attempt(...)`
  - `list_content_enrichment_candidates(...)`
  - stats helpers used by Tasks 5–8.

- [ ] **Step 1: Add failing migration tests**

Extend `tests/test_index_migrations.py` so a legacy DB initialized without v2 has rows preserved after `initialize()` and now contains:

```python
assert "content_class_source" in item_columns
assert legacy_row["content_class"] == "unknown"
assert legacy_row["content_class_source"] == "none"
```

Verify `content_enrichment_state` columns:

```text
item_id, provider, status, failure_count, last_attempt_at, next_attempt_at
```

with primary key on `item_id`.

- [ ] **Step 2: Add failing atomic-upsert/source tests**

In `tests/test_content_class_roundtrip.py`, assert an upsert of tags `professional` persists:

```python
stored.content_class == "studio"
```

and inspect raw SQLite:

```python
assert row["content_class_source"] == "tag_studio"
```

Then upsert the same id with tags `homemade` and no studio and assert class/source become `amateur/tag_amateur`; stale `tag_studio` must not survive.

- [ ] **Step 3: Add failing evidence-update safety test**

Create `tests/test_content_evidence_update.py` with a full row containing URL/title/thumbnail/preview/age-check/source_order/tags. Call:

```python
changed = update_content_evidence(
    item.id,
    tags=["hd", "professional"],
    studio="Example Studio",
    path=db,
)
```

Assert:
- returns `True` on first improvement and `False` when repeated unchanged;
- class/source recomputed atomically;
- URL/title/thumbnail/preview/age-check/source_order unchanged;
- existing studio is never replaced by a later different studio;
- FTS title is unchanged;
- FTS tags are refreshed only when tags change.

- [ ] **Step 4: Run DB tests and verify RED**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_index_migrations.py \
  tests/test_content_class_roundtrip.py \
  tests/test_content_evidence_update.py
```

Expected: FAIL because provenance/state schema and evidence helper do not exist.

- [ ] **Step 5: Implement additive schema**

In `initialize()` add:

```python
"content_class_source": "TEXT NOT NULL DEFAULT 'none'",
```

to additive columns and create:

```sql
CREATE TABLE IF NOT EXISTS content_enrichment_state (
    item_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    failure_count INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT NOT NULL,
    next_attempt_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_content_enrichment_next_attempt
ON content_enrichment_state(next_attempt_at);
```

Use a provider-state migration key for the enrichment-state index so startup workers do not repeatedly contend on index creation.

- [ ] **Step 6: Recompute class and source together on normal upsert**

Replace class-only derivation with:

```python
classification = classify_content_evidence(tags=item.tags, studio=item.studio)
content_class = (
    item.content_class if item.content_class != "unknown" else classification.content_class
)
content_class_source = (
    classification.source
    if item.content_class == "unknown" or item.content_class == classification.content_class
    else "explicit_provider"
)
```

Persist `content_class_source` in INSERT and `ON CONFLICT ... DO UPDATE`. Explicit non-unknown classes may use `explicit_provider` only when they arrived as explicit structured item metadata; provider identity is never consulted.

- [ ] **Step 7: Implement evidence-safe row update and candidate/state helpers**

`update_content_evidence()` must:
1. load the existing row;
2. stable-union stored tags with supplied tags;
3. fill studio only when stored studio is empty;
4. recompute class/source with `classify_content_evidence()`;
5. return `False` without writing when neither tags nor studio nor derived values change;
6. update only `tags_json`, `studio`, `content_class`, `content_class_source`, `indexed_at`;
7. refresh that item's FTS entry only when tags changed.

`list_content_enrichment_candidates(provider_names, limit, now, path)` must select only:

```sql
active = 1
AND content_class = 'unknown'
AND content_class_source = 'none'
AND url LIKE 'https://%'
AND provider IN (...)
```

and exclude rows whose `content_enrichment_state.next_attempt_at > now`.

`record_content_enrichment_attempt()` persists status and retry timestamp without touching the item row.

- [ ] **Step 8: Run DB tests**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_index_migrations.py \
  tests/test_content_class_roundtrip.py \
  tests/test_content_evidence_update.py \
  tests/test_content_class_filter.py
```

Expected: PASS.

- [ ] **Step 9: Commit provenance persistence**

```bash
git add backend/index.py \
  tests/test_index_migrations.py tests/test_content_class_roundtrip.py \
  tests/test_content_evidence_update.py
git commit -m "feat: persist content classification provenance"
```

---

### Task 5: Bounded offline reclassification and observability CLI

**Files:**
- Create: `backend/content_reclassify.py`
- Modify: `backend/cli.py`
- Create: `tests/test_content_reclassify.py`
- Modify: `tests/test_cli.py` if present; otherwise create `tests/test_content_class_cli.py`

**Interfaces:**
- Produces:
  - `ReclassifyReport`
  - `reclassify_content(*, path, batch_size, apply, after_id=None, max_rows=None) -> ReclassifyReport`
  - `content_class_stats(path=DB_PATH) -> ContentClassStats`
  - CLI `reclassify-content` and `content-class-stats`.

- [ ] **Step 1: Add failing dry-run/idempotency tests**

Create a temp DB with active rows representing amateur, studio-label, studio-tag, conflict, none, and one inactive row. Test:

```python
report = reclassify_content(path=db, batch_size=2, apply=False)
```

Assert:
- report scans only active rows;
- predicted before/after counts reconcile;
- conflicts count is correct;
- changed count reflects stale stored class/source;
- DB bytes/row values remain unchanged in dry-run.

Then:

```python
first = reclassify_content(path=db, batch_size=2, apply=True)
second = reclassify_content(path=db, batch_size=2, apply=True)
```

Assert first changes expected rows and second changes zero.

- [ ] **Step 2: Add failing bounded/resume tests**

With 5 ordered ids:

```python
report = reclassify_content(path=db, batch_size=2, apply=True, max_rows=2)
assert report.scanned == 2
assert report.complete is False
assert report.next_after_id is not None
```

Resume with `after_id=report.next_after_id` and verify no row is skipped or processed twice.

Verify provider cursors and FTS rows are byte-for-byte/logically unchanged by reclassification.

- [ ] **Step 3: Run reclassify tests and verify RED**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_content_reclassify.py
```

Expected: FAIL because the module does not exist.

- [ ] **Step 4: Implement keyset-scanned reclassification**

Define:

```python
@dataclass
class ReclassifyReport:
    scanned: int
    changed: int
    conflicts: int
    before: dict[str, int]
    after: dict[str, int]
    sources: dict[str, int]
    next_after_id: str | None
    complete: bool
```

Scan with:

```sql
SELECT id, tags_json, studio, content_class, content_class_source
FROM items
WHERE active = 1 AND id > ?
ORDER BY id
LIMIT ?
```

For `apply=True`, update only:

```sql
UPDATE items
SET content_class = ?, content_class_source = ?
WHERE id = ?
```

Commit per bounded batch. Do not touch `indexed_at`, FTS, or provider_state.

- [ ] **Step 5: Implement stats**

`ContentClassStats` reports:
- active total;
- class counts/percentages;
- source counts;
- conflict count;
- provider-level `{total, amateur, studio, unknown, none_source}`.

All class counts must reconcile to total active rows.

- [ ] **Step 6: Add CLI commands**

`backend/cli.py`:

```text
reclassify-content
  --apply
  --batch-size 5000
  --after-id <id>
  --max-rows <n>

content-class-stats
```

Default is dry-run. Output must include `scanned`, `changed`, `conflicts`, `next_after_id`, `complete`, before/after counts and source counts. `--apply` is the only write switch.

- [ ] **Step 7: Run reclassify/CLI/full content-class tests**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_content_reclassify.py \
  tests/test_content_class.py \
  tests/test_content_class_filter.py \
  tests/test_content_class_roundtrip.py
```

Expected: PASS.

- [ ] **Step 8: Commit offline reclassification**

```bash
git add backend/content_reclassify.py backend/cli.py tests/test_content_reclassify.py tests/test_content_class_cli.py
git commit -m "feat: add bounded content reclassification"
```

If the repository already had `tests/test_cli.py` and it was modified instead, stage that file instead of the new CLI test filename.

---

### Task 6: Bounded unknown-content enrichment with retry/backoff

**Files:**
- Create: `backend/content_enrichment.py`
- Modify: `backend/cli.py`
- Modify: `backend/index.py` only if Task 4 helper signatures need wiring, not redesign.
- Create: `tests/test_content_enrichment.py`

**Interfaces:**
- Consumes: providers with `content_class_enrichment=True` and callable `enrich_content_evidence()`; Task 4 candidate/state/evidence helpers.
- Produces:
  - `ContentEnrichmentReport`
  - `async enrich_unknown_content(providers, *, batch_size, max_seconds, path, now=None) -> ContentEnrichmentReport`
  - CLI `enrich-content`.

- [ ] **Step 1: Add failing enrichment behavior tests**

Use fake providers and a temp DB to cover:

```python
async def test_explicit_studio_upgrades_unknown_to_studio(): ...
async def test_explicit_amateur_tag_upgrades_unknown_to_amateur(): ...
async def test_conflict_stays_unknown_with_conflict_source(): ...
async def test_no_signal_stays_unknown_and_records_no_signal(): ...
async def test_one_page_failure_does_not_abort_batch(): ...
async def test_provider_without_capability_is_never_called(): ...
async def test_existing_studio_is_not_replaced(): ...
```

Also assert URL/title/thumbnail/preview/age-check/provider cursor remain unchanged after enrichment.

- [ ] **Step 2: Add failing retry/backoff tests**

Define exact retry policy in tests:
- `failure`: next attempt = `6h * 2**(failure_count - 1)`, capped at 7 days;
- `no_signal`: next attempt = 30 days;
- successful class/conflict evidence: no retry row is eligible while source is no longer `none`.

Test that a candidate with future `next_attempt_at` is skipped and becomes eligible after the supplied deterministic `now` passes it.

- [ ] **Step 3: Add failing time-budget test**

Use a fake monotonic clock/provider so:

```python
report = await enrich_unknown_content(..., batch_size=50, max_seconds=2.0)
```

stops before starting another fetch once the deadline is reached. Already completed candidates remain committed; unstarted candidates remain eligible for next run.

- [ ] **Step 4: Run enrichment tests and verify RED**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_content_enrichment.py
```

Expected: FAIL because the engine does not exist.

- [ ] **Step 5: Implement enrichment report and provider map**

Define:

```python
@dataclass
class ContentEnrichmentReport:
    attempted: int = 0
    enriched: int = 0
    classified_amateur: int = 0
    classified_studio: int = 0
    conflicts: int = 0
    no_signal: int = 0
    failures: int = 0
```

Build eligible providers only when:

```python
getattr(provider, "content_class_enrichment", False)
and callable(getattr(provider, "enrich_content_evidence", None))
```

- [ ] **Step 6: Implement sequential bounded enrichment**

For each candidate before deadline:
1. load provider from eligible map;
2. call `await provider.enrich_content_evidence(item)`;
3. compare only tags/studio against original;
4. if no evidence improvement, record `no_signal` with +30 days;
5. if improved, call `update_content_evidence()`;
6. inspect resulting class/source and record success/no-signal as appropriate;
7. on any page/provider exception, record `failure` with exponential backoff and continue.

Do not run multiple page requests concurrently in v2 maintenance. Existing per-provider page timeout already bounds a single request, and sequential execution keeps the maintenance writer/network footprint predictable.

- [ ] **Step 7: Add CLI command**

```text
enrich-content
  --batch-size 25
  --max-seconds 45
```

Print report counters and exit 0 when individual item failures were isolated successfully. Exit nonzero only for fatal setup/DB errors.

- [ ] **Step 8: Run enrichment and DB safety suites**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_content_enrichment.py \
  tests/test_content_evidence_update.py \
  tests/test_content_class_filter.py
```

Expected: PASS.

- [ ] **Step 9: Commit bounded enrichment**

```bash
git add backend/content_enrichment.py backend/cli.py backend/index.py \
  tests/test_content_enrichment.py
git commit -m "feat: add bounded unknown content enrichment"
```

---

### Task 7: Integrate enrichment into the existing maintenance window

**Files:**
- Modify: `backend/cli.py`
- Modify: `deploy/search-engine-backfill.service`
- Modify: `deploy/search-engine.env.example`
- Modify: `tests/test_deploy_units.py`
- Modify: `tests/test_backfill_many.py` or create `tests/test_backfill_enrichment_handoff.py`

**Interfaces:**
- Consumes: `backfill-all`, `enrich_unknown_content()`.
- Produces: optional `backfill-all --enrich-unknown-batch-size N --enrich-unknown-seconds S`; systemd defaults inside the same `run-maintenance.sh` lock.

- [ ] **Step 1: Add failing CLI handoff tests**

Test `_backfill_all()` with patched `backfill_many` and `enrich_unknown_content`:
- when ordinary backfill has no provider error and enrichment seconds > 0, enrichment runs once;
- when ordinary backfill reports a provider error, enrichment is skipped and command exits failure as today;
- when enrichment seconds is 0, enrichment is skipped;
- isolated item-level enrichment failures reported by `ContentEnrichmentReport` do not fail the whole maintenance unit.

- [ ] **Step 2: Add failing deploy-unit contract tests**

In `tests/test_deploy_units.py`, require:

```text
SEARCH_CONTENT_ENRICH_BATCH_SIZE=25
SEARCH_CONTENT_ENRICH_MAX_SECONDS=45
--enrich-unknown-batch-size "$SEARCH_CONTENT_ENRICH_BATCH_SIZE"
--enrich-unknown-seconds "$SEARCH_CONTENT_ENRICH_MAX_SECONDS"
```

and confirm `search-engine-backfill.service` still invokes exactly one `run-maintenance.sh /run/search_engine/maintenance.lock ...` wrapper. No second lock or parallel service is introduced.

- [ ] **Step 3: Run scheduler tests and verify RED**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_deploy_units.py \
  tests/test_backfill_many.py \
  tests/test_backfill_enrichment_handoff.py
```

If `tests/test_backfill_enrichment_handoff.py` was not needed because coverage was added to an existing file, omit it from the command.

Expected: FAIL because backfill-all has no enrichment handoff or env flags.

- [ ] **Step 4: Extend `backfill-all` arguments and orchestration**

Add:

```text
--enrich-unknown-batch-size (default 0 in CLI unless explicitly supplied)
--enrich-unknown-seconds (default 0)
```

After printing successful ordinary backfill runs and before returning, call:

```python
if not failures and enrich_unknown_seconds > 0 and enrich_unknown_batch_size > 0:
    report = await enrich_unknown_content(
        PROVIDERS,
        batch_size=enrich_unknown_batch_size,
        max_seconds=enrich_unknown_seconds,
    )
```

Print one deterministic summary line prefixed `content-enrichment:`.

- [ ] **Step 5: Add systemd/env defaults**

`deploy/search-engine.env.example`:

```text
SEARCH_CONTENT_ENRICH_BATCH_SIZE=25
SEARCH_CONTENT_ENRICH_MAX_SECONDS=45
```

Append matching CLI flags to the existing `ExecStart` inside the same maintenance wrapper. Keep `TimeoutStartSec=6min`; current 180s backfill + 45s enrichment remains below that ceiling with margin for deploy/runtime overhead.

- [ ] **Step 6: Run scheduler and full maintenance tests**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_deploy_units.py \
  tests/test_maintenance_runner.py \
  tests/test_backfill.py \
  tests/test_backfill_many.py \
  tests/test_backfill_deadline.py
```

Expected: PASS when run with `SHELL=/bin/bash`; the known `blackserv` nologin false-fail must not be interpreted as a code regression.

- [ ] **Step 7: Commit maintenance integration**

```bash
git add backend/cli.py deploy/search-engine-backfill.service \
  deploy/search-engine.env.example tests/test_deploy_units.py \
  tests/test_backfill_many.py tests/test_backfill_enrichment_handoff.py
git commit -m "feat: schedule bounded content enrichment"
```

Stage only files that exist/changed.

---

### Task 8: Integration gate, rollout, measurement, and handoff

**Files:**
- Modify: `docs/SEARCH_ENGINE_HANDOFF.md`
- No direct production edits.

**Interfaces:**
- Consumes: complete v2 implementation branch.
- Produces: verified release SHA, production schema/code, measured reclassify/enrichment results, representative query acceptance.

- [ ] **Step 1: Run targeted v2 suite**

```bash
SHELL=/bin/bash .venv/bin/python -m pytest -q \
  tests/test_content_class.py \
  tests/test_sitemap_crawl.py \
  tests/test_index_migrations.py \
  tests/test_content_class_roundtrip.py \
  tests/test_content_evidence_update.py \
  tests/test_content_reclassify.py \
  tests/test_content_enrichment.py \
  tests/test_content_class_filter.py \
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

Expected: all tests PASS; only the two pre-existing FastAPI `on_event` deprecation warnings are acceptable; syntax/whitespace clean.

- [ ] **Step 3: Capture pre-rollout production baseline read-only**

Before deployment, record in the handoff:
- production build;
- indexed active total;
- class counts and percentages;
- provenance column absent/not yet deployed;
- representative query `Tiny` exact counts for all/amateur/studio/unknown;
- service/timer state.

Use local API/DB read-only access only.

- [ ] **Step 4: Update handoff with exact pre-release gate and commit**

Record branch, exact HEAD, audit-enabled providers, exact test counts, rollout sequence, and `PRODUCTION_UNCHANGED`.

```bash
git add docs/SEARCH_ENGINE_HANDOFF.md
git commit -m "docs: record content classification v2 gate"
```

Rerun `git diff --check` and require clean tree.

- [ ] **Step 5: Push feature and fast-forward release**

Use the repository's existing deploy key/known-hosts override if needed. Verify:

```bash
git fetch origin feature/provider-registry-probe
git merge-base --is-ancestor origin/feature/provider-registry-probe HEAD
```

Expected exit `0`, then:

```bash
git push origin feature/content-classification-v2
git push origin HEAD:refs/heads/feature/provider-registry-probe
```

No force push.

- [ ] **Step 6: Prepare canonical sandbox and run official helper CHECK**

Inspect `/opt/bs-sandbox/search_engine`. If dirty only in handoff, preserve it with a named stash before FF; if unrelated app-code dirt exists, STOP instead of overwriting it.

FF canonical to exact release SHA and run as `blackserv`:

```bash
/usr/local/bin/search-engine-deploy-client check
```

Expected `SEARCH_DEPLOY_CHECK=PASS`.

- [ ] **Step 7: Respect maintenance lock and deploy officially**

Do not stop/kill sync or backfill. Wait for a natural free lock window, then:

```bash
/usr/local/bin/search-engine-deploy-client deploy
```

If transport times out, do not retry blindly. Verify helper status, `/api/health`, service state, and deployed source/build first.

- [ ] **Step 8: Verify schema/health before data mutation**

Confirm production:
- build equals released v2 code SHA prefix;
- health `status=ok`;
- `content_class_source` column exists;
- `content_enrichment_state` table exists;
- service and timers active;
- existing search/filter API still returns HTTP 200/422 exactly as before.

- [ ] **Step 9: Run production reclassify dry-run first**

Under the maintenance lock, run:

```bash
/opt/search_engine/.venv/bin/python -m backend.cli reclassify-content --batch-size 5000
```

Review report invariants before any apply:
- scanned <= active total;
- after class counts reconcile to scanned scope/global report;
- conflict count is plausible and never classified amateur/studio;
- no impossible mass jump caused by provider identity.

Record exact dry-run output in handoff.

- [ ] **Step 10: Apply reclassification in bounded chunks**

Run with explicit apply and bounded rows, e.g.:

```bash
/opt/search_engine/.venv/bin/python -m backend.cli reclassify-content \
  --apply --batch-size 5000 --max-rows 50000
```

Continue using returned `next_after_id` only through additional maintenance-lock windows until complete. After every chunk verify health and `content-class-stats`. Rerunning a completed range must report zero changes.

- [ ] **Step 11: Verify natural bounded enrichment**

Do not manually crawl the whole index. Let the normal `search-engine-backfill.timer` acquire the maintenance lock and run enrichment with configured `25 / 45s` limits. Verify journal contains:
- ordinary backfill summary;
- one `content-enrichment:` summary;
- no overlapping writer;
- individual page failures counted without failing the whole unit.

Observe at least two natural runs before calling scheduler stability PASS.

- [ ] **Step 12: Measure data-quality outcome**

Run:

```bash
/opt/search_engine/.venv/bin/python -m backend.cli content-class-stats
```

Record:
- active total;
- amateur/studio/unknown counts and percentages;
- source counts;
- conflicts;
- provider-level coverage;
- enriched/no-signal/failure counters from natural runs.

Success is evidence quality, not a target Unknown percentage.

- [ ] **Step 13: Re-test representative query and manual samples**

For `Tiny`, record exact counts for:
- all;
- amateur;
- studio;
- unknown.

Manually inspect a bounded sample from each non-empty class and conflicts. Reject rollout if any class is explained only by title/provider/domain identity. `Unknown` remains valid for insufficient/conflicting evidence.

- [ ] **Step 14: Final handoff and docs-only release update**

Write authoritative checkpoint containing:
- deployed code SHA;
- schema version/state;
- exact tests;
- dry-run/apply results;
- two natural enrichment runs;
- before/after distribution;
- `Tiny` before/after;
- remaining providers with low evidence coverage;
- explicit next task.

Commit/push docs-only by normal FF, but do not redeploy docs-only commit.

- [ ] **Step 15: Final cleanliness check**

```bash
git status --short
git log -1 --oneline
```

Expected: clean feature/canonical trees except explicitly documented safety stashes; production remains on the exact v2 code build, not the later docs-only SHA.
