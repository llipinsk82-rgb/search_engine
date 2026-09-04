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
