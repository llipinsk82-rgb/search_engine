# Search Product v2 Implementation Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to execute the linked plans in order unless the owner explicitly switches execution method.

**Goal:** Deliver reliable media cards, cleaner UI, real sorting, and honest Amateur/Studio filtering as four independently releasable phases.

**Architecture:** Preserve the existing FastAPI + SQLite/FTS + static frontend architecture. Each phase is testable/deployable on its own and must reach production acceptance before the next starts.

**Tech Stack:** Python 3.11, FastAPI, SQLite/FTS5, vanilla HTML/CSS/JS, pytest, systemd/nginx deploy helper.

**Spec:** `docs/superpowers/specs/2026-09-19-search-ui-preview-sort-design.md`

## Global Constraints

- Work from clean isolated worktrees; the original sandbox currently contains preserved PornFlip changes that must remain untouched.
- Use TDD RED → GREEN for every behavior change.
- Full pytest + `git diff --check` before every release commit/deploy.
- Push exact reviewed HEAD; helper CHECK; wait naturally for maintenance lock; official deploy; fresh production acceptance; handoff update.
- No protection bypasses, open proxies, autoplay, fabricated metadata, or title-based Amateur/Studio classification.

## Ordered Releases

1. `docs/superpowers/plans/2026-09-19-search-media-reliability.md`
   - provider-aware thumbnail/preview policy;
   - bounded healing/fallback;
   - dead PLAY suppression;
   - asset cache v23.

2. `docs/superpowers/plans/2026-09-19-search-cards-ui-v2.md`
   - premium compact card/search hierarchy;
   - mobile one-column feed preserved;
   - operational status demoted visually;
   - asset cache v24.

3. `docs/superpowers/plans/2026-09-19-search-metadata-sorting-v2.md`
   - nullable date/views/rating metadata;
   - RedTube first real enrichment source;
   - six sort modes with null-last semantics;
   - asset cache v25.

4. `docs/superpowers/plans/2026-09-19-search-content-class-filter.md`
   - explicit content classification only;
   - All/Amateur/Studio/Unknown filtering;
   - no title heuristics;
   - asset cache v26.

## Dependency Gates

- Phase 2 starts only after Phase 1 production acceptance.
- Phase 3 starts only after Phase 2 production acceptance.
- Phase 4 starts only after Phase 3 production acceptance.
- PornFlip provider work remains outside these plans until Phase 1 media behavior is accepted; then it can be resumed as a separate provider task against the new media policy.

## Completion Contract

Product v2 is complete only when all four phase handoff sections contain exact build SHA, deploy backup, health, automated verification and production smoke evidence. A plan file existing or a feature commit alone is not completion.
