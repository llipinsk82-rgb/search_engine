# Content Classification v2.1 — Provider Evidence Enrichment

Status: proposed for owner review
Date: 2026-09-21
Base: `4df78a1ff4779c7f7ecd7805b9d1e378a3e386cf`

## Intent

The existing Amateur / Studio / Unknown filter is technically correct but still weak as a product feature. Fresh production measurements show about 1.19M active rows, about 97.8k Amateur, only about 129 Studio, and about 1.09M Unknown. For query `Tiny`, v2 improved from 47 Amateur / 0 Studio / 8046 Unknown to about 1763 Amateur / 7 Studio / 6698 Unknown. The remaining problem is under-collected explicit studio evidence, not the filter UI.

## Preserve from v2

- API values remain exactly `amateur | studio | unknown`.
- `content_class_source` remains authoritative provenance.
- Free-form title text and provider identity are never classification signals.
- Conflict remains `unknown/conflict`.
- Existing reclassification, bounded enrichment, maintenance lock and retry/backoff remain in place.
- No direct production edits; release uses the official deploy helper.

## Root cause

The generic detail parser already consumes Schema.org `VideoObject.productionCompany`, tags and keywords. Most large providers do not expose `productionCompany` in the form currently parsed. Only eight configured providers have `content_class_enrichment=true`; their conversions are dominated by `tag_amateur`. Only xgroovy currently contributes a material number of `studio_label` rows. Increasing the batch size alone would therefore process Unknown faster without materially improving Studio.

## Chosen design

Add a bounded provider audit and provider-scoped rules for explicit, item-bound studio / producer / production-company metadata on canonical video pages. A rule is accepted only when reduced positive and negative fixtures prove that the field belongs to the canonical item.

Allowed evidence kinds are deliberately narrow:

- `jsonld_path`: explicit item-bound JSON-LD field;
- `meta_name`: explicit meta property/name field;
- `labelled_text`: provider-specific visible field explicitly labelled Studio / Producer / Production company.

Forbidden evidence:

- title keywords;
- provider name;
- performer/uploader/channel identity;
- categories or navigation labels;
- recommendation-card metadata;
- arbitrary full-page regex that merely finds a studio-like string.

Accepted extraction only fills the existing `SearchItem.studio`. `classify_content_evidence()` then produces the existing `studio_label` provenance. No public schema change is required.

## Provider audit

For each configured sitemap provider that can safely fetch a canonical item page:

1. sample at most three active Unknown URLs from the production DB read-only;
2. fetch through the existing provider-safe canonical fetch path;
3. inspect explicit item-bound metadata only;
4. reduce accepted markup into positive and negative fixtures;
5. record one status: `STUDIO_RULE_CONFIRMED`, `NO_STUDIO_SIGNAL`, `AMBIGUOUS`, or `FETCH_UNAVAILABLE`.

## Runtime rules

Runtime rules live in `deploy/search-engine-content-evidence-rules.json`. The rule layer is provider-scoped and fixture-driven. Missing, malformed or ambiguous markup produces no new evidence.

`SitemapProvider.enrich_content_evidence()` keeps the generic parser, then applies a provider rule when one exists. Merge behavior stays conservative: existing non-empty studio wins; tags are preserved; preview/title/URL/thumbnail/age state/source order/provider cursors are untouched.

Only providers with a confirmed rule or already-proven useful generic content enrichment are enabled for scheduled content enrichment.

## Rollout

No mass crawl. After tests, deploy the verified commit, run bounded enrichment under the existing maintenance lock, reclassify changed rows, then measure global class/source counts and query splits (`Tiny` plus two additional samples). Scheduled maintenance continues the work naturally.

## Acceptance

- Full suite, compileall, JS syntax and diff checks PASS.
- Every provider-specific studio rule has positive and negative fixtures.
- No title/provider inference exists.
- Ambiguous evidence remains Unknown.
- Existing explicit studio is never overwritten.
- Production Studio count may increase only from explicit item-bound evidence.
- Query totals remain internally consistent.
- Official deploy health/build checks PASS.
- Handoff records exact before/after counts and remaining gaps.

## Non-goals

No forcing all content into Amateur or Studio; no provider-wide classification; no performer/uploader-to-studio mapping; no frontend redesign; no preview-policy changes on this feature branch.
