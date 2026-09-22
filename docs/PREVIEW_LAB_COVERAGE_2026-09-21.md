# Preview Lab coverage — 2026-09-21

Scope: read-only preview audit. No production preview rules are changed by this document.

## PASS_CURRENT
Verified with real current `preview_url` and bounded Range GET returning 200/206 + `video/*`.

- bigfuck
- drtuber
- hqporn
- spankbang
- thumbzilla
- tnaflix
- tube8
- xhamster
- youjizz
- pornhub (2/2, video/webm)
- beeg (2/2, video/mp4)
- pornhat (2/2, video/mp4)
- porndr (2/2, video/mp4)
- anyporn (2/2, video/mp4)

## PASS_LAB
Not production-enabled by this audit. Two item-bound samples each were verified with Range GET returning 200/206 + `video/*`.

- xvideos — thumbnail directory + `preview.mp4`
- xnxx — thumbnail directory + `preview.mp4`
- xgroovy — `/videos/<bucket>/<id>/<id>_pr640.mp4` with source Referer
- mypornhere — `/contents/videos/<bucket>/<id>/<id>_preview.mp4`
- pussyspace — thumbnail CDN directory + `preview.mp4`
- porndig — `/previewclips/<year>/<month>/<internal_id>/<internal_id>_1.mp4`
- sexvid — `pr1.sexvid.xxx/.../<id>_short_preview.mp4`
- pornid — `pr1.pornid.xxx/.../<id>_short_preview_480x270.mp4`
- zbporn — `pr1.zbporn.com/.../<id>_short_preview.mp4`

## NOT_VERIFIED
No safe item-bound motion preview was proven in the bounded two-sample audit. Full-video URLs are not accepted as preview.

- xcafe
- sunporno
- serviporno
- fpo
- sextubespot
- freeporn
- xxxbule
- porngo (item-bound candidate timed out 2/2)
- txxx
- sexplex
- voyeurhit
- vxxx (candidate paths returned HTML, not video)
- hdzog
- theyarehuge
- justporn (candidate paths returned HTML, not video)
- bigassporn
- megatube (only template `${video.previewUrl}` found; no item-bound URL proven)
- tubev
- brazzilmoms (current tokenized MP4 is player `video_url`, i.e. full video)
- porndoe
- eporner
- pornone
- hqporner
- milfporn
- yourlust
- zzztube
- bustybus
- redtube

## NOT_TESTABLE
Provider search results were not individual playable items in the sampled API response.

- pornsexvideo — homepage / recently-added entries
- lexotic — homepage / models entries

## NOT_PROBED
Execution safety layer blocked the bounded probe in this session; no conclusion drawn.

- pornobae
- pornzog

## Rule
A provider is promoted to PASS only when the preview is item-bound and a bounded request returns `video/*`. Recommendation-card previews, HTML 200s, full-player video sources, inferred URLs without media proof, and timeouts are not PASS.

## Promotion checkpoint — 2026-09-21

Promoted to production build `de29714afbc5` after full release gate (373 PASS) and production smoke (8/8 item-bound previews returned HTTP 206 + `video/mp4`):

- xvideos
- xnxx
- mypornhere
- pussyspace — only items whose thumbnail is on `*.xvideos-cdn.com`; unsupported thumbnail CDNs remain without preview
- porndig
- sexvid
- pornid
- zbporn

Not promoted:

- xgroovy — direct browser requests require an upstream Referer; lab marks it `Proxy required`

`test.blackserv.eu` is the dedicated Preview Lab. Its current dropdown is intentionally limited to the nine active lab providers: xvideos, xnxx, xgroovy, mypornhere, pussyspace, porndig, sexvid, pornid, zbporn.

## Preview v3 closeout — 2026-09-22

This section supersedes the older open audit queue above. The audit is now complete for all 55 providers. No provider is left in NOT_PROBED.

### Production truth state

Production build de29714afbc5 already contains the eight promoted custom preview rules:

- xvideos
- xnxx
- mypornhere
- pussyspace — only thumbnails on *.xvideos-cdn.com; unsupported thumbnail CDNs remain No preview
- porndig
- sexvid
- pornid
- zbporn

Fresh production smoke on 2026-09-22: 8/8 PASS through /api/search + /api/preview, each returning HTTP 200 with a non-empty preview URL. Production service is active and /api/health reports build de29714afbc5.

### Browser / mobile acceptance

- test.blackserv.eu is the dedicated Preview Lab origin.
- Android owner test confirmed Play starts with one tap after the fine-pointer hover guard.
- xgroovy is not promoted: direct browser-style request without Referer returns 403; the same item-bound preview with source Referer returns 206 video/mp4. Lab status: Proxy required.

### Expanded remaining-provider audit

xcafe is the only additional provider with meaningful partial evidence: item-bound preview.anysex.com/<bucket>/<id>/<id>_pr640.mp4 returned 9/12 PASS (206 video/mp4) and 3/12 404. It is not promoted because support is not deterministic for every item.

No safe deterministic item-bound preview was proven for the rest of the queue:

- sunporno, fpo, sextubespot, txxx, sexplex, voyeurhit, hdzog, theyarehuge, bigassporn: sampled predictable motion paths returned 404.
- vxxx, justporn: sampled predictable motion paths returned HTTP 200 but text/html, not video.
- freeporn: sampled item pages / motion paths were blocked with 403; adding page or host Referer did not change the result.
- porngo: bounded item-bound probes timed out / returned transport code 000; no PASS claimed.
- megatube, serviporno, xxxbule, tubev, porndoe, eporner, pornone, hqporner, yourlust, zzztube, bustybus, redtube, pornobae, pornzog, pornsexvideo: sampled rows exposed no proven item-bound motion preview.
- brazzilmoms: page data-preview values were recommendation-card media; current-item predictable preview paths returned 404, so no promotion.
- milfporn: most sampled detail-page probes timed out; no item-bound preview was proven.
- lexotic: sampled search results were tag pages rather than playable items, so item-level preview remains NOT_TESTABLE.

### Closeout decision

Preview Coverage v3 is CLOSED. Do not re-run the full provider audit. Future preview work is incremental only:

1. xgroovy proxy support may be evaluated separately using the existing strict preview-proxy architecture.
2. xcafe may be revisited only if a deterministic item-level existence/capability signal is found; do not emit guessed URLs that create false browser errors.
3. All other providers stay without preview until new explicit item-bound evidence appears.
