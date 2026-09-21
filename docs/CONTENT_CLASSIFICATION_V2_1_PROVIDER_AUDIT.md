# Content Classification v2.1 — Provider Studio Evidence Audit

Date: 2026-09-21

Method: read-only production SQLite sampling of active rows with `content_class='unknown'` and `content_class_source='none'`, followed by canonical-page fetches through the existing configured sitemap-provider fetch path. First pass used one current sample per provider; only candidate/ambiguous providers were expanded to three samples. No production DB, provider state, service, config, or cursor was modified.

Accepted evidence is explicit and item-bound only. Title text, provider identity, uploader/channel identity, categories/navigation, recommendation cards and site-wide marketing copy are rejected.

| Provider | Samples | Status | Finding |
| --- | ---: | --- | --- |
| xvideos | 3 | AMBIGUOUS | `sponsors` and uploader data are not accepted as studio evidence |
| xnxx | 1 | FETCH_UNAVAILABLE | sampled canonical URL returned HTTP 404 |
| sunporno | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| xgroovy | 3 | STUDIO_RULE_CONFIRMED | 2/3 samples exposed JSON-LD `VideoObject.productionCompany` |
| txxx | 1 | NO_STUDIO_SIGNAL | unrelated site/ad studio text only |
| porndig | 1 | NO_STUDIO_SIGNAL | navigation/CSS studio text only |
| justporn | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| fpo | 1 | NO_STUDIO_SIGNAL | current sample fetched; no explicit item-bound field |
| bigassporn | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| brazzilmoms | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| sextubespot | 1 | NO_STUDIO_SIGNAL | site-wide marketing copy only |
| xcafe | 3 | STUDIO_RULE_CONFIRMED | 2/3 samples exposed scoped microdata `productionCompany` → `name` |
| mypornhere | 1 | NO_STUDIO_SIGNAL | navigation only |
| pussyspace | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| tubev | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| xxxbule | 3 | AMBIGUOUS | genre/keywords mix studio-like and performer names |
| theyarehuge | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| sexvid | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| pornid | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| zbporn | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| megatube | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| freeporn | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| pornsexvideo | 1 | AMBIGUOUS | site-level/related-card text, not canonical item metadata |
| lexotic | 1 | NO_STUDIO_SIGNAL | site-level sample; no item-bound signal |
| porndoe | 3 | STUDIO_RULE_CONFIRMED | 3/3 samples exposed JSON-LD `VideoObject.producer` Organization |
| voyeurhit | 1 | NO_STUDIO_SIGNAL | site-wide marketing copy only |
| porngo | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| hdzog | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| sexplex | 3 | AMBIGUOUS | serialized payload contains a studio index but no proven stable value path |
| vxxx | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| serviporno | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |

## Runtime decision

Only `xgroovy`, `xcafe`, and `porndoe` receive v2.1 runtime rules. `xgroovy` duplicates evidence the generic JSON-LD parser already understands and therefore serves as a compatibility/control rule. `xcafe` and `porndoe` add explicit studio/producer evidence not currently captured by the generic parser. Ambiguous providers remain Unknown until an item-bound contract can be proven.

## Pre-deploy gate

Verified code SHA: `671d9d57c993f8f51273efbf7a7d174852bbdc01`

Verification:
- full pytest suite: 360 PASS;
- compileall: PASS;
- frontend JavaScript syntax: PASS;
- git diff check: PASS.

Production baseline before v2.1 deploy (read-only):
- build: `3c0b1d05935f`;
- active rows: 1,204,370;
- unknown/none: 1,105,426;
- unknown/conflict: 3;
- amateur/tag_amateur: 98,781;
- studio/studio_label: 131;
- studio/tag_studio: 29;
- non-empty studio: 131.

Cached query splits (all / amateur / studio / unknown):
- Tiny: 8516 / 1767 / 8 / 6741;
- Sis: 4329 / 651 / 4 / 3674;
- Babe: 89408 / 17462 / 40 / 71906.

## Production rollout acceptance

Deployed code build: `671d9d57c993`.

Official helper deploy: PASS. Production health: PASS. Service and sync/backfill timers: active.

One bounded content-enrichment cycle was run through the existing maintenance lock after the post-deploy sync completed:
- attempted: 25;
- enriched: 21;
- classified amateur: 2;
- classified studio: 7;
- conflicts: 0;
- no_signal: 16;
- failures: 0.

Immediate post-cycle production measurements:
- active rows: 1,204,429;
- unknown/none: 1,105,476;
- unknown/conflict: 3;
- amateur/tag_amateur: 98,783;
- studio/studio_label: 138;
- studio/tag_studio: 29;
- non-empty studio: 138.

`studio_label` attribution by provider:
- xgroovy: 131;
- porndoe: 5;
- xcafe: 2.

The exact `studio_label` delta is +7 (131 -> 138), matching the bounded-cycle `classified_studio=7` report. This verifies that the new porndoe/xcafe rules create only explicit `studio_label` evidence. No conflict increase occurred.

Cached query splits after the cycle (all / amateur / studio / unknown):
- Tiny: 8516 / 1767 / 8 / 6741;
- Sis: 4329 / 651 / 4 / 3674;
- Babe: 89411 / 17462 / 40 / 71909.

The sample queries did not gain Studio hits in this first bounded cycle; Babe gained three new Unknown rows from the intervening normal sync. v2.1 is therefore production-verified as an evidence pipeline improvement, not as an immediate large-scale reclassification. Scheduled bounded enrichment continues naturally. A mass crawl remains explicitly out of scope.
