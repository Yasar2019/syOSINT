# Public RSS source reviews

**Review date:** 2026-09-25
**Decision owner:** repository owner (expanded pool explicitly approved)  
**Scope:** Milestone 4 — public RSS coverage and live-feed corrections

The nine enabled feeds below have public HTTPS endpoints, identifiable publishers, deterministic Syria topic policies, and linked attribution records. Configuration loading rejects unsafe URLs and incomplete attribution. The candidate-feed workflow checks every enabled source and requires a fresh Syria headline from a newly added source before merging. The CI live gate still checks every enabled feed immediately before either Pages workflow collects; any failed check stops deployment and preserves the previous artifact.

On 2026-09-25, the Pages gate checked all eight prior feeds: five passed, but all three European Parliament endpoints failed with `unsupported-content-type`. They were removed rather than allowing HTML through the XML-only client. Global Affairs Canada's official [RSS directory](https://international.canada.ca/en/global-affairs/news/rss) links to its Atom feed; its live deployment check passed. The six-source collection produced no matching headline published within the seven-day window, despite returning older matching items. This expansion adds Syrian publishers that report daily and requires a live premerge result. Local direct DNS checks remain unavailable; the GitHub Actions runner performs the final source checks.

## Enabled sources

| ID | Publisher / feed | Language and topic policy | Ownership, reuse, and check record |
|---|---|---|---|
| `syria-untold-english` | [SyriaUntold English feed](https://syriauntold.com/en/feed/) · [homepage](https://syriauntold.com/en/) | English; `keyword-filtered`: Syria, Syrian, Damascus, Aleppo, Idlib | Official publisher domain. [About/licence page](https://syriauntold.com/about-syria-untold/) identifies the project and CC BY-NC-SA terms. Local live check: DNS unavailable; CI gate required. |
| `syria-untold-arabic` | [SyriaUntold Arabic feed](https://syriauntold.com/ar/feed/) · [homepage](https://syriauntold.com/ar/) | Arabic; `keyword-filtered`: سوريا، سوري، سورية، دمشق، حلب، إدلب | Official publisher domain and the same [About/licence page](https://syriauntold.com/about-syria-untold/). Local live check: DNS unavailable; CI gate required. |
| `sana-english` | [SANA English RSS](https://sana.sy/en/feed/) · [homepage](https://sana.sy/en/) | English; `keyword-filtered` | Official Syrian Arab News Agency feed; retain original headline and direct article URL, with publisher attribution. The publisher [identifies itself](https://sana.sy/en/) on its site; no article body or media is copied. Premerge and deployment checks required. |
| `north-press-english` | [North Press English RSS](https://npasyria.com/en/feed/) · [homepage](https://npasyria.com/en/) | English; `keyword-filtered` | [Publisher about page](https://npasyria.com/%D8%AD%D9%88%D9%84-%D8%A7%D9%84%D9%88%D9%83%D8%A7%D9%84%D8%A9/) identifies North Press; public RSS on its own domain. Original headlines link to articles; no body or media is copied. Premerge and deployment checks required. |
| `north-press-arabic` | [North Press Arabic RSS](https://npasyria.com/feed/) · [homepage](https://npasyria.com/) | Arabic; `keyword-filtered` | Same publisher and attribution; original headlines link to articles. Premerge and deployment checks required. |
| `govuk-syria-news` | [GOV.UK Syria Atom feed](https://www.gov.uk/search/news-and-communications.atom?keywords=Syria) · [filtered homepage](https://www.gov.uk/search/news-and-communications?keywords=Syria) | English; `syria-only` because the publisher endpoint itself is filtered for Syria | Official government domain. Reuse is attributed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Local live check: DNS unavailable; CI gate required. |
| `global-affairs-canada` | [Global Affairs Canada Atom feed](https://international.canada.ca/en/global-affairs/news/rss) · [official feed directory](https://international.canada.ca/en/global-affairs/news/rss) | English; `keyword-filtered` | Government of Canada links the feed from its official directory and publishes [terms and conditions](https://www.canada.ca/en/transparency/terms.html). Live CI gate required. |
| `european-commission-press` | [European Commission Press Corner feed](https://ec.europa.eu/commission/presscorner/api/rss?language=en) · [homepage](https://ec.europa.eu/commission/presscorner/home/en) | English; `keyword-filtered` | Official Commission domain and [legal notice](https://commission.europa.eu/legal-notice_en). Local live check: DNS unavailable; CI gate required. |
| `eu-council-press-releases` | [Council press-release feed](https://www.consilium.europa.eu/en/rss/pressreleases.ashx) · [homepage](https://www.consilium.europa.eu/en/press/press-releases/) | English; `keyword-filtered` | Official Council domain and [copyright notice](https://www.consilium.europa.eu/en/about-site/copyright/). Local live check: DNS unavailable; CI gate required. |

Previously reviewed sources were accessed or reconfirmed on 2026-09-24; new publisher endpoints and attribution pages were reviewed on 2026-09-25. Public display is limited to the original headline and navigation metadata; it does not reproduce article bodies or images. The feed is unverified external reporting, not a confirmed incident.

## Rejected or deferred candidates

| Candidate | Decision |
|---|---|
| European Parliament — Mashreq, Foreign Affairs, External Relations | Removed after all three failed the live CI gate with `unsupported-content-type` on 2026-09-25; do not widen accepted content types to admit their responses. |
| UN News — Middle East | Removed from the enabled pool because the general regional feed was persistently delayed during deployment and its reuse/attribution record was not complete enough for this expansion. |
| BBC Arabic | Removed because the broad feed yielded sparse Syria matches and no approved feed-specific reuse record was established for automatic public projection. |
| Al Jazeera English / Arabic | Rejected: candidate feed ownership/redirect and reuse evidence were not sufficiently unambiguous for this allowlist. |
| France 24 English / Arabic | Deferred: no stable, reviewed candidate endpoint and complete feed-use evidence were established. |
| DW Arabic | Deferred: no stable, reviewed Syria-relevant feed endpoint and complete reuse evidence were established. |
| ReliefWeb — Syrian Arab Republic | Deferred pending confirmation of the exact official feed endpoint and reuse terms for this projection. |
| Syria Direct | Deferred pending an unambiguous official feed and reuse record. |
| SANA Arabic | Official RSS endpoint returned `parse-failed` in the GitHub Actions live candidate check on 2026-09-25. Defer until the publisher feed or parser is corrected and reviewed. |
| Enab Baladi Arabic / English | Arabic RSS returned HTTP 403 from GitHub Actions on 2026-09-25; English endpoint and publisher attribution remain unreviewed. Defer until an accessible feed is confirmed. |
| Syrian Observatory for Human Rights | Candidate feed endpoint returned 403 to the review client; no accessible RSS endpoint confirmed. |
| Syria TV | [Terms](https://www.syria.tv/%D8%A7%D8%AA%D9%81%D8%A7%D9%82%D9%8A%D8%A9-%D8%A7%D8%B3%D8%AA%D8%AE%D8%AF%D8%A7%D9%85-%D8%A7%D9%84%D9%85%D9%88%D9%82%D8%B9) permit attributed news links, but a stable public RSS endpoint was not confirmed. |
| Shaam Network | `/feed/` returned HTML rather than a verified RSS/Atom document; defer until a feed endpoint is confirmed. |
| Middle East Eye | Rejected: candidate feed ownership/redirect and reuse evidence remained ambiguous. |

Rejection does not assess editorial quality or credibility. It only means the source did not satisfy this repository's narrow automatic-publication and evidence requirements on the review date.
