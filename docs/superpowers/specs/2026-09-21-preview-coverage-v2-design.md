# Preview Coverage v2 — Design

Date: 2026-09-21
Project: BlackServ Search Engine
Branch: `feature/preview-coverage-v2`
Base: `1a9aa1f5e40ee6fbe0b9264a1aa850bf676ac581`
Status: DESIGN APPROVED IN CHAT; WRITTEN SPEC PENDING USER REVIEW

## Intent

Increase the number of search-result cards that have a real, playable preview without inventing preview URLs, misusing full-video URLs, weakening media-host policy, or crawling the full index aggressively.

The frontend already supports preview playback. The missing layer is reliable preview acquisition and bounded enrichment for indexed rows.

## Verified baseline

Read-only production audit before this spec:

- active indexed rows: 1,158,630
- rows with non-empty `preview_url`: 6,205
- overall preview coverage: about 0.54%
- providers with at least one stored preview: 14
- live provider parsers already contain multiple explicit preview extractors
- generic sitemap/page metadata parsing does not currently persist preview URLs
- `SitemapProvider._merge_enriched_item()` currently merges thumbnail/duration/quality/tags/studio but not `preview_url`
- media policy has explicit preview host rules
- `pornhat`, `porndr`, and `anyporn` currently have preview URLs in stored/live data but preview playback is deliberately disabled by policy

Representative current stored coverage:

| Provider | Active rows | Rows with preview | Coverage |
| --- | ---: | ---: | ---: |
| tnaflix | 1,239 | 1,239 | 100% |
| youjizz | 917 | 917 | 100% |
| spankbang | 908 | 892 | 98.24% |
| beeg | 804 | 804 | 100% |
| tube8 | 245,341 | 586 | 0.24% |
| thumbzilla | 385 | 385 | 100% |
| drtuber | 318 | 318 | 100% |
| xhamster | 276 | 276 | 100% |
| pornhub | 233 | 233 | 100% |
| hqporn | 128 | 128 | 100% |
| bigfuck | 125 | 125 | 100% |
| pornhat | 124 | 124 | 100% stored, policy disabled |
| porndr | 101 | 101 | 100% stored, policy disabled |
| anyporn | 77 | 77 | 100% stored, policy disabled |

The exact counts are expected to move with normal sync/backfill activity; the architectural conclusion is stable: preview coverage is sparse because most indexed rows do not have a safe canonical-item preview acquisition path. The provider population is not limited to configured sitemap providers; live adapters and index-only rows must be included in the audit.

## Hard rules

- Never synthesize a preview URL from provider identity, item id, page URL, thumbnail URL, or guessed path patterns.
- Never treat a full-video `contentUrl` as a preview merely to increase coverage.
- Accept preview evidence only from a field/attribute/pattern verified for that provider or from a conservative generic metadata field whose semantics are explicitly preview/trailer.
- Preview evidence must be bound to the exact canonical item being enriched. A preview found on a related/recommended card whose target URL differs from the item URL is invalid evidence.
- Never take the first `data-preview`, `data-mediabook`, trailer, MP4, or WebM hit from a canonical page unless the audited extractor proves that hit belongs to the current item.
- Every stored preview must pass provider media policy validation before being considered playable.
- Existing valid `preview_url` is preserved unless a later design explicitly introduces replacement validation.
- Missing or failed preview extraction must not damage thumbnail, title, URL, tags, studio, content classification, age-check state, FTS, or provider cursors.
- No direct production edits.
- No unbounded crawl of the 1.1M+ index.
- All enrichment work must be bounded, resumable, observable, failure-isolated, and run under the existing maintenance lock.
- `pornhat`, `porndr`, and `anyporn` remain policy-disabled unless a separate real probe proves a safe delivery mode.
- UI behavior is out of scope unless implementation reveals a concrete frontend defect.

## Existing architecture to preserve

- live preview extraction/adapters: `backend/live.py` and `LIVE_ADAPTERS`
- configured index providers: `backend/providers/__init__.py::PROVIDERS`
- generic page parser: `backend/providers/sitemap.py::parse_video_metadata`
- sitemap XML parser: `parse_sitemap_video_metadata`
- page fetch path: `SitemapProvider._fetch_page_item`
- enrichment merge: `SitemapProvider._merge_enriched_item`
- SQLite item storage: `backend/index.py`
- media policy: `backend/media_policy.py`
- preview proxy: `backend/app.py::preview_proxy`
- bounded maintenance orchestration: existing backfill service/timer and maintenance lock
- durable retry pattern: Content Classification v2 enrichment state model

Do not create a second generic crawler when an existing provider fetch path can be extended safely. Preview enrichment needs one audited rule registry shared by sitemap providers and live adapters; provider names that occur in both populations are deduplicated, with the configured sitemap provider preferred because it already carries canonical fetch/robots settings.

## Target pipeline

For new/updated indexed rows:

`provider sitemap/live -> explicit preview extraction -> media-policy validation -> non-destructive merge -> SQLite -> existing API/UI`

For existing rows without preview:

`active row without preview -> audited provider capability -> bounded page fetch -> explicit preview extraction -> media-policy validation -> preview-only update -> retry state`

Playback remains:

`stored preview_url -> media policy -> direct/proxy/disabled -> existing frontend preview control`

## Preview evidence model

Preview evidence is provider-specific unless the generic metadata field is semantically unambiguous.

Accepted categories may include, after audit/test proof:

- explicit HTML attributes such as `data-preview`, `data-trailer`, `data-webm`, `data-mediabook`, or equivalent provider-specific attributes
- provider JSON/JSON-LD fields explicitly representing a trailer/preview
- provider page metadata explicitly naming preview/trailer media
- an existing live search/listing adapter result when that returned card URL normalizes exactly to the indexed canonical item URL and the returned preview field is explicit

Do not accept:

- arbitrary `<video src>` without proof it is a preview rather than the full asset
- generic Schema.org `contentUrl`
- generic `embedUrl`
- first MP4/WebM link found in page source
- URLs inferred from thumbnail filenames
- URLs generated from numeric item ids
- provider/domain identity as evidence
- JavaScript player configuration fields with unclear semantics

## Provider preview audit

Implementation starts with a read-only audit.

For every currently indexed provider with active rows missing preview, record:

- provider name
- source kind: configured sitemap provider, live adapter, both, or index-only
- sample size and canonical sample URLs
- whether a safe evidence fetch path exists: canonical item page and/or existing live search/listing adapter
- explicit preview field/attribute observed
- how the preview candidate is bound to the exact canonical item URL; related/recommended-card candidates for a different target URL are rejected
- preview media type: MP4/WebM/other
- preview host(s)
- whether URL is HTTPS
- whether existing media policy allows it
- whether direct playback works or proxy/referer is required
- whether the field is absent, ambiguous, or unstable
- final capability decision: OFF / extract-only / playable-direct / playable-proxy

The audit must not classify a provider as preview-capable solely because a live search parser contains a regex or because a canonical page contains preview attributes for related cards. The exact candidate must be demonstrably bound to the current canonical item URL. A live search/listing adapter is valid evidence only after an actual bounded search returns a card whose normalized URL equals the indexed canonical URL. Providers with indexed rows but no safe page or exact-search binding path are `FETCH_UNAVAILABLE` or `AMBIGUOUS`, not preview-capable.

The audit artifact should be committed under `docs/` and should distinguish:

- `EXTRACT_CONFIRMED`
- `PLAYBACK_CONFIRMED`
- `NO_SIGNAL`
- `AMBIGUOUS`
- `BLOCKED_BY_POLICY`
- `FETCH_UNAVAILABLE`

Only providers with `PLAYBACK_CONFIRMED` evidence are enabled for preview enrichment. `EXTRACT_CONFIRMED` without proven playback remains capability-OFF; it is an audit finding, not permission to crawl.

The audit also writes `deploy/search-engine-preview-rules.json` as the deterministic runtime projection of only `PLAYBACK_CONFIRMED` canonical-bound rules. Runtime extraction code loads this committed file; it never derives capability from provider identity or from test fixtures.

## Provider capability and audited rule registry

Add one central audited preview-rule registry shared by configured sitemap providers and live adapters.

Each rule exists only for a provider whose audit status is `PLAYBACK_CONFIRMED`. Absence from the registry means capability OFF.

The runtime-facing capability remains:

`preview_enrichment: bool`

but its truth value is derived from the presence of an audited rule rather than inferred from provider identity or a broad class default.

Each rule must encode a canonical-item-bound extraction strategy. Allowed v2 strategies are deliberately narrow:
- `live_search_exact`: call an existing audited live adapter with the indexed item title, then accept a preview only from a returned card whose normalized URL equals the indexed canonical URL;
- a linked element/card where both target canonical URL and preview attribute are captured and the normalized target equals the item URL;
- a page-level JSON/metadata field whose containing object is proven to identify the current canonical URL.

A provider-specific custom extractor is allowed only when the audit fixture and tests prove exact canonical binding and neither narrow strategy can represent it.

The eligible runtime map combines configured sitemap providers and live adapters. Duplicate names are deduplicated; configured sitemap providers win because they already carry canonical fetch/robots settings. Index-only providers without a safe runtime fetcher remain capability OFF.

This capability means:
- page enrichment is allowed to look for preview evidence for this provider;
- it does not by itself make any URL trusted;
- final URL must still pass canonical binding and media policy validation.

Do not conflate this capability with Content Classification v2's `content_class_enrichment`.

## Generic/page preview extraction

Extend `parse_video_metadata()` conservatively.

Preferred design:
- one central audited rule registry for sitemap and live providers
- canonical-item-bound extraction; page extractors compare captured item URL/object identity with `page_url`, while `live_search_exact` compares the returned card URL with the indexed item URL
- one central media-policy validation path
- return/store `SearchItem.preview_url` only when semantics and canonical binding are explicit

If a conservative generic trailer field is found during audit, support it with dedicated tests only when its metadata object is proven to represent the current canonical item. Do not add broad MP4 scraping. Do not accept the first preview-looking attribute from related/recommended cards.

Any provider-specific extractor must have:
- fixture or real captured markup reduced to a deterministic test case
- positive test that binds preview to the exact canonical URL
- negative test where an otherwise valid preview belongs to a related/recommended URL and must be rejected
- negative/ambiguity test for full-video/unrelated fields where practical
- HTTPS normalization rules if needed
- host validation in policy tests

## Non-destructive merge

Extend `SitemapProvider._merge_enriched_item()`:

- preserve existing `base.preview_url` if present
- otherwise take `fetched.preview_url` only if non-empty
- do not alter unrelated fields
- continue current additive tags/studio behavior

Conceptually:

`preview_url = base.preview_url or fetched.preview_url`

The merge function itself does not replace media-policy validation; the fetched preview must already be evidence-safe, and persistence/playability must still enforce policy.

## Preview persistence

Add a narrow DB helper:

`update_preview_url(item_id, *, preview_url, path=DB_PATH) -> bool`

Required behavior:
1. load active row
2. refuse empty URL
3. preserve an existing non-empty preview
4. update only `preview_url` and a bookkeeping timestamp/state if required
5. do not touch title, canonical URL, thumbnail, tags, studio, content class/source, age-check state, source_order, FTS, or provider cursor
6. return `False` if no change

A preview update must not trigger content reclassification.

## Playability validation

A preview is useful only if the application can serve/play it under current policy.

Before a newly enriched preview is stored:

`media_url_allowed(provider, "preview", url)` must be true.

If extraction succeeds but policy validation fails, do not write `preview_url`; record `blocked_policy` in enrichment state. Existing historical stored URLs for currently disabled providers are left untouched by this project.

If audit proves a valid preview host that is not currently in policy:
- add the exact minimal host suffix required
- choose `direct` only when real probe proves direct playback
- choose `proxy` only when referer/range handling is required and existing proxy safety constraints are sufficient
- keep `disabled` when reliable/safe playback is not proven

No wildcard broadening merely to increase coverage.

### Policy-disabled providers

`pornhat`, `porndr`, `anyporn` start this project as `BLOCKED_BY_POLICY`.

They remain disabled unless the audit separately proves:
- stable preview URL semantics
- allowed HTTPS host
- required referer behavior
- bounded range behavior if proxy is needed
- successful real playback probe

Stored preview presence alone is not proof.

## Preview enrichment state

Use a dedicated durable state rather than overloading content-classification state.

Preferred additive table:

`preview_enrichment_state`

Fields:
- `item_id` primary key
- `provider`
- `status`
- `failure_count`
- `last_attempt_at`
- `next_attempt_at`

Statuses:
- `success`
- `no_preview`
- `failure`
- `blocked_policy`

A successful stored preview is naturally excluded from future candidates.

## Candidate selection

Preview enrichment candidates must be:

- `active = 1`
- `preview_url IS NULL OR preview_url = ''`
- valid HTTPS canonical item URL
- provider has `preview_enrichment=True`, which implies `PLAYBACK_CONFIRMED` audit status
- retry state says attempt is eligible

Do not scan/crawl providers without audited capability.

Candidate ordering should be deterministic. If implementation can cheaply prioritize user-relevant rows (for example recent/indexed or high-demand rows) without new analytics infrastructure, that can be considered, but v2 should not add a new popularity subsystem.

Default to deterministic bounded keyset/order behavior.

## Retry/backoff

A page failure must not fail the batch.

Recommended policy, aligned with classification enrichment:
- network/parser `failure`: exponential backoff starting around 6h, capped at 7d
- explicit `no_preview`: long cooldown, e.g. 30d
- `blocked_policy`: long cooldown or ineligible until config changes
- `success`: no further enrichment eligibility

Use deterministic `now` in tests.

## Bounded enrichment engine

Add a dedicated preview enrichment operation:

`enrich_missing_previews(...)`

Required report counters:
- attempted
- extracted
- stored
- playable
- no_preview
- blocked_policy
- failures

Execution:
1. build one deduplicated eligible provider map from configured sitemap providers plus live adapters; configured sitemap provider wins duplicate names; only audited-rule providers are eligible
2. fetch bounded candidate list
3. before each request, check wall-clock deadline
4. call existing provider page-fetch/extraction path
5. inspect only `preview_url`
6. validate through media policy
7. persist only via narrow preview helper
8. record durable attempt state
9. continue after individual failures

Sequential execution is preferred initially for predictability and low footprint. Concurrency may be introduced only if real measurements show it is necessary and remains bounded.

## CLI and observability

Add:

`search-engine preview-coverage-stats`

Report:
- total active rows
- rows with stored preview
- stored coverage percentage
- rows with preview playable by current policy
- playable coverage percentage
- per-provider total/stored/playable/percentage
- enrichment-state counts

Add:

`search-engine enrich-previews --batch-size N --max-seconds S`

The CLI should print one deterministic summary line.

No command should default to unbounded execution.

## Scheduler integration

Reuse the existing maintenance lock and existing backfill scheduler.

Preferred order in one maintenance window:

1. ordinary provider backfill
2. Content Classification unknown enrichment
3. Preview Coverage enrichment, if time budget remains / dedicated preview budget is enabled

Do not create parallel writers.

Recommended environment defaults should be conservative and may be smaller than content-classification enrichment initially, for example:
- batch 10–25
- 30–45 seconds

Exact defaults are chosen from provider audit/runtime evidence in implementation planning.

If the backfill window is already consumed, preview enrichment waits for the next timer run.

## New-row strategy

Where a provider is already fetching canonical pages for core metadata or content classification, preview extraction should happen in the same fetch and merge path rather than issuing a second page request.

For sitemap rows that already contain all core metadata and would otherwise avoid a page fetch:
- do not globally force page fetch for every new row
- use the bounded preview enrichment path instead unless provider-specific runtime evidence supports a cheap page-fetch strategy

This avoids converting normal index backfill into an expensive crawl.

## Tube8 case

Tube8 is the clearest coverage gap:
- about 245k active indexed rows
- only about 586 stored previews
- Tube8 is a `Tube8LiveAdapter`, not one of the configured `SitemapProvider` instances
- live search/listing parser already knows a `data-mediabook` preview pattern
- existing media policy allows Tube8 preview host suffixes

The canonical-page audit found only unrelated/recommended-card previews for Tube8, so those page attributes are rejected. A separate bounded live-search audit on 2026-09-21 matched 3/3 sampled indexed Tube8 URLs exactly and returned explicit preview URLs. Combined with the authoritative 2026-09-19 bounded playback audit (`206 video/mp4` on `.t8cdn.com`), Tube8 qualifies for the `live_search_exact` strategy.

Tube8 therefore becomes a strong candidate for bounded preview enrichment, not a one-shot full crawl. No URL is derived from item id, thumbnail, or unrelated listing card.

## Existing live providers

Existing live-result preview extraction remains as-is. Preview Coverage v2 may reuse an audited live adapter as an enrichment evidence source only through `live_search_exact`, which requires an exact normalized canonical URL match before accepting its preview.

Preview Coverage v2 should not regress providers already near 100% preview coverage in live/indexed rows.

Tests must protect known-good providers such as:
- beeg
- youjizz
- tnaflix
- thumbzilla
- drtuber
- xhamster
- pornhub
- hqporn
- bigfuck

SpankBang's slightly sub-100% stored coverage should be treated as normal missing evidence unless audit proves a parser defect.

## API/UI compatibility

No public API contract change is required.

`SearchItem.preview_url` already exists.

Frontend preview button behavior remains driven by:
- non-empty `preview_url`
- media policy mode
- existing one-active-preview behavior

No new visible UI control is required for v2.

## Security and reliability

Preserve current preview proxy safeguards:
- HTTPS only
- allowlisted host suffix
- no embedded credentials
- standard port only
- bounded Range
- bounded response size
- explicit provider policy

Do not proxy arbitrary user-supplied preview hosts.

Page enrichment must use the existing provider-safe fetch path and robots behavior where applicable.

## Testing strategy

TDD is required for behavior changes.

At minimum:
- provider capability defaults OFF
- audited providers only enabled
- positive preview extraction fixture
- ambiguous/full-video field negative test
- related/recommended-card preview for a different canonical URL negative test
- live-adapter and configured-provider deduplication test
- merge preserves existing preview
- DB preview update touches only preview-related state
- candidate selection excludes existing-preview rows
- retry/backoff
- time budget
- failure isolation
- media policy accepted host
- media policy rejected host
- policy-disabled provider remains unplayable
- scheduler same-lock handoff
- coverage stats reconciliation
- existing preview/live parser regressions remain green

Run full project suite with `SHELL=/bin/bash` because the blackserv account uses nologin and maintenance-runner tests otherwise false-fail.

## Production rollout

1. capture production baseline
2. deploy code/schema through official helper only
3. verify health/build/schema before enrichment
4. run stats read-only
5. run a very small manual enrichment batch under maintenance lock
6. inspect resulting previews and playback for each newly enabled provider
7. only then allow natural scheduler enrichment
8. observe at least two natural runs
9. measure stored and playable coverage
10. manually sample successes and failures
11. document provider-level gaps and cooldown/failure rates

Do not run a mass manual backfill of preview candidates.

## Acceptance criteria

Preview Coverage v2 is accepted when:

- only audited providers can run preview enrichment
- no guessed/synthesized preview URLs are stored
- no full-video URL is knowingly mislabeled as preview
- stored preview updates are non-destructive
- every playable preview passes media policy
- disabled providers remain blocked unless separately proven safe
- bounded enrichment survives individual provider/page failures
- maintenance lock prevents overlapping writers
- existing preview providers do not regress
- coverage increases measurably for at least one previously sparse indexed provider
- success is measured as real playable previews, not an arbitrary percentage target
- two natural scheduler runs complete successfully
- final handoff records exact before/after stored and playable coverage

## Non-goals

Out of scope for v2:
- redesigning result cards
- autoplay
- multiple simultaneous previews
- preview transcoding
- storing preview media locally
- CDN mirroring
- user popularity analytics
- crawling the entire index in one operation
- bypassing provider access controls
- weakening age/access restrictions
- replacing media-policy allowlists with arbitrary remote fetches

## Failure/rollback model

The implementation must remain additive.

If preview enrichment misbehaves:
- disable provider `preview_enrichment` capability
- keep scheduler budget at zero if needed
- existing stored previews remain intact
- search/cards continue using thumbnail fallback
- no content classification rollback is required
- code rollback follows the normal release/deploy process

No destructive DB migration is permitted.

## Exact next gate

After this written spec is committed:
1. user reviews/approves the written spec;
2. only then invoke the writing-plans workflow;
3. create the task-by-task TDD implementation plan;
4. user reviews the plan and selects execution method;
5. only then begin implementation.

## Production acceptance addendum — storage lifetime and on-demand resolution (2026-09-21)

Production acceptance changed one architectural assumption without changing the product goal.

### Signed preview lifetime

A preview URL can be correctly canonical-bound, policy-allowed, and immediately playable while still being unsafe to persist. Production probing proved that Tube8 signed preview URLs include short-lived `validfrom` / `validto` / `hash` parameters. A previously stored Tube8 URL whose `validto` was in the past returned HTTP 472. The same pattern exists for Thumbzilla and YouJizz, while TNAFlix uses a signed `secure=...,timestamp` trailer URL.

Therefore `PLAYBACK_CONFIRMED` is no longer equivalent to `safe to persist`.

Runtime preview rules now declare:

- `storage_mode="stable"` — preview URL may be persisted and enriched in the background;
- `storage_mode="ephemeral"` — preview URL may be resolved for playback but must not be persisted by preview enrichment or ordinary sitemap page-fetch paths.

Audited stable providers:
`bigfuck`, `drtuber`, `hqporn`, `spankbang`, `xhamster`.

Audited ephemeral providers:
`thumbzilla`, `tnaflix`, `tube8`, `youjizz`.

Historical stored URLs for those four ephemeral providers are treated as legacy data and are excluded from persistent-playable telemetry. No direct production SQL cleanup is part of this rollout.

### On-demand resolution

Ephemeral providers use a read-only on-demand resolver:

`GET /api/preview/{item_id}`

The resolver:

- loads the indexed item;
- uses only an audited exact-binding provider implementation;
- obtains a fresh preview candidate;
- re-applies media-policy host validation;
- returns the fresh URL with API `no-store` response semantics;
- never writes the resolved URL back to SQLite.

The frontend exposes `on_demand` only for `storage_mode="ephemeral"`. Stable providers remain `stored` in UI capability metadata because a stable record missing a stored preview is not guaranteed to be rediscoverable by live exact search.

For an ephemeral provider, the preview URL is fetched only after the user presses the manual preview button. The frontend ignores any legacy stored signed preview for playback and requests a fresh URL. Thumbzilla continues through the existing strict bounded preview proxy; Tube8, TNAFlix and YouJizz use their audited direct media path.

### Telemetry semantics

Coverage now distinguishes:

- `stored` — any active row with a stored preview URL;
- `persistently playable` — stored URL that passes media policy and belongs to a stable provider;
- `resolver eligible` — active rows belonging to an audited ephemeral provider that can request a fresh preview on demand.

This prevents expired signed URLs from inflating the playable count.
