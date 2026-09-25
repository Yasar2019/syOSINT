# Project State

**Project:** syOSINT  
**Repository:** `Yasar2019/syOSINT`  
**Current branch:** `feat/shared-intake-telegram`
**Last completed milestone:** Milestone 3 — RSS collection and public news wire
**Current milestone:** Milestone 4 — public RSS coverage deployed; Telegram intake in progress
**Source of truth updated:** 2026-09-25

## Current release state

PRs #1 through #13 are merged into `main`. Milestones 1–3 and Milestone 4's public RSS coverage are deployed; the latest merged commit is `9f6621f`.

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

Collector, API, analyst-desk, schema, and public-dashboard tests cover the implementation with synthetic fixtures. The scheduled workflow is deployed through GitHub Pages. The current allowlist has nine reviewed English and Arabic feeds, including North Press and Enab Baladi English. The dated official evidence and rejected candidates are in `docs/source-policy/RSS-SOURCE-REVIEWS.md`.

The public wire retains seven days of headlines, capped at 100 per source and 500 globally. Both Pages workflows run a shared fail-closed live gate before collection. Safe logs contain one bounded status line per source and the GitHub summary contains aggregate configured/healthy/delayed/item counts only. A gate, collection, schema, test, or build failure leaves the previous Pages artifact in place. Recovery is to inspect the safe category, rerun after a transient outage, or disable and re-review a permanently changed source; the gate must not be bypassed.

The automatic public path is deliberately narrow: only source identity/status, reviewed legal attribution, original headline, publication/collection/refresh times, language, stable identifier, retained count, and canonical publisher link may appear. It never exports article bodies, descriptions, failure detail, analyst notes, evidence, locations, incident claims, or confidence labels. Reviewed incidents still require explicit human safety and publication actions. General incident correction and withdrawal tooling remains Milestone 5 scope; Milestone 4 includes only the minimum revision handling required for human-approved public Telegram leads.

## Active work

Milestone 4 combines deployed public RSS source expansion with local public-Telegram intake and an individually human-approved public Telegram wire. The written design and plans are approved. On `feat/shared-intake-telegram`, Tasks 1–4 are committed: session settings, an identity-preserving shared-intake migration, RSS-compatible private intake, and terminal-only Telegram authentication. Local collector tests pass on Python 3.12; Python 3.14 CI, live collection, and analyst UI remain pending. Task 5 is next: manual public-channel approval and bounded read-only collection. Tasks 6–8 cover optional media, analyst views, and verification. Public Telegram publication is a separate subsequent plan and is not deployed.

Active design: `docs/superpowers/specs/2026-09-24-source-expansion-telegram-design.md`.

Active plans:

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
- Public methodology: `docs/methodology/METHODOLOGY.md`
- Roadmap: `docs/ROADMAP.md`
- Architectural decisions: `docs/DECISIONS.md`
- Agent handoff procedure: `docs/AGENT_HANDOFF.md`

## Continuity rule

Before starting work, an agent must read this file, the handoff document, the relevant design/plan, and the latest commits/PRs. Do not infer project state from chat memory alone.
