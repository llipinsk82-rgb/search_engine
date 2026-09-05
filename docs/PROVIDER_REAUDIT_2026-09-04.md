# Provider re-audit — 2026-09-04

Policy used: ordinary ads/interstitials and one or two popups are not automatic rejection criteria. Reject only aggressive multi-window/tab storms or repeated forced redirects. Static popup-capable code alone is not sufficient evidence. No provider is auto-enabled without behavior review.

## XHamster
- Existing live adapter works on page 1 and page 2.
- Probe: 7/7 thumbnails, previews and durations on each sampled page; quality metadata absent.
- CDN thumbnail and preview return HTTP 206.
- Direct video target from the server-side probe returned Cloudflare HTTP 520 in one acceptance request, so target behavior should be confirmed in an end-user browser before enable.
- Status: TECHNICALLY READY, BROWSER BEHAVIOR/TARGET CHECK PENDING.

## SpankBang
- Existing live adapter works on page 1 and page 2.
- Probe: 8/8 thumbnails, previews and durations; quality 7/8 then 8/8 in samples.
- Target HTTP 200, thumbnail HTTP 206, preview HTTP 206.
- robots.txt explicitly advertises `Content-Signal: search=yes` and allows `/` for generic user agents.
- Status: TECHNICALLY READY, BROWSER BEHAVIOR CHECK PENDING.

## Thumbzilla
- Previous parser was stale because current result cards are `<article class="video-box ...">`, not the old anchor-based card shape.
- Parser updated and regression-covered. Live probe now returns 8/8 thumbnails, previews and durations.
- Target HTTP 200 and preview HTTP 206.
- Current thumbnail CDN returns HTTP 403 without a Thumbzilla Referer but HTTP 206 image/jpeg with `Referer: https://www.thumbzilla.com/`.
- Existing Search Engine thumbnail endpoint redirects rather than proxies, so browser rendering can still fail.
- Status: PARSER FIXED; NEED THUMBNAIL REFERER/PROXY HANDLING + BROWSER BEHAVIOR CHECK BEFORE ENABLE.

## XGroovy
- Home page and sitemap requests from the Search Engine host are currently Cloudflare-blocked with HTTP 403 (`Just a moment...`).
- robots.txt is reachable and declares sitemap locations plus Crawl-delay: 5.
- Status: BLOCKED FOR SERVER-SIDE COLLECTION; do not add bypass logic.

## SunPorno
- Home HTTP 200; robots.txt HTTP 200; sitemap.xml HTTP 200.
- Video sitemap is directly compatible with existing generic SitemapProvider.
- Generic probe result: GENERIC_READY; 5/5 unique URLs, thumbnails, durations and tags.
- No custom provider code is required for indexing.
- Status: TECHNICALLY READY AS SITEMAP CANDIDATE, BROWSER BEHAVIOR CHECK PENDING BEFORE SEARCH ENABLE.

## Environment limitation
The sandbox host currently has no Chromium/Chrome/Firefox binary and no Playwright/Selenium/Pyppeteer module. Therefore this pass does not claim a real browser popup/redirect behavior audit. Technical readiness and HTTP behavior were verified without bypassing site protections.

## Discovery continuation — 2026-09-04
- XGroovy rechecked again: home, robots and `/sitemap/` now return HTTP 200 without bypass. Video sitemap shards are generic-ready; production promotion prepared separately.
- PornHat: reachable, but advertised `/sitemap.xml` currently returns an empty body; not a generic sitemap candidate.
- PornTrex: DNS resolution failed from the server; not promoted.
- PornHits: redirects to Pornhub, so it is not an independent source.
- Porn00: reachable but no sitemap at `/sitemap.xml`; not promoted in this pass.
- TXXX: reachable, robots allows normal crawling, sitemap index exposes video shards. The index currently advertises several not-yet-published 404 child shards. Generic crawler hardened to skip only missing child sitemap 404s while preserving fatal behavior for root/other HTTP failures.
- TXXX candidate discovered with 2072 video sitemap shards. Candidate filter corrected to match `/sitemap_vids_<n>.xml`; post-fix probe must pass before promotion.


## Discovery continuation — evening pass
- RedTube and YouPorn: reachable, but `/sitemap.xml` returns ordinary HTML rather than a sitemap; no generic promotion.
- DrTuber and FapVid: reachable, but no sitemap at the conventional endpoint; custom/live adapter work would be required.
- 4Tube: server-side home/sitemap HTTP 403; no bypass attempted.
- PornDoe: robots explicitly advertises sitemap; video sitemap contains rich video metadata. Initial 20-item generic probe: 20/20 unique + thumbnail, but only 7/20 duration/tags in the first mixed sample, so status CUSTOM_REQUIRED pending a better bounded strategy. Added candidate-only, not searchable.
- PornDig: robots permits normal video pages and sitemap index exposes three gzip video chunks. Generic crawler gained transparent gzip sitemap decoding. Fresh probe after support: GENERIC_READY, 20/20 unique + thumbnail + duration. Added candidate-only pending release/promotion decision.


## User candidate list continuation 2026-09-05
- Thumbzilla mobile thumbnail path confirmed PASS by user after API proxy/Nginx fix.
- Expanded 100-item gate: JustPorn GENERIC_READY 100/100 URL, thumbnail, duration, tags.
- Expanded 100-item gate: FPO GENERIC_READY 100/100 URL, thumbnail, duration; tags absent but not required for generic readiness.
- SexVid, PornID, MegaTube: 100/100 URL + thumbnail + tags, but 0/100 duration => CUSTOM_REQUIRED; not promoted.
- JustPorn and FPO promoted to configured/searchable catalog pending release acceptance.


## Loop batch 2026-09-05 B
- Confirmed Thumbzilla mobile thumbnail fix PASS from user.
- Expanded 100-item gate PASS: BigAssPorn 100/100 URL/thumb/duration/tags.
- Expanded 100-item gate PASS: BrazzilMoms 100/100 URL/thumb/duration/tags.
- Expanded 100-item gate PASS: SexTubeSpot 100/100 URL/thumb/duration, 97/100 tags.
- Expanded 100-item gate PASS: XCafe 100/100 URL/thumb/duration/tags.
- JustPorn/FPO catalog promotion corrected to also be trusted/searchable in source policy.
- SexVid/PornID/MegaTube remain CUSTOM_REQUIRED because duration metadata is absent.


## Loop batch 2026-09-05 C
- Expanded 100-item gate PASS: MyPornHere 100/100 URL/thumb/duration.
- Expanded 100-item gate PASS: PussySpace 100/100 URL/thumb/duration.
- Expanded 100-item gate PASS: TubeV 100/100 URL/thumb/duration.
- Expanded gate PASS: XXXBule 98/98 URL/thumb/duration, 73/98 tags.
- Promoted all four to configured + trusted/searchable catalog.
- BigFuck, BustyBus, CumLouder, HDSexVideo, HDTubeMovies, HQPorn, MILFPorn, PornSexVideo, ZZZTube remain CUSTOM_REQUIRED from generic probe.


## Loop batch 2026-09-05 D
- TheyAreHuge expanded gate: GENERIC_READY 100/100 URL, thumbnail, duration, tags.
- Promoted to configured + trusted/searchable production catalog.


## Loop batch 2026-09-05 E
- Added optional page enrichment for sitemap records missing core metadata; generic parser now also understands visible Duration: Nmin Nsec.
- SexVid expanded enriched gate PASS 100/100 URL/thumb/duration/tags.
- PornID expanded enriched gate PASS 100/100 URL/thumb/duration/tags.
- ZBPorn expanded enriched gate PASS 100/100 URL/thumb/duration/tags.
- MegaTube improved to 29/100 duration but remains CUSTOM_REQUIRED; not promoted.
- Promoted SexVid, PornID, ZBPorn with bounded 10k backfill and enrichment enabled.
