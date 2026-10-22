# Staging isolation and search rollout design

## Intent and constraints

`test.blackserv.eu` must exercise the candidate frontend and backend without touching the production API or database. `search.blackserv.eu` stays on its current build until the candidate passes staging checks. The operator asked to stop if a step poses a material risk to the shared VPS.

## Topology

- Production remains on port 8775 and `/var/lib/search_engine/search.db`.
- The test vhost's `/api/` and `/test-api/` both target port 8776. Its static root remains `/opt/search-engine-premium-test`.
- The test service retains its own SQLite database at `/opt/search-engine-premium-test-data/search.db`. Its code is switched to a versioned release directory, not written into `/opt/search_engine`.
- A consistent SQLite backup and copies of the previous Nginx and test-service configuration are retained until acceptance.

## Release gates

1. Verify the candidate matches the chosen release commit, the test vhost routes only to 8776, and production health reports its pre-deployment build.
2. Verify the test service restarts without a prolonged memory increase; stop if memory or swap pressure threatens the shared host.
3. Confirm staging health, representative searches (`4k`, plain multiword, forced `+` terms), pagination past offset 5000, UI states, and thumbnail fallback. Do not interpret upstream 404/410 images as fixed.
4. Run the repository's Linux tests and the official production deployment `check`. Deploy production only when staging and checks pass, with the official rollback-capable deploy client.

## Rollback

Restore the previous test service working directory and static frontend from saved copies, reload the service, verify its original build, and restore the vhost backup if routing needs to return to the original setup. Never restore the production database from a test backup.
