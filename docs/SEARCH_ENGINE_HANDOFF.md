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
