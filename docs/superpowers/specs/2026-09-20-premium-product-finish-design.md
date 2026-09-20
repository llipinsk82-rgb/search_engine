# Phase E — Premium Product Finish Design

**Date:** 2026-09-20
**Status:** approved direction; implementation not started
**Base:** `82a152999e173b8649e4d6dfce5e0003cdf579d0`
**Branch:** `feature/premium-product-finish`

## Goal

Turn the existing functional dark Search frontend into a premium, media-first search/browser experience without changing the backend API contract or adding a frontend framework.

Success means the product no longer feels like “a form above a grid”. Search, filtering, cards, loading/error states and responsive behavior must feel intentional, calm and coherent while preserving current provider/search/preview behavior.

## Product direction

Approved direction: dark premium media browser, closer to a polished streaming/search product than an adult-site clone.

Principles:
- media first: thumbnail/preview dominates each card;
- quiet chrome: controls are compact and secondary to content;
- hierarchy comes from typography, spacing and surfaces, not clutter;
- no fake navigation/features or subscription UI;
- manual preview only, one at a time;
- desktop and mobile are designed separately, not merely scaled.

## Constraints / non-goals

Keep vanilla `index.html`, `styles.css`, `app.js`; existing endpoints/query model; Provider, Quality, Duration, Age Check and Content Type behavior; thumbnail self-healing; preview policy; one-column mobile media intent.

Do not add React/Vue/Svelte, Trending, Favorites, History, Studios/Performers sidebars, premium upsells, autoplay on hover/scroll, fabricated counters, recommendations or personalization.

## Desktop UX

Header: compact premium header with Search brand, no fake navigation and less vertical waste than the current hero/sticky stack.

Search hierarchy:
1. large query field;
2. primary controls: Sort + Content Type;
3. secondary controls: Provider + Quality + Duration;
4. Age Check stays advanced/secondary.

Replace the current six equal-priority selects with a clear primary/secondary hierarchy.

Results summary stays compact. Provider diagnostic detail remains available but visually de-emphasized.

## Mobile UX

Primary row: **Sort / Content / Filters**.

`Filters` opens a bottom/full-height sheet with Provider, Quality, Duration, Age Check, Clear/Reset and Apply.

Requirements:
- one-column, full-width 16:9 cards;
- large touch targets;
- keyboard-accessible, focus-managed sheet;
- body scroll controlled while open;
- filter state preserved across open/close;
- no horizontal scrolling filter strip in the finished UI.

## Result cards

Hierarchy:
1. thumbnail / motion preview;
2. Quality + Duration overlays;
3. preview control;
4. title;
5. views / rating / published date;
6. provider / studio / explicit classification metadata.

Desktop target: generally 3 columns; tablet 2; mobile 1. Use subtle borders/surfaces and spacing rather than heavy shadows.

Metadata rules:
- show `Amateur` only when explicitly amateur;
- no generic `Unknown` or `Studio` badge;
- show real studio label only when present;
- provider stays secondary;
- avoid dense metadata strings.

## Preview behavior

- manual only;
- one active preview at a time;
- no hover/scroll autoplay;
- preview button is a sibling of the media link, never nested inside `<a>`;
- starting another preview stops the previous one;
- failed preview restores static media cleanly;
- thumbnail remains independently clickable.

## Accessibility

Must fix:
- invalid button-inside-link nesting;
- thumbnail link gets an accessible name derived from title;
- remove `aria-live` from the whole results grid;
- use a dedicated status/live region;
- strong visible keyboard focus;
- useful secondary/disabled contrast;
- explicit labels for compact controls;
- mobile sheet focus trap and return-focus behavior.

## UI states

Design explicit states for idle, searching, live updating, initial skeleton, loading more, no results, filtered-empty, partial-provider availability, recoverable error + Retry, and preview failure.

Skeletons mirror card geometry and should not cause layout shift.

## Visual system

Add a small CSS token layer for page background, elevated surfaces, borders, primary/secondary/muted text, focus/accent, radius and spacing scales.

Theme remains dark and restrained. Avoid neon, loud gradients, glossy gaming aesthetics and clone branding. Keep system typography unless a font is already bundled.

## PWA update behavior

Bump frontend asset version. Keep deterministic cache invalidation. Replace abrupt/loop-prone update behavior with a safe one-time guarded refresh or a lightweight update-ready/deferred-refresh path if achievable without creating a new subsystem.

## File boundaries

- `frontend/index.html`: semantic structure, mobile sheet, corrected card template.
- `frontend/styles.css`: tokens, responsive layout, cards, sheet, skeleton/error/focus states.
- `frontend/app.js`: sheet behavior, render states, preview wiring, accessible status/labels, SW update behavior.
- `frontend/sw.js` / manifest: only as required for asset/update versioning.
- `tests/test_frontend_contract.py`: structural and behavioral contract coverage.

Backend changes are out of scope. If an API limitation blocks the approved UI, stop and re-scope rather than silently changing backend behavior.

## Data flow

Existing flow remains: query/filters → search API → indexed results → optional live refresh → merge/update cards.

One canonical filter state is shared between desktop and mobile sheet. Search state drives skeleton/status/error presentation. Result rendering continues from existing `SearchItem` fields. Preview controller owns the one-active-preview invariant.

## Error handling

Preserve usable existing results on recoverable API errors when possible. With no results, show dedicated Retry state. Thumbnail failure uses existing self-heal then placeholder. Preview failure restores image. Partial provider failures keep successful results plus a quiet notice. Sheet errors must never strand focus or page scrolling.

## TDD and verification

Extend `tests/test_frontend_contract.py` first for:
- new asset version;
- desktop/mobile filter structure;
- no nested interactive preview control;
- accessible thumbnail naming;
- dedicated live/status region;
- mobile sheet Apply/close/reset structure;
- 3/2/1 responsive layout contract;
- absence of old horizontal mobile filter strip;
- manual one-active-preview behavior retained;
- content-class metadata rules retained;
- safe service-worker update contract.

Release gate:
- targeted frontend tests;
- full Python suite;
- `python -m compileall -q backend`;
- `node --check frontend/app.js`;
- `git diff --check`;
- authenticated desktop/mobile visual smoke when operator credentials are available;
- official deploy helper only;
- post-deploy `/api/health`, build ID, service/timer checks.

## Rollout

1. implement on `feature/premium-product-finish`;
2. targeted + full gates;
3. push feature branch;
4. fast-forward release only after gates;
5. official helper CHECK;
6. official helper DEPLOY when maintenance lock is free;
7. production build/health verification;
8. authenticated visual acceptance;
9. update handoff.

## Acceptance

Phase E is complete only when desktop no longer has six equal-priority selects or a cramped four-column grid; mobile uses Sort/Content/Filters with a real sheet; cards are visibly larger and media-first; preview remains manual and one-at-a-time; invalid interactive nesting is gone; focus/status behavior is materially improved; loading/empty/error states are designed; existing functionality is preserved; automated gates pass; production build matches released SHA; and visual smoke is explicitly PASS or clearly `NOT_VERIFIED`.
