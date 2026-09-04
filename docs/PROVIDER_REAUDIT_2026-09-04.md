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
