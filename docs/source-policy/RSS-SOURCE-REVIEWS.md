# Public RSS source reviews

**Review date:** 2026-09-25
**Decision owner:** repository owner (expanded pool explicitly approved)  
**Scope:** Milestone 4 — public RSS coverage and live-feed corrections

The six enabled feeds below have public HTTPS endpoints, identifiable publishers, deterministic Syria topic policies, and linked attribution records. Configuration loading rejects unsafe URLs and incomplete attribution. The CI live gate checks every enabled feed immediately before either Pages workflow collects; any failed check stops deployment and preserves the previous artifact.

On 2026-09-25, the Pages gate checked all eight prior feeds: five passed, but all three European Parliament endpoints failed with `unsupported-content-type`. No response body or URL was logged by the gate. They were removed from the enabled pool rather than allowing HTML through the XML-only client. Global Affairs Canada's [official RSS directory](https://international.canada.ca/en/global-affairs/news/rss) links to its English Atom feed on the government service domain; the endpoint serves `application/xml`, which the client accepts. Its [government terms](https://www.canada.ca/en/transparency/terms.html) are linked for attribution. The exact endpoint still requires the deployment's live validation. The pool is temporarily six, below the former eight-source breadth target; two additional sources require separate ownership, feed, and reuse review. Local DNS restrictions prevent a direct collector run here, and no proxy or network bypass was used.

## Enabled sources

| ID | Publisher / feed | Language and topic policy | Ownership, reuse, and check record |
|---|---|---|---|
| `syria-untold-english` | [SyriaUntold English feed](https://syriauntold.com/en/feed/) · [homepage](https://syriauntold.com/en/) | English; `keyword-filtered`: Syria, Syrian, Damascus, Aleppo, Idlib | Official publisher domain. [About/licence page](https://syriauntold.com/about-syria-untold/) identifies the project and CC BY-NC-SA terms. Local live check: DNS unavailable; CI gate required. |
| `syria-untold-arabic` | [SyriaUntold Arabic feed](https://syriauntold.com/ar/feed/) · [homepage](https://syriauntold.com/ar/) | Arabic; `keyword-filtered`: سوريا، سوري، سورية، دمشق، حلب، إدلب | Official publisher domain and the same [About/licence page](https://syriauntold.com/about-syria-untold/). Local live check: DNS unavailable; CI gate required. |
| `govuk-syria-news` | [GOV.UK Syria Atom feed](https://www.gov.uk/search/news-and-communications.atom?keywords=Syria) · [filtered homepage](https://www.gov.uk/search/news-and-communications?keywords=Syria) | English; `syria-only` because the publisher endpoint itself is filtered for Syria | Official government domain. Reuse is attributed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Local live check: DNS unavailable; CI gate required. |
| `global-affairs-canada` | [Global Affairs Canada Atom feed](https://international.canada.ca/en/global-affairs/news/rss) · [official feed directory](https://international.canada.ca/en/global-affairs/news/rss) | English; `keyword-filtered` | Government of Canada links the feed from its official directory and publishes [terms and conditions](https://www.canada.ca/en/transparency/terms.html). Live CI gate required. |
| `european-commission-press` | [European Commission Press Corner feed](https://ec.europa.eu/commission/presscorner/api/rss?language=en) · [homepage](https://ec.europa.eu/commission/presscorner/home/en) | English; `keyword-filtered` | Official Commission domain and [legal notice](https://commission.europa.eu/legal-notice_en). Local live check: DNS unavailable; CI gate required. |
| `eu-council-press-releases` | [Council press-release feed](https://www.consilium.europa.eu/en/rss/pressreleases.ashx) · [homepage](https://www.consilium.europa.eu/en/press/press-releases/) | English; `keyword-filtered` | Official Council domain and [copyright notice](https://www.consilium.europa.eu/en/about-site/copyright/). Local live check: DNS unavailable; CI gate required. |

Previously reviewed sources were accessed or reconfirmed on 2026-09-24; the three Parliament gate failures and Canadian directory/terms were checked on 2026-09-25. Public display is limited to the original headline and navigation metadata; it does not reproduce article bodies or images.

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
| Enab Baladi Arabic / English | Rejected: candidate endpoints and automatic-publication reuse permission remained ambiguous. |
| Middle East Eye | Rejected: candidate feed ownership/redirect and reuse evidence remained ambiguous. |

Rejection does not assess editorial quality or credibility. It only means the source did not satisfy this repository's narrow automatic-publication and evidence requirements on the review date.
