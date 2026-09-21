# Content Classification v2.1 — Provider Studio Evidence Audit

Date: 2026-09-21

Method: read-only production SQLite sampling of active rows with `content_class='unknown'` and `content_class_source='none'`, followed by canonical-page fetches through the existing configured sitemap-provider fetch path. First pass used one current sample per provider; only candidate/ambiguous providers were expanded to three samples. No production DB, provider state, service, config, or cursor was modified.

Accepted evidence is explicit and item-bound only. Title text, provider identity, uploader/channel identity, categories/navigation, recommendation cards and site-wide marketing copy are rejected.

| Provider | Samples | Status | Finding |
| --- | ---: | --- | --- |
| xvideos | 3 | AMBIGUOUS | `sponsors` and uploader data are not accepted as studio evidence |
| xnxx | 1 | FETCH_UNAVAILABLE | sampled canonical URL returned HTTP 404 |
| sunporno | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| xgroovy | 3 | STUDIO_RULE_CONFIRMED | 2/3 samples exposed JSON-LD `VideoObject.productionCompany` |
| txxx | 1 | NO_STUDIO_SIGNAL | unrelated site/ad studio text only |
| porndig | 1 | NO_STUDIO_SIGNAL | navigation/CSS studio text only |
| justporn | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| fpo | 1 | NO_STUDIO_SIGNAL | current sample fetched; no explicit item-bound field |
| bigassporn | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| brazzilmoms | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| sextubespot | 1 | NO_STUDIO_SIGNAL | site-wide marketing copy only |
| xcafe | 3 | STUDIO_RULE_CONFIRMED | 2/3 samples exposed scoped microdata `productionCompany` → `name` |
| mypornhere | 1 | NO_STUDIO_SIGNAL | navigation only |
| pussyspace | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| tubev | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| xxxbule | 3 | AMBIGUOUS | genre/keywords mix studio-like and performer names |
| theyarehuge | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| sexvid | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| pornid | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| zbporn | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| megatube | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| freeporn | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| pornsexvideo | 1 | AMBIGUOUS | site-level/related-card text, not canonical item metadata |
| lexotic | 1 | NO_STUDIO_SIGNAL | site-level sample; no item-bound signal |
| porndoe | 3 | STUDIO_RULE_CONFIRMED | 3/3 samples exposed JSON-LD `VideoObject.producer` Organization |
| voyeurhit | 1 | NO_STUDIO_SIGNAL | site-wide marketing copy only |
| porngo | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| hdzog | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| sexplex | 3 | AMBIGUOUS | serialized payload contains a studio index but no proven stable value path |
| vxxx | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |
| serviporno | 1 | NO_STUDIO_SIGNAL | no explicit item-bound field |

## Runtime decision

Only `xgroovy`, `xcafe`, and `porndoe` receive v2.1 runtime rules. `xgroovy` duplicates evidence the generic JSON-LD parser already understands and therefore serves as a compatibility/control rule. `xcafe` and `porndoe` add explicit studio/producer evidence not currently captured by the generic parser. Ambiguous providers remain Unknown until an item-bound contract can be proven.
