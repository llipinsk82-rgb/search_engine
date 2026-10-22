# Staging Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the search-completeness release branch HEAD on an API- and database-isolated staging site before any production deployment.

**Architecture:** Keep the existing test service and database, route the test vhost only to that service, and point its working directory at a versioned code release. Retain immutable backups and use the official production deploy client only after staging passes.

**Tech Stack:** Nginx, systemd, FastAPI, SQLite, static HTML/CSS/JS.

**Spec:** `docs/superpowers/specs/2026-10-22-staging-isolation-design.md`

## Global Constraints

- Never direct-edit `/opt/search_engine` or `/var/lib/search_engine/search.db`.
- Keep the test backend on `127.0.0.1:8776` and production on `127.0.0.1:8775`.
- Stop when memory or swap pressure creates material risk to the shared VPS.
- Candidate source must match the chosen Git release commit exactly; after any review fix, re-archive, restage, and rerun checks.

## Review Focus

- A stale Nginx worker briefly serving the old route after reload: wait until repeated health reads show the test build.
- A test worker that grows back to multi-gigabyte private memory: monitor cgroup memory and swap after realistic searches.
- SQLite migration on the test database: take a consistent backup before the candidate service starts.
- Static assets cached by the browser: verify cache version 37 and service-worker behavior on the test origin.
- Upstream thumbnails returning 404/410: verify graceful fallback, not perfect upstream availability.

---

### Task 1: Isolate the test route

**Files:** Remote test Nginx vhost only.

**Interfaces:** `/api/health` on the test host reports the build on 8776; production 8775 is unchanged.

- [x] **Step 1: Reproduce wrong route.** Test `/api/health` returned production build `761ac2100b96`.
- [x] **Step 2: Save the previous vhost, change only its `/api/` upstream, and run `nginx -t`.**
- [x] **Step 3: Reload and verify.** A subsequent read returned isolated build `2a00325f2844-test`; production still reported `761ac2100b96`.

### Task 2: Prepare the isolated test release

**Files:** New versioned directory under `/opt/search-engine-staging/releases`, test SQLite backup, test-service drop-in.

**Interfaces:** Test service runs candidate source from its release directory and retains `SEARCH_DB_PATH=/opt/search-engine-premium-test-data/search.db`.

- [x] **Step 1: Archive the selected candidate commit and verify archive integrity.** Repeat after review fixes.
- [x] **Step 2: Back up the test SQLite database using SQLite's online backup command.**
- [x] **Step 3: Install the release in a new directory; validate imports and shell syntax there.** Repeat after review fixes.
- [x] **Step 4: Add the test-only systemd working-directory/build-id override; run `daemon-reload`, restart only the test service, and verify build and memory.** Repeat after review fixes.
- [ ] **Step 5: If verification fails, remove the override, restart the old test service, and verify its old build.**

### Task 3: Stage the frontend and acceptance tests

**Files:** Test static root only, with previous copy retained.

**Interfaces:** `test.blackserv.eu` serves candidate frontend v37 and isolated API 8776.

- [x] **Step 1: Back up the current test static root and install candidate assets.** Repeat asset update after review fixes.
- [x] **Step 2: Verify health, page assets, search syntax, deep pagination, UI states, and image fallback against staging.** Repeat after review fixes.
- [x] **Step 3: Measure test memory/swap and production health after the workload. Roll back staging if thresholds indicate risk.** Repeat after review fixes.

### Task 4: Production gate

**Files:** No direct edits to production paths.

**Interfaces:** Official `search-engine-deploy-client check` and `deploy` outputs determine release readiness.

- [ ] **Step 1: Run the full repository test suite and verify no failures.**
- [ ] **Step 2: Run official deployment `status` and `check`; stop on any failed check or active maintenance lock.**
- [ ] **Step 3: Deploy only through the official client, then verify build, search endpoints, resource usage, and rollback status.**
