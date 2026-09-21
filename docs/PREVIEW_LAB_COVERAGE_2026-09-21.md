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
