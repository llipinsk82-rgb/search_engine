# Premium Brandless Search Redesign — Design Spec

Date: 2026-09-23
Project: BlackServ Search Engine
Status: Design approved in chat; implementation not started

## 1. Goal

Replace the current technically clean but visually generic search UI with a clearly premium, media-first experience.

The redesign must feel like a finished consumer product rather than an admin panel or developer tool. Premium quality must come from hierarchy, spacing, typography, imagery, interaction and restraint — not from BlackServ branding.

## 2. Product direction

The product is intentionally brand-light / brandless.

Do not add:
- BlackServ or BS branding;
- infrastructure identity;
- corporate logo treatment;
- decorative product naming invented for the redesign.

The existing `SEARCH` wordmark is not a defining part of the experience and may be removed, reduced or visually de-emphasized.

The visual language should be:
- dark, cinematic and calm;
- image-led;
- minimal but not empty;
- premium through typography, rhythm and depth;
- fast and practical on mobile;
- readable and efficient on desktop.

## 3. Scope

This is a frontend redesign only.

Primary implementation scope:
- `frontend/index.html`
- `frontend/styles.css`
- minimal UI-binding changes in `frontend/app.js` only where required by the redesigned controls or card structure
- frontend contract tests
- PWA asset/cache version bump only as required for rollout

Out of scope:
- backend API changes;
- provider adapters;
- preview resolver rules;
- classification semantics;
- database schema;
- search ranking logic;
- preview promotion policy;
- provider expansion.

Existing search, filters, preview resolution and pagination behavior must be preserved.

## 4. Current problems to solve

The current UI is functional but visually reads like a generic application panel:

1. The large visible grid of native-like selects dominates the page.
2. Search, sort, content type and secondary filters have too-similar visual weight.
3. Cards read as bordered containers instead of media objects.
4. Metadata is visually flat and dense.
5. Thumbnails do not dominate enough.
6. The topbar and `SEARCH` label do not create meaningful product identity.
7. Desktop hierarchy is weak despite correct three-column layout.
8. Mobile is usable, but it still feels like a responsive admin/search UI rather than a premium media feed.

## 5. Information architecture

### Desktop

The page has four visual layers:

1. **Minimal top chrome**
   - no BlackServ branding;
   - optional small neutral `Search` label only if needed for orientation;
   - sticky behavior allowed, but visually quiet.

2. **Primary search zone**
   - search field is the dominant control;
   - wide input with high contrast and generous spacing;
   - search action integrated visually with the field rather than appearing as a separate administrative button.

3. **Primary filtering row**
   - sort control remains available;
   - Amateur / Production becomes a segmented control or similarly premium two-state selector;
   - secondary filters collapse behind a single `Filters` action;
   - active filters show a small count or compact summary.

4. **Media results**
   - three-column desktop grid remains the default at current supported widths;
   - cards are image-first and visually lighter than the current bordered boxes.

### Mobile

The mobile page is feed-first:

1. sticky compact search header;
2. one large result card per row;
3. full-width 16:9 media;
4. minimal metadata below media;
5. filters open in the existing bottom-sheet pattern;
6. Play remains one-tap;
7. no horizontal overflow;
8. no permanently visible wall of secondary filters.

## 6. Search and filter design

### Search

The search field is the strongest control on the page.

Requirements:
- comfortable desktop width;
- full-width mobile behavior;
- high-contrast focus state;
- clear placeholder;
- no decorative clutter;
- keyboard submit preserved;
- current state persistence preserved.

### Sort

Sort remains a compact single control.

It must not visually compete with search.

### Amateur / Production

Use a segmented control or pill-group treatment rather than a conventional select.

Semantic behavior remains exactly current production behavior:
- Amateur = explicitly classified amateur;
- Production = every active item not explicitly amateur;
- no Unknown option in the UI.

### Secondary filters

Provider, quality, duration and age-check move behind `Filters` on all compact layouts and may also be hidden behind the same action on desktop.

The Filters action should expose active state through:
- count badge, or
- compact text summary.

Do not show four equally weighted selects in the default desktop surface.

## 7. Card redesign

The card is a media object, not a boxed panel.

### Media

- 16:9 thumbnail remains dominant;
- subtle radius;
- no heavy outer card border;
- use restrained shadow / tonal separation / gradient instead of visible container framing;
- image should occupy most of the visual weight;
- thumbnail and preview video use the same frame.

### Overlay information

Keep only immediate media information on the image:
- duration;
- quality / HD / 4K when present;
- Play control when preview is available.

Play control:
- obvious but not oversized;
- visually centered or lower-right depending on final implementation test;
- one tap/click starts preview;
- active state clearly changes to stop/pause behavior;
- no autoplay by default on touch devices.

### Text hierarchy below image

1. Title — strongest text, max two lines.
2. Primary metadata — provider, views, rating where available.
3. Optional secondary metadata — studio / Amateur / age-check / alternate sources, only when meaningful.

Do not render empty metadata placeholders.

Avoid a single long undifferentiated metadata row.

### Desktop hover

When fine pointer + hover are available:
- subtle image scale or card lift;
- restrained transition;
- no dramatic motion;
- hover must not start video unless existing product behavior explicitly keeps that interaction.

Touch must remain click/tap driven.

## 8. Visual system

### Palette

Keep dark mode as the primary and only required theme for this redesign.

Direction:
- near-black page background;
- slightly elevated surfaces only where hierarchy requires them;
- white/off-white primary text;
- muted cool-gray secondary text;
- one restrained neutral accent for focus/active states;
- avoid bright brand colors unless later justified by product need.

### Typography

Use the existing system-font strategy unless there is a strong implementation reason to change it.

Hierarchy matters more than font novelty:
- larger, clearer titles;
- reduced metadata size;
- stronger weight contrast;
- consistent line-height;
- clamp long titles to two lines.

### Spacing

Use fewer separators and more spacing.

Premium feel should come from:
- predictable vertical rhythm;
- larger breathing room around search;
- tighter but deliberate metadata spacing;
- consistent media-card gaps.

## 9. Responsive behavior

Desktop:
- three-column results at normal wide desktop widths;
- two columns at intermediate width;
- one column on mobile.

Mobile:
- large full-width card;
- search remains easy to reach;
- filter sheet uses existing dialog semantics;
- controls meet touch target expectations;
- preview control remains at least 44×44 effective hit area.

No horizontal scrolling is allowed in normal content.

## 10. States

The redesign must preserve and visually improve:
- initial/ready state;
- loading skeletons;
- zero results;
- partial provider failure;
- global error;
- preview unavailable;
- preview playback error;
- pagination / Show more;
- active filter state.

Skeletons should visually match the new card geometry.

Error states should be compact and calm; they must not dominate the page unless search itself cannot function.

## 11. Accessibility

Preserve or improve current accessibility behavior:
- semantic form controls;
- keyboard operation;
- visible `:focus-visible` states;
- filter sheet focus trap and dialog semantics;
- accessible labels for Play / Stop preview;
- sufficient contrast;
- reduced-motion compatibility for non-essential transitions;
- no interaction that depends only on hover.

## 12. Performance

The redesign must not materially worsen frontend performance.

Requirements:
- no new frontend framework;
- no heavy icon library;
- no remote font dependency required for the first implementation;
- preserve lazy-loaded thumbnails;
- preserve preview `preload="none"` / on-demand resolution behavior;
- avoid layout shift from metadata;
- transitions limited to cheap CSS properties where practical.

## 13. Architecture and code boundaries

Keep the existing simple architecture.

### `index.html`
Owns:
- structural layout;
- semantic controls;
- card template structure;
- filter sheet structure.

### `styles.css`
Owns:
- visual system;
- responsive breakpoints;
- search/filter presentation;
- card hierarchy;
- motion and state styling.

### `app.js`
Owns only behavior and data binding.

Allowed changes:
- binding segmented Amateur/Production UI to the existing `content_class` parameter;
- active-filter count/summary;
- binding to a changed card DOM structure;
- preserving existing preview behavior in the new card.

Do not move visual decisions into JavaScript.

## 14. Data flow

No backend contract changes.

Existing flow remains:

1. User search/filter state -> `buildSearchParams()`.
2. Frontend calls current `/api/search`.
3. Result item -> card binding.
4. Thumbnail uses existing provider-aware resolution.
5. Preview button uses existing eligibility and `/api/preview` resolution.
6. Show more uses current pagination/prefetch behavior.

The redesign changes presentation, not data semantics.

## 15. Testing strategy

### Contract tests

Update/add frontend tests for:
- no BlackServ/BS branding in the public search shell;
- no dependency on the old `SEARCH` wordmark;
- Amateur/Production segmented control maps to the same API values;
- secondary filters remain available and accessible;
- filter active-count behavior;
- card title/media/metadata bindings;
- Play control remains one-click/tap;
- no regression in preview error handling;
- Show more remains functional;
- mobile filter sheet remains keyboard-accessible.

### Static verification

- full frontend contract test set;
- full project test suite;
- `node --check frontend/app.js`;
- `python -m compileall backend` as part of the normal release gate;
- `git diff --check`.

### Visual acceptance

A visual test environment must be used before production.

Required acceptance:
- desktop wide: three-column search results;
- desktop filter-open state;
- mobile one-column feed;
- mobile filter sheet;
- card with preview;
- card without preview;
- long title;
- missing metadata;
- loading skeleton;
- empty result state.

Owner approval of the real rendered test frontend is required before production rollout.

## 16. Rollout

1. Implement on a dedicated frontend redesign branch/worktree.
2. Publish only to an isolated test frontend environment.
3. Keep production SEARCH unchanged during visual review.
4. Run contract/full-suite gates.
5. Perform owner visual acceptance on mobile and desktop.
6. Only after acceptance, use the official deploy helper for production.
7. Bump frontend asset/service-worker cache version during the accepted production release.
8. Post-deploy verify source hashes, `/api/health`, desktop/mobile shell and preview interaction.

## 17. Non-goals

This redesign will not:
- invent a BlackServ consumer brand;
- redesign backend APIs;
- change provider coverage;
- alter preview rules;
- change search ranking;
- change content classification semantics;
- add accounts, favorites or recommendations;
- add autoplay feeds;
- introduce a JS framework.

## 18. Acceptance criteria

The redesign is accepted only when all of the following are true:

1. The default page no longer reads visually like an admin/filter panel.
2. Search is the dominant control.
3. Secondary filters no longer form a permanent wall of selects.
4. Amateur/Production uses a premium compact control while preserving semantics.
5. Desktop results are visually image-first and three-column at the target width.
6. Mobile results are one large card per row.
7. Cards no longer rely on a heavy full-card border for visual structure.
8. Titles and metadata have clear hierarchy.
9. Preview remains one tap/click and preserves current safety/resolver behavior.
10. No BlackServ/BS branding is introduced.
11. Loading, empty, partial-error and preview-error states remain functional.
12. Accessibility and keyboard behavior do not regress.
13. Full automated release gate passes.
14. Owner approves the rendered test frontend before production deployment.
