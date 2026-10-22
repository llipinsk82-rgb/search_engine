---
version: alpha
name: "Search Engine"
description: "A quiet, media-first cross-source video index with editorial search guidance."
colors:
  background: "#08090b"
  surface: "#101216"
  raised: "#15181d"
  control: "#171a20"
  text: "#f5f7fa"
  secondaryText: "#b7bec8"
  mutedText: "#7f8792"
  focus: "#dfe5ec"
typography:
  interface:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
  technical:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace"
rounded:
  control: "14px"
  media: "16px"
  sheet: "22px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
components:
  search: {}
  mediaCard: {}
  filterSheet: {}
---

# Search Engine design system

## Overview

The product is a single-screen video discovery tool. Its job is to make a large, cross-source catalog feel searchable without making the interface compete with the media. The visual reference is a quiet screening-room index: dark surfaces, precise type, fine boundaries, and imagery as the main color. The empty state is an editorial index card that teaches search, then disappears when results arrive. Avoid casino-neon accents, fake platform branding, dense badges, and decorative motion.

The UI is English; result titles preserve source languages. It is a product surface, not a promotional landing page. Browser-native select popups are intentionally accepted because their keyboard and platform behavior is more important than custom popup geometry here.

`frontend/styles.css` is the canonical runtime token owner. This file mirrors its accepted values and explains their roles; it does not generate CSS. The mapping is direct: frontmatter colors map to the `:root` variables `--bg-page`, `--surface-soft`, `--surface-raised`, `--surface-control`, `--text-primary`, `--text-secondary`, `--text-muted`, and `--focus-ring`; rounded and spacing values map to `--radius-*` and `--space-*` in the same file. Compare these when changing either side.

## Colors

Background and surfaces are near-black neutrals. Text hierarchy is white, cool gray, then muted gray. Fine translucent white lines separate controls and metadata. The visible media supplies expressive color; UI actions do not use an invented brand accent. Focus uses a solid pale ring. Errors and empty states use copy and structure, never color alone. The only supported authored theme is dark; forced-colors leaves system colors operable.

## Typography

Interface text uses the existing Inter-first system stack. Numeric and query-syntax examples use the technical stack. Results favor short, scan-friendly lines; titles may contain non-Latin scripts and must retain a system fallback rather than force a condensed Latin font. The welcome headline is larger and tighter than utility copy, but only in the ready state.

## Layout

The search controls stay first. Results use the existing responsive media grid: four columns from 1240px, fewer columns on smaller screens, one on narrow phones. Cards preserve a media aspect ratio so image loading cannot push the list around. The ready-state index card has a main search invitation and a secondary syntax tip; it stacks on small viewports. Body scrolling remains the single vertical scroll owner. The manual Show more control remains available even when automatic near-end loading is enabled.

## Elevation & Depth

Hierarchy comes from tonal surfaces, thin borders, and media gradients. Blur belongs only to small overlays and sticky controls. Avoid heavy shadows on static cards. The welcome card uses one quiet directional line texture to suggest an index, not a decorative background image.

## Shapes

Controls use 14px radii, media 16px, and sheets 22px. Search suggestions are pill-shaped to read as optional actions, not filters already applied. Media corners and badges remain consistent across provider results.

## Components

Search has idle, loading, cached-results, live-refresh, empty, and error states. It shows cached results before live refresh completes and never discards already-fetched rows during pagination. The search status is a polite live region; Show more remains a real button. Suggestion actions fill and submit a query, then leave the ready state.

Media cards reserve image geometry and fall back to a labeled placeholder if an upstream image cannot load. Preview motion is user-controlled or hover-enhanced and must not be the only access path. Provider, duration, quality, and alternate-source labels stay small and legible.

The filter sheet keeps its existing focus and Escape behavior. Native selects remain the shared choice for sort, source, quality, duration, and age-check controls. Loading changes labels without shifting control dimensions. Keyboard focus stays visible. Scrollbars use one global tokenized baseline; reduced-motion users do not receive decorative hover movement.

## Do's and Don'ts

- Do lead with search and let media carry color after results load.
- Do keep query syntax guidance visible only while it is useful.
- Do preserve cached results and browsing position during live refresh and pagination.
- Don't add fluorescent accents, autoplaying grids, or fake completeness claims.
- Don't let an unavailable upstream thumbnail collapse a card or block its link.
