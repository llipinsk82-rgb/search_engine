# Search Engine — CURRENT HANDOFF

Updated: 2026-09-20 UK

## Project

- Repo: `llipinsk82-rgb/search_engine`
- Development branch: `feature/content-class-filter`
- Release branch: `feature/provider-registry-probe`
- Canonical sandbox: `/opt/bs-sandbox/search_engine`
- Production: `/opt/search_engine`
- Deploy helper: `/usr/local/bin/search-engine-deploy-client`
- Public alias: `search.blackserv.eu`
- Backend: `127.0.0.1:8775`

## Fresh VM101 / production verification — 2026-09-20

BlackServ Bridge was functional at the start of this session and reached VM101 (`os2.blackserv.eu`) as user `blackserv`.

Fresh verified production state:

- production build: `6eb04675eda9505ab4794a4cb5eb5f622b0bf0f2` (`6eb04675eda9`)
- `search-engine.service`: active
- sync timer: active
- backfill timer: active
- `/api/health`: `status=ok`
- indexed items at the fresh check: `1095322`
- configured index providers: 31
- live providers: 25
- trusted providers: 55
- available providers: 55

Fresh canonical sandbox state at that check:

- branch: `feature/provider-registry-probe`
- HEAD: `6eb04675eda9505ab4794a4cb5eb5f622b0bf0f2`
- working tree dirty only because `docs/SEARCH_ENGINE_HANDOFF.md` had an uncommitted documentation update
- no application-code diff was present
- official helper `check` correctly refused a dirty source checkout

Direct read of `/opt/search_engine` remains permission-denied for `blackserv`; production state must be verified through the authorized helper/API path, not by bypassing permissions.

Later in the same session the BlackServ Bridge capability disappeared from the available tool registry again. Plugin discovery does not expose a reconnectable public BlackServ Bridge plugin. Therefore no further VM101 mutation/test/deploy was attempted after that point.

## Phase A / B / C

- Phase A Media Reliability: DONE / deployed / production smoke PASS.
- Phase B Cards/UI v2: code/tests/deploy PASS; authenticated visual browser smoke remains `NOT_VERIFIED`.
- Phase C Metadata + Sorting: DONE / deployed / production API acceptance PASS.
- Current production frontend is v25 because production remains on `6eb04675...`.

## Phase D code state

Phase D Tasks 1–4 are implemented on `feature/content-class-filter`.

Relevant history:

1. `9dcbef3218f9bf6cdb698e18a392c60624fe24c1` — explicit content classifier
2. `a09103b49fe575cef26dfca2bb3f5888d4010547` — persistence/migration
3. `d5b8ede35b4b6c8f0475be4dd2a4f42c2d4c4af4` — API/search/live filter
4. `9cb5948995da9115e281f4f28d9bb3310f927bf0` — frontend v26
5. `3107e7552762d80b44d463c5af77ecc3a6f75916` — docs-only handoff refresh
6. `613cf769e1adfe665416ef7f6dcc269e1ed0fbcc` — restore minimal `backend/index.py` structure after Task 3 patch churn
7. `6533ab7c541832eab519ff43c6621fb981ead3ff` — docs-only release blocker/cleanup handoff

GitHub still freshly verifies `613cf769...` is a clean fast-forward descendant of release `6eb04675...`:

- ahead: 6
- behind: 0
- merge base: `6eb04675eda9505ab4794a4cb5eb5f622b0bf0f2`

However, **do not fast-forward or deploy `613cf769...` as-is now**. A new cache-semantics RED FLAG was found by direct code inspection and must be closed first.

## Implemented Phase D behavior

- Explicit content classes: `amateur`, `studio`, `unknown`.
- No title-based inference.
- Tag/studio driven classification only.
- Conflicting explicit evidence resolves to `unknown`.
- SQLite schema/persistence includes `content_class` and `studio`.
- Migration is additive and preserves existing rows.
- Search supports exact `content_class` filtering.
- GET/POST validation rejects unsupported values.
- Frontend v26: All / Amateur / Studio / Unknown.
- Cards show `Amateur` only for explicit amateur classification.
- Studio name appears only when a real studio value exists.
- No fake `Unknown` card badge.
- Mobile one-column behavior preserved.

## Resolved earlier RED FLAG: backend/index.py rewrite

Task 3 previously rewrote/minified too much of `backend/index.py`. Repair commit `613cf769...` restored the Task 2 structure and kept only the minimal content-class plumbing.

Historical shadow verification on exact `613cf769...`:

- full Python suite: 227 passed
- targeted content-class/sorting/migration gate: 29 passed
- 2 existing FastAPI `on_event` warnings
- `python -m compileall -q backend`: PASS
- `node --check frontend/app.js`: PASS
- `git diff --check`: PASS

These remain shadow results and do not replace a fresh canonical VM101 gate.

## NEW RED FLAG — live filtered request can narrow the cache

Fresh inspection of `backend/app.py` at exact `613cf769...` confirms the current flow in `/api/live-refresh` is:

1. `refresh_live_search(...)` fetches provider results.
2. Each provider result is passed through `filter_live_items(provider_result.items, payload.content_class)`.
3. The already filtered `result.providers` collection is then passed to `cache_live_provider_results(...)` as a background task.
4. The filtered collection is also used to build the response.

Therefore a request such as `content_class=amateur` can cause only the amateur subset from that live fetch to be handed to the cache layer. This is the exact architecture concern already called out in the broader project handoff.

Root-cause evidence:

- `backend/app.py` mutates `provider_result.items` before scheduling the cache task.
- `tests/test_content_class_filter.py::test_live_results_are_classified_before_content_filtering_and_cache` checks response classification/filtering but does **not** assert what collection is passed to `cache_live_provider_results`.
- This explains how the historical 227-test shadow suite could remain green while cache narrowing was not actually pinned by a regression test.

### Required semantics

The intended minimal model is:

1. fetch full live provider results,
2. classify/normalize all live items,
3. cache the full normalized provider batches,
4. derive a filtered response copy for the current `content_class` request,
5. never mutate/cache a request-specific subset as the canonical live cache representation.

Do not add a new subsystem. This should remain a small Phase D correction.

## Required TDD fix before release

When canonical VM101 execution is available again:

1. Create/use an isolated clean worktree from the latest Phase D code branch.
2. Add a regression test that patches `cache_live_provider_results` and proves an `amateur` request still hands the cache the full classified batch (`amateur`, `studio`, `unknown`), while the returned response contains only amateur items.
3. Run the new test and observe the expected RED on current code.
4. Make the smallest implementation change that separates full classified cache data from the filtered response data.
5. Re-run the regression test to GREEN.
6. Run the existing content-class targeted gate.
7. Run the full pytest suite.
8. Run `python -m compileall -q backend`.
9. Run `node --check frontend/app.js` if Node exists on VM101; otherwise keep that limitation explicit.
10. Run `git diff --check`.
11. Verify clean worktree and inspect the final diff.
12. Commit/push the code fix to `feature/content-class-filter`.
13. Record the new exact code SHA. That new SHA, not `613cf769...`, becomes the Phase D deploy candidate.
14. Verify release `feature/provider-registry-probe` remains at `6eb04675...` and the new code SHA is a clean fast-forward descendant.
15. Fast-forward the release branch to the new exact code SHA only; do not include later docs-only commits in the release target.
16. Push release branch.
17. Run `/usr/local/bin/search-engine-deploy-client check`.
18. If CHECK PASS and maintenance gate is naturally free, deploy only through the authorized helper.
19. Verify deployed build exact SHA, `/api/health`, service, sync timer and backfill timer.
20. Production acceptance must cover cached/live `amateur`, `studio`, `unknown`, invalid value 422, no-title-inference, and specifically prove that a filtered live request does not poison/narrow subsequent cached results.
21. Verify frontend v26 selector/assets if authorized access is available; authenticated visual browser smoke remains `NOT_VERIFIED` if access is unavailable. Do not bypass Basic Auth.
22. Only then mark Phase D DONE.

## Release safety

Do not:

- deploy `613cf769...` before the cache semantics fix,
- deploy any docs-only commit,
- edit production directly,
- fake a VM101 gate from shadow tests,
- use unrelated SentinelX host `blackserv` as VM101,
- kill healthy sync/backfill jobs,
- bypass the authorized deploy helper,
- bypass Basic Auth,
- claim Phase D production PASS before canonical test gate + helper deploy + independent acceptance.

## Phase E — Frontend Product Finish

Phase E starts only after Phase D is production-complete.

Approved direction:

1. a11y card semantics: remove interactive button inside thumbnail link; give thumbnail link an accessible name; narrow `aria-live` to a status region.
2. Result Card V3: image -> quality/duration -> preview -> title -> views/rating/date -> provider/studio/content metadata.
3. Mobile Filters V2: visible `Sort | Type | Filters(n)`; secondary filters in an apply-based mobile panel/bottom sheet.
4. Loading/updating/empty/error/partial-provider states.
5. Product identity cleanup: remove `DEV`/generic technical chrome.
6. Desktop filter hierarchy: Sort/Content primary; Provider/Quality/Duration secondary; Age check advanced.
7. Stronger manual Preview affordance; still no autoplay and only one preview at a time.
8. Safer PWA update UX.
9. Browser-level regression coverage where feasible.

No React/Vue/framework rewrite. Preserve existing search/live/prefetch/media behavior.

## Current blocker

At this handoff update the required next action is blocked by missing BlackServ Bridge/VM101 execution capability in the active tool registry. GitHub remains available, but GitHub-only edits or shadow tests are not an acceptable substitute for the required canonical RED→GREEN/full gate.

## CTO mode

`/loop /cto /minimal /handoff /go` means continue autonomously through safe reversible steps. Stop only for a real blocker, irreversible/destructive risk, or evidence that would require guessing.
