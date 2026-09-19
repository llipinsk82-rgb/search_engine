# Search Engine — Preview, Cards and Sorting v2 Design

Status: proposed for owner review
Date: 2026-09-19
Branch: feature/provider-registry-probe

## 1. Intent

The next product phase shifts focus from adding provider count to improving result quality and usability.
The owner wants three things:

1. thumbnails/previews that behave reliably — no visible PLAY affordance that repeatedly fails;
2. a cleaner, more premium search/result experience, especially on mobile where the thumbnail is the primary content signal;
3. real sorting and filtering such as newest, most viewed, best rated and Amateur/Studio, without inventing metadata that a provider does not expose.

The current dark/minimal visual direction remains the base. This is an evolution, not a full visual rebrand.

## 2. Current baseline

- Frontend is static HTML/CSS/JS (`frontend/index.html`, `frontend/styles.css`, `frontend/app.js`).
- Mobile is already one result card per row with a large 16:9 thumbnail.
- Current filters: provider, quality, duration and observed age-check behavior.
- Current indexed ordering is relevance (FTS BM25) for text queries and `indexed_at/source_order` for empty queries.
- `SearchItem` currently carries URL, thumbnail, optional `preview_url`, duration, quality, tags, age-check state and score.
- The browser shows PLAY whenever `preview_url` exists. A failed media element falls back to the still image, but the availability decision is not provider-aware.
- Thumbnail self-healing is currently hard-coded around Thumbzilla/Tube8; the thumbnail proxy is explicitly allowlisted only for Thumbzilla.
- No first-class `published_at`, `views`, `rating` or Amateur/Studio field exists today.
- Provider expansion is temporarily lower priority. The uncommitted PornFlip adapter remains preserved and is not part of this design change.

## 2.1. Approaches considered

### Approach A — frontend-only patch

Keep the current data model and add more provider-name exceptions in `app.js` for broken thumbnails/previews, plus client-side sort controls over whatever fields already exist. This is the cheapest short-term change, but it scales poorly, cannot support real newest/views/rating sorts, and would deepen the current Thumbzilla/Tube8-style special-case problem. Rejected.

### Approach B — provider-aware media policy + additive metadata (chosen)

Keep the existing FastAPI/SQLite/static-frontend architecture, centralize media capability rules server-side, add only nullable metadata columns, and evolve the cards/UI in place. This fixes the actual preview/thumbnail reliability problem without a rewrite and enables honest sorting as providers expose real metadata. Chosen because it has the best reliability/complexity trade-off and preserves the current deployment model.

### Approach C — frontend/backend rewrite

Move to a component framework and redesign the search API/schema around a new result model in one release. This could produce a cleaner long-term UI architecture, but it creates unnecessary migration and deployment risk for a product that already has working search, prefetch, live providers and mobile cards. Rejected for this phase.

## 3. Goals

### G1 — Reliable result media

A result card must always prefer a usable still thumbnail. PLAY is displayed only when a preview is eligible under a provider media policy. Preview failure must degrade to the still image without breaking the card or repeatedly inviting the same failed action in the same session.

### G2 — Premium but compact cards

The UI should make visual scanning faster: thumbnail first, title second, small useful metadata third. Mobile remains one large card per row. Desktop keeps a dense grid but with clearer hierarchy and less status/noise text.

### G3 — Real sorting

Add these sort modes:

- Relevance (default)
- Newest
- Most viewed
- Best rated
- Longest
- Shortest

Sorting must use real provider metadata only. Missing values sort after known values rather than being synthesized.

### G4 — Amateur / Studio filter

Add a content classification filter:

- All
- Amateur
- Studio
- Unknown

Classification must come from explicit provider metadata/tags/categories/studio fields. Do not infer Amateur/Studio from free-form titles.

## 4. Non-goals

- No video mirroring or hosting.
- No bypass of robots, age gates, anti-bot systems or private AJAX contracts.
- No general-purpose open media proxy.
- No autoplay on page load or scroll.
- No more than one active motion preview at a time.
- No fabricated view counts, ratings, dates or content classifications.
- No promise that a live provider's page-N batch represents a mathematically global “most viewed/newest” ordering across its complete remote catalog.
- No recommendation/personalization/history subsystem in this phase.

## 5. Architecture decision — provider-aware media policy

Replace frontend provider-name special cases with one server-side media capability policy per provider.

Conceptual policy fields:

- `thumbnail_mode`: `direct | proxy | refresh`
- `preview_mode`: `direct | proxy | disabled`
- allowed thumbnail host suffixes
- allowed preview host suffixes
- optional required Referer for proxied upstream requests

The policy is not an arbitrary URL proxy. Server validation remains strict:

- HTTPS only;
- host suffix allowlist per provider;
- no embedded credentials;
- port 443/default only;
- redirects rejected unless a future provider-specific rule explicitly validates the redirect target;
- image/video content type validation;
- bounded timeout and response size;
- preview proxy supports bounded streaming/range semantics only where explicitly enabled.

Direct media remains the default. Proxying is an exception for providers that demonstrably require Referer/header handling or browser-incompatible media delivery.

## 6. Thumbnail behavior

Frontend cards use one resolver path instead of hard-coded provider checks.

1. Render the indexed/live thumbnail according to provider media policy.
2. On thumbnail error, perform one provider-safe refresh/resolution attempt through `/api/thumb/{item_id}?refresh=true` when the item exists in cache/index.
3. If the provider requires thumbnail proxying, use the allowlisted proxy route.
4. After the bounded retry budget is exhausted, show the card placeholder; do not loop.
5. When thumbnail refresh changes the URL, keep the current existing behavior of persisting the resolved thumbnail in the index when safe.

The old `selfHealingProvider === thumbzilla || tube8` frontend branch should disappear in favor of policy-driven behavior.

## 7. Preview behavior

PLAY eligibility becomes explicit.

A card displays PLAY only when all are true:

- `preview_url` is present;
- the provider media policy says preview is supported;
- that item has not failed preview in the current browser session.

On click:

1. stop any other active preview;
2. attempt the policy-selected direct/proxied preview;
3. keep the still as poster until playback starts;
4. if playback fails/errors/times out, immediately restore the still;
5. hide/disable PLAY for that item for the current session;
6. do not repeatedly retry automatically.

No preview URL is fabricated from thumbnail rotation sequences or guessed paths. Image-rotation providers remain still-image cards unless a separate supported image-preview mode is deliberately designed later.

## 8. Card/UI v2

### Desktop

- compact sticky top search area;
- search remains visually primary;
- sort control appears before secondary filters;
- provider/quality/duration/content-class filters remain compact;
- result grid remains responsive (roughly 4 columns on wide desktop, 3 on medium, 2 where useful, 1 on mobile);
- 16:9 media stays dominant;
- duration bottom-right, quality bottom-left;
- PLAY uses a clear overlay only when eligible;
- provider is a small secondary chip/line, not competing with title;
- views/rating/date appear only when present.

### Mobile

- one full-width card per row remains mandatory;
- minimal side padding;
- large thumbnail/preview;
- maximum two title lines;
- metadata line stays small and scannable;
- filters remain horizontally scrollable rather than becoming a tall form;
- no hover-dependent feature.

### Status text

Operational provider-refresh detail remains available but should be visually secondary. Normal users should primarily see result count/state, not implementation noise.

## 9. Metadata model v2

Extend `SearchItem` with optional fields:

- `published_at: datetime | None`
- `views: int | None`
- `rating_percent: float | None` (normalized 0–100 only when the source supplies a convertible rating)
- `rating_count: int | None`
- `content_class: amateur | studio | unknown`
- `studio: str | None`

SQLite receives additive nullable columns only. Existing rows remain valid. No destructive table rebuild is required.

Recommended indexes:

- `published_at`
- `views`
- `rating_percent`
- `content_class`

Migration follows the existing `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` pattern and uses a versioned provider-state/index migration marker for index creation.

## 10. Metadata ingestion rules

Provider parsers may populate the new fields incrementally.

Rules:

- `published_at`: only a source date explicitly tied to the video/item;
- `views`: explicit numeric view/watch count only;
- `rating_percent`: normalize explicit source rating to 0–100 when scale is known;
- `rating_count`: explicit vote/rating count only;
- `studio`: explicit studio/production label only;
- `content_class=amateur`: explicit amateur/user/homemade category/tag/field;
- `content_class=studio`: explicit studio/production/professional metadata;
- otherwise `unknown`.

Never classify from title keywords alone.

Provider coverage can improve over time; the sort/filter feature does not require every provider to expose every field.

## 11. Search API v2

Add to `SearchRequest` and GET `/api/search`:

- `sort`: `relevance | newest | views | rating | longest | shortest`
- `content_class`: `amateur | studio | unknown | null`

Add the same filter/sort intent to `LiveRefreshRequest` where meaningful.

URL/hash state in the frontend persists both fields so searches remain shareable/restorable.

### SQL ordering rules

`relevance`
- text query: existing FTS rank, then freshness/source order;
- empty query: existing freshness/source order.

`newest`
- known `published_at` first, descending;
- missing dates last;
- stable tie-breaker by relevance/indexed/source order.

`views`
- known `views` first, descending;
- missing values last;
- stable relevance/source tie-breaker.

`rating`
- known `rating_percent` first, descending;
- then `rating_count` descending when present;
- missing ratings last;
- no synthetic Bayesian score in v1.

`longest` / `shortest`
- known duration first in requested direction;
- missing duration last.

## 12. Live result semantics

Live adapters may return the new metadata immediately when available. `refresh_live_search` can sort the merged fetched batch using the same sort key before caching/rendering.

Important limitation: live sorting is exact for the fetched result pool, not a guarantee about every unseen page on every remote provider. Indexed providers can provide stronger global ordering because their local corpus is queryable by SQLite.

The UI should not claim stronger semantics than this.

## 13. Rollout phases

### Phase A — Media Reliability

- introduce provider media policy;
- centralize thumbnail resolution;
- preview eligibility and failure memory;
- add preview proxy only for providers proven to need it;
- remove dead/misleading PLAY states.

No sort schema change in this phase.

### Phase B — Cards/UI v2

- compact sticky search/filter area;
- improved cards/badges/meta hierarchy;
- preserve one-column mobile experience;
- reduce operational/status noise.

### Phase C — Metadata + Sorting

- additive schema migration;
- `SearchItem`/API fields;
- SQL sort modes;
- frontend sort selector and state persistence;
- missing metadata always sorts last.

### Phase D — Amateur/Studio

- content-class field/filter;
- provider-by-provider explicit metadata enrichment;
- no title-based guessing.

Provider expansion resumes after Phase A/B stability unless a provider change is required specifically to repair media metadata.

## 14. Testing and acceptance

### Automated

- media policy rejects non-HTTPS, wrong hosts, credentials, unexpected redirects and invalid content types;
- allowed thumbnail/preview hosts pass;
- preview button visibility follows policy + URL presence;
- preview failure restores thumbnail and prevents repeated session retry;
- only one preview can be active;
- schema migration preserves old databases/rows;
- every sort mode places null metadata after known metadata;
- rating normalization boundaries are tested;
- content-class filtering keeps `unknown` distinct;
- API/hash state round-trips sort and content class;
- existing search, provider and deploy suites remain green;
- `git diff --check` passes.

### Production smoke

Use a bounded provider acceptance set containing:

- a direct-working thumbnail provider;
- a provider that needs thumbnail resolution/proxy;
- a working direct preview provider;
- any provider requiring preview proxy, if such a provider is enabled;
- a no-preview provider.

For each sampled card verify:

- thumbnail renders or cleanly falls back;
- PLAY exists only when eligible;
- failed preview returns to still without broken card;
- no autoplay;
- switching preview stops the previous one;
- mobile remains one large result per row.

Sorting acceptance uses fixtures/rows containing both known and missing metadata so “missing last” is proven for every sort mode.

## 15. Security / operational constraints

- Continue official sandbox → tests → commit/push → helper CHECK → maintenance gate → deploy → health/acceptance workflow.
- Never deploy a dirty worktree.
- Preserve the current provider robots/no-bypass policy.
- Media proxy rules are explicit code/config allowlists, not user-extensible URL forwarding.
- Keep response limits/timeouts bounded so a bad media host cannot tie up application workers indefinitely.
- No real provider/player content is mirrored into local persistent storage beyond existing metadata/cache behavior.

## 16. Success criteria

This phase is complete when:

1. sampled production cards no longer expose knowingly dead PLAY controls;
2. thumbnail failures have bounded self-healing/fallback rather than provider-name hacks in frontend code;
3. the visual hierarchy is thumbnail-first and clean on both desktop and mobile;
4. sort modes Relevance/Newest/Most viewed/Best rated/Longest/Shortest work from real metadata and always place missing metadata last;
5. Amateur/Studio filtering uses explicit metadata only;
6. no regressions to provider search, prefetch/load-more, one-preview-at-a-time behavior or deploy safety gates.

## 17. Explicit design decisions

- Keep the existing dark visual identity; refine it rather than redesign the brand.
- Fix media reliability before adding richer sorting UI.
- Add nullable metadata instead of forcing immediate enrichment of all providers.
- Treat Amateur/Studio as a filter, not a ranking signal.
- Do not use title heuristics to invent content class.
- Do not show PLAY just because `preview_url` is non-null; provider media capability is part of eligibility.
- PornFlip remains preserved but unreleased until this product-phase plan is approved and media reliability work begins.
