# RSS/Atom Source and Operations Policy

This policy governs both the automatic public headline wire and local private RSS intake. The public wire accepts only enabled sources in `config/rss-sources.json`; adding or changing an entry requires repository review.

## Allowlist review

Before enabling a public feed, a reviewer must confirm:

- the feed and every expected redirect use public HTTPS without credentials, cookies, private access, or nonstandard ports;
- the publisher owns or clearly operates the feed and provides a stable homepage;
- displaying the original headline with attribution and a link is compatible with the publisher's stated feed terms;
- `id`, bilingual source labels, language, homepage, and topic terms are accurate;
- the feed parses as RSS 2.0 or Atom within the collector's byte and item limits; and
- broad feeds have deterministic Syria terms that are narrow enough for the public wire.

The initial reviewed entries are UN News — Middle East and BBC Arabic. Their configured terms are `Syria`/`Syrian` and `سوريا`/`سوري`/`سورية`. syOSINT republishes no article body, description, image, or publisher branding. Each entry preserves the publisher label and canonical link; ownership remains with the publisher.

To disable a problematic source without losing review history, set `enabled` to `false` and commit the reason. Remove an entry only when its identifier will not be reused. Never silently substitute an unreviewed feed after an endpoint failure.

## Public schedule and projection

`.github/workflows/rss-wire.yml` runs every 30 minutes and through manual dispatch. It installs Python 3.14, collects enabled feeds, validates `data/public/news-wire.v1.json`, builds the static dashboard, and deploys through GitHub Pages. Entries normally appear within 30–35 minutes, but GitHub queueing and publisher delays can make that longer.

The public dataset is limited to seven days and 500 newest-first entries. It contains only stable ID, source ID and label, language, original headline, canonical URL, publication time, and collection time, plus aggregate healthy/delayed source counts. Every entry is presented as **Unverified external reporting** rather than a syOSINT finding.

If a source is delayed, the collector may retain its still-current entries from the last valid deployed dataset. If collection, validation, or the build fails, deployment stops and Pages continues serving the previous successful artifact. The initial deployment tolerates a missing prior wire.

## Deterministic topic filtering

The collector normalizes Unicode, folds case, and tests the original headline against the source's configured terms. It performs no semantic classification, translation, summarization, or credibility scoring. This transparent headline-only rule can miss indirectly worded Syria reporting and can include an ambiguous match; the public disclosure and human incident workflow account for that limitation.

## Local private collection

Start the local API with `.venv314/bin/python -m syosint`, open the analyst desk at `http://127.0.0.1:3001/rss`, and register an RSS/Atom source. Enabled sources poll at their configured interval, from 15 to 1,440 minutes, with a 30-minute default. The scheduler persists cursors, `ETag`, `Last-Modified`, next poll time, failure count, safe error category, normalized items, and quarantines in the private SQLite database.

The source-health states are:

- `pending`: no completed attempt yet;
- `healthy`: fetched and parsed successfully;
- `not-modified`: the publisher returned HTTP 304; this is a successful poll;
- `delayed`: fetching or parsing failed safely.

Transient timeout, network, DNS, HTTP 408/425/429, and server failures receive at most three attempts with bounded delay and `Retry-After` support. Permanent failures are recorded without continuous retry. Error displays and logs use categories such as `dns-failure`, `timeout`, `network-error`, `http-status`, `unsupported-content-type`, or parser exception type; they do not include response bodies, credentials, or sensitive query strings.

Malformed matching items are quarantined rather than published. Item reasons include `missing-headline`, `missing-url`, and `future-published-at`; the private store keeps a digest and safe review fields. A quarantine record does not block other items or sources.

An analyst may promote a new item into triage or attach it to an editable incident. Those actions are idempotent and audited. They do not create public text, confidence, category, location, approval, or publication.

## Validation and recovery

Use the latest stable Python 3.14 patch release:

```bash
python3.14 -m venv .venv314
.venv314/bin/python -m pip install -e './services/collector-api[test]' pip-audit
.venv314/bin/python -m syosint.rss_cli check-source FEED_URL
.venv314/bin/python -m pytest services/collector-api/tests -q
```

On Windows, use `py -3.14 -m venv .venv314` and `.venv314\Scripts\python.exe`. Live feed checks require public DNS and HTTPS; automated tests use fixtures.

For a stale wire:

1. inspect the most recent `Refresh RSS News Wire` run and its safe per-source categories;
2. manually dispatch the workflow after a transient publisher or GitHub outage;
3. disable and review a feed if a permanent endpoint, terms, ownership, or format change occurred;
4. do not hand-edit generated public entries or bypass schema/build validation; and
5. keep the previous Pages artifact online until a complete valid replacement deploys.
