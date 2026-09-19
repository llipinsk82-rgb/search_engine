# Search Media Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make thumbnails and motion previews reliable and policy-driven so cards never advertise a knowingly dead PLAY action and thumbnail recovery is bounded rather than provider-name logic in the browser.

**Architecture:** Add a small server-side provider media policy module, expose media capability rows through the existing `/api/providers` response, and make the frontend resolve thumbnails/previews from that policy. Keep direct media as the default; retain Thumbzilla proxying and Tube8 refresh behavior through policy, and do not add a preview proxy unless a sampled provider proves it is required and can be strictly allowlisted.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, static HTML/CSS/JavaScript, pytest/unittest, existing urllib proxy path.

**Spec:** `docs/superpowers/specs/2026-09-19-search-ui-preview-sort-design.md`

## Global Constraints

- No video mirroring or persistent media hosting.
- No bypass of robots, age gates, anti-bot systems or private AJAX contracts.
- HTTPS-only provider media; no embedded credentials; default HTTPS port only.
- Redirects remain rejected unless an explicit provider rule validates a future redirect target.
- No autoplay; at most one motion preview active at a time.
- Preview URLs are never fabricated from image rotations or guessed paths.
- Failed preview falls back to the still and is not retried repeatedly in the same browser session.
- Thumbnail retry budget is bounded; no retry loop.
- Never deploy a dirty worktree; use the official helper CHECK/maintenance/deploy/acceptance workflow.
- Execute this plan from a separate git worktree created from `5c0764c` or later; leave the preserved PornFlip dirty files in the original sandbox untouched.

## Review Focus

- Preview URL is HTTPS but host is not in the provider allowlist: PLAY must be hidden/rejected.
- Preview begins loading but never reaches playback: restore the still and suppress repeat attempts for that item in-session.
- Thumbnail refresh endpoint returns 404/502: card must settle on placeholder without retrying forever.
- A second preview starts while one is active: the first must stop before the second plays.
- Provider has `preview_url` but policy says `disabled`: the frontend must not render PLAY.

---

### Task 1: Provider media policy module

**Files:**
- Create: `backend/media_policy.py`
- Create: `tests/test_media_policy.py`

**Interfaces:**
- Produces: `ProviderMediaPolicy`, `provider_media_policy(name: str) -> ProviderMediaPolicy`, `media_policy_rows(names: set[str]) -> list[dict[str, object]]`, `media_url_allowed(provider: str, kind: str, url: str) -> bool`.
- Initial observed preview-capable providers from the 2026-09-19 sandbox audit: `beeg`, `youjizz`, `drtuber`, `pornhat`, `porndr`, `bigfuck`, `hqporn`, `anyporn`, `tnaflix`, `spankbang`, `thumbzilla`, `xhamster`, `pornhub`, `tube8`. Their sampled preview host suffixes are respectively `vp.externulls.com`, `.youjizz.com`, `.drtst.com`, `pornhat.one`, `porndr.com`, `.bigfuck.tv`, `.hqporn.xxx`, `anyporn.com`, `.tnaflix.com`, `.sb-cd.com`, `.ypncdn.com`, `.xhcdn.com`, `.phncdn.com`, `.t8cdn.com`.

- [ ] **Step 1: Write failing policy tests**

```python
from backend.media_policy import media_policy_rows, media_url_allowed, provider_media_policy


def test_unknown_provider_defaults_to_safe_media_modes():
    p = provider_media_policy("unknown")
    assert p.thumbnail_mode == "direct"
    assert p.preview_mode == "disabled"


def test_thumbzilla_policy_uses_proxy_thumbnail_and_direct_preview():
    p = provider_media_policy("thumbzilla")
    assert p.thumbnail_mode == "proxy"
    assert p.preview_mode == "direct"
    assert media_url_allowed("thumbzilla", "thumbnail", "https://pix-cdn77.ypncdn.com/a.jpg")
    assert not media_url_allowed("thumbzilla", "thumbnail", "https://evil.example/a.jpg")


def test_non_https_credentials_and_non_default_ports_are_rejected():
    assert not media_url_allowed("thumbzilla", "thumbnail", "http://pix-cdn77.ypncdn.com/a.jpg")
    assert not media_url_allowed("thumbzilla", "thumbnail", "https://u:p@pix-cdn77.ypncdn.com/a.jpg")
    assert not media_url_allowed("thumbzilla", "thumbnail", "https://pix-cdn77.ypncdn.com:8443/a.jpg")


def test_preview_host_allowlist_is_provider_specific():
    assert media_url_allowed("bigfuck", "preview", "https://icdn05.bigfuck.tv/x.mp4")
    assert not media_url_allowed("bigfuck", "preview", "https://evil.example/x.mp4")


def test_provider_rows_expose_modes_without_url_secrets():
    row = next(r for r in media_policy_rows({"tube8"}) if r["name"] == "tube8")
    assert row["name"] == "tube8"
    assert row["thumbnail_mode"] == "refresh"
    assert row["preview_mode"] == "direct"
    assert ".t8cdn.com" in row["preview_host_suffixes"]
```

- [ ] **Step 2: Run tests and verify RED**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_media_policy.py`

Expected: import failure because `backend.media_policy` does not exist.

- [ ] **Step 3: Implement the minimal policy module**

Use literals `direct | proxy | refresh` for thumbnails and `direct | proxy | disabled` for previews. Store only explicit host suffixes, including the audited preview suffixes listed above. Configure Thumbzilla thumbnail proxy suffix `.ypncdn.com`; configure Tube8 thumbnail mode `refresh`; set `preview_mode="direct"` only for the audited preview-capable providers above and `disabled` for providers without observed preview metadata. `media_policy_rows()` exposes modes plus host suffixes so the browser can suppress an unexpected direct preview host before creating a media request. Keep the policy data separate from source trust policy.

- [ ] **Step 4: Run policy tests and existing source-policy tests**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_media_policy.py tests/test_source_policy.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/media_policy.py tests/test_media_policy.py
git commit -m "feat: add provider media policy"
```

### Task 2: Centralize thumbnail proxy validation and expose capabilities

**Files:**
- Modify: `backend/app.py`
- Modify: `tests/test_thumbnail_proxy.py`
- Create: `tests/test_provider_media_api.py`

**Interfaces:**
- Consumes: `media_url_allowed`, `media_policy_rows`, `provider_media_policy` from Task 1.
- Produces: `/api/providers` response field `media_policies` and policy-driven thumbnail proxy validation.

- [ ] **Step 1: Write failing API/proxy tests**

Add assertions that `/api/providers` contains `media_policies`, Thumbzilla remains `proxy`, Tube8 remains `refresh`, a non-preview provider such as `milfporn` is `disabled`, and `_thumbnail_proxy_fetch()` delegates host/scheme/credential/port acceptance to media policy rather than a private `_THUMBNAIL_PROXY_RULES` tuple.

```python
async def test_provider_api_exposes_media_policy():
    payload = await providers()
    rows = {row["name"]: row for row in payload["media_policies"]}
    assert rows["thumbzilla"]["thumbnail_mode"] == "proxy"
    assert rows["milfporn"]["preview_mode"] == "disabled"
    assert ".phncdn.com" in rows["pornhub"]["preview_host_suffixes"]
```

- [ ] **Step 2: Run targeted tests and verify RED**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_thumbnail_proxy.py tests/test_provider_observability.py tests/test_provider_media_api.py`

Expected: failure on absent `media_policies`/new validation path.

- [ ] **Step 3: Modify `backend/app.py` minimally**

Import media-policy helpers, remove `_THUMBNAIL_PROXY_RULES`, obtain the referer/allowed-host decision from `ProviderMediaPolicy`, preserve `_ThumbnailProxyNoRedirect`, the 2 MiB image limit, timeout, JPEG preference, and existing `/api/thumb-proxy` aliases. Extend `/api/providers` with `"media_policies": media_policy_rows(set(names))`.

- [ ] **Step 4: Verify security edge cases**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_media_policy.py tests/test_thumbnail_proxy.py tests/test_thumbnail_endpoint.py tests/test_provider_observability.py tests/test_provider_media_api.py`

Expected: PASS including wrong host, credentials, non-default port, redirect refusal, and valid Thumbzilla response.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py tests/test_thumbnail_proxy.py tests/test_provider_observability.py tests/test_provider_media_api.py
git commit -m "refactor: centralize provider media validation"
```

### Task 3: Audit current preview URLs and disable bad direct previews

**Files:**
- Modify: `backend/media_policy.py`
- Modify: `tests/test_media_policy.py`
- Create: `docs/media/preview-audit-2026-09-19.md`

**Interfaces:**
- Consumes: current live adapters and Task 1 policy.
- Produces: an evidence-backed direct-preview allowlist; no proxy route unless a provider fails direct browser-compatible playback solely because of a reproducible Referer/header requirement.

- [ ] **Step 1: Run bounded read-only preview audit**

For query `step`, fetch one preview-bearing item from each audited provider and perform a bounded GET/Range probe from the server. Record provider, preview host, HTTP status, content type, redirect behavior, and whether the URL is expiring/signed. Do not bypass protection and do not probe non-public/private endpoints.

- [ ] **Step 2: Write failing policy tests for any provider that must be disabled**

For every provider whose sample consistently returns non-video content, hard failure, or forbidden redirect, add an explicit assertion `provider_media_policy(name).preview_mode == "disabled"` before changing policy code.

- [ ] **Step 3: Update only evidence-backed policy entries**

Keep direct preview only where the sampled public URL returns a browser-playable video response. If a provider demonstrably requires a fixed Referer and the media host can be strictly allowlisted, document it but defer adding `preview_mode="proxy"` to a separate RED/GREEN change in this same task; otherwise disable the PLAY capability.

- [ ] **Step 4: Re-run policy tests**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_media_policy.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/media_policy.py tests/test_media_policy.py docs/media/preview-audit-2026-09-19.md
git commit -m "fix: gate previews by verified media capability"
```

### Task 4: Policy-driven frontend thumbnail and preview behavior

**Files:**
- Modify: `frontend/app.js`
- Modify: `frontend/index.html`
- Modify: `frontend/sw.js`
- Modify: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: `/api/providers.media_policies` from Task 2.
- Produces: `providerMediaPolicies: Map`, `resolveThumbnailUrl(item)`, `previewEligible(item)`, bounded thumbnail healing, session preview-failure memory.

- [ ] **Step 1: Write failing frontend contract tests**

Replace the old `thumbzilla || tube8` assertion with checks for a media policy map and helpers. Pin these behaviors in source-contract tests:

```python
assert 'const providerMediaPolicies = new Map();' in app
assert 'function resolveThumbnailUrl(item)' in app
assert 'function previewEligible(item)' in app
assert 'const failedPreviewIds = new Set();' in app
assert 'sessionStorage' in app
assert 'item.provider === "thumbzilla" || item.provider === "tube8"' not in app
```

Also assert there is no autoplay/IntersectionObserver/pointerenter behavior.

- [ ] **Step 2: Run frontend tests and verify RED**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_frontend_contract.py`

Expected: FAIL because the policy helpers do not exist and the old provider-name branch remains.

- [ ] **Step 3: Implement provider policy loading and thumbnail resolver**

During `loadProviders()`, populate `providerMediaPolicies` from `data.media_policies`. `resolveThumbnailUrl(item)` returns `/api/thumb-proxy?...` for `proxy`, the original thumbnail for `direct/refresh`, and the thumbnail error handler performs at most two existing refresh attempts only when mode is `refresh`. After budget exhaustion, show placeholder.

- [ ] **Step 4: Implement preview eligibility and failure memory**

`previewEligible(item)` requires `item.preview_url`, policy `preview_mode !== "disabled"`, URL scheme `https:`, preview hostname matching one of the provider policy suffixes, and item ID absent from `failedPreviewIds`. Start with the still visible until the video fires `playing`; on `error`, rejected `play()`, or a 4-second startup timeout, stop/hide motion, restore still, add the item ID to `failedPreviewIds`, persist a bounded array of failed IDs in `sessionStorage`, and hide the toggle. Keep one active preview at a time.

- [ ] **Step 5: Bump frontend cache version**

Change `v=22` to `v=23` in `frontend/index.html`, service-worker registration, and `CACHE = "search-shell-v23"`.

- [ ] **Step 6: Verify frontend contract**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q tests/test_frontend_contract.py tests/test_deploy_assets.py`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/app.js frontend/index.html frontend/sw.js tests/test_frontend_contract.py
git commit -m "fix: make card media policy driven"
```

### Task 5: Full verification and production acceptance

**Files:**
- Modify only if verification exposes a defect; any fix requires its own RED/GREEN test first.

**Interfaces:**
- Produces: releasable Phase A build.

- [ ] **Step 1: Run full suite and whitespace gate**

Run: `env -u SEARCH_PROVIDER_CONFIG_FILE PYTHONPATH=. .venv/bin/pytest -q && git diff --check`

Expected: all tests PASS, only the existing FastAPI deprecation warnings, diff check clean.

- [ ] **Step 2: Push the exact verified HEAD**

Push the exact HEAD to `feature/provider-registry-probe`. If Step 1 fails, do not push; return to the owning task, add a failing regression test, fix it, rerun the full gate, then resume here.

- [ ] **Step 3: Official helper CHECK and maintenance gate**

Run `/usr/local/bin/search-engine-deploy-client check`; confirm `SEARCH_DEPLOY_PROVIDER_CATALOG=PASS` and `SEARCH_DEPLOY_CHECK=PASS`. Wait for healthy sync/backfill lock naturally; never kill it.

- [ ] **Step 4: Official deploy**

Run `/usr/local/bin/search-engine-deploy-client deploy`. Require formal `SEARCH_DEPLOY=PASS` plus matching `/api/health.build` before acceptance.

- [ ] **Step 5: Production smoke**

Sample: one direct thumbnail provider, Thumbzilla proxy thumbnail, Tube8 refresh thumbnail, one verified working preview provider, and one `preview_mode=disabled` provider. Confirm thumbnail/fallback, PLAY eligibility, manual-only playback, one-preview-at-a-time, and failed preview returning to still.

- [ ] **Step 6: Record release**

Append build SHA, backup path, sampled providers, and acceptance results to `docs/SEARCH_ENGINE_HANDOFF.md`; commit/push docs-only.
