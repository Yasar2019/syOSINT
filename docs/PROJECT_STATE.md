# Project State

**Project:** syOSINT  
**Repository:** `Yasar2019/syOSINT`  
**Current branch:** `main` (PR #18 merged as `d61a80d`)
**Last completed milestone:** Milestone 5 — private candidate-source review (first slice)
**Current milestone:** Milestone 5 — design the next independent slice: grouping suggestions
**Source of truth updated:** 2026-09-30

## Current release state

PR #18 is merged into `main` after green CI, including the analyst desk browser workflow. Milestones 1–3 and Milestone 4's public RSS coverage, local Telegram intake, and item-specific Telegram publication workflow are merged. PR #15 passed Python 3.14 CI, browser tests, and the live RSS gate before merging as `9199406`. On 2026-09-29 UTC, the public Pages URL returned HTTP 200 with a `Last-Modified` time of 2026-09-28 14:48 UTC, after PR #15 merged at 14:33 UTC; its HTML contains both “Approved Telegram” and “Live News Wire.” This verifies that the new public dashboard build is served, but does not test a real Telegram account or a real approved post. The tracked Telegram dataset remains empty until a real report is individually approved and staged.

The public dashboard provides:

- bilingual English/Arabic UI with RTL support;
- synthetic demonstration incidents in the reviewed incident section;
- a separate bilingual Live News Wire for unverified external headlines;
- filters, confidence labels, incident details, correction history, timeline, and Syria map;
- strict public-data validation;
- unit/browser checks, CI, and GitHub Pages deployment configuration;
- a scheduled 30-minute RSS refresh that deploys only after validation and a successful static build.

The static client does not fetch publishers directly. GitHub Actions creates the bounded public wire from the committed allowlist, while the local-only analyst backend collects independently into private SQLite storage. Public wire contract `1.1.0` exposes the complete configured source set with healthy, not-modified, or delayed state, last successful refresh, retained count, and visible reviewed attribution; failure details remain private.

## Completed Milestone 3

Milestone 3 adds:

- safe RSS 2.0 and Atom fetching, parsing, canonicalization, and deterministic fingerprints;
- allowlisted English and Arabic Syria-topic feeds;
- per-source health, cursors, conditional requests, bounded retries, and quarantine;
- local scheduling and a private RSS review inbox;
- idempotent promotion and attachment to the existing human-review workflow;
- a versioned, seven-day/500-entry public news-wire contract;
- a bilingual public Live News Wire with source/language filters and stale states;
- `.github/workflows/rss-wire.yml`, scheduled every 30 minutes with manual dispatch.

Collector, API, analyst-desk, schema, and public-dashboard tests cover the implementation with synthetic fixtures. The scheduled workflow is deployed through GitHub Pages. The current allowlist has eleven reviewed English and Arabic feeds, including North Press, Enab Baladi English, and Hawar News Agency English and Arabic. The dated official evidence and deferred candidates are in `docs/source-policy/RSS-SOURCE-REVIEWS.md`.

The public wire retains seven days of headlines, capped at 100 per source and 500 globally. Both Pages workflows run a shared fail-closed live gate before collection. Safe logs contain one bounded status line per source and the GitHub summary contains aggregate configured/healthy/delayed/item counts only. A gate, collection, schema, test, or build failure leaves the previous Pages artifact in place. Recovery is to inspect the safe category, rerun after a transient outage, or disable and re-review a permanently changed source; the gate must not be bypassed.

The automatic public path is deliberately narrow: only source identity/status, reviewed legal attribution, original headline, publication/collection/refresh times, language, stable identifier, retained count, and canonical publisher link may appear. It never exports article bodies, descriptions, failure detail, analyst notes, evidence, locations, incident claims, or confidence labels. Reviewed incidents still require explicit human safety and publication actions. General incident correction and withdrawal tooling remains Milestone 5 scope; Milestone 4 includes only the minimum revision handling required for human-approved public Telegram leads.

## Completed Milestone 4

Milestone 4 combines public RSS source expansion with local public-Telegram intake and an individually human-approved public Telegram wire. The local intake and analyst views merged through PR #14. PR #15 merged the versioned and validated public Telegram contract, append-only private editorial review, item-specific preview and approval, a private pending export, manual staging, bilingual public presentation, and dual-contract Pages validation. The post-merge public build was verified as served on 2026-09-29 UTC. A channel approval still only enables private collection. Each public Telegram record requires explicit item approval, manual staging, a reviewed and merged public data change, and Pages deployment. The public Telegram dataset contains zero entries until an analyst publishes a real approved report. Real-account collection and publication remain an operator acceptance check, not a completed live test.

## Completed Milestone 5 candidate-source review

PR #18 merged private candidate-source submission, strict public URL validation, duplicate/conflict handling, append-only review history, five-check acceptance, and a private desk queue with status filters and pagination. Candidates remain inert: acceptance creates no registered source, collection authorization, allowlist entry, export, or public dashboard change. Synthetic API and desk tests cover this boundary; the integrated browser workflow covers web and public-channel suggestions, rejection, revisit, and acceptance with preserved history.

This work is released on `main` as `d61a80d`. PR CI passed policy, API and desk tests, builds, public RSS verification, and the analyst desk browser workflow after independent review. Real-account Telegram collection and publication acceptance remain pending and separate from this synthetic workflow.

## Next work

Design the next independent Milestone 5 slice: grouping suggestions. General incident correction/withdrawal, retention jobs, backup documentation, and threat-model review remain later roadmap items. Never place credentials or raw posts in the repository.

Candidate review design: `docs/superpowers/specs/2026-09-29-candidate-source-review-design.md`.
Candidate review plan: `docs/superpowers/plans/2026-09-30-candidate-source-review.md`.

Milestone 4 design: `docs/superpowers/specs/2026-09-24-source-expansion-telegram-design.md`.

Milestone 4 plans:

- `docs/superpowers/plans/2026-09-24-public-rss-coverage.md`
- `docs/superpowers/plans/2026-09-24-shared-intake-telegram.md`
- `docs/superpowers/plans/2026-09-24-public-telegram-wire.md`

## Safety invariants

These constraints apply to all future work:

- Public sources only.
- No private/invite-only collection or access-control bypassing.
- No autonomous publication of incidents or analyst-authored material. The sole exception is minimal, unverified metadata from committed RSS/Atom allowlist entries.
- No ordinary-person tracking, profiling, doxxing, or facial recognition.
- No precise live tactical locations.
- Raw evidence, credentials, sessions, private notes, local paths, and restricted metadata never enter the public export.
- Telegram-derived content must never be processed by AI or ML systems.
- Publication remains an explicit human action and fails closed.

## Canonical references

- Product architecture: `docs/superpowers/specs/2026-09-22-syosint-design.md`
- Milestone 1 plan: `docs/superpowers/plans/2026-09-22-foundation-public-dashboard.md`
- Milestone 2 design: `docs/superpowers/specs/2026-09-23-analyst-desk-design.md`
- Milestone 3 design: `docs/superpowers/specs/2026-09-23-rss-collection-design.md`
- Milestone 4 design: `docs/superpowers/specs/2026-09-24-source-expansion-telegram-design.md`
- RSS operations and source policy: `docs/source-policy/RSS.md`
- Local Telegram operations: `docs/source-policy/TELEGRAM.md`
- Public methodology: `docs/methodology/METHODOLOGY.md`
- Roadmap: `docs/ROADMAP.md`
- Architectural decisions: `docs/DECISIONS.md`
- Agent handoff procedure: `docs/AGENT_HANDOFF.md`

## Continuity rule

Before starting work, an agent must read this file, the handoff document, the relevant design/plan, and the latest commits/PRs. Do not infer project state from chat memory alone.
