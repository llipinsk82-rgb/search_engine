---
version: alpha
name: Search
description: A fast video index with a calm editorial search surface.
colors:
  background: "#10131b"
  surface: "#1b202b"
  surface-raised: "#242b37"
  line: "#343d4a"
  text: "#f6f3ed"
  muted: "#a5adb8"
  primary: "#eb8278"
  secondary: "#91bfc3"
typography:
  display:
    fontFamily: "Arial Narrow, Segoe UI, sans-serif"
  body:
    fontFamily: "Segoe UI, system-ui, sans-serif"
  utility:
    fontFamily: "ui-monospace, Cascadia Code, monospace"
rounded:
  DEFAULT: "15px"
  card: "12px"
  control: "11px"
omitted:
  - section: spacing
    reason: "The single search screen uses responsive CSS dimensions rather than a shared spacing system."
components:
  search: {}
  filter: {}
  result-card: {}
---

# Search Design System

## Overview

A dark, cinematic index for people finding videos across sources. The search field is the main action; the coral second line of the headline is its visual signature. Result cards stay quiet so imagery and titles carry the content. The UI is English; this does not imply a target country.

The runtime token owner is `frontend/styles.css` `:root`; this file records its durable values. Changed color tokens must be mirrored in both places.

## Colors

The dark navy background and raised blue-gray surfaces distinguish the page from the content cards. Coral marks the search action and one headline line. Pale teal marks source information and keyboard focus. Muted text remains legible against all surfaces.

## Typography

The compressed display stack makes the headline distinctive. The body stack prioritizes readable search results. The utility monospace stack is used for short labels, source names and durations, never for long titles.

## Layout

The search form is limited to 970px for scanability; the result grid expands to 1360px. Four columns step down to three below 1050px and two below 720px. At narrow phone widths the search action becomes a full-width row. Card media has a reserved aspect ratio to prevent layout shifts.

## Elevation & Depth

Most hierarchy uses color and borders. Only the search field receives a large shadow. The sticky header uses translucent blur without covering content.

## Shapes

Controls use 10–15px radii; thumbnails use 12px. The brand mark alone uses a tilted square. Focus is visible with a teal outline.

## Components

Search and filters use native controls with keyboard operation. Loading and error messages occupy the persistent status region. Cards show a stable thumbnail frame and a clear fallback if a remote preview fails. Motion is limited to thumbnail hover and respects reduced-motion settings. Buttons retain text labels alongside decorative arrows.

## Do's and Don'ts

- Do keep the search field visually dominant and result cards compact.
- Do preserve readable focus, error and empty states.
- Don't let decorative animation delay searching or browsing.
- Don't infer result count from the number of indexed providers.
