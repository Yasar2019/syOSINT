# Public RSS source reviews

**Review date:** 2026-09-24  
**Decision owner:** repository owner (expanded pool explicitly approved)  
**Scope:** Milestone 4, pull request 1 — public RSS coverage only

The eight enabled feeds below were selected from a fixed candidate pool. Each feed is public HTTPS, has an identifiable official publisher, an official feed endpoint, a deterministic Syria topic policy, and an official legal or licence page linked in the public dashboard. Configuration loading rejects unsafe URLs and incomplete attribution. The shared CI live gate checks every enabled feed immediately before either Pages workflow collects; any failed check stops deployment and preserves the previous artifact.

The restricted execution environment used for this review could not resolve public DNS, so local `check-source` attempts failed closed at DNS resolution. No proxy or network bypass was used. Reachability is therefore a mandatory dynamic CI gate, not a claim recorded from an unavailable local network.

## Enabled sources

| ID | Publisher / feed | Language and topic policy | Ownership, reuse, and check record |
|---|---|---|---|
| `syria-untold-english` | [SyriaUntold English feed](https://syriauntold.com/en/feed/) · [homepage](https://syriauntold.com/en/) | English; `keyword-filtered`: Syria, Syrian, Damascus, Aleppo, Idlib | Official publisher domain. [About/licence page](https://syriauntold.com/about-syria-untold/) identifies the project and CC BY-NC-SA terms. Local live check: DNS unavailable; CI gate required. |
| `european-parliament-mashreq` | [European Parliament Mashreq feed](https://www.europarl.europa.eu/rss/delegation/dmas/en.xml) · [homepage](https://www.europarl.europa.eu/delegations/en/dmas/home) | English; `keyword-filtered` | Official Parliament domain and [legal notice](https://www.europarl.europa.eu/legal-notice/en). Local live check: DNS unavailable; CI gate required. |
| `syria-untold-arabic` | [SyriaUntold Arabic feed](https://syriauntold.com/ar/feed/) · [homepage](https://syriauntold.com/ar/) | Arabic; `keyword-filtered`: سوريا، سوري، سورية، دمشق، حلب، إدلب | Official publisher domain and the same [About/licence page](https://syriauntold.com/about-syria-untold/). Local live check: DNS unavailable; CI gate required. |
| `govuk-syria-news` | [GOV.UK Syria Atom feed](https://www.gov.uk/search/news-and-communications.atom?keywords=Syria) · [filtered homepage](https://www.gov.uk/search/news-and-communications?keywords=Syria) | English; `syria-only` because the publisher endpoint itself is filtered for Syria | Official government domain. Reuse is attributed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Local live check: DNS unavailable; CI gate required. |
| `european-parliament-foreign-affairs` | [Foreign Affairs Committee feed](https://www.europarl.europa.eu/rss/committee/afet/en.xml) · [homepage](https://www.europarl.europa.eu/committees/en/afet/home/highlights) | English; `keyword-filtered` | Official Parliament domain and [legal notice](https://www.europarl.europa.eu/legal-notice/en). Local live check: DNS unavailable; CI gate required. |
| `european-commission-press` | [European Commission Press Corner feed](https://ec.europa.eu/commission/presscorner/api/rss?language=en) · [homepage](https://ec.europa.eu/commission/presscorner/home/en) | English; `keyword-filtered` | Official Commission domain and [legal notice](https://commission.europa.eu/legal-notice_en). Local live check: DNS unavailable; CI gate required. |
| `european-parliament-external-relations` | [European Parliament external-relations feed](https://www.europarl.europa.eu/rss/topic/903/en.xml) · [news homepage](https://www.europarl.europa.eu/news/en) | English; `keyword-filtered` | Official Parliament domain and [legal notice](https://www.europarl.europa.eu/legal-notice/en). Local live check: DNS unavailable; CI gate required. |
| `eu-council-press-releases` | [Council press-release feed](https://www.consilium.europa.eu/en/rss/pressreleases.ashx) · [homepage](https://www.consilium.europa.eu/en/press/press-releases/) | English; `keyword-filtered` | Official Council domain and [copyright notice](https://www.consilium.europa.eu/en/about-site/copyright/). Local live check: DNS unavailable; CI gate required. |

All review evidence and URLs above were accessed or reconfirmed on 2026-09-24. Public display is limited to the original headline and navigation metadata; it does not reproduce article bodies or images.

## Rejected or deferred candidates

| Candidate | Decision |
|---|---|
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
