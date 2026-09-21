# Preview Coverage v2 — Provider Audit

Date: 2026-09-21

Bounded read-only audit. No production DB rows or provider state were changed.

## Evidence model

- Canonical item pages: up to 3 current indexed URLs/provider; preview-looking related-card attributes were rejected unless they targeted the exact canonical URL.
- Canonical-page pass covered 55 providers and found 0 exact-item-bound preview candidates; 27 providers exposed only unrelated/recommended-card preview attributes.
- Live adapters: up to 3 current indexed items/provider were searched by current title; a preview was accepted only when the returned card URL normalized exactly to the indexed canonical URL.
- Playback evidence: authoritative 2026-09-19 bounded media audit (`docs/media/preview-audit-2026-09-19.md`) used `Range: bytes=0-1023` and verified direct `206 video/*` or the strict Thumbzilla proxy `206 video/mp4`.
- PornHat, PornDr, AnyPorn remain blocked by policy; redirects outside the original allowlist are not expanded.

## Runtime-capable providers

| Provider | Current exact matches with preview | Playback | Host policy |
|---|---:|---|---|
| bigfuck | 3 | direct / historical 206 | .bigfuck.tv |
| drtuber | 1 | direct / historical 206 | .drtst.com |
| hqporn | 3 | direct / historical 206 | .hqporn.xxx |
| spankbang | 2 | direct / historical 206 | .sb-cd.com |
| thumbzilla | 2 | proxy / historical 206 | .ypncdn.com |
| tnaflix | 3 | direct / historical 206 | .tnaflix.com |
| tube8 | 3 | direct / historical 206 | .t8cdn.com |
| xhamster | 3 | direct / historical 206 | .xhcdn.com |
| youjizz | 3 | direct / historical 206 | .youjizz.com |

## Full provider audit

| Provider | Source | Status | Samples | Reason |
|---|---|---|---:|---|
| anyporn | live | BLOCKED_BY_POLICY | 3 | 2026-09-19 bounded media audit: public preview redirects left the provider allowlist; current policy remains disabled |
| beeg | live | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| bigassporn | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| bigfuck | live | PLAYBACK_CONFIRMED | 3 | current exact live-search binding + 2026-09-19 bounded playback proof |
| brazzilmoms | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| bustybus | live | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| drtuber | live | PLAYBACK_CONFIRMED | 1 | current exact live-search binding + 2026-09-19 bounded playback proof |
| eporner | live | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| fpo | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| freeporn | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| hdzog | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| hqporn | live | PLAYBACK_CONFIRMED | 3 | current exact live-search binding + 2026-09-19 bounded playback proof |
| hqporner | live | NO_SIGNAL | 2 | no explicit canonical-bound preview field in sampled pages |
| justporn | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| lexotic | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| megatube | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| milfporn | live | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| mypornhere | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| porndig | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| porndoe | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| porndr | live | BLOCKED_BY_POLICY | 3 | 2026-09-19 bounded media audit: public preview redirects left the provider allowlist; current policy remains disabled |
| porngo | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| pornhat | live | BLOCKED_BY_POLICY | 3 | 2026-09-19 bounded media audit: public preview redirects left the provider allowlist; current policy remains disabled |
| pornhub | live | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| pornid | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| pornobae | live | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| pornone | live | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| pornsexvideo | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| pornzog | live | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| pussyspace | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| redtube | live | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| serviporno | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| sexplex | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| sextubespot | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| sexvid | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| spankbang | live | PLAYBACK_CONFIRMED | 2 | current exact live-search binding + 2026-09-19 bounded playback proof |
| sunporno | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| theyarehuge | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| thumbzilla | live | PLAYBACK_CONFIRMED | 2 | current exact live-search binding + 2026-09-19 bounded playback proof |
| tnaflix | live | PLAYBACK_CONFIRMED | 3 | current exact live-search binding + 2026-09-19 bounded playback proof |
| tube8 | live | PLAYBACK_CONFIRMED | 3 | current exact live-search binding + 2026-09-19 bounded playback proof |
| tubev | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| txxx | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| voyeurhit | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| vxxx | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| xcafe | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| xgroovy | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| xhamster | live | PLAYBACK_CONFIRMED | 3 | current exact live-search binding + 2026-09-19 bounded playback proof |
| xnxx | both | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| xvideos | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| xxxbule | sitemap | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| youjizz | live | PLAYBACK_CONFIRMED | 3 | current exact live-search binding + 2026-09-19 bounded playback proof |
| yourlust | live | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |
| zbporn | sitemap | AMBIGUOUS | 3 | preview-looking evidence exists only on unrelated/unbound cards |
| zzztube | live | NO_SIGNAL | 3 | no explicit canonical-bound preview field in sampled pages |

## Decision

Only `PLAYBACK_CONFIRMED` rows are projected into `deploy/search-engine-preview-rules.json`. The runtime projection therefore cannot enable a provider merely because a page contains a preview-looking URL.

The largest actionable gap is Tube8: the current live adapter matched 3/3 sampled indexed canonical URLs and returned preview URLs, while the 2026-09-19 bounded media audit already verified Tube8 direct preview as HTTP 206 `video/mp4` under `.t8cdn.com`.
