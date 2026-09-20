# Content Classification v2 — Design

Date: 2026-09-21
Project: BlackServ Search Engine
Branch: `feature/content-classification-v2`
Base: `2f1352a545b74be56efb2bef9e7f4ce5563bd1a7`
Status: DESIGN APPROVED IN CHAT; WRITTEN SPEC PENDING USER REVIEW

## Intent

Make `Amateur / Studio / Unknown` meaningful without guessing from titles, provider names, domains, thumbnails, or visual appearance.

The filter/API are already correct. Verified query `Tiny` before v2:
- all 8,093
- amateur 47
- studio 0
- unknown 8,046

So the missing layer is trusted classification evidence, not filtering.

## Hard rules

- Keep public values exactly `amateur`, `studio`, `unknown`.
- No title/provider/domain/image inference.
- No substring matching.
- Missing evidence stays `unknown`.
- Amateur + studio evidence stays `unknown` as conflict.
- No direct production edits.
- All data work must be bounded, resumable, observable, and respect the existing maintenance lock.

## Existing architecture to preserve

- classifier: `backend/content_class.py`
- page JSON-LD/HTML parser: `backend/providers/sitemap.py::parse_video_metadata`
- sitemap metadata parser: `parse_sitemap_video_metadata`
- SQLite upsert/classification: `backend/index.py::_upsert_item_row`
- incremental scheduled backfill: `backend/ingest.py`
- durable provider cursors: `provider_state`
- existing DB evidence: `items.tags_json`, `items.studio`, `items.content_class`

No UI/API rewrite is required.

## Target pipeline

New/updated items:

`provider -> trusted metadata extraction -> tags + studio -> deterministic classifier -> class + provenance -> SQLite -> existing API/UI`

Existing rows:

`stored tags + studio -> offline reclassify -> unresolved unknown -> bounded page enrichment -> reclassify`

## Classification result and provenance

Add an internal result:

```python
@dataclass(frozen=True)
class ContentClassification:
    content_class: ContentClass
    source: ContentClassSource
```

Internal sources:
- `none`
- `tag_amateur`
- `tag_studio`
- `studio_label`
- `explicit_provider`
- `conflict`

Rules:
1. Keep current exact token normalization.
2. Amateur exact signals remain `amateur`, `homemade`, `user generated`.
3. Studio tag signals remain `studio`, `professional`, `production`.
4. Non-empty explicit studio label is studio evidence.
5. Amateur + any studio evidence => `unknown/conflict`.
6. Amateur only => `amateur/tag_amateur`.
7. Studio label => `studio/studio_label`.
8. Studio tag only => `studio/tag_studio`.
9. No signal => `unknown/none`.
10. Provider-explicit class is allowed only from a documented/tested explicit metadata field; never from provider identity.

Keep `classify_content()` as a compatibility wrapper returning only the class.

## Trusted metadata extraction

### JSON-LD / HTML

Conservatively extend `parse_video_metadata()`.

Accepted studio evidence:
- Schema.org `VideoObject.productionCompany`
  - non-empty string
  - object/list containing non-empty `name`
- provider-specific explicit studio/production metadata only after a fixture or real probe proves the field

Do NOT use as studio evidence:
- `publisher`
- `creator`
- `author`
- site name
- uploader/channel
- performer/model name

These can represent a platform or person rather than a production studio.

Tags continue to come from explicit keywords/tags.

### Sitemap XML

Keep current `<video:tag>` and `<video:category>` extraction.

Only accept studio from an explicit studio/production element actually observed for a provider. Do not reinterpret unrelated XML fields.

### Live providers

If an existing live parser exposes an explicit studio/production field, populate `studio`. Prefer ordinary `tags + studio` over embedding new classifier logic in each parser.

## Provider metadata audit

Implementation starts with a read-only audit.

For each provider record:
- source type: sitemap/live/page
- explicit amateur tag available
- explicit studio/production label available
- explicit studio/professional tag available
- page enrichment required

Commit only verified fixtures/tests/capabilities. Never create a map meaning “provider X = studio”.

Preview Coverage is separate and out of scope.

## Database provenance

Add:

`content_class_source TEXT NOT NULL DEFAULT 'none'`

Additive migration only.

Prefer keeping provenance internal to the index layer; do not expose it in the public `SearchItem` unless implementation proves transport needs it.

Upsert recomputes class + source atomically from current evidence, so stale provenance cannot survive tag/studio changes.

No provenance index initially.

## Offline reclassification

Add:

`search-engine reclassify-content`

Required:
- default dry-run
- explicit `--apply`
- bounded `--batch-size`
- keyset/resumable scanning
- safe to rerun

Dry-run reports:
- scanned rows
- before/after class counts
- provenance counts
- conflicts
- changed rows

Apply updates only:
- `content_class`
- `content_class_source`

It must not alter URLs, titles, thumbnails, previews, tags, age-check state, FTS, or provider cursors.

This reuses existing metadata before any network crawl.

## Unknown enrichment

Only unresolved `unknown/none` rows are candidates.

Candidate requirements:
- active row
- valid HTTPS canonical URL
- provider explicitly supports page enrichment
- retry/backoff permits an attempt

Per item:
1. fetch canonical page with existing provider-safe HTTP behavior
2. extract trusted tags/studio
3. merge only improved evidence
4. reclassify
5. persist only if metadata improved the row

One page failure must not fail the batch.

Never attempt to crawl the whole 1.1M+ index in one run.

## Retry state

Use durable per-item/provider state for:
- last attempt
- `success / no_signal / failure`
- retry/backoff eligibility

A `no_signal` result is valid and stays `unknown`.

If `provider_state` is not a clean fit, use a small additive SQLite table with migration tests.

## Scheduler integration

Reuse the existing maintenance lock.

Preferred shape:
- keep `search-engine-backfill.service/timer`
- give unknown enrichment a separate bounded time budget after ordinary backfill
- if backfill consumes the window, enrichment waits for the next run
- no parallel DB writer

A separate timer is allowed only if implementation proves orchestration would otherwise be too coupled; it must use the same lock and bounded runtime.

## API/frontend

No new filter values and no request-shape changes.

`Unknown` continues to mean:
“no sufficient trusted evidence or conflicting trusted evidence.”

Do not relabel it as a semantic category.

Frontend changes are out of scope until data quality is proven.

## Observability

Report:
- active total
- class counts/percentages
- provenance counts
- conflicts
- enriched rows
- no-signal rows
- failures
- provider-level coverage

Success is measured by real evidence coverage, not by forcing an arbitrary Unknown percentage.

## TDD requirements

Unit:
- productionCompany string/object/list
- publisher/creator/author do not imply studio
- conflict remains unknown
- no title inference
- provenance correctness

Sitemap:
- tag/category behavior preserved
- provider-specific studio fixture only when verified
- unrelated XML never becomes studio

Index:
- additive provenance migration preserves legacy rows
- atomic class/source upsert
- dry-run changes nothing
- apply bounded/idempotent
- unrelated fields/FTS unchanged

Enrichment:
- page failure isolated
- no-signal stays unknown
- explicit studio upgrades to studio
- explicit amateur upgrades to amateur
- conflict stays unknown
- retry/backoff works

API:
- current content filter tests stay green
- invalid class still 422

## Production rollout

1. Capture pre-rollout distribution.
2. Deploy code/schema with official helper.
3. Verify health/service/timers.
4. Run reclassify dry-run.
5. Review counts for impossible jumps.
6. Run bounded apply under maintenance lock.
7. Verify search/health.
8. Enable bounded unknown enrichment.
9. Let natural scheduled runs execute.
10. Measure class/provenance distribution.
11. Manually sample each class.
12. Re-test representative queries including `Tiny`.

## Acceptance

- API/filter semantics unchanged
- no forbidden inference exists
- all class counts reconcile with total rows
- conflicts remain unknown
- explicit studio/amateur evidence classifies correctly
- reclassify is dry-run capable, bounded, idempotent
- enrichment is bounded, resumable, failure-isolated
- maintenance lock respected
- full suite PASS
- production health PASS
- manual samples semantically correct
- before/after Unknown share measured
- improvement accepted only when supported by real metadata

## Rollback

- normal code revert/fast-forward workflow
- original tags/studio remain source evidence
- content class is derived and recomputable
- provenance schema is additive
- enrichment must not destroy unrelated fields
- no destructive schema migration

## Out of scope

- Preview Coverage
- ML/image classification
- title NLP
- provider/domain blanket classification
- public enum changes
- UI redesign
- removing Unknown
- age-check classification

## Exact implementation order

1. Provider metadata audit fixtures/evidence.
2. Evidence/provenance classifier API.
3. Trusted JSON-LD/HTML studio extraction.
4. SQLite provenance migration + atomic upsert.
5. Offline reclassify dry-run/apply CLI.
6. Bounded unknown enrichment + durable retry state.
7. Maintenance scheduler integration.
8. Full gates.
9. Deploy.
10. Dry-run -> bounded apply -> natural enrichment.
11. Measure and manually verify.
12. Update authoritative handoff.
