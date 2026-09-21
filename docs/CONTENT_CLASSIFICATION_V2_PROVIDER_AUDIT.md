# Content Classification v2 — Provider Evidence Audit

Date: 2026-09-21

Method: read-only sample of at most 3 current sitemap/page records per configured sitemap provider using the existing SearchEngineIndexer/0.5 fetch path. No SQLite/provider-state/config writes were made. Provider identity/domain/title/image were never treated as classification evidence.

| Provider | Samples | Explicit amateur tag | Explicit studio tag | Explicit productionCompany/studio label | Page enrichment safe | Enabled for v2 enrichment | Notes |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| bigassporn | 3 | no | no | no | yes | no | — |
| brazzilmoms | 3 | yes | no | no | yes | yes | — |
| fpo | 3 | yes | no | no | yes | yes | page_error:InvalidURL |
| freeporn | 3 | no | no | no | yes | no | — |
| hdzog | 3 | no | no | no | yes | no | — |
| justporn | 3 | no | no | no | yes | no | — |
| lexotic | 3 | no | no | no | yes | no | — |
| megatube | 3 | no | no | no | yes | no | — |
| mypornhere | 3 | no | no | no | yes | no | — |
| porndig | 3 | no | no | no | yes | no | — |
| porndoe | 3 | no | no | no | yes | no | — |
| porngo | 3 | no | no | no | yes | no | — |
| pornid | 3 | no | no | no | yes | no | — |
| pornsexvideo | 3 | no | no | no | yes | no | — |
| pussyspace | 3 | no | no | no | yes | no | — |
| serviporno | 3 | yes | no | no | yes | yes | — |
| sexplex | 3 | no | no | no | yes | no | — |
| sextubespot | 3 | yes | no | no | yes | yes | — |
| sexvid | 3 | no | no | no | yes | no | — |
| sunporno | 3 | no | no | no | yes | no | — |
| theyarehuge | 3 | no | no | no | yes | no | — |
| tubev | 3 | no | no | no | yes | no | — |
| txxx | 3 | no | no | no | yes | no | — |
| voyeurhit | 3 | no | no | no | yes | no | — |
| vxxx | 3 | no | no | no | yes | no | — |
| xcafe | 3 | yes | no | no | yes | yes | — |
| xgroovy | 3 | yes | no | yes | yes | yes | — |
| xnxx | 3 | yes | no | no | yes | yes | page_error:HTTPError |
| xvideos | 3 | yes | no | no | yes | yes | — |
| xxxbule | 3 | no | no | no | yes | no | — |
| zbporn | 3 | no | no | no | yes | no | — |

## Decision

Only providers with an observed explicit classification signal and a successful existing page-fetch path are enabled. A transient per-sample HTTP/URL failure does not erase positive evidence from another successful sample; individual enrichment failures remain failure-isolated by design.

No provider is enabled because of brand/domain identity. `xgroovy` additionally exposed a `productionCompany` field. The other enabled providers exposed an exact amateur signal in sampled explicit tags/keywords.
