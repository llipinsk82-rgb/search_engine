# Content Classification v2.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Increase trustworthy `studio` classification coverage by extracting only explicit, canonical-item-bound studio / producer / production-company metadata from audited provider pages, while preserving the existing `amateur | studio | unknown` API and never inferring from titles or provider identity.

**Architecture:** Keep the existing `SearchItem.studio` and `content_class_source` model. Add a committed provider-evidence audit plus machine-readable rules, a small provider-scoped extractor, and integrate it into the existing bounded content-enrichment path. Rule-backed providers become eligible for scheduled content enrichment automatically; all writes still go through the existing SQLite update and reclassification flow under the maintenance lock.

**Tech Stack:** Python 3.11, Pydantic, SQLite/FTS5, urllib-based sitemap providers, JSON/HTML parsing, pytest, systemd maintenance timers.

**Spec:** `docs/superpowers/specs/2026-09-21-content-classification-v2-1-design.md`

## Global Constraints

- Public API values remain exactly `amateur | studio | unknown`.
- `content_class_source` remains authoritative provenance.
- Never classify from free-form title text or provider identity.
- Never treat performer, uploader, channel, category, navigation or recommendation-card metadata as studio evidence.
- Conflict remains `unknown/conflict`.
- Existing non-empty `SearchItem.studio` always wins over newly extracted evidence.
- Rule extraction may only fill `SearchItem.studio`; it must not mutate URL, title, thumbnail, preview, tags, age state, source order or provider cursors.
- Missing, malformed or ambiguous provider markup returns no studio evidence.
- No unbounded crawl; production audit samples at most three active Unknown canonical URLs per provider.
- Scheduled enrichment stays bounded and uses the existing maintenance lock/backoff.
- TDD is required for every behavior change.
- Full test runs use `SHELL=/bin/bash`.
- Production changes use the official deploy helper only; never edit `/opt/search_engine` directly.

## Review Focus

1. Existing studio already present: provider rule must not overwrite it.
2. Recommendation-card false positive: evidence attached to another item is ignored.
3. Uploader/channel false positive: creator/channel fields never become `studio`.
4. Malformed rule or markup: fail closed to no evidence, never crash the batch.
5. Rule-backed provider without config flag: still becomes enrichment-eligible, without enabling unrelated providers.

---

### Task 1: Provider studio-evidence audit and deterministic rule manifest

**Files:**
- Create: `docs/CONTENT_CLASSIFICATION_V2_1_PROVIDER_AUDIT.md`
- Create: `tests/fixtures/content_evidence_audit_manifest.json`
- Create: `deploy/search-engine-content-evidence-rules.json`
- Create positive/negative fixtures per confirmed provider under `tests/fixtures/content_evidence_pages/`
- Create: `tests/test_content_evidence_provider_audit.py`

**Interfaces:** audit statuses are `STUDIO_RULE_CONFIRMED | NO_STUDIO_SIGNAL | AMBIGUOUS | FETCH_UNAVAILABLE`; runtime rules are an exact projection of confirmed rows only.

- [ ] Step 1: Write failing manifest contract tests covering provider uniqueness, allowed statuses, required positive/negative fixtures, and exact confirmed-rule projection.
- [ ] Step 2: Run `SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_content_evidence_provider_audit.py` and verify RED because the manifest/rules do not exist.
- [ ] Step 3: For every configured provider, select at most three active production rows with `content_class='unknown'` and `content_class_source='none'` using read-only SQLite; fetch only canonical pages through the existing provider-safe path.
- [ ] Step 4: Accept only explicit item-bound `productionCompany`, Studio/Producer/Production company meta fields, or visible labelled fields. Mark creator/uploader/channel/category/navigation/recommendation data `AMBIGUOUS`.
- [ ] Step 5: Reduce accepted markup into deterministic positive and negative fixtures; populate audit and exact runtime-rule projection.
- [ ] Step 6: Re-run the audit tests and verify GREEN.
- [ ] Step 7: Commit as `docs: audit studio evidence providers`.

### Task 2: Provider-scoped studio rule loader and extractor

**Files:**
- Create: `backend/content_evidence_rules.py`
- Create: `tests/test_content_evidence_rules.py`
- Read: `deploy/search-engine-content-evidence-rules.json`

**Interfaces:**
- `ContentEvidenceRule`
- `CONTENT_EVIDENCE_RULES: dict[str, ContentEvidenceRule]`
- `extract_studio_evidence(provider: str, html: str, page_url: str) -> str | None`
- `has_content_evidence_rule(provider: str) -> bool`

- [ ] Step 1: Write RED tests proving positive fixture extraction, negative fixture rejection, unruled-provider `None`, and uploader/channel rejection.
- [ ] Step 2: Verify RED with `SHELL=/bin/bash .venv/bin/python -m pytest -q tests/test_content_evidence_rules.py`.
- [ ] Step 3: Implement minimal loader: normalize provider names, reject duplicates/unsupported kinds, support only `jsonld_path`, `meta_name`, `labelled_text`, return stripped non-empty strings, never perform network access, fail closed on malformed markup.
- [ ] Step 4: Add parameterized positive/negative coverage for every confirmed rule in the committed runtime manifest.
- [ ] Step 5: Verify GREEN for audit + rule tests.
- [ ] Step 6: Commit as `feat: add provider studio evidence rules`.

### Task 3: Integrate rules into canonical-page enrichment

**Files:**
- Modify: `backend/providers/sitemap.py`
- Modify: `backend/providers/__init__.py` only if required by construction path
- Create: `tests/test_content_evidence_enrichment.py`

**Behavior:**
- Existing non-empty studio wins.
- Rule fills studio only when generic parser left it empty.
- `content_class_enrichment` is true when either existing config flag is true or `has_content_evidence_rule(provider)` is true.
- All preview/core-metadata behavior remains unchanged.

- [ ] Step 1: Write RED test that existing studio is never overwritten.
- [ ] Step 2: Write RED test that confirmed-rule markup fills missing studio.
- [ ] Step 3: Write RED test that rule-backed provider becomes enrichment-eligible without explicit JSON flag.
- [ ] Step 4: Verify RED.
- [ ] Step 5: Implement minimal integration in `_fetch_page_item()` and provider initialization.
- [ ] Step 6: Run focused content-class/enrichment tests and verify GREEN.
- [ ] Step 7: Commit as `feat: enrich explicit provider studio evidence`.

### Task 4: Preserve bounded persistence and provenance

**Files:**
- Modify only if failing tests require it: `backend/content_enrichment.py`, `backend/index.py`
- Create/modify: `tests/test_content_enrichment.py`

- [ ] Step 1: Add regression test: rule-derived explicit studio persists as `content_class='studio'` and `content_class_source='studio_label'`.
- [ ] Step 2: Add regression test: no signal does not mutate item and records bounded retry state.
- [ ] Step 3: Add regression test: `amateur` tag + explicit studio remains `unknown/conflict`.
- [ ] Step 4: Run focused tests. If already GREEN, do not modify production code.
- [ ] Step 5: Commit tests as `test: lock studio enrichment provenance` if no product change is needed.

### Task 5: Full verification and pre-deploy gate

**Files:**
- Modify: `docs/SEARCH_ENGINE_HANDOFF.md`
- Update: `docs/CONTENT_CLASSIFICATION_V2_1_PROVIDER_AUDIT.md`

- [ ] Step 1: Run `SHELL=/bin/bash .venv/bin/python -m pytest -q`.
- [ ] Step 2: Run `.venv/bin/python -m compileall -q backend`, `node --check frontend/app.js`, and `git diff --check`.
- [ ] Step 3: Record exact pre-deploy production measurements read-only: active total; class/source counts; non-empty studio; `Tiny` split all/amateur/studio/unknown; two additional fixed smoke queries.
- [ ] Step 4: Update handoff with VERIFIED/NOT_VERIFIED facts and commit as `docs: gate content classification v2.1`.

### Task 6: Official deploy and bounded rollout

- [ ] Step 1: Push branch and run `sudo -u blackserv /usr/local/bin/search-engine-deploy-client check`.
- [ ] Step 2: Deploy the exact verified code SHA through the official helper only.
- [ ] Step 3: If transport times out, do not blindly retry; independently verify helper status/build and `/api/health`.
- [ ] Step 4: Run one bounded content-enrichment cycle through the existing maintenance-lock path; never edit production DB manually.
- [ ] Step 5: Collect exact post-deploy global class/source counts and the same three query splits.
- [ ] Step 6: Accept only if health PASS, totals are consistent, and any Studio increase is attributable to explicit `studio_label` evidence.
- [ ] Step 7: Close `docs/SEARCH_ENGINE_HANDOFF.md` with exact branch/SHA/tests/build/before-after counts/remaining gaps; commit docs-only and do not redeploy docs-only commit.
