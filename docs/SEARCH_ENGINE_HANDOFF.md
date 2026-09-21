# Search Engine handoff

Updated 2026-09-03 23:33 UK.

CRITICAL:
Do not continue archaeological recovery of deleted local commits.
Production build d054dd78c440 is the healthy behavioral baseline and source of truth.
The sandbox is now a newly rebuilt development baseline matching production behavior.
Do not spend time reproducing old hashes or 153 historical tests one by one.

Paths:
Sandbox: /opt/bs-sandbox/search_engine
Production: /opt/search_engine
Backups: /opt/search_engine-backups
Branch: feature/provider-registry-probe
Current base HEAD: 0104170380d1 plus reconstructed uncommitted changes.
GitHub origin: https://github.com/llipinsk82-rgb/search_engine.git

Bridge and deployment:
Use BlackServ Bridge first.
Do not bypass permissions and do not use sudo tricks.
Do not read protected production source directly.
Authorized helper only:
/usr/local/bin/search-engine-deploy-client status
/usr/local/bin/search-engine-deploy-client check
/usr/local/bin/search-engine-deploy-client deploy
Do not kill healthy sync/backfill jobs. Respect maintenance lock.

Current production:
build d054dd78c440
search-engine.service active
search-engine-sync.timer active
search-engine-backfill.timer active
indexed_items snapshot: 259748
indexed providers: 13
configured index: tube8,xnxx,xvideos
live: beeg,eporner,hqporner,pornone,tnaflix,xnxx,youjizz
available/searchable: beeg,eporner,hqporner,pornhub,pornone,tnaflix,xnxx,xvideos,youjizz

Current sandbox:
Rebuilt backend API/search/index/live, source policy, provider registry, sitemap ingest,
bounded backfill, deploy/rollback layer, frontend v18, manual preview, mobile one-column,
prefetch and service worker search-shell-v18.
Current suite: 94 passed, 2 FastAPI deprecation warnings.
Known old-DB migration ordering bug was fixed: add missing columns before creating age-check index.
Do not commit search_engine.db, WAL or SHM files.

UX contract:
Mobile one card per row.
Thumbnail primary.
Quality and duration badges on image.
Preview OFF by default.
Play button only when preview_url exists.
No autoplay on scroll or hover.
One preview at a time.
Prefetch next page while viewing current page.
Show more consumes ready buffer and starts following prefetch.

Provider policy:
Previous policy was too strict.
Ads, interstitials, one or two popups, popup/popunder mechanisms and age checks do NOT disqualify a source.
Reject only aggressive spam UX: many windows/tabs, repeated forced redirect storms, or navigation that is effectively impossible to close/back out of.
Static window.open/popunder code alone is not enough evidence.
Age check is informational only, not a source-selection criterion.

Re-audit:
XHamster
SpankBang
Thumbzilla
XGroovy
SunPorno

Tube8 remains a separate login/source-UX case.

Immediate next action:
Stop recovery archaeology.
Review current sandbox diff and rerun tests.
Keep the current green development baseline.
Commit it as a new baseline and push to GitHub.
GitHub push is mandatory backup discipline.
Then run helper check.
Do not deploy merely to change the build hash if production behavior is already healthy.
After baseline is secured, resume real development:
re-audit rejected providers under the clarified aggressive-spam-only policy,
re-enable those that pass,
then expand high-quality provider coverage.

Release discipline for every major change:
tests -> commit -> GitHub push -> helper check -> deploy -> independent acceptance -> handoff update.

User works in CTO mode:
GO means proceed autonomously.
STOP or HOLD means stop risky work.
Do not repeatedly ask for confirmation for normal safe development.

## Re-audit update 2026-09-04
Fresh technical re-audit is in `docs/PROVIDER_REAUDIT_2026-09-04.md`.
- SpankBang: technically ready; browser behavior check pending.
- XHamster: technically ready; target/browser check pending (server-side target probe saw Cloudflare 520, media works).
- Thumbzilla: parser fixed for current article markup; thumbnail requires Thumbzilla Referer, so proxy/referrer handling is needed before enable.
- XGroovy: Cloudflare 403 from server; do not bypass.
- SunPorno: generic sitemap probe is GENERIC_READY; no custom provider code required; browser behavior check pending.
No provider was auto-enabled in this pass.

## Update 2026-09-04 — provider media hardening
- Baseline recovery is closed; GitHub push works with dedicated Search Engine deploy key.
- Re-audit commit 1fe0868f5ec4 is on origin/feature/provider-registry-probe.
- Thumbzilla parser was updated for current article/video-box markup and live probe returns thumbnails, previews and durations.
- Thumbzilla hotlink thumbnails require Referer; sandbox now has a strict /thumb-proxy endpoint limited to HTTPS hosts under *.ypncdn.com with Thumbzilla Referer, image-only responses and 2 MiB cap. Frontend uses it only for provider=thumbzilla.
- Real live proxy acceptance passed (image/avif returned from fresh Thumbzilla result).
- SunPorno generic sitemap probe is GENERIC_READY (thumbnail/duration/tags complete). It is registered as trusted candidate but remains search-disabled; candidate config lives in deploy/search-engine-provider-candidates.example.json and is not part of the production provider catalog.
- XGroovy remains Cloudflare 403 from server-side client; do not bypass.
- SpankBang remains technically ready but not auto-enabled until browser-behavior acceptance under the clarified aggressive-spam-only policy.
- XHamster live metadata works; server-side target may receive Cloudflare 520, so keep disabled pending browser acceptance.
- Current suite after proxy/candidate work: 99 passed, 2 FastAPI deprecation warnings.

## Production update 2026-09-04 — SpankBang + Thumbzilla enabled
- Commit `7badcd2659b6` enables SpankBang and Thumbzilla as searchable live providers after the technical re-audit.
- Full suite before release: 101 passed, 2 FastAPI deprecation warnings.
- GitHub push PASS and helper check PASS.
- Production deploy PASS with backup `/opt/search_engine-backups/20260904T085019Z-7badcd2659b6`.
- Production acceptance reports build `7badcd2659b6`, service/sync/backfill timers active, indexed_items 293505.
- Local production API `/api/providers` exposes both providers.
- Live refresh acceptance: SpankBang 3/3 with thumbnail+preview+duration+HD; Thumbzilla 3/3 with thumbnail+preview+duration.
- Thumbzilla strict thumbnail proxy live check PASS (200 image/avif).
- Public endpoint from the bridge host returns 401 at the external auth layer; this is not an app health failure because helper/local acceptance passed.
- Still disabled/pending: XHamster (Cloudflare target instability/browser check), SunPorno (candidate config ready; browser behavior check), Tube8 (login/source UX), XGroovy (Cloudflare 403; no bypass).

## Production update 2026-09-04 — SunPorno promoted + immediate seed
- SunPorno was promoted from candidate-only to the production sitemap provider catalog.
- Generic provider path only; no custom parser/live adapter was added.
- Filtered production config probe: 20/20 unique video URLs, thumbnails, durations and tags.
- Release commits: `2a9d369bec4b` (provider promotion), `cc277967d148` (deploy catalog guard), `c4b755ffb1ee` (sync-before-backfill warmup).
- Final full suite: 103 passed, 2 FastAPI deprecation warnings.
- Helper check/deploy PASS. Production backup: `/opt/search_engine-backups/20260904T101703Z-c4b755ffb1ee`.
- Warmup now starts existing `search-engine-sync.service` before backfill so newly configured providers do not wait up to the regular 30-minute timer.
- Warmup result: items 293509 -> 293759, grown provider `sunporno`.
- Production SunPorno count after deployment: 250.
- Production search acceptance: total=250; first 5/5 results have thumbnail + duration + tags.
- Current production build `c4b755ffb1ee`; service, sync timer and backfill timer active.
- Remaining provider work: XHamster browser/target stability, Tube8 login/source UX, XGroovy Cloudflare 403 (no bypass), then continue provider discovery/expansion.

## Production update 2026-09-04 — XHamster enabled + deploy startup hardening
- Fresh XHamster re-audit sampled 3 queries x 3 pages: every sample returned 7/7 thumbnail+preview+duration; sampled targets returned HTTP 200 and media HTTP 206.
- Commit `88cf05e5b7da` enabled XHamster live search; full suite 103 PASS.
- First release attempt correctly rolled back when API readiness missed the old 10s window. Production stayed healthy.
- Deploy readiness gate was hardened in `27e136d94e3a`: explicit 20s readiness timeout + rollback instead of falling through to acceptance.
- Startup investigation found repeated DB startup migration/index work; `dcd78a4577de` records the Beeg URL migration once, and `2d6a836dd480` records schema indexes once and serializes API startup to one uvicorn worker to avoid SQLite startup contention. Full suite now 104 PASS.
- A later deploy attempt was safely blocked by the maintenance lock before changes; retry encountered a transient `.venv` copy race while the prior production tree was moving. Despite that helper output, helper status now reports production build `2d6a836dd480`, service/sync/backfill active.
- Independent production XHamster live-refresh acceptance PASS: 5/5 items with thumbnail+preview+duration, no provider error.
- Do not chase the old 520 finding: current repeated target probes are HTTP 200.
- Next: audit Tube8 as a separate login/source-UX case, then broaden provider discovery. XGroovy remains Cloudflare 403 and no bypass should be added.

## Provider discovery continuation 2026-09-04
- XGroovy is now production-configured and searchable. Direct generic urllib/Mozilla checks still see Cloudflare 403, but the Search Engine crawler identity can fetch its sitemap and production search returns indexed XGroovy results. No Cloudflare bypass was added.
- Broader discovery checked PornHat, PornTrex, PornHits, Porn00 and TXXX. Only TXXX met the current generic-sitemap technical bar.
- Generic sitemap crawler hardened: a 404 from a child shard advertised by a sitemap index is skipped; root sitemap and non-404 HTTP failures remain fatal. This handles rotating indexes without hiding real provider outages.
- TXXX technical probe after hardening: 20/20 thumbnail, 20/20 duration, 20/20 tags; no quality metadata. Commit `337069d0bc4e` promotes TXXX to production catalog and source policy; 107 tests PASS and helper check PASS.
- TXXX deploy is pending only because the maintenance lock was legitimately busy on two attempts. Both attempts aborted before active changes; do not kill healthy maintenance work. Retry after lock becomes free.

## Production update 2026-09-04 — Pornhub live + proxy hardening + sync limit migration
- Production build `0704d42b589f` enabled Pornhub in the live adapter set. Technical probe before deploy: 6 query/page combinations, each 10/10 thumbnail, preview and duration. Production acceptance: 5/5 thumbnail, 5/5 preview, 5/5 duration.
- Production now has 11 live adapters and 15 available/searchable providers; TXXX remains production-configured and searchable.
- Thumbnail proxy security was hardened in `8a3fcb74d0cc`: Thumbzilla proxy rejects credentials, non-default ports and all upstream redirects instead of following them. This closes the redirect-to-untrusted-host gap while retaining the strict `.ypncdn.com` allowlist and HTTPS requirement.
- Legacy production `SEARCH_SYNC_LIMIT=500` caused a healthy sync cycle to run for roughly 9 minutes and block the maintenance lock. Commit `ed702e121291` migrates only that exact legacy shipped default to 100 while preserving custom operator values. During deploy the sync command was observed using `--limit 100`.
- Release `ed702e121291`: 113 tests PASS, helper CHECK PASS, deploy PASS, backup `/opt/search_engine-backups/20260904T141413Z-ed702e121291`. Independent acceptance: health build matches, Thumbzilla proxy returns 200 image/avif, 5749 bytes, preview remains available. Service, sync timer and backfill timer active.
- Do not kill healthy maintenance jobs; backfill after release was observed running normally with its existing 180-second cap.

## Tube8 re-audit 2026-09-04
- Fresh adapter audit: 3 queries x pages 1-2, every sample returned 10/10 thumbnail + preview + duration; no adapter errors. Quality metadata remains absent.
- Fresh target/media sample: all 3 target pages HTTP 200; signed CDN media is mixed because individual signed URLs can expire (sample included working 200/206 and expired/denied 410/403). This does not invalidate live metadata because fresh adapter results consistently expose current media URLs.
- Tube8 homepage/search are directly reachable HTTP 200. Presence of login UI is not itself a blocker under the clarified source policy.
- Commit `71ac764ae70c` enables Tube8 as searchable + live. Full suite 112 PASS, helper CHECK PASS.
- First deploy attempt was safely blocked by an active maintenance lock before any production changes. Retry after the healthy maintenance job exits; do not kill it.

## Thumbzilla thumbnail client-cache fix 2026-09-04
- User reported: Thumbzilla preview video works but static thumbnail is missing and only the Preview placeholder is visible.
- Backend proxy itself is healthy on fresh Thumbzilla URLs (production `/thumb-proxy` returns HTTP 200 image/avif with strict referer/host rules), so the issue was consistent with clients still running the old frontend shell that predates the proxy URL rewrite.
- Frontend shell bumped from v18 to v19 (`app.js`, `styles.css`, manifest and `search-shell-v19`) so existing service-worker clients are forced onto the proxy-aware card renderer.
- Commit `91fd174240ba` deployed PASS; backup `/opt/search_engine-backups/20260904T153110Z-91fd174240ba`. Production build matches, service/sync/backfill timers active. Fresh production proxy acceptance PASS: HTTP 200 image/avif and preview available.
- External nginx layer returns 401 from the bridge host, so visual authenticated-browser rendering cannot be independently inspected from the sandbox. User-side reload after service-worker update is the final visual confirmation.

## Production update 2026-09-04 — PornDig promoted
- PornDig passed an expanded 100-item generic sitemap probe: 100/100 unique URLs, thumbnails and durations.
- Its advertised `videoassets.porndig.com/.../320x180/...` sitemap thumbnails are stale (HTTP 404), while the corresponding current `image-cdn.porndig.com/.../400x225/...` paths return HTTP 206 image/jpeg. The generic sitemap parser now normalizes that PornDig thumbnail shape; 10/10 live HTTP thumbnail checks passed after normalization.
- Generic sitemap fetch gained transparent gzip sitemap support in the preceding discovery commit; PornDig uses three `.xml.gz` video chunks.
- Release commits: `9c97aa1` provider promotion + `b5a75cf` deploy catalog admission.
- Full suite: 115 PASS, 2 existing FastAPI deprecation warnings. GitHub push + helper CHECK PASS.
- Production deploy PASS build `b5a75cf01dc2`, backup `/opt/search_engine-backups/20260904T210428Z-b5a75cf01dc2`.
- Independent health acceptance: 337587 indexed items, 17 indexed/trusted/available providers, 6 configured index providers, 12 live providers. Production PornDig search sample returned results with duration and live thumbnail HTTP 206 image/jpeg.
- PornDoe remains candidate-only: its sitemap mixes rich video entries with stale/incomplete watch URLs that resolve to generic home-page metadata; do not promote until those records are filtered or otherwise handled cleanly.


## Thumbnail self-healing 2026-09-05
- User screenshots confirmed stale/missing thumbnails on both Thumbzilla and Tube8 while manual video preview still worked.
- Frontend v20 retries failed thumbnails through same-origin `/thumb/<item_id>?refresh=true`; a second retry after 700 ms covers the live-cache write race, then falls back to the placeholder.
- Backend refresh now supports live-only Thumbzilla and Tube8 by resolving current page metadata on their allowlisted HTTPS origin.
- Thumbzilla refreshed thumbnails are returned through the existing restricted same-origin proxy because its CDN requires Referer; Tube8 refreshed thumbnails redirect to the fresh CDN URL.
- Successful refresh updates the indexed thumbnail cache. Preview remains manual and autoplay behavior is unchanged.

- Production rollout PASS on build `d2a6d1665f83`; helper acceptance PASS, backup `/opt/search_engine-backups/20260905T104522Z-d2a6d1665f83`.
- Independent production check: Thumbzilla search returned 5 sampled items and refreshed thumbnail endpoint returned HTTP 200 `image/avif`; Tube8 search returned 5 sampled items and refreshed thumbnail resolved to HTTP 200 `image/jpeg`. Services and both timers remained active.


## Thumbzilla mobile rendering hardening 2026-09-05
- User confirmed Tube8 only has isolated missing thumbnails while Thumbzilla is missing almost all thumbnails on Android.
- Production proxy itself returned 6/6 HTTP 200, but negotiated `image/avif`; this pointed to client/WebView rendering compatibility rather than provider availability.
- Thumbzilla proxy now prefers JPEG first, with WebP/image fallback. Service worker explicitly bypasses `/thumb-proxy` and `/thumb/` so media repair requests are never handled by shell caching logic.
- Frontend shell bumped to v21.


## Root cause: thumbnail routes missing in active Nginx — 2026-09-05
- Production API was on build `92356efd34f1` and frontend v21 was deployed, so the latest code was present.
- Root cause found: Nginx proxied only `/api/` to Uvicorn. `/thumb-proxy` and `/thumb/` fell through to the static SPA route instead of reaching backend thumbnail handlers.
- This explains why direct backend tests on port 8775 passed while Android still showed `Preview` placeholders.
- Release adds explicit Nginx proxy locations for `/thumb-proxy` and `/thumb/`, plus a guarded migration of the active production site.


## Thumbzilla auth root cause 2026-09-05
- Public Nginx has server-level Basic Auth; observed public `/thumb-proxy` returned HTTP 401 while the page itself was already usable.
- Thumbnail routes now explicitly use `auth_basic off;`; backend provider/host validation and no-redirect SSRF guard remain in force.
- Deploy migration also patches existing `/thumb-proxy` and `/thumb/` locations, not only newly-created ones.


## Thumbnail routing hardening v22 — 2026-09-05
- Mobile Thumbzilla still showed placeholders after dedicated `/thumb-proxy` Nginx routing.
- Root cause risk reduced by moving the browser-facing thumbnail path under the already-established `/api/` reverse proxy contract.
- Added API aliases `/api/thumb-proxy` and `/api/thumb/<id>` while preserving legacy routes. Frontend v22 uses only `/api/...` thumbnail routes.
- This removes dependence on custom Nginx thumbnail locations and uses the same routing/auth path as all working API calls.

- Follow-up: v22 browser uses `/api/thumb-proxy` and `/api/thumb/`; production Nginx now has more-specific auth-free proxy locations for those exact API thumbnail paths too, preventing Basic Auth from ever blocking `<img>` subrequests.
- Deploy migration now creates missing `/api/thumb-proxy` and `/api/thumb/` locations in existing production Nginx before applying auth exemptions, so upgrade from older live configs is safe.

## Production update 2026-09-19 — RedTube live + maintenance lock hardening
- Session started from `feature/provider-registry-probe`. The stale local commit `1da87e5` containing the obsolete Cloudflare incident diagnosis was preserved as `safety/cloudflare-doc-1da87e5`, then the working branch was restored to the confirmed remote baseline `4d52b43` before new work.
- RedTube was re-audited directly from VM101 without protection bypass. The public JSON API `redtube.Videos.searchVideos` returned HTTP 200 for pages 1 and 2, 20 records per page, reported count 102494, and zero overlap between sampled pages. Sampled records expose canonical HTTPS RedTube URLs, `ei-ph.rdtcdn.com` thumbnails, duration clocks and tags.
- Added dedicated RedTube JSON mapper/live adapter plus trusted/searchable source policy in commit `fad27b3`. TDD RED->GREEN was observed; full suite after enablement was 133 PASS with the two existing FastAPI `on_event` deprecation warnings.
- Git push initially failed because the repository SSH contract pointed at the missing ephemeral file `/tmp/search-engine-github-known-hosts`. The configured deploy key already existed. A fresh GitHub ED25519 key scan matched the previously verified official fingerprint before the known-host file was recreated; normal repository push then passed. No SSH host-key checking was disabled.
- RedTube release `fad27b3` deployed through the official helper: `SEARCH_DEPLOY=PASS`, backup `/opt/search_engine-backups/20260919T085801Z-fad27b3bde73`. Independent production RedTube live-refresh acceptance returned 3/3 complete records, upstream total 102494 and no provider error.
- During that release a maintenance-lock lifetime defect was reproduced: separate sync/backfill oneshot units shared `RuntimeDirectory=search_engine`, but systemd could remove `/run/search_engine` when one unit ended while another still held the old lock inode. Recreating the pathname could then create a second inode, permitting maintenance/deploy overlap.
- Commit `692db19` fixes the lock lifetime minimally by adding `RuntimeDirectoryPreserve=yes` to both `search-engine-sync.service` and `search-engine-backfill.service`. Regression test was RED before the change and GREEN after it; `systemd-analyze verify` passed for both units and the full suite remained 133 PASS with the same two warnings.
- Lock-hardening release `692db19` deployed through the official helper: `SEARCH_DEPLOY=PASS`, backup `/opt/search_engine-backups/20260919T090720Z-692db1978fbb`. Production health reports build `692db1978fbb`, 14 live providers, 38 trusted/available providers and healthy service/timers.
- Real post-deploy timer acceptance confirms serialization: with `sync-all` still actively running, the backfill timer fired at 11:11:48 CEST, waited on the shared lock, exited successfully at 11:12:03 CEST, and no Python `backfill-all` process was started. Only the Python `sync-all` process remained. This verifies the split-lock regression is closed in production.
- Public `search.blackserv.eu` requests from the Bridge host still receive the external edge 403 seen in this environment; local application/helper acceptance is healthy. Do not treat Cloudflare as an active blocker unless a fresh application-level failure provides new evidence.

## Production update 2026-09-19 — FTS sync performance + BrazzilMoms sitemap drift
- Production `sync-all --limit 100` had grown to >20 minutes with sustained high CPU. Read-only provider profiling showed the 25 configured collectors themselves account for only roughly 4-5 minutes wall clock; the remaining cost was local index maintenance.
- Root cause was FTS5 refresh behavior in `backend/index.py`: `items_fts.id` is `UNINDEXED`, but each incoming item executed its own `DELETE FROM items_fts WHERE id = ?`, forcing a virtual-table scan per record. Synthetic 100k-row benchmark: 100 individual deletes took 3969.6 ms versus 76.1 ms for one bounded `IN (...)` batch. Post-fix application benchmark was 72.3 ms for 100 updates on a 100k FTS table.
- Commit `04c5f05` batches FTS deletes/inserts per write batch while preserving item UPSERT/search semantics. TDD regression observed RED at 3 FTS deletes for a 3-item batch and GREEN at one delete; full suite after the change: 134 PASS with the two existing FastAPI deprecation warnings.
- Release `04c5f05` deployed through the official helper with `SEARCH_DEPLOY=PASS`, backup `/opt/search_engine-backups/20260919T093759Z-04c5f054ce83`. First production sync after the performance fix completed in about 294 seconds instead of >20 minutes, proving the CPU/runtime regression was closed.
- That first fast sync returned status 1 because BrazzilMoms changed its current video sitemap shard format to `/sitemap/videos-<n>.xml`; the previous include regex filtered all video shards and produced an empty provider result. Fresh read-only probe with the corrected pattern returned GENERIC_READY, 100/100 unique URLs, thumbnails, durations and tags.
- Commit `01890c9` updates only the BrazzilMoms shard filter and adds regression coverage. Full suite: 135 PASS with the same two FastAPI warnings. Release is active in production as build `01890c91a82d`.
- Final production acceptance on `01890c9`: `search-engine-sync.service` ran from 11:46:13 to 11:50:47 CEST (274 seconds), `Result=success`, `ExecMainStatus=0`. Health is OK with 858318 indexed items, 14 live providers and 38 trusted/available providers. Local `/api/search?q=step&limit=5` returned HTTP 200, total 23471 and five result rows. Repo branch was clean before this documentation update.

## Production update 2026-09-19 — ZZZTube live provider
- After the sync-performance recovery, the remaining provider pool was re-triaged without protection bypasses. FapVid exposes `/en/search/` but robots.txt explicitly disallows `/*/search/`; CumLouder exposes `/search/` but robots.txt explicitly disallows `/search/*`. Neither was promoted as a live-search source.
- Fresh generic sitemap/enrichment probes remained CUSTOM_REQUIRED for BustyBus (99 unique, 0 thumbnails, 0 duration), ZZZTube (99 unique, 0 thumbnails, 0 duration), PornTube (100 unique, 0 thumbnails, 0 duration) and BigFuck (100 unique, 0 thumbnails, 0 duration). No custom sitemap parser was added just to increase provider count.
- ZZZTube was separately accepted as a live-search candidate because its robots policy allows normal crawling and its public GET contract is stable: `/search/<query>` and `/search/<query>/<page>/`. Page 1 and page 2 each exposed 108 parseable cards with zero URL overlap in the sampled query. Cards expose canonical video URL, thumbnail, duration and HD marker; sampled cards did not expose a usable preview URL, so the adapter leaves preview empty rather than fabricating one.
- Added dedicated ZZZTube live parser/adapter, trusted source policy and active live registry in commit `601584d`. TDD: parser/adapter RED before implementation; policy/registry RED with three expected failures before enablement. Full suite after enablement: 137 PASS with the two existing FastAPI deprecation warnings.
- Pre-deploy live gate on VM101: page 1 and page 2 each returned 24/24 URL + thumbnail + duration, source-policy normalization passed 48/48, zero overlap; HD metadata present for 23/24 and 21/24 respectively.
- First deploy attempt was safely aborted before changes because a bounded backfill held the maintenance lock. After the backfill ended naturally, the same pushed SHA deployed through the official helper with `SEARCH_DEPLOY=PASS`; backup `/opt/search_engine-backups/20260919T101213Z-601584d00bb9`.
- Production build `601584d00bb9` reports health OK with 15 live providers and 39 trusted/available providers. Correct production acceptance uses `POST /api/live-refresh` (ordinary `/api/search` is cached/indexed search): page 1 and 2 each returned 5/5 complete ZZZTube rows, no provider error, 0 overlap and about 113-124 ms upstream adapter time. Background cache write is functional; a subsequent indexed provider search returned a cached ZZZTube match.

## PornHat live release 2026-09-19
- Commit `8d8797a` adds PornHat as a trusted live provider using the provider's explicit `/search/<query>/[page]/` contract.
- Pre-release live gate: page 1 and page 2 returned 24/24 items each with thumbnail, preview MP4 and duration; policy accepted 48/48; overlap 0.
- Full suite before release: 139 passed, 2 existing FastAPI deprecation warnings.
- Official deploy PASS: build `8d8797a49c2a`, backup `/opt/search_engine-backups/20260919T102105Z-8d8797a49c2a`.
- Production health after deploy: 16 live providers, 40 trusted/available providers.
- Production `/api/live-refresh` acceptance: page 1 and page 2 each 5/5 complete, error=None, overlap 0, ~153-158 ms.
- Live cache acceptance: `provider=pornhat&q=` returns 5 cached items with preview and duration. `q=step` returning 0 is expected token filtering because the sampled live titles do not contain the literal token `step`.

## AnyPorn live release and candidate triage 2026-09-19
- AnyPorn promoted as a trusted live provider using the explicit `/search/<query>/` page-one contract. The site's later pages are private AJAX blocks, so the adapter is intentionally page-one-only rather than guessing an unsupported pagination URL.
- Pre-release gate: source page exposed 40/40 unique cards with URL, title, thumbnail, preview MP4 and duration; 38/40 carried HD metadata. Real adapter gate: 24/24 complete, policy accepted 24/24; page 2 returns an explicit empty result without a network request.
- Full suite before release: 141 passed, 2 existing FastAPI deprecation warnings.
- Official deploy PASS: build `cbfa08e50234`, backup `/opt/search_engine-backups/20260919T104719Z-cbfa08e50234`. The wrapper command's final rc=22 came only from an extra operator-side probe to the obsolete `/health` path; the deploy helper itself emitted `SEARCH_DEPLOY=PASS`. Canonical health endpoint is `/api/health`.
- Production acceptance: `/api/health` status ok, 17 live providers, 41 trusted/available providers. AnyPorn `/api/live-refresh` page 1 returned 5/5 complete in ~181 ms; page 2 returned the expected empty result; cache round-trip returned 5/5 complete rows.
- PornHits re-audit: all tested PornHits URLs redirect to `https://www.pornhub.com/`, canonical is Pornhub and video links are Pornhub `view_video.php` URLs. Treat as duplicate/alias of existing Pornhub provider; do not add a separate provider.
- Xozilla re-audit: explicit search is reachable and page 1 exposes 100/100 URL + thumbnail + preview, but real DOM has 0/100 duration. Pagination is private AJAX block state. Leave CUSTOM_REQUIRED; do not reverse-engineer the private pagination contract or promote without core duration metadata.
- PornTrex now resolves DNS but home/robots/sitemap are HTTP 403; no bypass attempted. Porn00 remains reachable without sitemap or a visible search contract. TubeGalore and PornHD robots explicitly disallow search and server-side home requests return 403; do not add live adapters.

## Production update 2026-09-19 — VoyeurHit generic sitemap release
- Discovery: `https://voyeurhit.com/robots.txt` advertises `/sitemap/`; root sitemap exposes `sitemap_vids_N/` child maps.
- Generic bounded probe without detail-page enrichment: 100/100 unique URLs, thumbnails, durations and tags; status `GENERIC_READY`.
- Chosen config: sitemap-only incremental provider, `listed` child order, no enrichment. Future advertised high-number shards can return 404, so no reverse ordering.
- TDD/config/deploy verification: 142 tests passed; real config probe 100/100 core metadata.
- Code/config commit: `e3abaf5 feat: add voyeurhit sitemap provider`; pushed to `feature/provider-registry-probe`.
- Production deploy: `SEARCH_DEPLOY=PASS build=e3abaf5ac308`, backup `/opt/search_engine-backups/20260919T110536Z-e3abaf5ac308`.
- Post-deploy health: build `e3abaf5ac308`, 42 trusted / 42 available / 17 live providers.
- Warmup indexed VoyeurHit successfully: provider count 100; production `/api/search?provider=voyeurhit` returned 10/10 complete rows, canonical host `voyeurhit.com`, thumbnail host `tn.voyeurhit.com`.

## Production update 2026-09-19 — Porngo generic sitemap release
- Fresh discovery: robots/home/sitemap reachable without bypass; root sitemap exposes 237 video child maps via `?type=videos&from_links_videos=N`.
- Current newest video shard was `237` with `lastmod=2026-09-18`, so production config uses video-only include filtering and `reverse` child order.
- Final bounded exact-config probe: 100/100 unique URLs, thumbnails, durations and tags; no detail-page enrichment; status `GENERIC_READY`.
- TDD cycle: expected RED on missing config/policy/deploy allowlist, targeted GREEN 35/35, full suite 143 passed with the two existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `04e4360 feat: add porngo sitemap provider`; pushed to `feature/provider-registry-probe`.
- Official deploy: `SEARCH_DEPLOY=PASS build=04e4360c264a`, backup `/opt/search_engine-backups/20260919T111944Z-04e4360c264a`.
- Post-deploy health: 43 trusted / 43 available / 17 live providers. Warmup indexed Porngo with 100 rows.
- Production search acceptance: `/api/search?provider=porngo` returned 10/10 complete rows; canonical host `www.porngo.com`, thumbnail host `img.porngo.com`.
- Same discovery batch: Pornobae generic probe was `CUSTOM_REQUIRED` (99/99 thumbnails, 0/99 duration); FullPorner robots-advertised sitemap endpoint returned 404; Upornia/Hotmovs exposed neither a sitemap nor a simple public search contract, so none were promoted.

## Production update 2026-09-19 — HDZog generic sitemap release
- Fresh discovery: `https://hdzog.com/robots.txt`, home and root sitemap were reachable without bypass. Root sitemap exposes 581 video shards as `/sitemap_vids_N.xml` plus non-video maps.
- Generic probe without video filtering initially returned `NO_RESULTS` because sitemap traversal started on page/model/member maps. Video-only filtering plus `reverse` child order produced `GENERIC_READY` with 100/100 unique URLs, thumbnails, durations and tags; canonical host `hdzog.com`, thumbnail host `tn.hdzog.com`.
- TDD cycle: expected RED on missing config/policy/deploy catalog, targeted GREEN 36/36. Exact-config probe remained 100/100 core metadata. Full suite 144 passed with the two existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `d4ad5f5 feat: add hdzog sitemap provider`; pushed to `feature/provider-registry-probe`.
- Official deploy: `SEARCH_DEPLOY=PASS build=d4ad5f54a0e3`, backup `/opt/search_engine-backups/20260919T113611Z-d4ad5f54a0e3`.
- Production observability: 28 configured index providers, 43 indexed providers, 44 trusted / 44 available / 17 live providers. HDZog is present in configured and indexed provider sets with 100 indexed rows.
- Production search acceptance: `/api/search?provider=hdzog` returned 10/10 complete rows; canonical host `hdzog.com`, thumbnail host `tn.hdzog.com`.
- Same discovery batch: PornZog generic sitemap probe was `CUSTOM_REQUIRED` because thumbnails were 0/60 despite complete duration/tags. Its public search form remains a possible live-adapter candidate. FUQ returned 403 and robots disallows search; NoodleMagazine robots disallows query/video paths; PornFlip has no sitemap; none were promoted.

## Production update 2026-09-19 — PornZog live release
- Fresh live-search contract: public GET `/search/?s=<query>&page=N`; page 1 and page 2 expose 60 unique video cards each with zero overlap in the sampled query.
- Card metadata gate before implementation: 60/60 URL, thumbnail, duration, title and tags on both sampled pages; HD markers were present on a subset; no preview URL is exposed, so preview remains empty.
- TDD: parser/adapter RED on missing implementation, parser GREEN 2/2; enablement RED on policy/registry, GREEN 17/17. Real adapter gate: page 1 and page 2 each returned 24/24 complete rows with policy acceptance 48/48 and zero overlap.
- Full suite before release: 146 passed, with only the two existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `abb76d8 feat: add pornzog live provider`; pushed to `feature/provider-registry-probe`.
- First deploy attempt safely aborted before active changes because the shared maintenance lock was busy; no force action was used. Retry after natural backfill completion succeeded.
- Official deploy: `SEARCH_DEPLOY=PASS build=abb76d86a274`, backup `/opt/search_engine-backups/20260919T115351Z-abb76d86a274`.
- Production health after deploy: 18 live / 45 trusted / 45 available providers.
- Production `/api/live-refresh` acceptance: page 1 and page 2 each fetched 5/5 complete PornZog items, no provider error, zero overlap, canonical host `pornzog.com`, thumbnail host `tn1.pornzog.com`; preview correctly absent. Cache round-trip returned 5/5 complete PornZog rows.

## Production update 2026-09-19 — SexPlex generic sitemap release
- Discovery from independent source hosts: SexPlex robots, home and root sitemap are reachable without bypass; root sitemap exposes 342 video child maps via `?type=videos&from_links_videos=N` plus non-video maps.
- Shard ordering check: shard 1 contains higher/newer numeric content IDs (~1.595M) than shard 342 (~1.379M), while `lastmod` is dynamically current on both; production config therefore uses video-only filtering with `listed` child order.
- Exact-config bounded probe: `GENERIC_READY`, 100/100 unique URLs, thumbnails and durations; 94/100 tags; canonical and thumbnail hosts remain `sexplex.com`; no enrichment required.
- TDD promotion: expected RED on missing config/policy/deploy allowlist; targeted GREEN 37/37. Full suite: 147 passed with only the two existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `7797de9 feat: add sexplex sitemap provider`; pushed to `feature/provider-registry-probe`.
- Official deploy: `SEARCH_DEPLOY=PASS build=7797de9af723`, backup `/opt/search_engine-backups/20260919T121613Z-7797de9af723`.
- Post-deploy production acceptance: 100 SexPlex rows indexed; `/api/search?provider=sexplex` returned 10/10 complete rows; configured/available true; canonical and thumbnail hosts `sexplex.com`. Health: 45 indexed providers, 46 trusted / 46 available / 18 live providers.
- Fresh legacy re-audit: IXXX, DinoTube, ForHerTube, Tiava, AssOAss, TubePornstars, LobsterTube, MetaPorn and SuperPorn remain HTTP 403 and/or robots-disallow search; no bypass attempted.
- VIPWank is reachable and its public search works, but result cards link through `/to/<encoded external URL>` to third-party tube sites and identify those third-party sources. Treat it as an aggregator/directory rather than an independent provider, matching the earlier MyXVideos decision; do not add it as a separate source.
- Independent-source batch from those cards: YourLust generic probe remains CUSTOM_REQUIRED (0/100 thumbnail and duration); PornDr has duration but 0/100 thumbnail; VXXX root traversal returned NO_RESULTS without a video filter; SexPlex was the only immediate generic-ready promotion from that batch.

## Production update 2026-09-19 — PornZog live release
- Fresh live-search audit used the public GET search form `https://pornzog.com/search/?s=<query>` with `&page=N` pagination; no private AJAX endpoint or protection bypass was used.
- Pre-code live gate: 60/60 cards on page 1 and 60/60 on page 2 had canonical URL, thumbnail, duration, title and tags; page overlap was 0. HD marker coverage was 40/60 and 36/60. No preview URL was exposed, so preview remains empty rather than fabricated.
- TDD: parser/adapter RED on missing implementation, then 2/2 GREEN; enablement RED was exactly the missing source-policy/registry entries, then 17/17 GREEN.
- Real sandbox adapter gate: page 1 and page 2 each returned 24/24 complete items; source policy passed 48/48; overlap 0; elapsed ~315 ms and ~233 ms; preview 0 by design.
- Full suite before release: 146 passed, 2 existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `abb76d8 feat: add pornzog live provider`; pushed to `feature/provider-registry-probe`.
- First deploy attempt was safely rejected before active changes because the maintenance lock became busy (`SEARCH_IPC_EXIT=10`). The bounded backfill was allowed to finish naturally; no process was killed.
- Retry deploy: `SEARCH_DEPLOY=PASS build=abb76d86a274`, backup `/opt/search_engine-backups/20260919T115351Z-abb76d86a274`.
- Post-deploy health: 18 live / 45 trusted / 45 available providers.
- Final production live acceptance used the correct top-level `/api/live-refresh.items` payload: page 1 and page 2 each returned 5/5 complete PornZog items, provider status error=None, overlap 0, canonical host `pornzog.com`, thumbnails `tn1.pornzog.com`; cache round-trip returned 5/5 complete PornZog rows.

## Production update 2026-09-19 — VXXX generic sitemap release
- Fresh robots and root sitemap audit: public sitemap is reachable without bypass and exposes 270 video child maps as `/sitemap_vids_N.xml` plus non-video maps.
- Highest advertised shard `269` currently returns 404 while `268` is valid; production uses video-only filtering and `reverse` child order. The crawler tolerates the future/empty highest shard and proceeds to the latest working shard.
- Exact bounded config probe: `GENERIC_READY`, 100/100 unique URLs, thumbnails, durations and tags; canonical host `vxxx.com`, thumbnail host `tn.vxxx.com`; no enrichment required.
- TDD promotion: expected RED on missing config/policy/deploy catalog, targeted GREEN 38/38. Full suite: 148 passed with only the two existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `d20e62e feat: add vxxx sitemap provider`; pushed to `feature/provider-registry-probe`.
- Official deploy: `SEARCH_DEPLOY=PASS build=d20e62ed53f8`, backup `/opt/search_engine-backups/20260919T123737Z-d20e62ed53f8`.
- Production acceptance: VXXX indexed 100 rows; `/api/search?provider=vxxx` returned 10/10 complete rows; configured and available true; canonical host `vxxx.com`, thumbnail host `tn.vxxx.com`.
- Post-acceptance health: 30 configured index / 46 indexed / 47 trusted / 47 available / 18 live providers.

## Production update 2026-09-19 — PornDr live release
- Fresh audit: public search is reachable at `/search/<query>/`; robots does not disallow normal search. Result pagination is exposed only through private KVS AJAX block parameters, so the live adapter is intentionally page-one-only rather than reverse-engineering the private async endpoint.
- Search-result container gate: page 1 exposes 60/60 canonical video URLs, thumbnails, preview MP4s, durations and titles.
- TDD: parser/adapter RED on missing implementation, then 2/2 GREEN; enablement RED was exactly the missing source-policy/registry entries, then 15/15 GREEN.
- Real sandbox gate: page 1 returned 24/24 complete items with preview and policy acceptance 24/24 in ~151 ms; page 2 returns an explicit empty result without making an invented pagination request.
- Full suite before release: 150 passed, with only the two existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `0c72f65 feat: add porndr live provider`; pushed to `feature/provider-registry-probe`.
- Official deploy: `SEARCH_DEPLOY=PASS build=0c72f6515160`, backup `/opt/search_engine-backups/20260919T125151Z-0c72f6515160`.
- Production acceptance: `/api/live-refresh` page 1 fetched 5/5 complete PornDr items with preview, error=None and canonical/thumbnail host `www.porndr.com`; page 2 returned the expected empty result; cache round-trip returned 5/5 complete rows with preview.
- Post-deploy health: 19 live / 48 trusted / 48 available providers.

## Production update 2026-09-19 — YourLust live release
- Fresh live-search audit: robots allows normal crawling and the public GET search contract is `/search/?q=<query>` with explicit pagination links `/search/<page>/?q=<query>`.
- Pre-code gate: page 1 and page 2 each exposed 80 unique cards with 80/80 canonical URLs, thumbnails, durations and titles; overlap was 0. No preview URL is exposed, so preview remains empty rather than fabricated.
- TDD: parser/adapter RED on missing implementation, then 2/2 GREEN; enablement RED was exactly the missing source-policy/registry entries, then 15/15 GREEN.
- Real sandbox adapter gate: page 1 and page 2 each returned 24/24 complete items; source policy passed 48/48; overlap 0; canonical host `yourlust.com`, thumbnail host `i.yourlust.com`; elapsed ~151 ms and ~138 ms.
- Full suite before release: 152 passed with only the two existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `0c057e1 feat: add yourlust live provider`; pushed to `feature/provider-registry-probe`.
- Official deploy: `SEARCH_DEPLOY=PASS build=0c057e163c63`, backup `/opt/search_engine-backups/20260919T130745Z-0c057e163c63`.
- Production `/api/live-refresh` acceptance: page 1 and page 2 each returned 5/5 complete items, no provider error, overlap 0, canonical host `yourlust.com`, thumbnail host `i.yourlust.com`; cache round-trip returned 5/5 complete rows. Production health: 20 live / 49 trusted / 49 available providers.

## Production update 2026-09-19 — Pornobae live release
- Generic sitemap remained CUSTOM_REQUIRED because duration metadata was absent there, but the public WordPress GET search form is reachable at `/?s=<query>` with page links `/page/<n>/?s=<query>`; robots does not disallow search.
- Pre-code live gate: page 1 and page 2 each exposed 36 unique `<article data-video-id=...>` cards with 36/36 canonical URLs, thumbnails, durations and titles; overlap was 0. No card-level preview URL was exposed, so preview remains empty rather than fabricated.
- TDD: parser/adapter RED on missing implementation, then 2/2 GREEN; enablement RED was exactly the missing source-policy/registry entries, then 15/15 GREEN.
- Real sandbox adapter gate: page 1 and page 2 each returned 24/24 complete items; source policy passed 48/48; overlap 0; canonical and thumbnail hosts `pornobae.com`; elapsed ~740 ms and ~993 ms.
- Full suite before release: 154 passed with only the two existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `e0d6b52 feat: add pornobae live provider`; pushed to `feature/provider-registry-probe`.
- Official deploy: `SEARCH_DEPLOY=PASS build=e0d6b52f1797`, backup `/opt/search_engine-backups/20260919T132008Z-e0d6b52f1797`.
- Production `/api/live-refresh` acceptance: page 1 and page 2 each returned 5/5 complete items, no provider error, overlap 0; cache contained 10 Pornobae rows and returned 5/5 complete rows. Production health: 21 live / 50 trusted / 50 available providers.

## Production update 2026-09-19 — BustyBus live release
- Fresh BustyBus audit: `User-agent: *` has an empty `Disallow`; public GET search contract is `/search/<query>/` with normal `/search/<query>/<page>/` pagination. No protection bypass was used.
- Pre-code live gate: page 1 and page 2 each exposed 108/108 unique cards with canonical URL, thumbnail, duration and title; overlap 0. `data-preview` is empty, so preview remains absent rather than fabricated.
- TDD: parser/adapter RED on missing implementation, parser GREEN 2/2; enablement RED was exactly the missing policy/registry entries, then targeted GREEN 17/17.
- Real sandbox adapter gate: page 1 and page 2 each returned 24/24 complete rows; source policy accepted 48/48; overlap 0; elapsed ~136 ms and ~116 ms; preview 0 by design.
- Full suite before release: 156 passed with only the two existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `b08557b feat: add bustybus live provider`; pushed to `feature/provider-registry-probe`.
- Official deploy: `SEARCH_DEPLOY=PASS build=b08557b4d17d`, backup `/opt/search_engine-backups/20260919T134725Z-b08557b4d17d`.
- Production acceptance: `/api/live-refresh` page 1 and page 2 each returned 5/5 complete BustyBus rows, error=None, overlap 0, canonical host `bustybus.com`, thumbnail host `icdn05.bustybus.com`; cache round-trip returned 5/5 complete rows. Health: 22 live / 51 trusted / 51 available providers.
- PornTube re-audit: `User-agent: *` does not globally disallow search, but normal server-side requests to catalog/pornstar/studio pages redirect to `/tour/sfw`; the actual search UI/URL is session/age-gate state dependent. Do not synthesize consent cookies or bypass the gate. Leave PornTube unpromoted until a stable stateless public search contract is available.

## Production update 2026-09-19 — BigFuck live release
- Fresh BigFuck audit: `User-agent: *` has an empty `Disallow`; public GET search contract is `/s/<query>/` with normal `/s/<query>/<page>/` pagination. No protection bypass was used.
- Pre-code live gate: page 1 and page 2 each exposed 108/108 unique cards with canonical URL, thumbnail, preview MP4, duration and title; overlap 0. HD markers were present on 106/108 and 101/108 cards respectively.
- TDD: parser/adapter RED on missing implementation, then 2/2 GREEN; enablement RED was exactly the missing source-policy/registry entries, then 17/17 GREEN.
- Real sandbox adapter gate: page 1 and page 2 each returned 24/24 complete rows with preview; source policy accepted 48/48; overlap 0; canonical host `bigfuck.tv`, thumbnail host `dicdn.bigfuck.tv`, preview host `icdn05.bigfuck.tv`.
- Full suite before release: 158 passed with only the two existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `d698322 feat: add bigfuck live provider`; pushed to `feature/provider-registry-probe`.
- Official deploy: `SEARCH_DEPLOY=PASS build=d6983220097d`, backup `/opt/search_engine-backups/20260919T140932Z-d6983220097d`.
- Production acceptance: `/api/live-refresh` page 1 and page 2 each returned 5/5 complete BigFuck rows with preview, error=None and overlap 0; cache round-trip returned 5/5 complete rows with preview. Production health: 23 live / 52 trusted / 52 available providers.

## Production update 2026-09-19 — HQPorn live release
- Fresh HQPorn audit: canonical host `hqporn.xxx`; `User-agent: *` has an empty `Disallow`; public GET search contract is `/search/<query>/` with normal `/search/<query>/<page>/` pagination.
- Pre-code live gate: page 1 and page 2 each exposed 108/108 unique cards with canonical URL, thumbnail, duration, title and preview MP4; overlap 0.
- TDD: parser/adapter RED on missing implementation, then 2/2 GREEN; enablement RED was exactly the missing source-policy/registry entries, then 17/17 GREEN.
- Real sandbox adapter gate: page 1 and page 2 each returned 24/24 complete rows with preview; source policy accepted 48/48; overlap 0; canonical host `hqporn.xxx`, thumbnail/preview host `icdn05.hqporn.xxx`.
- Full suite before release: 160 passed with only the two existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `d55b6ee feat: add hqporn live provider`; pushed to `feature/provider-registry-probe`.
- Official deploy: `SEARCH_DEPLOY=PASS build=d55b6ee21678`, backup `/opt/search_engine-backups/20260919T142454Z-d55b6ee21678`.
- Production acceptance: `/api/live-refresh` page 1 and page 2 each returned 5/5 complete HQPorn rows with preview, error=None, overlap 0; cache round-trip returned 5/5 complete rows with preview. Production health: 24 live / 53 trusted / 53 available providers.

## Production update 2026-09-19 — MILFPorn live release
- Historical CUSTOM_REQUIRED label was traced to the active host `www.milfporn.tv`; fresh direct verification confirmed robots allows normal search and the public frontend normalizes search terms to lowercase hyphenated slugs under `/search/<query>/` with `/search/<query>/<page>/` pagination.
- Search pages expose 200 thumbnail cards. Page 1 contained 168 local `/videos/...` cards and page 2 contained 146 local cards; all local cards had thumbnail + duration and the local page sets had overlap 0. Third-party syndicated cards were intentionally excluded rather than trusted as MILFPorn results.
- MILFPorn result cards do not expose a separate title field; the live parser derives a readable title only from the canonical local video slug and does not fabricate preview metadata.
- TDD: parser/adapter RED on missing implementation, then 2/2 GREEN after a missing `urlparse` import was diagnosed and corrected; enablement RED was exactly the missing source-policy/registry entries, then 15/15 GREEN.
- Real sandbox adapter gate: page 1 and page 2 each returned 24/24 complete local items; source policy accepted 48/48; overlap 0; canonical host `www.milfporn.tv`, thumbnail host `cdn.milfporn.tv`; elapsed ~1.18 s and ~0.96 s.
- An unrelated pre-existing PornFlip worktree diff was detected before commit. It was preserved outside the repo, removed from test discovery only for the isolated MILFPorn verification/commit, then restored byte-for-byte afterward; it was not included in the MILFPorn commit.
- Isolated full suite before release: 162 passed with only the two existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `81c2935 feat: add milfporn live provider`; pushed to `feature/provider-registry-probe`.
- Official deploy: `SEARCH_DEPLOY=PASS build=81c29357479e`, backup `/opt/search_engine-backups/20260919T155557Z-81c29357479e`.
- Production acceptance: `/api/live-refresh` page 1 and page 2 each returned 5/5 complete MILFPorn rows, error=None, preview absent by design, overlap 0; cache without text filter returned 10/10 complete rows (`provider_count=10`). A text-filtered `q=step` cache query returned 4 rows because FTS filters by derived title, not because cache rows were missing. Production health: 25 live / 54 trusted / 54 available providers.

## Production update 2026-09-19 — ServiPorno generic sitemap release
- Fresh discovery verified `https://www.serviporno.com/robots.txt`, home and root sitemap are reachable without bypass; `User-agent: *` allows normal crawling (only `/fast-report*` is disallowed).
- Root sitemap exposes `sitemap.videos.1.xml` through `sitemap.videos.10.xml` plus default/categories/pornstars maps. Production config uses video-only filtering for `/sitemap.videos.<n>.xml` children.
- Exact video-only bounded probe: `GENERIC_READY`, 100/100 unique URLs, thumbnails and durations; canonical host `www.serviporno.com`; no enrichment required.
- TDD promotion: RED was exactly the missing production config, trusted policy and deploy-catalog requirements; targeted GREEN 39/39. Isolated full suite before commit: 163 passed with only the two existing FastAPI deprecation warnings; `git diff --check` passed.
- Feature commit: `10092a2 feat: add serviporno sitemap provider`; pushed to `feature/provider-registry-probe`.
- First official deploy attempt safely aborted before active changes because a new bounded maintenance backfill acquired the shared lock (`SEARCH_IPC_EXIT=10`). No force action was used; retry after natural completion succeeded.
- Official deploy: `SEARCH_DEPLOY=PASS build=10092a249476`, backup `/opt/search_engine-backups/20260919T164544Z-10092a249476`.
- Post-warmup production acceptance: ServiPorno has 100 indexed rows; `/api/search?provider=serviporno&limit=10` returned 10/10 complete rows; configured/available true. Canonical host is `www.serviporno.com`; thumbnail hosts sampled as `pics.serviporno.com` and `pics2.serviporno.com`.
- Production health after acceptance: 31 configured index providers, 55 trusted / 55 available / 25 live providers.
- Independent PornFlip worktree changes were isolated before verification/deploy and restored byte-for-byte afterward; they were not included in the ServiPorno feature commit.
- Same discovery pass: BigPorn rejected because search redirects to robots-disallowed `/search-*`; PornKai rejected because its public `/search?query=` contract currently returns HTTP 500; GotPorn search is robots-disallowed and host returns 403; PornKat remains CUSTOM_REQUIRED because listing and sampled target pages expose no duration; PornDroids generic root probe remains CUSTOM_REQUIRED.

## Production update — 2026-09-19 — Media Reliability Phase A

Released provider-aware thumbnail/preview handling from build `4296dc144989`.

- Tests before release: `177 passed, 2 warnings`; `git diff --check` PASS.
- Official helper CHECK: PASS.
- Official deploy: `SEARCH_DEPLOY=PASS build=4296dc144989`.
- Backup: `/opt/search_engine-backups/20260919T174339Z-4296dc144989`.
- Production health after deploy: 55 trusted / 55 available / 25 live providers.
- Media policy decisions from bounded 2026-09-19 audit:
  - direct preview verified with `206 video/*`: Beeg, YouJizz, DrTuber, BigFuck, HQPorn, TNAFlix, SpankBang, XHamster, Pornhub, Tube8;
  - PornHat, PornDr and AnyPorn preview disabled because their public preview URLs redirect outside the original provider allowlist;
  - Thumbzilla preview uses strict provider-aware proxy because direct access returned 410 while the same public URL with the fixed public Thumbzilla Referer returned `206 video/mp4`.
- Production smoke:
  - BigFuck direct preview: `206 video/mp4`;
  - Thumbzilla preview proxy: `206 video/mp4`;
  - Thumbzilla thumbnail proxy: `200 image/webp`;
  - Tube8 refresh endpoint: `302` to a freshly resolved thumbnail;
  - MILFPorn sample has no preview and remains still-image only;
  - media API reports Thumbzilla `thumbnail=proxy, preview=proxy`, Tube8 `thumbnail=refresh`, and PornHat/PornDr/AnyPorn `preview=disabled`.
- Frontend assets were bumped to shell v23. Direct requests to Uvicorn `:8775` correctly return 404 for static assets; the production frontend is served by Nginx and protected by Basic Auth (local HTTPS probe returned 401 without credentials), so no credential bypass was attempted.
- Preserved PornFlip dirty worktree was restored byte-for-byte after deploy; hashes remain `9fa362b9...` for `backend/live.py` and `f2ec7827...` for `tests/test_pornflip_live_parser.py`.

# SESSION HANDOFF — 2026-09-19 18:50 Europe/London

## 1. Cel projektu
BlackServ Search Engine jest agregatorem metadanych wyników z wielu publicznych providerów. Nie hostuje ani nie mirroruje wideo. Bieżący kierunek produktu po rozbudowie katalogu providerów: poprawa niezawodności miniaturek/preview, jakości kart i UX, a następnie uczciwe sortowanie na podstawie realnych metadanych oraz filtr Amateur/Studio bez heurystyk tytułowych.

Zatwierdzona kolejność prac z `docs/superpowers/specs/2026-09-19-search-ui-preview-sort-design.md` i planów w `docs/superpowers/plans/`:
1. Phase A — Media Reliability.
2. Phase B — Cards/UI v2.
3. Phase C — Metadata + Sorting.
4. Phase D — Amateur/Studio.

## 2. Repozytorium i bieżący stan Git — VERIFIED
- Repo: `llipinsk82-rgb/search_engine`.
- Sandbox: `/opt/bs-sandbox/search_engine`.
- Branch główny pracy: `feature/provider-registry-probe`.
- Aktualny lokalny HEAD: `c4ba694fdb3532f896e93ef690802ec4e4a24807`.
- `origin/feature/provider-registry-probe`: ten sam SHA `c4ba694fdb3532f896e93ef690802ec4e4a24807`.
- Główny sandbox przy końcu sesji: clean (`git status --short` bez wpisów).
- Worktree Phase B: `/opt/bs-sandbox/search_engine-worktrees/cards-ui-v2`, branch `feature/cards-ui-v2`, HEAD ten sam `c4ba694fdb3532f896e93ef690802ec4e4a24807`, clean.
- Worktree Phase A: `/opt/bs-sandbox/search_engine-worktrees/media-reliability-v2`, branch `feature/media-reliability-v2`, HEAD `4296dc14498957670bbb9be5abe9e6b678cfc0f2`.

Istotne commity bieżącej fazy:
- `3a4250b refactor: simplify search card markup`
- `2f1b06b style: refine desktop result hierarchy`
- `c194f5c style: polish mobile result feed`
- `c4ba694 feat: ship cards ui v2`

Poprzednia faza:
- `424a32e feat: add provider media policy`
- `28d7bb5 refactor: centralize provider media validation`
- `83ec2af fix: gate previews by verified media capability`
- `629eb5e fix: make card media policy driven`
- `4296dc1 test: isolate provider media api index state`
- `70d92b5 docs: record media reliability release`

## 3. Phase A — Media Reliability — VERIFIED COMPLETE
Wykonano provider-aware media policy, thumbnail handling, preview capability gating, session failure memory i strict preview proxy tylko tam, gdzie był potrzebny.

### Zweryfikowany audit preview
Bez bypassów i bez prywatnych endpointów. Bounded `Range` probe na publicznych preview URL-ach:
- direct preview `206 video/*`: Beeg, YouJizz, DrTuber, BigFuck, HQPorn, TNAFlix, SpankBang, XHamster, Pornhub, Tube8;
- PornHat, PornDr, AnyPorn: preview wyłączony, bo publiczne preview URL-e robiły redirect poza pierwotny provider allowlist;
- Thumbzilla: plain request zwracał 410, ten sam publiczny URL z `Referer: https://www.thumbzilla.com/` zwracał `206 video/mp4`; wdrożony strict allowlisted preview proxy.

### Testy Phase A
- Finalny full suite przed release: `177 passed, 2 warnings in 6.21s`.
- `git diff --check`: PASS.
- Znane warnings: tylko FastAPI `@app.on_event("startup")` deprecated.

### Produkcja Phase A
- Formalny helper CHECK: PASS.
- Formalny deploy: `SEARCH_DEPLOY=PASS build=4296dc144989`.
- Backup: `/opt/search_engine-backups/20260919T174339Z-4296dc144989`.
- Production smoke VERIFIED:
  - BigFuck direct preview `206 video/mp4`;
  - Thumbzilla preview proxy `206 video/mp4`;
  - Thumbzilla thumbnail proxy `200 image/webp`;
  - Tube8 `/api/thumb/<id>?refresh=true` -> `302` do świeżo rozwiązanej miniatury;
  - MILFPorn sample bez preview, zgodnie z policy;
  - media API: Thumbzilla `thumbnail=proxy, preview=proxy`; Tube8 `thumbnail=refresh`; PornHat/PornDr/AnyPorn `preview=disabled`.
- Frontend shell po Phase A: v23.

## 4. Phase B — Cards/UI v2 — IMPLEMENTED, TESTED, ON ORIGIN, CURRENTLY RUNNING IN PRODUCTION
Zmiany nie modyfikują search API ani semantyki wyników. Dotyczą wyłącznie warstwy UI/statusu:
- nowe hooki `.search-panel`, `.filter-strip`, `.result-summary`, `.media-badges`, `.card-meta-primary`, `.card-meta-secondary`;
- zachowane istniejące media controls i Phase A preview logic;
- desktop: sticky compact search panel, 4 -> 3 -> 2 kolumny, thumbnail-first hierarchy, secondary metadata muted;
- mobile <=680px: jeden pełny card/row, 16:9, poziomy scroll filtrów, 44px controls, 40px preview target, zabezpieczenia na overflow/długie tytuły;
- status rozdzielony na primary result state i secondary provider/live detail;
- frontend cache/assets bump v23 -> v24;
- prefetch/load-more logic nie była celowo zmieniana.

### TDD / testy Phase B — VERIFIED
Task-level:
- markup contract: `9 passed`;
- desktop hierarchy: `10 passed`;
- mobile contract: `11 passed`;
- final UI/status/assets contract: `15 passed`.

Finalny full gate na clean worktree, HEAD `c4ba694fdb35...`:
- `181 passed, 2 warnings in 6.28s`;
- `git diff --check`: PASS;
- JS syntax check: PASS;
- po usunięciu lokalnego symlinka `.venv` worktree był clean.

Dodatkowo przy zamykaniu sesji na głównym checkoutcie:
- `tests/test_frontend_contract.py`: `12 passed in 0.06s`.

### Produkcja Phase B — VERIFIED FACTS
- `/api/health`: `status=ok`.
- Production build: `c4ba694fdb35`.
- `search-engine-deploy-client status`: `build=c4ba694fdb35 service=active sync_timer=active backfill_timer=active`.
- Produkcja w chwili handoffu: `indexed_items=925027`, `configured_index_provider_count=31`, `live_provider_count=25`, `trusted_provider_count=55`, `available_provider_count=55`.
- Nie było aktywnego `sync-all` ani `backfill-all` przy finalnym sprawdzeniu maintenance.
- Istnieje backup deployu: `/opt/search_engine-backups/20260919T181300Z-c4ba694fdb35`.
- `origin/feature/provider-registry-probe` i lokalny HEAD są dokładnie na tym samym SHA co production build.

### Phase B — NOT_VERIFIED / UNKNOWN
- Nie odzyskano z journald bezpośredniej linii `SEARCH_DEPLOY=PASS build=c4ba694fdb35`; journald search dla tego SHA był pusty. Produkcyjny build, aktywny service i backup potwierdzają, że build został wdrożony, ale formalnego tekstowego markera PASS nie należy dopisywać jako zweryfikowanego.
- Nie wykonano końcowego wizualnego production smoke Phase B przez chroniony frontend. Local Nginx HTTPS bez credentials zwraca `401`; nie szukano ani nie obchodzono Basic Auth credentials.
- Dlatego desktop/mobile rendering, long-title card, missing-metadata card, Show more/prefetch i preview button na faktycznym production frontendzie pozostają `NOT_VERIFIED`, mimo zielonych source-contract/full-suite testów.

## 5. PornFlip — RED FLAG / PRESERVED BUT NOT IN CHECKOUT
Wcześniej istniał niezależny, niecommitowany PornFlip adapter/test. Był zweryfikowany read-only przed Phase A:
- live contract: page1 `21/21` complete, page2 `22/22` complete;
- overlap 0;
- thumbnail/duration/title kompletne;
- preview 0.

Aktualny stan przy końcu sesji:
- główny checkout jest clean i `tests/test_pornflip_live_parser.py` jest nieobecny;
- PornFlip NIE jest obecnie odtworzony w working tree;
- dwa backupy nadal istnieją w `/tmp`:
  - `/tmp/search_engine_phaseA_pornflip_live.py` SHA256 `9fa362b91778270d4f3015dfbf67dd44107c85cec6cda4468fdeb0fe485e9c01`;
  - `/tmp/search_engine_phaseA_test_pornflip.py` SHA256 `f2ec782760890ee8a880eb9552ecf507a90a046c92286a1f8e5276e70e4a3e0f`.
- `/tmp` jest storage tymczasowym. Nie traktować PornFlip jako bezpiecznie zapisanej funkcji projektu ani jako release candidate, dopóki pliki nie zostaną odzyskane do izolowanego worktree i ponownie przeprowadzone przez TDD/full gate.

To jest bieżący fakt i nadpisuje starszy historyczny wpis mówiący, że PornFlip został odtworzony po Phase A.

## 6. Aktualny provider/product state — VERIFIED
- 31 configured index providers.
- 25 live providers.
- 55 trusted providers.
- 55 available providers.
- Provider expansion celowo wstrzymany na czas Product v2; po Phase A/B następna zaplanowana faza to metadata/sorting, nie dalsze dokładanie providerów.

Ostatnie wydane providery przed Product v2 obejmują m.in. BigFuck, HQPorn, MILFPorn i ServiPorno; ich szczegółowe acceptance pozostają w wcześniejszych sekcjach tego handoffu.

## 7. Znane problemy / RED FLAGS
1. Phase B production UI nie ma jeszcze wizualnego authenticated smoke — `NOT_VERIFIED`.
2. Formalny marker `SEARCH_DEPLOY=PASS` dla `c4ba694fdb35` nie został odzyskany — nie wolno twierdzić, że go widzieliśmy.
3. PornFlip istnieje tylko jako dwa backupy w `/tmp`; obecny checkout jest clean i nie zawiera jego testu/zmiany.
4. FastAPI nadal emituje 2 deprecation warnings dla `@app.on_event("startup")`; nie jest to blocker bieżących release'ów.
5. Publiczny frontend jest za Nginx Basic Auth; nie obchodzić auth i nie wyciągać credentials tylko dla smoke.
6. Standard deploy safety pozostaje obowiązkowy: clean sandbox -> full tests -> diff check -> push exact HEAD -> helper CHECK -> natural maintenance gate -> official deploy -> formal marker + health -> acceptance. Nie zabijać zdrowych bounded sync/backfill jobs.

## 8. NOT_VERIFIED / UNKNOWN — nie zgadywać
- Wizualny wygląd Phase B w prawdziwej authenticated przeglądarce produkcyjnej.
- Formalny textual deploy PASS dla Phase B `c4ba694fdb35`.
- Czy `/tmp` PornFlip backups przetrwają reboot/cleanup hosta.
- PornFlip nie jest aktualnie commitowany ani wydany.
- Phase C i D nie zostały rozpoczęte implementacyjnie.

## 9. Dokładny następny krok
NIE powtarzać Phase A ani implementacji Phase B.

1. Najpierw zamknąć Phase B acceptance bez zmian kodu:
   - sprawdzić production UI przez autoryzowany, istniejący sposób dostępu do frontend Nginx; nie szukać/obchodzić credentials;
   - desktop smoke: search, filtry, 4/3/2 grid, preview button, primary/secondary status, Show more/prefetch;
   - mobile smoke w ~320–420px: 1 card/row, brak horizontal card overflow, 16:9, scrollable filters, long title, brakujące quality/duration;
   - potwierdzić asset shell v24.
2. Jeżeli UI smoke PASS: dopisać production acceptance Phase B do tego handoffu. Nie redeployować tylko po to, żeby uzyskać marker, jeśli aktualny build jest zdrowy i smoke PASS.
3. Następnie rozpocząć `docs/superpowers/plans/2026-09-19-search-metadata-sorting-v2.md` (Phase C) w nowym clean worktree z aktualnego `feature/provider-registry-probe`.
4. PornFlip traktować osobno. Jeżeli ma być zachowany, pierwszą bezpieczną czynnością jest odzyskanie dwóch `/tmp` backupów do osobnego worktree i ponowne sprawdzenie SHA + testów. Nie mieszać PornFlip z Phase C.

## 10. FINAL SESSION CHECKPOINT — 2026-09-19
Ten wpis jest autorytatywnym stanem końcowym tej sesji i nadpisuje starsze sprzeczne wpisy historyczne.

### Repo / branch / HEAD — VERIFIED
- Repo: `llipinsk82-rgb/search_engine`
- Branch: `feature/provider-registry-probe`
- Lokalny HEAD: `b4ec3807b66ffb76d88416edd99b2bfb19f5a295`
- `origin/feature/provider-registry-probe`: dokładnie `b4ec3807b66ffb76d88416edd99b2bfb19f5a295`
- Working tree: CLEAN.

Istotne ostatnie commity:
- `b4ec380` — `docs: hand off cards ui v2 session`
- `c4ba694` — `feat: ship cards ui v2`
- `c194f5c` — `style: polish mobile result feed`
- `2f1b06b` — `style: refine desktop result hierarchy`
- `3a4250b` — `refactor: simplify search card markup`
- `70d92b5` — `docs: record media reliability release`
- `4296dc1` — Phase A releasable build / media reliability final code state.

### Testy — VERIFIED
Phase A final gate przed release:
- `177 passed, 2 warnings`.

Phase B task gates:
- markup: `9 passed`;
- desktop hierarchy: `10 passed`;
- mobile feed: `11 passed`;
- final UI/status/assets: `15 passed`.

Phase B final full gate na clean worktree `c4ba694fdb35...`:
- `181 passed, 2 warnings in 6.28s`;
- `git diff --check`: PASS;
- JS syntax: PASS.

Znane warnings pozostają wyłącznie FastAPI `@app.on_event("startup")` deprecated.

### Produkcja — FRESH VERIFIED AT SESSION CLOSE
- `search-engine-deploy-client status`: `build=c4ba694fdb35 service=active sync_timer=active backfill_timer=active`.
- `/api/health`: `status=ok`, `build=c4ba694fdb35`.
- `indexed_items=930245`.
- `configured_index_provider_count=31`.
- `live_provider_count=25`.
- `trusted_provider_count=55`.
- `available_provider_count=55`.
- Phase A backup: `/opt/search_engine-backups/20260919T174339Z-4296dc144989`.
- Phase B backup widoczny w poprzednim zweryfikowanym checkpointcie: `/opt/search_engine-backups/20260919T181300Z-c4ba694fdb35`.

Phase A production smoke jest VERIFIED i obejmował m.in. direct preview, Thumbzilla thumbnail/preview proxy, Tube8 refresh i disabled-preview policy.

Phase B kod jest na origin i działa jako aktualny production build. Nie odzyskano formalnej tekstowej linii `SEARCH_DEPLOY=PASS build=c4ba694fdb35`, więc nie wolno twierdzić, że taki marker został odczytany. Production status/health i backup potwierdzają faktyczne wdrożenie builda.

### Phase B — NOT_VERIFIED
Nie wykonano końcowego authenticated visual smoke prawdziwego frontendu za Nginx Basic Auth. Bez obchodzenia auth nie potwierdzono wizualnie na produkcji:
- desktop 4/3/2 grid;
- mobile 1 card/row przy ~320–420 px;
- long-title / missing-metadata layout;
- Show more / prefetch w prawdziwej przeglądarce;
- preview button UX na faktycznym production frontendzie;
- asset shell v24 przez zalogowaną sesję browserową.

Testy source-contract/full-suite są zielone, ale nie zastępują tego wizualnego acceptance.

### PornFlip — RED FLAG / VERIFIED CURRENT STATE
- Nie ma `tests/test_pornflip_live_parser.py` w bieżącym checkoutcie.
- Bieżący checkout jest clean i nie zawiera PornFlip jako funkcji projektu.
- Backup `/tmp/search_engine_phaseA_pornflip_live.py`: SHA256 `9fa362b91778270d4f3015dfbf67dd44107c85cec6cda4468fdeb0fe485e9c01`.
- Backup `/tmp/search_engine_phaseA_test_pornflip.py`: SHA256 `f2ec782760890ee8a880eb9552ecf507a90a046c92286a1f8e5276e70e4a3e0f`.
- `/tmp` jest tymczasowe. PornFlip nie jest release candidate i nie wolno go mieszać z Phase C.

### Dokładny następny krok
1. NIE powtarzać Phase A ani implementacji Phase B.
2. Najpierw, jeśli dostępny jest autoryzowany frontend access, wykonać wyłącznie brakujący visual acceptance Phase B bez obchodzenia Basic Auth. Jeśli nie ma dostępu, zostawić ten punkt `NOT_VERIFIED` i nie blokować dalszego rozwoju.
3. Rozpocząć Phase C z `docs/superpowers/plans/2026-09-19-search-metadata-sorting-v2.md` w NOWYM clean worktree utworzonym z aktualnego HEAD `b4ec3807b66f...`.
4. Phase C cel: additive metadata (`published_at`, `views`, `rating_percent`, `rating_count`) + sortowanie `relevance/newest/views/rating/longest/shortest`, z brakującymi wartościami zawsze na końcu i bez wymyślania danych.
5. Po Phase C dopiero Phase D: explicit `Amateur / Studio / Unknown`, bez heurystyk z tytułów.
6. PornFlip osobno; jeśli ma być zachowany, odzyskać dwa `/tmp` backupy do osobnego worktree i ponownie przejść TDD/full gate.

## 11. WIADOMOŚĆ STARTOWA DO NOWEGO CHATU

```text
BlackServ Search Engine — kontynuacja CTO.

Przeczytaj najpierw kompletnie:
1. /opt/bs-sandbox/search_engine/docs/SEARCH_ENGINE_HANDOFF.md
2. /opt/bs-sandbox/search_engine/docs/superpowers/specs/2026-09-19-search-ui-preview-sort-design.md
3. /opt/bs-sandbox/search_engine/docs/superpowers/plans/2026-09-19-search-product-v2-roadmap.md
4. /opt/bs-sandbox/search_engine/docs/superpowers/plans/2026-09-19-search-metadata-sorting-v2.md

Tryb pracy: /loop /cto /minimal.
Nie zgaduj. Najpierw zweryfikuj aktualny git HEAD/origin/status i production health/status. Nie powtarzaj wykonanych Phase A ani Phase B.

Stan końcowy poprzedniej sesji:
- repo: llipinsk82-rgb/search_engine
- branch: feature/provider-registry-probe
- HEAD/origin: b4ec3807b66ffb76d88416edd99b2bfb19f5a295
- working tree: CLEAN
- production build: c4ba694fdb35
- production health: ok
- provider counts: 31 configured index / 25 live / 55 trusted / 55 available
- Phase A Media Reliability: wdrożone i production-smoke PASS
- Phase B Cards/UI v2: kod/testy PASS, na origin i aktualnie w produkcji; brakuje tylko authenticated visual browser smoke, więc ten punkt pozostaje NOT_VERIFIED
- Phase C Metadata + Sorting: NIE rozpoczęta
- Phase D Amateur/Studio: NIE rozpoczęta
- PornFlip: NIE jest w checkoutcie; tylko dwa backupy /tmp opisane w handoffie — nie mieszać z Phase C

Dokładny następny krok:
- jeśli istnieje autoryzowany dostęp do frontend Nginx, zrób brakujący visual acceptance Phase B bez obchodzenia Basic Auth;
- niezależnie od tego rozpocznij Phase C w nowym clean worktree z aktualnego HEAD, zgodnie z planem metadata/sorting;
- TDD RED→GREEN, full pytest, git diff --check, commit/push, helper CHECK, natural maintenance gate, deploy, health/acceptance, handoff.
- nie zabijaj zdrowych bounded sync/backfill jobs.
- nie twierdź, że widziano formalny SEARCH_DEPLOY=PASS dla Phase B — tego markera nie odzyskano.
```

## 12. AUTHORITATIVE PHASE C CHECKPOINT — 2026-09-19

Ten wpis jest nowszy niż wcześniejsze checkpointy w tym pliku i nadpisuje ich stan Phase C / produkcji tam, gdzie występuje sprzeczność.

### Repo / release state — VERIFIED
- Repo: `llipinsk82-rgb/search_engine`
- Release branch: `feature/provider-registry-probe`
- Phase C release code SHA: `6eb04675eda9505ab4794a4cb5eb5f622b0bf0f2`
- `origin/feature/provider-registry-probe` był dokładnie na tym SHA przed niniejszym docs-only handoff commit.
- Feature worktree/branch: `feature/metadata-sorting-v2`, również `6eb04675eda9505ab4794a4cb5eb5f622b0bf0f2`, clean i pushnięty.
- Release był fast-forward-only z poprzedniego `91c9f6a0854b471831aed731dc0c6e90c572c1a6`; bez merge conflictów.
- Po zapisaniu tego handoffu branch może być o jeden docs-only commit przed production code SHA. Produkcja pozostaje świadomie na `6eb04675eda9`; nie redeployować tylko dla dokumentacji.

Istotne Phase C commity:
- `6ba5312` — `feat: add sortable result metadata`
- `beb758f` — `feat: persist sortable metadata`
- `e3932a3` — `feat: ingest redtube sort metadata`
- `902e2b8` — `fix: require aware published timestamps`
- `4115ee3` — `feat: add indexed result sorting`
- `a0170f8` — `feat: expose result sort modes`
- `6eb0467` — `feat: add search sorting controls`

### Phase C implementation — VERIFIED
Wdrożone:
- nullable real metadata: `published_at`, `views`, `rating_percent`, `rating_count`;
- timezone-aware `published_at` validation;
- additive SQLite migration, persistence/round-trip i indeksy;
- RedTube explicit parsing z publicznego JSON API, bez heurystyk/fabrykowania danych;
- sort modes dokładnie: `relevance`, `newest`, `views`, `rating`, `longest`, `shortest`;
- SQL sorting przed LIMIT/OFFSET;
- missing metadata zawsze po known dla sortów non-relevance;
- GET/POST `/api/search` + POST `/api/live-refresh` obsługują sort;
- invalid sort jest odrzucany przez FastAPI/Pydantic;
- live sort jest stabilny i dotyczy wyłącznie pobranego live pool;
- frontend `#sort`, hash state tylko dla non-default, local/live payload plumbing;
- optional date/views/rating są renderowane wyłącznie, gdy źródło je faktycznie podało;
- frontend shell/cache bumped do v25;
- poprawione łączenie live+cached: round-robin pozostaje tylko dla `relevance`; non-relevance sortuje wspólny dostępny pool, żeby frontend nie niszczył kolejności backendu.

### Testy — FRESH VERIFIED
Ostatni full gate na exact release code SHA `6eb04675...`:
- `206 passed, 2 warnings`;
- `node --check frontend/app.js`: PASS;
- `git diff --check`: PASS;
- release worktree po fast-forward miał ten sam wynik: `206 passed, 2 warnings`.

Znane 2 warnings: wyłącznie FastAPI `@app.on_event("startup")` deprecation; nadal nie są blockerem.

### Deploy — VERIFIED
Official helper CHECK:
- `SEARCH_DEPLOY_PROVIDER_CATALOG=PASS`
- `SEARCH_DEPLOY_CHECK=PASS build=6eb04675eda9 source=/opt/bs-sandbox/search_engine`

Official helper DEPLOY:
- `SEARCH_ROOT_HELPER=DEPLOY_START build=6eb04675eda9`
- `SEARCH_DEPLOY_PROVIDER_CATALOG=PASS`
- `SEARCH_ACCEPT_API=PASS build=6eb04675eda9 ... indexed_items=942180`
- `SEARCH_ACCEPT_SERVICES=PASS`
- `SEARCH_ACCEPT=PASS`
- warmup: `SEARCH_WARMUP=QUEUED ... reason=sync-still-running wait_seconds=120` — helper nie zabijał zdrowego sync joba;
- `SEARCH_DEPLOY=PASS build=6eb04675eda9 backup=/opt/search_engine-backups/20260919T193943Z-6eb04675eda9`
- `SEARCH_ROOT_HELPER=DEPLOY_PASS build=6eb04675eda9`.

Podczas deploy output pojawił się niezwiązany warning systemd:
- `/etc/systemd/system/oscam-panel.service:13: Unknown key 'StartLimitIntervalSec' in section [Service], ignoring.`
Nie wpłynął on na Search Engine deploy/acceptance. Nie naprawiać go w Search Engine.

### Produkcja — FRESH VERIFIED AFTER DEPLOY
`search-engine-deploy-client status`:
- build `6eb04675eda9`
- service `active`
- sync_timer `active`
- backfill_timer `active`

`/api/health` po deploy:
- `status=ok`
- `build=6eb04675eda9`
- ostatni odczyt `indexed_items=942354` (licznik dynamiczny, sync działa)
- configured index `31`
- live `25`
- trusted `55`
- available `55`.

Invalid sort production check:
- GET `/api/search?q=step&sort=popular&limit=1` -> HTTP `422` z Literal validation.

### RedTube real metadata acceptance — VERIFIED
Normalny POST `/api/live-refresh` dla `q=step`, `provider=redtube`, `limit_per_provider=5`, `sort=views`:
- fetched 5, error `None`;
- 5/5 ma real `published_at`, `views`, `rating_percent`, `rating_count`, `duration_seconds`;
- live `views_desc=True`.

Przykładowy real item z acceptance:
- id `314e3fc4e826378ad2dd5bdb`
- `published_at=2026-02-18T15:45:44Z`
- `views=787772`
- `rating_percent=98.008`
- `rating_count=251`
- `duration_seconds=1395`.

Po normalnym background cache zwykłe `/api/search` dla RedTube zwróciło te same metadata; żadnej ręcznej edycji production DB nie wykonano.

### Production sort acceptance — VERIFIED
Dla `q=step`, bounded page 100:
- `newest`: total `26229`, known `5`, missing `95`, `missing_last=True`, `ordered=True`;
- `views`: total `26229`, known `5`, missing `95`, `missing_last=True`, `ordered=True`;
- `rating`: total `26229`, known `5`, missing `95`, `missing_last=True`, `ordered=True`.

Duration mixed-set znaleziony bez ręcznej edycji DB:
- provider `megatube`, `q=step`, total `32`;
- known duration `28`, missing `4`;
- `longest`: 28 known malejąco, potem 4 `None`;
- `shortest`: 28 known rosnąco, potem te same 4 `None`.

Relevance/paging:
- implicit default relevance == explicit `sort=relevance` dla pierwszych 40 IDs: PASS;
- `views` paging 0..2 i 3..5: brak overlap, combined order zachowany, missing-last PASS.

### Verification limitations / NOT_VERIFIED
1. Phase B authenticated visual browser smoke nadal `NOT_VERIFIED`; brak autoryzowanego browser access w tej sesji i auth nie był obchodzony.
2. Phase C selector/card visual smoke w prawdziwej authenticated przeglądarce również `NOT_VERIFIED` z tego samego powodu. Source-contract tests są PASS, ale nie zastępują visual smoke.
3. Użytkownik `blackserv` nie ma prawa czytać `/opt/search_engine/frontend/index.html`; direct prod-file grep zwrócił `Permission denied`. Nie użyto sudo/root. Exact helper deploy build + health potwierdzają production code build, ale nie oznaczamy direct file read jako PASS.
4. `blackserv` nie ma dostępu do system journal; `journalctl -u search-engine.service` zwrócił insufficient permissions. Helper service acceptance + health są PASS, ale journal tail pozostaje `NOT_VERIFIED`.
5. PornFlip pozostaje poza checkoutem; tylko wcześniej zweryfikowane backupy `/tmp`. Nie mieszano go z Phase C.

### Phase status po tym checkpointcie
- Phase A Media Reliability: DONE / production smoke PASS.
- Phase B Cards/UI v2: code/tests/deploy PASS; authenticated visual smoke `NOT_VERIFIED`.
- Phase C Metadata + Sorting: DONE / code tests PASS / official deploy PASS / production API acceptance PASS; authenticated visual smoke `NOT_VERIFIED`.
- Phase D Amateur/Studio: NOT_STARTED na moment tego checkpointu.

### Następny krok /loop
1. Nie powtarzać Phase A/B/C.
2. Jeżeli pojawi się autoryzowany browser access, wykonać brakujący visual smoke B/C bez obchodzenia Basic Auth.
3. Kontynuować Phase D z design spec `docs/superpowers/specs/2026-09-19-search-ui-preview-sort-design.md`: explicit `Amateur / Studio / Unknown`, bez title heuristics i bez fabrykowania klasyfikacji.
4. Najpierw sprawdzić, czy istnieje osobny Phase D implementation plan. Jeżeli nie, przygotować minimalny plan na bazie zaakceptowanego spec i wdrażać TDD w nowym clean worktree.
5. Zachować standard release workflow: clean sandbox -> tests -> diff -> commit/push -> helper CHECK -> maintenance gate -> official deploy -> health -> acceptance -> handoff.
6. PornFlip nadal osobno.

## 13. WIADOMOŚĆ STARTOWA PO PHASE C

```text
BlackServ Search Engine — kontynuacja CTO po zakończeniu Phase C.

Tryb: /loop /cto /minimal /handoff.

Najpierw przeczytaj najnowszy autorytatywny checkpoint w:
- /opt/bs-sandbox/search_engine/docs/SEARCH_ENGINE_HANDOFF.md
oraz spec:
- docs/superpowers/specs/2026-09-19-search-ui-preview-sort-design.md

Nie powtarzaj Phase A/B/C.

Zweryfikowany release code:
- branch release: feature/provider-registry-probe
- production code build: 6eb04675eda9
- official deploy: PASS
- backup: /opt/search_engine-backups/20260919T193943Z-6eb04675eda9
- health: OK
- providers: 31 configured / 25 live / 55 trusted / 55 available
- full gate: 206 passed, JS syntax PASS, diff-check PASS
- Phase C sort acceptance: newest/views/rating missing-last PASS; longest/shortest na mixed megatube set PASS; relevance default unchanged; paging PASS; RedTube real metadata PASS

NOT_VERIFIED:
- authenticated browser visual smoke Phase B/C (nie obchodzić Basic Auth)
- direct prod frontend file read i journal tail z konta blackserv z powodu permissions

Dalej:
- Phase D Amateur/Studio/Unknown z wyłącznie explicit metadata; żadnych heurystyk z tytułów.
- najpierw znajdź osobny Phase D plan; jeśli go nie ma, zrób minimalny plan ze spec, potem TDD RED->GREEN.
- PornFlip pozostaw osobno.
```


---

# AUTHORITATIVE CURRENT CHECKPOINT — PHASE D / CACHE FIX 2026-09-20

# Search Engine — CURRENT HANDOFF

Updated: 2026-09-19 21:25 UK

## Project

- Repo: `llipinsk82-rgb/search_engine`
- Development branch: `feature/content-class-filter`
- Canonical sandbox: `/opt/bs-sandbox/search_engine`
- Production: `/opt/search_engine`
- Deploy helper: `/usr/local/bin/search-engine-deploy-client`
- Public alias: `search.blackserv.eu`
- Backend: `127.0.0.1:8775`

## Last verified production state

This session could NOT re-check VM101 because BlackServ Bridge is currently broken at invocation time (`Resource not found`).

Last verified production state carried from the previous handoff:

- production build: `6eb04675eda9505ab4794a4cb5eb5f622b0bf0f2`
- Phase C deployed
- service/health previously PASS

Treat this production state as **last verified, not freshly reverified in this session**.

## Phase D implementation state

Phase D Tasks 1–4 are implemented and pushed on `feature/content-class-filter`.

Verified code commits:

1. `9dcbef3218f9bf6cdb698e18a392c60624fe24c1` — `feat: add explicit content classifier`
2. `a09103b49fe575cef26dfca2bb3f5888d4010547` — `feat: persist explicit content class`
3. `d5b8ede35b4b6c8f0475be4dd2a4f42c2d4c4af4` — `feat: filter results by content class`
4. `9cb5948995da9115e281f4f28d9bb3310f927bf0` — `feat: add amateur studio filtering`

### Implemented behavior

- Explicit content classes: `amateur`, `studio`, `unknown`.
- No title-based inference.
- Tag/studio driven classification only.
- Conflicting explicit evidence resolves to `unknown`.
- SQLite schema/persistence includes `content_class` and `studio`.
- Migration is additive and preserves existing rows.
- Search supports exact `content_class` filtering.
- GET/POST API validation rejects unsupported values.
- Live results are classified and filtered before cache/render.
- Frontend v26 adds filter: All / Amateur / Studio / Unknown.
- Cards render `Amateur` only for explicit amateur classification.
- Studio name is rendered only when a real studio value exists.
- No fake `Unknown` card badge.
- Mobile one-column behavior is preserved.

## Verification completed outside VM101

Exact feature code SHA tested: `9cb5948995da9115e281f4f28d9bb3310f927bf0`.

Results:

- full Python suite: **227 passed**
- FastAPI warnings: 2 existing `on_event` deprecation warnings
- `git diff --check`: **PASS**
- `python -m compileall`: **PASS** during the implementation gates
- `node --check frontend/app.js`: **PASS** using temporary Node v20.18.0 under `/tmp`
- shadow clone fetched/reset to exact GitHub SHA before final suite
- branch worktree was clean after reset

Do not claim VM101 or production PASS from these shadow tests.

## Access / blocker

### BlackServ Bridge

Discovery exposes `BlackServ_Bridge.bridge_health`, but invocation returns:

`Resource not found: BlackServ_Bridge.bridge_health`

This was reproduced multiple times.

### SentinelX

SentinelX currently exposes one host:

- hostname: `blackserv`
- host id: `host_e174a7a41f23328d`

That host is **not** the canonical Search Engine VM101 environment:

- `/opt/bs-sandbox/search_engine` is absent
- `/opt/search_engine` is absent
- `/opt/bs-sandbox` contains Sentinel_BS work instead

Do NOT use this SentinelX host as a substitute for VM101 Search Engine deployment.

## Release safety

Do not:

- edit production directly,
- fake a VM101 gate from the shadow clone,
- use unrelated SentinelX host as a deploy substitute,
- kill healthy sync/backfill jobs,
- bypass the authorized deploy helper,
- claim Phase D production PASS until helper deploy + independent production acceptance actually pass.

## Exact next action

When BlackServ Bridge becomes functional:

1. Re-read this handoff.
2. Run Bridge health.
3. Inspect canonical `/opt/bs-sandbox/search_engine` status/branch/HEAD/diff.
4. Fetch `origin/feature/content-class-filter`.
5. Move canonical sandbox to exact code SHA `9cb5948995da9115e281f4f28d9bb3310f927bf0` only if the canonical tree is clean and no unrelated work would be overwritten.
6. Run full suite on VM101.
7. Run `node --check frontend/app.js` on VM101 if Node exists there; otherwise keep the already verified shadow Node result but state the limitation.
8. Run `git diff --check` and verify clean tree.
9. Fast-forward the release branch only after all canonical gates pass.
10. Push release branch.
11. Run `/usr/local/bin/search-engine-deploy-client check`.
12. If CHECK PASS and maintenance lock is free, run authorized deploy helper.
13. Verify production build equals the deployed code SHA.
14. Verify `/api/health`, service state, sync timer, backfill timer.
15. Acceptance test cached search + live refresh for content class filtering.
16. Verify frontend v26 assets and content-class selector are served.
17. Only then mark Phase D production PASS and update this same handoff file.

## CTO mode

User commands such as `/loop /cto /minimal /handoff /go` mean continue autonomously through safe reversible steps. Stop only for a real blocker, irreversible/destructive risk, or evidence that would require guessing.


---

## 2026-09-20 SentinelX → VM101 canonical Phase D cache-fix checkpoint

User explicitly authorized SentinelX as a temporary transport path, with the constraint that work stays inside the Search Engine sandbox on VM101 and nothing else is changed.

Verified access path:

- SentinelX host: `host_e174a7a41f23328d`
- PVE host: `blackserv.eu`
- PVE network: `vmbr2 = VM101 / VPS services side`
- VM101 config MAC: `BC:24:11:09:5D:E2`
- VM101 IP from PVE neighbour table: `192.168.1.100`
- root SSH alias on PVE: `sentinel-bs-os2`
- SSH target: `os2.blackserv.eu`
- SSH login: `debian`
- VM101 work is performed as `blackserv` via `sudo -u blackserv`
- canonical sandbox remains `/opt/bs-sandbox/search_engine`
- production remains `/opt/search_engine`

Important Git detail:

- `blackserv` repo has `core.sshCommand` pointing at `/tmp/search-engine-github-known-hosts`
- that temporary known-hosts file was absent
- the Search Engine sandbox already had the correct `github.com` ED25519 host key in `/opt/bs-sandbox/.ssh/known_hosts`
- fetch was therefore performed with a temporary `GIT_SSH_COMMAND` override using only sandbox-owned key/known-hosts files
- no system SSH config was changed

Fresh Git refs after fetch:

- `origin/feature/provider-registry-probe` = `6eb04675eda9505ab4794a4cb5eb5f622b0bf0f2`
- `origin/feature/content-class-filter` = `c527d4ae1ff0da49622f2d7f82cafe4b6dbc87b1` (docs-only continuity HEAD)
- canonical checkout stayed on `feature/provider-registry-probe` at `6eb04675...`
- canonical checkout still has only the pre-existing dirty `docs/SEARCH_ENGINE_HANDOFF.md`
- no canonical code file was modified

Isolated implementation worktree created:

`/opt/bs-sandbox/search_engine-worktrees/content-class-cache-fix`

Branch:

`feature/content-class-cache-fix`

Base code SHA:

`613cf769e1adfe665416ef7f6dcc269e1ed0fbcc`

A local `.venv` was created inside this worktree only and contains project requirements + pytest. No system Python packages were changed.

### TDD evidence

Baseline before code change:

- `tests/test_content_class_filter.py`: **5 passed**
- 2 existing FastAPI `on_event` deprecation warnings

New regression test:

`test_filtered_live_response_caches_full_classified_batch`

Observed RED on the original code:

- response correctly contained only `["amateur-tag"]`
- cache received only `["amateur-tag"]`
- expected cache batch was full classified set:
  - `amateur-tag`
  - `studio-tag`
  - `studio-label`
  - `title-only`

This directly reproduced the cache narrowing bug.

### Minimal fix semantics

`backend/app.py` now:

1. classifies every provider batch using `filter_live_items(items, None)`,
2. schedules the full classified `result.providers` collection for cache,
3. derives a separate request-filtered response collection,
4. builds interleaved response items and provider `fetched` counts from that filtered response collection,
5. never mutates the cache collection down to the request-specific `content_class` subset.

No new subsystem was added.

### GREEN / verification

Regression test after fix:

- **1 passed**
- 2 existing warnings

Targeted content-class file:

- **6 passed**
- 2 existing warnings

First full-suite run through `sudo -u blackserv` produced:

- **227 passed**
- **1 failed**
- 2 warnings

The single failure was `test_maintenance_runner.py::MaintenanceRunnerTests::test_lock_contention_is_clean_skip`.

Root cause was execution environment, not application code:

- `blackserv` account shell is `/usr/sbin/nologin`
- the test's `flock -c` uses `$SHELL`
- with the inherited nologin shell the lock-holder command exits immediately with `This account is currently not available`
- the test then sees the protected `/bin/false` execute and returns 1

Fresh full-suite rerun with the execution environment explicitly set to `SHELL=/bin/bash`:

- **228 passed**
- **0 failed**
- 2 existing FastAPI warnings

Additional fresh gate:

- `python -m compileall -q backend`: **PASS**
- `node --check frontend/app.js`: **PASS**
- `git diff --check`: **PASS**

### Local code commit

Exact code commit:

`82a152999e173b8649e4d6dfce5e0003cdf579d0`

Commit message:

`fix: keep full classified live cache`

Files changed:

- `backend/app.py`
- `tests/test_content_class_filter.py`

The code worktree was clean immediately after the code commit.

### Release / production status

Because the user explicitly limited this SentinelX exception to the Search Engine sandbox on VM101:

- code commit was **not pushed**
- release branch was **not changed**
- helper CHECK was **not run**
- production was **not deployed**
- `/opt/search_engine` was **not modified**

Production/release therefore remain at the last verified build:

`6eb04675eda9505ab4794a4cb5eb5f622b0bf0f2`

### Exact next action

When permission scope includes GitHub/release again:

1. fresh-verify worktree `feature/content-class-cache-fix` is clean at code SHA `82a152999e173b8649e4d6dfce5e0003cdf579d0`,
2. push this code branch using the sandbox Search Engine SSH key/known-hosts context,
3. verify `82a1529...` is a clean fast-forward descendant of release `6eb04675...`,
4. do not use docs-only continuity HEAD `c527d4ae...` as a deploy target,
5. fast-forward release to the exact code SHA only,
6. run authorized helper CHECK,
7. deploy only if CHECK + maintenance gate PASS,
8. run production acceptance including proof that a filtered live request cannot narrow/poison subsequent cached results,
9. only then mark Phase D DONE and proceed to Phase E Product Finish.

## 2026-09-20 — AUTHORITATIVE PHASE D COMPLETE / PHASE E DESIGN CHECKPOINT

This section supersedes older Phase D blocker/next-action notes above.

### Production — VERIFIED

- production build: `82a152999e17`
- `/api/health`: `status=ok`
- `search-engine.service`: active
- sync timer: active
- backfill timer: active
- indexed items at acceptance: 1,120,245
- providers: 31 configured / 25 live / 55 trusted / 55 available

Phase D content-class production acceptance:
- invalid content class -> HTTP 422
- indexed `amateur` -> only `amateur`
- indexed `unknown` -> only `unknown`
- live `amateur` -> only `amateur`
- full classified live batches are cached before response-specific filtering

Phase D is CLOSED.

### Release / source

- release branch `feature/provider-registry-probe` was fast-forwarded to exact code SHA `82a152999e173b8649e4d6dfce5e0003cdf579d0`
- official deploy helper CHECK passed
- official deploy completed; SentinelX transport timed out, but independent post-check verified production build `82a152999e17`
- no direct production edits were made

### Phase E — Premium Product Finish

User approved the premium Product Finish direction.

Dedicated branch/worktree:
- branch: `feature/premium-product-finish`
- base: `82a152999e173b8649e4d6dfce5e0003cdf579d0`
- worktree: `/opt/bs-sandbox/search_engine-worktrees/premium-product-finish`

Design spec:
- `docs/superpowers/specs/2026-09-20-premium-product-finish-design.md`

Approved direction:
- dark premium media-first browser
- no framework rewrite
- desktop primary controls: Sort + Content
- Provider/Quality/Duration secondary; Age Check advanced
- desktop generally 3 columns, tablet 2, mobile 1
- mobile controls: Sort / Content / Filters with bottom/full-height filter sheet
- larger media-first cards
- manual one-active-preview preserved
- accessibility fixes: no nested button-in-link, accessible thumb link, scoped live region, focus management
- explicit skeleton/empty/error/partial-provider states
- safe PWA update behavior

### Current gate

Implementation has NOT started.

The design spec has been written and self-reviewed. Per the agreed design workflow, the next required action is user review/approval of the written spec. After that, create the implementation plan and execute TDD on this branch.

Do not revert to older Phase D blocker instructions above.

## 2026-09-20 - AUTHORITATIVE PHASE E PLAN CHECKPOINT

This section supersedes the earlier Phase E current-gate paragraph.

Phase E design spec is approved.
Implementation plan is complete and self-reviewed: docs/superpowers/plans/2026-09-20-premium-product-finish.md
Branch: feature/premium-product-finish
Base/deployed Phase D code: 82a152999e173b8649e4d6dfce5e0003cdf579d0
Implementation code has NOT started.

Plan: semantic shell; premium CSS 3/2/1; mobile filter sheet; accessible card/preview; explicit UI states; guarded PWA v27; full release/deploy acceptance.

Self-review PASS: spec coverage checked; no TODO/TBD placeholders; five Review Focus failure modes pinned to tests; every implementation task ends green; backend out of scope; git diff --check PASS.

Next gate: user reviews plan and selects Native or Subagent-driven execution. After approval execute task-by-task with TDD and release gates.

## 2026-09-20 — AUTHORITATIVE PHASE E PREMIUM PRODUCT FINISH PRE-RELEASE GATE

This section supersedes the previous Phase E design-only checkpoint.

### Feature state — VERIFIED

- branch: `feature/premium-product-finish`
- implementation HEAD before this handoff commit: `8fbdf679d7d98b4bad4cd0a7fbef598d2dc6dfaa`
- base production/release code: `82a152999e173b8649e4d6dfce5e0003cdf579d0`
- frontend shell: v27
- implementation tasks 1-6: complete
- pre-release accessibility review fix: mobile filter-sheet initial Shift+Tab escape closed by `8fbdf67`

Implemented product finish:
- restrained dark premium media-first shell;
- desktop 3-column cards, tablet 2, mobile 1;
- desktop primary Sort + Content hierarchy;
- secondary Provider/Quality/Duration/Age Check hierarchy;
- mobile Sort/Content/Filters with real modal filter sheet;
- same secondary filter DOM group is relocated rather than duplicated;
- manual one-active-preview retained;
- preview control is no longer nested inside the media link;
- thumbnail link gets an accessible name from title;
- dedicated status live region replaces live results-grid announcements;
- visible focus treatment and trapped/returned filter-sheet focus;
- skeleton, filtered-empty, empty, error/Retry and partial-live-failure states;
- live failure preserves cached/indexed results;
- PWA shell v27 with sessionStorage controllerchange reload guard.

### Fresh automated gate — VERIFIED

Run on VM101 worktree `/opt/bs-sandbox/search_engine-worktrees/premium-product-finish`:
- `tests/test_frontend_contract.py`: **31 passed**
- full Python suite: **241 passed**
- warnings: **2 existing FastAPI `on_event` deprecation warnings only**
- `python -m compileall -q backend`: PASS
- `node --check frontend/app.js`: PASS
- `git diff --check`: PASS
- worktree clean before this documentation update

### Production state before Phase E release

Production remains unchanged at Phase D build `82a152999e17` at this checkpoint.
No Phase E production deploy has been attempted yet.

### Visual acceptance

`PENDING` — authenticated desktop/mobile production visual smoke has not yet been performed.
Do not mark visual PASS without operator-authenticated browser evidence.

### Exact next action

1. Push `feature/premium-product-finish`.
2. Verify current remote release is an ancestor of the exact Phase E HEAD.
3. Fast-forward `feature/provider-registry-probe` only.
4. Preserve any canonical local handoff-only edits; stop on unrelated app-code dirt.
5. Fast-forward canonical sandbox to exact release HEAD.
6. Official helper CHECK as `blackserv`.
7. Wait for natural maintenance-lock window; do not kill sync/backfill.
8. Official helper DEPLOY.
9. Verify build ID, `/api/health`, service and timers.
10. Run local production API acceptance for search/live/content-class/provider media policy.
11. Record authenticated visual smoke as PASS or `NOT_VERIFIED`.
12. Write final authoritative deployed Phase E checkpoint.

## 2026-09-20 — AUTHORITATIVE PHASE E DEPLOYED CHECKPOINT

This section supersedes all earlier Phase E PENDING / pre-release notes above.

### Source / release

- feature branch: `feature/premium-product-finish`
- deployed code SHA: `82f18f9d47bbbc8fae6c6bb0b815101570748263`
- release branch was fast-forwarded to that exact SHA before deploy
- official deploy helper CHECK: PASS
- official deploy executed; SentinelX transport timed out, so success was established only by independent production verification
- no direct production edits were made

### Production — VERIFIED

- `/api/health`: `status=ok`
- production build reported by health/helper: `82f18f9d47bb`
- indexed items at final acceptance: 1,126,450
- providers: 31 configured / 25 live / 55 trusted / 55 available
- `search-engine.service`: active
- sync timer: active
- backfill timer: active
- latest backfill service state after deploy: inactive / `Result=success` / `ExecMainStatus=0`

### Frontend v27 — VERIFIED ON PRODUCTION FILES

Production frontend contains:
- `/styles.css?v=27`
- `/app.js?v=27`
- service-worker cache `search-shell-v27`

SHA256 for production `index.html`, `styles.css`, `app.js`, and `sw.js` exactly matched the canonical release files after deploy.

Implemented Phase E product contract:
- premium dark media-first shell
- desktop 3-column result grid
- tablet 2 columns
- mobile 1 column
- mobile primary controls: Sort / Content / Filters
- mobile secondary filters in an accessible modal sheet
- no horizontal mobile filter strip
- manual one-active-preview preserved
- preview button no longer nested inside media link
- thumbnail link receives accessible name from title
- explicit keyboard focus / mobile sheet focus trap and focus return
- skeleton, filtered-empty, empty, retry/error and partial-live states
- safe service-worker v27 reload guard

### Automated gates — VERIFIED

Final pre-release gate on the deployed code:
- frontend contract suite: 31 PASS
- full suite: 241 PASS
- only 2 pre-existing FastAPI `on_event` deprecation warnings
- `python -m compileall -q backend`: PASS
- `node --check frontend/app.js`: PASS
- `git diff --check`: PASS

### Production API acceptance — VERIFIED

- indexed search with `content_class=amateur`: HTTP 200, sampled items only `amateur`
- invalid content class: HTTP 422
- `/api/providers`: HTTP 200, 55 providers
- live refresh with `content_class=amateur`: HTTP 200, sampled items only `amateur`

### Visual acceptance

`NOT_VERIFIED` from the automation session because the public UI is protected by operator Basic Auth and no authentication bypass is permitted.

A user-side authenticated refresh/browser smoke is still required to mark visual acceptance PASS.

### Operational note

Before Phase E deploy, one backfill run failed because SexPlex returned malformed XML (`not well-formed (invalid token)`). This was not caused by Phase E. After deploy the backfill unit later reported `Result=success`, so this is a historical provider incident to monitor, not an active release blocker.

### Exact next action

1. User performs authenticated desktop/mobile visual smoke on the freshly deployed v27 UI.
2. If visual smoke PASS, mark Phase E fully CLOSED.
3. If visual defects are observed, capture screenshots and fix only on a new isolated branch/worktree; do not edit production directly.
4. Independently monitor recurrence of the SexPlex malformed-XML backfill failure; treat it as provider-maintenance work, separate from Phase E.

## 2026-09-20 — AUTHORITATIVE PREMIUM V28 BODY-SURFACE HOTFIX

This section supersedes the previous Phase E deployed checkpoint only for the frontend shell/build identifiers below.

### Root cause — VERIFIED

Source-level post-deploy audit found a real CSS selector typo in the premium stylesheet: `bwdy {` instead of `body {`.

Impact:
- browser default body margin could remain active;
- intended full-page premium background/gradient and base body color were not guaranteed to apply;
- automated Phase E contract tests did not previously cover the real `body` selector.

### TDD fix — VERIFIED

Dedicated branch/worktree:
- branch: `fix/premium-body-selector`
- code SHA: `510540ea5f093afa05eec0fa6782d986517d1ee2`

Changes:
- corrected `bwdy {` -> `body {`;
- added regression coverage for body surface selector;
- bumped frontend shell from v27 to v28 so existing service-worker caches cannot retain the broken CSS;
- updated SW cache and guarded reload key to v28.

Final gate:
- frontend contract suite: 32 PASS;
- full suite: 242 PASS;
- only 2 pre-existing FastAPI `on_event` deprecation warnings;
- `python -m compileall -q backend`: PASS;
- `node --check frontend/app.js`: PASS;
- `git diff --check`: PASS.

### Production — VERIFIED

Official helper CHECK: PASS.
Official helper deploy executed; independent verification established:
- production build: `510540ea5f09`;
- `/api/health`: `status=ok`;
- `search-engine.service`: active;
- sync timer: active;
- backfill timer: active;
- production HTML serves `/styles.css?v=28` and `/app.js?v=28`;
- production service worker cache is `search-shell-v28`;
- production stylesheet contains `body {` and no `bwdy {` selector.

No direct production edits were made.

### Visual acceptance

Still `NOT_VERIFIED` from automation because no authenticated browser/Chromium harness is available on VM101 and public Basic Auth must not be bypassed.

Exact next action for Phase E visual closure: authenticated user-side hard refresh and desktop/mobile screenshots.

### Separate operational RED FLAG

SexPlex sitemap/XML currently intermittently/repeatedly returns malformed XML (`not well-formed (invalid token): line 11502, column 245`) and can make `search-engine-backfill.service` exit 1. This is independent of the Phase E frontend release and maintenance lock was free during the v28 deploy. Treat SexPlex as separate provider-maintenance work.

## 2026-09-21 — AUTHORITATIVE SEXPLEX MALFORMED CHILD SITEMAP FIX

This section closes the SexPlex malformed-XML operational RED FLAG recorded in the Phase E checkpoints.

### Root cause — VERIFIED

SexPlex root sitemap index at https://sexplex.com/sitemap.xml is valid and currently advertises 342 video child sitemaps.

A fresh read-only scan with SearchEngineIndexer/0.5 found exactly one malformed child shard:
- https://sexplex.com/sitemap/?type=videos&from_links_videos=41
- parser error: not well-formed (invalid token): line 11502, column 245

The generic sitemap crawler previously tolerated missing child shards with HTTP 404 but treated ElementTree.ParseError from any child as fatal, aborting the whole provider and causing search-engine-backfill.service to exit 1.

### Fix — VERIFIED

Branch: fix/sitemap-malformed-child
Code SHA: 75d25430070d60ff1f022d47d6e1142275f773fa

Behavior:
- malformed child sitemap: skip that child and continue;
- malformed root sitemap: remains fatal;
- no broad XML sanitization and no provider-specific bypass.

Verification:
- malformed-child regression observed RED before fix and GREEN after;
- malformed-root regression remained fatal;
- tests/test_sitemap_crawl.py: 9 PASS;
- full suite: 244 PASS;
- only 2 pre-existing FastAPI on_event deprecation warnings;
- python compileall backend: PASS;
- git diff check: PASS.

A real-network probe using current SexPlex shard 41 followed by shard 42 confirmed the fixed crawler skipped shard 41 and returned a valid record from shard 42.

### Production — VERIFIED

Official helper CHECK passed for build 75d25430070d.
Official helper deploy executed. SentinelX transport timed out, so success was established independently:
- helper status build: 75d25430070d;
- /api/health: status=ok;
- search-engine.service: active;
- sync timer: active;
- backfill timer: active;
- deployed sitemap.py contains the child-only ElementTree.ParseError guard.

Natural production acceptance after deploy:
- backfill started: 2026-09-21 00:16:34 CEST;
- maintenance lock acquired normally;
- SexPlex result: batches=1 fetched=250 status=paused;
- backfill final state: Result=success, ExecMainStatus=0;
- unit finished successfully at 2026-09-21 00:19:37 CEST.

The recurring SexPlex malformed-XML backfill failure is CLOSED.

### Remaining product gate

Phase E automated and production verification is complete, including frontend shell v28 and this provider-maintenance fix.
Authenticated browser visual smoke remains NOT_VERIFIED because public UI access is protected by operator Basic Auth and no authentication bypass is permitted.
Exact next action: authenticated user-side hard refresh plus desktop/mobile screenshots to close Phase E visual acceptance.

## 2026-09-21 — SEXPLEX STABILITY RECHECK

Fresh production verification after the malformed-child sitemap fix:
- production build: 75d25430070d
- API health: status=ok
- indexed items observed: 1,131,703
- service, sync timer and backfill timer: active
- second independent natural backfill acquired the maintenance lock
- SexPlex result: batches=1 fetched=250 status=paused
- backfill unit result: success, ExecMainStatus=0

This is a second independent production acceptance after the initial successful run. The SexPlex malformed-child incident remains CLOSED.

Phase E visual acceptance remains NOT_VERIFIED until an authenticated desktop/mobile browser screenshot is supplied.

## 2026-09-21 — CONTENT CLASSIFICATION V2 DESIGN CHECKPOINT

User approved the in-chat Content Classification v2 design direction.

Verified problem statement:
- the existing content-class filter/API works correctly;
- representative query `Tiny` before v2: all=8,093, amateur=47, studio=0, unknown=8,046;
- the deficiency is trusted classification evidence, not filter transport.

V2 design principles:
- no title/provider/domain/image inference;
- no provider-wide studio assumptions;
- missing evidence remains unknown;
- amateur+studio conflict remains unknown;
- public enum remains amateur/studio/unknown;
- classification provenance is internal;
- existing tags/studio are reclassified offline before network enrichment;
- unresolved unknown rows are enriched only through bounded/resumable page metadata collection;
- existing maintenance lock remains authoritative;
- Preview Coverage is explicitly out of scope.

Written design spec:
`docs/superpowers/specs/2026-09-21-content-classification-v2-design.md`

Branch/worktree:
- branch: `feature/content-classification-v2`
- worktree: `/opt/bs-sandbox/search_engine-worktrees/content-classification-v2`
- base: `2f1352a545b74be56efb2bef9e7f4ce5563bd1a7`

No product code has been changed yet.
No production change has been made.

Exact next gate:
1. user reviews/approves the written spec;
2. only after written-spec approval, create the implementation plan with the writing-plans workflow;
3. only after plan review/execution-method approval, begin TDD implementation.

## 2026-09-21 — AUTHORITATIVE CONTENT CLASSIFICATION V2 PLAN CHECKPOINT

Content Classification v2 written spec has been approved.
Implementation plan is complete and self-reviewed.

Branch: feature/content-classification-v2
Spec: docs/superpowers/specs/2026-09-21-content-classification-v2-design.md
Plan: docs/superpowers/plans/2026-09-21-content-classification-v2.md

Plan decomposition: 8 tasks.
1. Read-only provider evidence audit and explicit enrichment capability.
2. Provenance-aware deterministic classifier.
3. Trusted productionCompany/page metadata extraction and evidence-safe merge.
4. SQLite provenance migration and atomic evidence persistence.
5. Bounded offline reclassification and observability CLI.
6. Bounded Unknown enrichment with retry/backoff.
7. Existing maintenance-lock scheduler integration.
8. Integration gate, rollout, measurement, and handoff.

Hard rules remain: no title/provider/domain/image inference, no public enum/API change, conflicts remain Unknown, all production data work bounded/resumable, official deploy path only.

Implementation has NOT started.
Next gate: plan review and execution method selection.
## 2026-09-21 — CONTENT CLASSIFICATION V2 PRE-RELEASE GATE

Status: implementation complete on isolated branch; production unchanged.

Branch: `feature/content-classification-v2`
Code HEAD before this docs checkpoint: `810c332002a1bfc6070579f1309af2ff6abaad62`

Implemented:
- read-only provider evidence audit and explicit `content_class_enrichment` capability;
- provenance-aware deterministic classifier with no title/provider/domain/image inference;
- trusted Schema.org `VideoObject.productionCompany` extraction;
- additive SQLite `content_class_source` and durable enrichment retry state;
- evidence-safe update path preserving unrelated row fields;
- bounded dry-run/apply `reclassify-content` plus `content-class-stats`;
- bounded sequential unknown-content enrichment with failure isolation and retry/backoff;
- enrichment handoff after successful ordinary backfill inside the existing maintenance lock;
- systemd defaults: batch 25 / 45 seconds.

Audit-enabled providers:
`brazzilmoms`, `fpo`, `serviporno`, `sextubespot`, `xcafe`, `xgroovy`, `xnxx`, `xvideos`.

Verification:
- targeted Content Classification v2 gate: 64 PASS;
- full suite: 285 PASS;
- only 2 pre-existing FastAPI `on_event` deprecation warnings;
- backend compileall: PASS;
- frontend `node --check`: PASS;
- `git diff --check`: PASS.

Production baseline before v2 deploy:
- production build: `75d25430070d`;
- health: `status=ok`;
- active indexed rows: 1,152,018;
- class distribution: amateur 1,722 (0.15%), studio 0, unknown 1,150,296 (99.85%);
- `content_class_source`: absent;
- `content_enrichment_state`: absent;
- representative query `Tiny`: all 8,390 / amateur 79 / studio 0 / unknown 8,311;
- `search-engine.service`, sync timer, backfill timer: active.

Rollout sequence:
1. push feature and fast-forward `feature/provider-registry-probe`;
2. fast-forward canonical sandbox to exact release SHA;
3. official helper CHECK;
4. official deploy during a natural free maintenance-lock window;
5. verify health/schema/API before any data mutation;
6. run production reclassify dry-run;
7. apply reclassification only in bounded maintenance-lock chunks;
8. observe at least two natural backfill+enrichment runs;
9. record after-distribution, `Tiny`, manual evidence samples and final handoff.

`PRODUCTION_UNCHANGED` at this checkpoint.

## 2026-09-21 — AUTHORITATIVE CONTENT CLASSIFICATION V2 PRODUCTION CLOSEOUT

Status: **DONE / PRODUCTION ACCEPTED**.

This section supersedes earlier Content Classification v2 checkpoints where rollout was pending.

### Final release state
- Feature branch: `feature/content-classification-v2`
- Release branch: `feature/provider-registry-probe`
- Final deployed code SHA: `caf2da197ae6144bb5bacfcada2cd51b397e81ce`
- Production build: `caf2da197ae6`
- Health: `status=ok`
- search service, sync timer, backfill timer: active
- Production must stay on code build `caf2da197ae6`; later closeout commit is docs-only.

### Final verification
- full suite: **286 PASS**
- only 2 pre-existing FastAPI `on_event` deprecation warnings
- backend compileall: PASS
- frontend node syntax: PASS
- git diff check: PASS
- `content_class_source`: present
- `content_enrichment_state`: present
- search API normal/studio requests: HTTP 200
- invalid content class: HTTP 422

### Important rollout ruling
The first v2 dry-run predicted 49 Studio rows. Manual review showed that bare tag `studio` can describe context such as a recording studio rather than a production company. No apply was performed from that dry-run.

TDD regression fix `caf2da197ae6144bb5bacfcada2cd51b397e81ce` removed bare `studio` from studio tag evidence. Valid Studio evidence remains exact `professional` or `production`, or an explicit structured studio label.

Corrected dry-run before apply:
- scanned 1,155,501
- changed 95,645
- conflicts 3
- before: amateur 2,016 / studio 1 / unknown 1,153,484
- predicted after: amateur 96,002 / studio 30 / unknown 1,059,469

Manual bounded evidence review PASS:
- Amateur rows had explicit `amateur` or `homemade` evidence.
- Studio rows had explicit `professional` evidence or structured studio labels such as Brazzers or Old4K.
- conflict rows contained both evidence classes and remained `unknown/conflict`.
- no title, provider, domain, or image inference was introduced.

### Production reclassification
Reclassification was applied in bounded 50,000-row chunks under the existing maintenance lock. An overlapping timer tick was cleanly skipped with `SEARCH_MAINTENANCE=SKIPPED reason=lock-busy`; no writers overlapped.

Final idempotency dry-run:
- scanned **1,157,022**
- changed **0**
- conflicts **3**
- amateur **96,041**
- studio **33**
- unknown **1,060,948**
- sources: tag_amateur 96,041 / tag_studio 29 / studio_label 4 / conflict 3 / none 1,060,945
- percentages: amateur 8.3007% / studio 0.0029% / unknown 91.6964%

High Unknown remains valid where trusted evidence is absent.

### Natural enrichment acceptance
Configured in the existing backfill maintenance lock:
- `SEARCH_CONTENT_ENRICH_BATCH_SIZE=25`
- `SEARCH_CONTENT_ENRICH_MAX_SECONDS=45`

Natural run A: attempted 25 / enriched 14 / amateur 5 / studio 1 / conflicts 0 / no_signal 19 / failures 0 / unit success.

Natural run B: attempted 25 / enriched 17 / amateur 3 / studio 3 / conflicts 0 / no_signal 19 / failures 0 / unit success.

Scheduler stability: PASS.

One first post-deploy backfill invocation failed with status 2 during a deploy race where the systemd unit already had new flags while that invocation still observed the old CLI argument surface. Read-only investigation confirmed the final runtime CLI exposes both enrichment flags, and subsequent natural runs passed. Incident CLOSED.

### Representative query acceptance: Tiny
Before v2 via production `/api/search?q=Tiny`:
- all 8,390
- amateur 79
- studio 0
- unknown 8,311

After v2 via the same API query:
- all 8,398
- amateur 1,759
- studio 1
- unknown 6,638

The small total-count difference is from normal sync/backfill activity during rollout. The class split now reflects explicit evidence rather than leaving nearly every result Unknown.

### Provider coverage
Page enrichment capability is enabled only for audited providers:
`brazzilmoms`, `fpo`, `serviporno`, `sextubespot`, `xcafe`, `xgroovy`, `xnxx`, `xvideos`.

No provider identity or domain is classification evidence.

### Next product slice
Content Classification v2 is closed. No more reclassification mutation is required.

Recommended next slice: **Preview Coverage**. Audit provider preview extraction and media-policy coverage, then improve `preview_url` coverage in bounded or on-demand fashion instead of crawling the whole index aggressively.

## 2026-09-21 — PREVIEW COVERAGE V2 SPEC CHECKPOINT

Status: in-chat architecture approved; written spec created; implementation NOT started.

Branch: `feature/preview-coverage-v2`
Base: `1a9aa1f5e40ee6fbe0b9264a1aa850bf676ac581`
Spec: `docs/superpowers/specs/2026-09-21-preview-coverage-v2-design.md`

Verified read-only baseline used by the spec:
- active rows: 1,158,630
- stored non-empty previews: 6,205 (~0.54%)
- 14 providers currently have any stored preview
- sitemap/page pipeline does not persist previews today
- `SitemapProvider._merge_enriched_item()` does not merge preview today
- existing media policy allows several known providers and deliberately disables `pornhat`, `porndr`, `anyporn`
- Tube8 is the clearest gap: ~245k indexed rows but only ~586 stored previews

Approved architecture:
- provider-by-provider read-only preview audit
- explicit `preview_enrichment` capability, default OFF
- evidence-only preview extraction; no guessed URLs/full-video substitution
- media-policy validation before playable storage/use
- non-destructive preview-only DB update
- durable preview enrichment retry state
- bounded enrichment under the existing maintenance lock
- stats for stored vs policy-playable preview coverage
- no UI rewrite
- no mass crawl

Hard gate:
- user must review/approve the written spec before implementation planning
- implementation has NOT started
