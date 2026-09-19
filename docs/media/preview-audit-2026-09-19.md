# Preview audit — 2026-09-19

Bounded read-only audit for query `step`. Each provider contributed one current `preview_url`; the probe used `Range: bytes=0-1023`, no redirect following, and no private/protected endpoint bypass.

| Provider | Sample host | Result | Type | Signed/query | Decision |
|---|---|---:|---|---|---|
| beeg | `vp.externulls.com` | 206 | video/mp4 | no | direct |
| youjizz | `cdne-mobile.youjizz.com` | 206 | video/mp4 | yes | direct |
| drtuber | `g7.drtst.com` | 206 | video/mp4 | no | direct |
| pornhat | `www.pornhat.one` | 302 | text/html | no | disabled; redirect leaves initial allowlist |
| porndr | `www.porndr.com` | 302 | text/html | no | disabled; redirect leaves initial allowlist |
| bigfuck | `icdn05.bigfuck.tv` | 206 | video/mp4 | no | direct |
| hqporn | `icdn05.hqporn.xxx` | 206 | video/mp4 | no | direct |
| anyporn | `anyporn.com` | 302 | text/html | no | disabled; redirect leaves initial allowlist |
| tnaflix | `fck-cl37.tnaflix.com` | 206 | video/mp4 | yes | direct |
| spankbang | `tbv.sb-cd.com` | 206 | video/mp4 | no | direct |
| thumbzilla | `ev-ph.ypncdn.com` | 410 plain / 206 with fixed public Referer | video/mp4 with Referer | yes | strict proxy |
| xhamster | `thumb-v5.xhcdn.com` | 206 | video/mp4 | no | direct |
| pornhub | `kw.phncdn.com` | 206 | video/webm | yes | direct |
| tube8 | `ev-ph.t8cdn.com` | 206 | video/mp4 | yes | direct |

## Thumbzilla follow-up

The same freshly generated signed URL returned HTTP 410 without a Referer and HTTP 206 `video/mp4` with `Referer: https://www.thumbzilla.com/`. The provider therefore requires a strict allowlisted preview proxy rather than a dead direct PLAY button.

## Policy result

- Direct preview remains enabled only for the 10 samples returning `206 video/*` directly.
- PornHat, PornDr and AnyPorn preview capability is disabled for this release; no redirect host expansion is guessed.
- Thumbzilla uses `preview_mode=proxy` with `.ypncdn.com` and the fixed public Referer.
