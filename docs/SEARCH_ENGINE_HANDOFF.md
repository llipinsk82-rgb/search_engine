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
