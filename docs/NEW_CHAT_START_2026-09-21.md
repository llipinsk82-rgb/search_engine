# NEW CHAT START — BlackServ Search Engine — 2026-09-21

Paste this message into the new chat.

---

## 2026-09-22 CURRENT OVERRIDE

This block supersedes older build / Preview-v3-next-step statements later in this file.

- Canonical branch: feature/provider-registry-probe.
- Production code/build: de29714afbc5.
- Canonical health endpoint: /api/health; production service is active.
- Preview Coverage v3 is CLOSED; do not restart the provider audit.
- Newly promoted production preview providers: xvideos, xnxx, mypornhere, pussyspace, porndig, sexvid, pornid, zbporn.
- Fresh production smoke on 2026-09-22: 8/8 /api/preview PASS with non-empty preview URLs.
- xgroovy is not promoted: lab status Proxy required.
- xcafe is partial only: 9/12 item-bound preview probes PASS, 3/12 404; no production rule.
- test.blackserv.eu is the isolated Preview Lab; owner confirmed one-tap Play on Android.
- Next product priority: read-only frontend truth check for stale DEV report and authenticated desktop three-column visual acceptance. Do not patch frontend before loaded asset/cache truth is established.
- Classification v2.1 continues scheduled enrichment; no heuristic mass crawl.

You are continuing **BlackServ Search Engine** as CTO / Tech Lead.

Work mode:
`/loop /cto /minimal /handoff /go`

Do not restart discovery from zero. Do not guess. Verify current state first and continue from the exact verified point below.

## FIRST ACTIONS

1. Check tool availability in this session.
2. Prefer BlackServ Bridge if it exists and works.
3. If Bridge is unavailable, the owner explicitly authorized **SentinelX as a temporary exception**, ONLY for Search Engine / VM101. Do not change other projects or PVE configuration.
4. Read in full:
   - `/opt/bs-sandbox/search_engine/docs/SEARCH_ENGINE_HANDOFF.md`
   - `/opt/bs-sandbox/search_engine/docs/NEW_CHAT_START_2026-09-21.md`
5. Verify git and production state before changing anything.
6. Do not reset/clean/force-checkout existing worktrees or delete stashes.
7. Do not redeploy docs-only commits.

## PROJECT / ACCESS

Repo: `llipinsk82-rgb/search_engine`
Canonical sandbox: `/opt/bs-sandbox/search_engine`
Production: `/opt/search_engine`
Backend: `127.0.0.1:8775`
Public: `search.blackserv.eu`
Production DB: `/var/lib/search_engine/search.db`

Public UI is behind external authentication. Do not bypass it or extract credentials.

Official deploy helper only:
```bash
sudo -u blackserv /usr/local/bin/search-engine-deploy-client status
sudo -u blackserv /usr/local/bin/search-engine-deploy-client check
sudo -u blackserv /usr/local/bin/search-engine-deploy-client deploy
```

No direct production edits. No manual production DB writes. Respect maintenance lock and healthy sync/backfill jobs.

SentinelX transport if Bridge is missing:
- host id: `host_e174a7a41f23328d`
- PVE hostname: `blackserv`
- VM101 alias: `sentinel-bs-os2`
- VM101: `vps-vpn`, `192.168.1.100`
- Search Engine scope only.

## CURRENT GIT STATE TO VERIFY

Canonical worktree:
- path: `/opt/bs-sandbox/search_engine`
- branch: `feature/provider-registry-probe`
- local HEAD at handoff time: `671d9d57c993f8f51273efbf7a7d174852bbdc01`
- origin branch at handoff time: `4df78a1ff4779c7f7ecd7805b9d1e378a3e386cf`
- canonical local branch was ahead by 6 commits

Current v2.1 worktree:
- path: `/opt/bs-sandbox/search_engine-worktrees/content-classification-v2-1`
- branch: `feature/content-classification-v2-1`
- HEAD before final docs refresh: `5c14966387e5c0ab8963919037ca1ebd789a94f0`
- origin before final docs refresh: `0876f9ef863153f41ed4e95d3e080a92f3a66757`
- branch was ahead by one docs-only closeout commit before this final handoff/docs commit

Preserved stashes:
- `stash@{0}: pre-phase-e-release-handoff-20260920`
- `stash@{1}: predeploy-handoff-20260920`
Do not delete them.

## PRODUCTION — VERIFIED CURRENT STATE

Production code build: `671d9d57c993`

Health:
- status OK
- version 0.5.0
- indexed items 1,206,272
- indexed providers 55
- configured index providers 31
- live providers 25
- trusted providers 55
- available providers 55
- service active
- sync timer active
- backfill timer active

## CONTENT CLASSIFICATION — WHAT HAPPENED AND WHY

User reported that `Amateur / Studio / Unknown` looked broken.

We proved the select/API filter works. The issue is metadata/evidence coverage.

Old `Tiny` split:
- All 8093
- Amateur 47
- Studio 0
- Unknown 8046

After Classification v2:
- All 8468
- Amateur 1763
- Studio 7
- Unknown 6698

Fresh handoff split:
- All 8518
- Amateur 1767
- Studio 8
- Unknown 6743

Therefore:
- filtering is correct;
- `Unknown` means insufficient trusted evidence;
- do NOT infer from titles/provider names just to improve counts.

### Classification v2.1 is COMPLETE and DEPLOYED

Spec:
`docs/superpowers/specs/2026-09-21-content-classification-v2-1-design.md`

Plan:
`docs/superpowers/plans/2026-09-21-content-classification-v2-1.md`

Audit:
`docs/CONTENT_CLASSIFICATION_V2_1_PROVIDER_AUDIT.md`

Verified/deployed code SHA:
`671d9d57c993f8f51273efbf7a7d174852bbdc01`

Important commits:
- `d524be9` define v2.1
- `05eb302` plan v2.1
- `b552321` provider audit
- `86e0303` studio evidence rule loader/extractor
- `527395a` provider enrichment integration
- `671d9d5` provenance regression lock / deployed code
- `0876f9e` predeploy gate docs
- `5c14966` production closeout docs

All 31 configured sitemap providers were audited.

Confirmed item-bound Studio rules:
- xgroovy: JSON-LD `VideoObject.productionCompany`
- xcafe: scoped microdata `productionCompany -> name`
- porndoe: JSON-LD `VideoObject.producer -> name`

Rejected as ambiguous:
- xvideos sponsor/uploader data
- xxxbule mixed genre/performer data
- pornsexvideo site/related-card text
- sexplex serialized studio index without a proven stable item-bound value path

No title/provider/uploader/channel/category/recommendation inference is allowed.

Verification:
- baseline 345 PASS
- final v2.1 full suite 360 PASS
- compileall PASS
- JS syntax PASS
- diff check PASS
- helper CHECK PASS
- deploy PASS
- health PASS

Initial bounded post-deploy enrichment:
- attempted 25
- enriched 21
- amateur 2
- studio 7
- conflicts 0
- no_signal 16
- failures 0

Immediate `studio_label`: 131 -> 138 (+7), exactly matching the cycle.

Fresh current production classification:
- unknown/none 1,107,149
- amateur/tag_amateur 98,937
- studio/studio_label 154
- studio/tag_studio 29
- unknown/conflict 3

Scheduled enrichment is still progressing naturally.

Fresh query splits `(all/amateur/studio/unknown)`:
- Tiny `8518/1767/8/6743`
- Sis `4334/651/4/3679`
- Babe `89739/17502/47/72190`

Do NOT implement a mass crawl or heuristic Studio classifier.

## PREVIEW — CURRENT STATE AND NEXT WORK

User also asked why so few result cards have preview. This was measured.

Fresh production:
- active rows 1,206,272
- stored non-empty preview_url 6,246
- coverage ~0.52%

Stored preview rows:
- tnaflix 1239
- youjizz 917
- spankbang 915
- beeg 804
- tube8 596
- thumbzilla 385
- drtuber 318
- xhamster 276
- pornhub 234
- hqporn 133
- pornhat 126
- bigfuck 125
- porndr 101
- anyporn 77

Current practical allowed preview providers:
`beeg, youjizz, drtuber, bigfuck, hqporn, tnaflix, spankbang, thumbzilla, xhamster, pornhub, tube8`

Policy-disabled despite stored URLs:
- pornhat 126
- porndr 101
- anyporn 77

Stored potentially usable previews: **5942** before browser/session media failure.

Preview Coverage v2 already exists. Do not redo it.

Read:
- `docs/PREVIEW_COVERAGE_V2_PROVIDER_AUDIT.md`
- `docs/superpowers/specs/2026-09-21-preview-coverage-v2-design.md`
- `docs/superpowers/plans/2026-09-21-preview-coverage-v2.md`
- `deploy/search-engine-preview-rules.json`

v2 audit summary:
- PLAYBACK_CONFIRMED 9: bigfuck, drtuber, hqporn, spankbang, thumbzilla, tnaflix, tube8, xhamster, youjizz
- BLOCKED_BY_POLICY 3: anyporn, porndr, pornhat
- AMBIGUOUS 16: bigassporn, brazzilmoms, fpo, freeporn, justporn, megatube, mypornhere, porngo, pornhub, pornid, sextubespot, sexvid, sunporno, theyarehuge, xgroovy, zbporn
- NO_SIGNAL 27: beeg, bustybus, eporner, hdzog, hqporner, lexotic, milfporn, porndig, porndoe, pornobae, pornone, pornsexvideo, pornzog, pussyspace, redtube, serviporno, sexplex, tubev, txxx, voyeurhit, vxxx, xcafe, xnxx, xvideos, xxxbule, yourlust, zzztube

Beeg/Pornhub still have usable preview through existing live-adapter behavior; v2 did not need a new canonical rule for them.

### If continuing preview work, call it Preview Coverage v3

Do only:
1. fresh read-only re-audit of the 16 `AMBIGUOUS` providers plus relevant live providers;
2. accept only exact canonical item-bound preview/trailer media;
3. reject recommendation-card media, unrelated page video and full-video substitution;
4. keep current host allowlist/media safety policy;
5. use bounded/on-demand enrichment, not mass crawling.

Important opportunity:
Tube8 has ~245k indexed rows but only 596 stored preview URLs. Never crawl all 245k detail pages. Improve bounded/on-demand enrichment only if evidence supports it.

## FRONTEND / VISUAL

Premium dark media-first UI is implemented.

Authenticated mobile visual checks previously passed for:
- shell
- result cards/feed
- Filters sheet

Desktop authenticated 3-column smoke remains NOT_VERIFIED.

Premium polish source removed `DEV`, compacted provider telemetry, simplified age text, improved Reset and moved cache to v30.

However, the owner's latest mobile screenshots STILL show `DEV`.

RED FLAG:
- likely stale PWA/service-worker/browser shell, but not proven;
- verify actual loaded asset versions before changing source;
- do not blindly patch DEV again.

Floating download button and bottom `Tab / Progress / Finished` are browser-extension UI, not Search Engine.

## WHAT TO DO NEXT

No incident exists. Production is healthy.

Current user-visible priority: **preview coverage**, not another classification rewrite.

Recommended next task:
**Preview Coverage v3 audit**, starting from the existing v2 manifest and only re-checking ambiguous/current live providers.

Parallel low-risk observation:
let Classification v2.1 scheduled enrichment continue; re-measure only unless new explicit provider metadata appears.

Also keep stale-DEV/PWA verification on the board.

## WORK RULES

- TDD for behavior changes.
- Isolated worktree/branch for new implementation.
- Never direct-edit production.
- Never manually mutate production DB.
- No Cloudflare/age-gate/auth bypass.
- No guessed URLs or metadata.
- No mass crawling to force coverage.
- No deploy of docs-only commits.
- If deploy transport times out, do not blindly retry; verify helper status/build/health first.
- Keep handoff updated.
- GitHub push is part of backup discipline.

Full test command in linked worktree:
```bash
SHELL=/bin/bash /opt/bs-sandbox/search_engine/.venv/bin/python -m pytest -q
```

Release verification:
```bash
SHELL=/bin/bash /opt/bs-sandbox/search_engine/.venv/bin/python -m pytest -q
/opt/bs-sandbox/search_engine/.venv/bin/python -m compileall -q backend
node --check frontend/app.js
git diff --check
```

Continue autonomously until:
`PROJECT_DONE`, `REAL_BLOCKER`, `CRITICAL_RISK`, or explicit `STOP`.

Do not ask the owner to repeat project history. The handoff is the source of truth.
