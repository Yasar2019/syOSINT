# Milestone 3 — RSS Collection and Public News Wire

**Status:** Approved

**Date:** 2026-09-23

**Branch:** `feat/rss-collection`

**Depends on:** Milestone 2 analyst desk in `feat/analyst-desk`

## Purpose

Milestone 3 adds standards-based RSS and Atom collection to syOSINT. It serves two related workflows:

1. a public, automatically refreshed news wire containing minimal headline metadata from a repository-controlled feed allowlist; and
2. a private local inbox where richer collected records can enter the existing human verification workflow.

The public dashboard remains available at `https://yasar2019.github.io/syOSINT/`. Its reviewed incident feed and the automatic news wire are visually and semantically separate.

## Success criteria

The milestone is complete when:

- GitHub Actions collects approved RSS and Atom feeds every 30 minutes and deploys a validated public news-wire dataset;
- the public dashboard displays new allowlisted headlines normally within 30–35 minutes of their appearance in a feed;
- the wire clearly labels all entries as unverified external reporting;
- a local scheduled collector stores feed items, collection cursors, source health and quarantine results in SQLite;
- analysts can promote a collected item into the existing triage workflow without automatic approval or publication;
- deterministic URL and content fingerprints prevent duplicate public and private entries;
- one failing or malicious feed cannot block other sources or replace the last valid public dataset;
- the collector runs on the latest stable Python 3.14 patch release supported by the dependency and test suite; and
- policy, dependency audit, unit, integration, build and browser checks pass.

## Scope and boundaries

### Included

- RSS 2.0 and Atom parsing;
- repository-controlled public source allowlist;
- automatic GitHub Actions collection every 30 minutes;
- local scheduled collection for analyst intake;
- public source, language and time metadata;
- canonical URLs, deterministic fingerprints and idempotent storage;
- per-source health, cursors, bounded retry behavior and quarantine;
- a bilingual public news-wire interface;
- a private RSS inbox and promotion into triage;
- bounded public retention and last-valid-dataset behavior.

### Excluded

- generic HTML scraping or JavaScript-rendered-page extraction;
- Telegram collection, which remains Milestone 4;
- automated summarization, translation, classification, credibility scoring or incident creation;
- copying article bodies into the public dataset;
- feeds requiring authentication, cookies, access-control bypassing or anti-bot circumvention;
- automatic confidence labels, incident merges or publication decisions;
- correction and withdrawal tooling, which remains Milestone 5.

## Publication policy change

The approved architecture originally prohibited all automatic publication. This milestone creates one narrow exception: GitHub Actions may automatically publish allowlisted RSS/Atom headline metadata consisting only of the source name, original headline, publication time and canonical source URL.

This exception does not apply to incidents, analyst summaries, evidence text, confidence labels, locations, media, descriptions or extracted article content. Those records continue to require explicit human review and publication. The interface must call automatic entries **Unverified external reporting** and must not present them as syOSINT findings.

## Architecture

### Shared collection core

The Python collector service owns a small RSS collection core used by both execution environments. It has clear modules for:

- feed configuration and allowlist validation;
- safe HTTP retrieval;
- RSS/Atom parsing and normalization;
- canonical link handling and deterministic fingerprints;
- public record projection;
- private persistence, cursors, health and quarantine;
- bounded scheduling and retry policy.

The shared core produces normalized feed items. Public and private projections consume those items independently so that private fields cannot enter the public schema accidentally.

### Public collector

A scheduled GitHub Actions workflow runs every 30 minutes and may also be dispatched manually. It:

1. checks out the repository;
2. installs the supported Python runtime and locked collector dependencies;
3. reads the repository feed allowlist;
4. safely fetches each enabled public feed;
5. parses and deduplicates valid items;
6. retrieves the currently deployed news-wire JSON from the project’s own GitHub Pages origin, validates it, and combines still-current entries with the new results;
7. writes and validates the public news-wire JSON;
8. builds and tests the public dashboard; and
9. deploys the generated static artifact to GitHub Pages.

The workflow does not need feed credentials or analyst-desk data. It deploys an artifact rather than committing generated news data back to the repository. If the currently deployed JSON is unavailable or invalid, the run uses fresh valid items only; it never trusts or republishes an invalid prior dataset.

### Private collector

The localhost collector runs an independent scheduler while the local service is active. It uses the shared collection core and records normalized evidence in SQLite. It preserves permitted original feed text locally for analyst review, but never exports that text automatically.

The scheduler uses per-source intervals with a 30-minute default. It avoids overlapping runs, resumes from persisted state after restart and pauses naturally when the analyst computer is offline.

### Public dashboard

The dashboard statically imports two validated datasets:

- the existing reviewed incident dataset; and
- the generated public news-wire dataset.

The **Live News Wire / شريط الأخبار المباشر** appears near the top of the dashboard and remains separate from reviewed incident intelligence.

## Source configuration

The repository contains a versioned allowlist with these fields:

- stable source identifier;
- English and Arabic display names when available;
- public HTTPS feed URL;
- source homepage URL;
- primary language;
- enabled status; and
- one or more deterministic Syria-topic terms when the feed covers a broader region; and
- optional attribution note.

Only reviewed entries committed to this allowlist can enter the public wire. The private analyst source registry may contain additional experimental feeds, but those sources do not become public automatically.

For a broad regional feed, an item enters the Syria wire only when its normalized headline contains at least one configured topic term, using Unicode-aware case-insensitive matching. The initial English terms are `Syria` and `Syrian`; the initial Arabic terms are `سوريا`, `سوري` and `سورية`. Topic filtering is transparent configuration, not an AI classifier, and the methodology documents that a headline-only rule can miss indirectly worded reports.

Feed URLs and redirects must remain public HTTPS resources. Credentials, URL fragments, nonstandard ports, IP literals, localhost names and private, link-local, loopback or otherwise non-public network destinations are rejected. DNS results are checked before connection and after redirects to reduce server-side request forgery and DNS-rebinding risk.

## Normalized feed item

The shared internal item contains:

- source identifier;
- source-native identifier when supplied;
- original plain-text headline;
- canonical article URL;
- source publication time when valid;
- collection time;
- normalized content fingerprint;
- raw-content digest;
- language inherited from source configuration;
- collection status; and
- safe error category when quarantined.

Original descriptions or content may be retained only in the private evidence store. HTML is sanitized before local display and is never included in the public projection.

## Deterministic identity and cursors

The collector resolves identity in this order:

1. source plus stable source-native ID;
2. normalized canonical URL;
3. normalized headline and publication-time fingerprint.

Normalization is deterministic and versioned. It handles case-normalized hosts, default HTTPS ports, fragments, tracking parameters from a conservative denylist, Unicode normalization and collapsed whitespace. Similarity alone never merges items.

Each private source stores its last successful collection time, last seen stable IDs, HTTP validators when provided (`ETag` and `Last-Modified`), consecutive failure count and last safe error category. A conditional request returning `304 Not Modified` is a successful healthy poll.

## Public dataset contract

The public news-wire schema includes:

- schema version;
- generated timestamp;
- last successful refresh timestamp;
- an array of entries containing stable ID, source ID, source label, language, headline, canonical URL, publication time and collection time; and
- non-sensitive aggregate source status sufficient to distinguish a current dataset from a delayed refresh.

It excludes descriptions, article bodies, raw XML, response headers, private notes, quarantine payloads, local paths, network details and analyst-desk identifiers.

Entries are newest first. The dataset retains at most seven days and 500 entries, whichever limit is reached first. Future-dated timestamps outside a small clock-skew allowance are quarantined instead of controlling sort order.

## Public interface

The news wire provides:

- newest-first cards or compact rows;
- original-language headlines;
- source and publication time;
- safe links to the original publisher;
- source and language filters;
- English and Arabic interface labels with RTL support;
- last successful refresh time; and
- a persistent **Unverified external reporting** explanation.

The interface does not apply syOSINT confidence badges to wire entries. A headline click opens the publisher in a new tab with safe link attributes. Empty, stale and temporarily delayed states explain the condition without implying that no news exists.

## Private analyst workflow

The analyst desk adds an RSS inbox with views for new, promoted, duplicate and quarantined items. An analyst can:

- inspect safe source metadata and locally stored evidence;
- open the original public report;
- promote one item into a new triage incident; and
- attach additional collected items to an existing editable incident.

Promotion copies provenance and a private evidence record, then opens the existing bilingual incident workflow. It does not generate a summary, confidence label, category or location. Repeated promotion is idempotent and audited.

## Fetch limits and failure behavior

Each source is isolated. Collection uses:

- a descriptive syOSINT user agent;
- strict connection and total timeouts;
- an explicit compressed and decompressed response-size limit;
- RSS/Atom content-type and parser checks;
- a maximum item count per response;
- bounded exponential backoff with jitter;
- no more than three attempts for transient failures; and
- `Retry-After` when a server supplies it.

Permanent configuration failures are not retried continuously. Logs contain source IDs and safe error categories, never feed bodies, credentials or sensitive query strings.

Malformed items enter private quarantine with a reason code and raw-content digest. Public collection simply excludes them. One source failure cannot fail parsing for other sources.

If a public run has no valid replacement because of collection, validation or build failure, deployment stops and GitHub Pages continues serving the previous successful artifact. Partial success may publish healthy-source updates while retaining still-valid prior entries from a failed source, with duplicate and retention rules reapplied.

## Python runtime and dependencies

Python 3.14 is the current stable feature series as of this design. Development, CI and Windows instructions target the latest available 3.14 patch rather than a stale micro-version. Python 3.15 prereleases are excluded.

The project declares `requires-python = ">=3.14,<3.15"`. Before implementation is accepted, all direct dependencies must support Python 3.14, the dependency audit must report no known vulnerabilities at the configured severity gate, and the complete API, collector and browser suite must pass. If a required dependency has no compatible secure release, the implementation records the incompatibility and stays on the newest secure supported feature series until migration is possible.

## Testing

Tests use local fixtures and controlled HTTP doubles; routine tests do not depend on live publishers.

Required coverage includes:

- representative RSS 2.0 and Atom fixtures;
- missing IDs, invalid dates, relative links, duplicate links and malformed XML;
- canonicalization and deterministic fingerprints;
- conditional requests and persisted cursors;
- private, loopback, link-local and unsafe redirect rejection;
- timeout, response-size, item-count, retry and quarantine behavior;
- independent source failures and partial success;
- retention, ordering and last-valid-dataset behavior;
- public allowlist and schema validation;
- Unicode-aware English and Arabic topic filtering for broad feeds;
- absence of descriptions, bodies and private fields from public JSON;
- analyst inbox states and idempotent promotion;
- bilingual public rendering, filtering, stale state and external-link safety;
- dependency audits, lint, types, builds and existing regression suites.

A browser test uses synthetic feeds to prove the full path from collection through public wire rendering. A separate local integration test proves collection, inbox review and promotion into triage.

## Operational documentation

The milestone documents:

- how to add, review, disable and remove a public feed;
- how the 30-minute GitHub schedule and manual dispatch work;
- attribution and feed-use review expectations;
- local scheduler configuration and source-health interpretation;
- quarantine reason categories;
- stale public-wire recovery;
- Python 3.14 installation on Windows, macOS and Linux; and
- the distinction between unverified wire metadata and reviewed syOSINT incidents.

## Milestone exit gate

Milestone 3 may be merged when the public workflow, private inbox and promotion path satisfy this specification; all required checks pass; the initial allowlist contains only reviewed public feeds; generated artifacts contain no restricted fields; and a reviewer confirms that the automatic wire remains visually distinct from reviewed intelligence.
