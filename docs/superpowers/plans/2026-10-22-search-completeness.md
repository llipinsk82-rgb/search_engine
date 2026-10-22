# Search completeness and safe rollout

## Verified baseline

- Production runs commit `761ac2100b96` on `127.0.0.1:8775` and has about 1.38 million indexed items.
- `test.blackserv.eu/api/` currently targets production `8775`; only `/test-api/` targets the older isolated `8776` backend.
- Cached search parses `sis step family` and `sis+step+family` as AND across title/tags; live explicit-plus queries are also post-filtered.
- API rejects offsets above 5000. Frontend repeatedly asks for offset 0 and excludes at most 800 seen IDs, so deep paging cannot be complete.
- Live refresh can return many results from 25 providers, but the frontend keeps only 40 merged items per page and discards the rest.
- Baseline Windows suite has 399 passing and 31 failing tests, mostly due to Windows SQLite file-lock teardown; Linux verification is required before release.

## Implementation

1. Add failing API and frontend regression tests for deep offset and lossless merged paging.
2. Remove the artificial API offset ceiling, use a one-row lookahead for accurate `has_more`, and give local pages a monotonic offset.
3. Keep unused cached and live rows in separate frontend buffers, consuming them over later pages without re-fetching page 1 or dropping provider results. Preserve paging state across browse-position snapshots.
4. Run focused tests, full suite in a Linux-safe environment, JS syntax and frontend contract checks.
5. Stage through the project's official isolated test path only after the current test worker's high memory footprint is understood; verify routing, performance and rollback before any production deploy.

## Stop conditions

- Do not deploy simplified `main` over production.
- Do not direct-edit `/opt/search_engine` or the production SQLite database.
- Stop server-side rollout if memory, swap, maintenance lock, test routing or official deployment checks indicate material risk.
