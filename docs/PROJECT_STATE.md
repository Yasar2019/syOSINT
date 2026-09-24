# Project State

**Project:** syOSINT  
**Repository:** `Yasar2019/syOSINT`  
**Current branch:** `feat/rss-collection`
**Last completed milestone:** Milestone 2 — private analyst desk
**Current milestone:** Milestone 3 — RSS collection, implemented pending review
**Source of truth updated:** 2026-09-23

## Current release state

PR #1, **feat: launch syOSINT public dashboard foundation**, is merged into `main`.

PR #2, **feat: add the private analyst desk**, contains the completed Milestone 2 implementation and is the base of this branch.

The public dashboard provides:

- bilingual English/Arabic UI with RTL support;
- synthetic demonstration incidents in the reviewed incident section;
- a separate bilingual Live News Wire for unverified external headlines;
- filters, confidence labels, incident details, correction history, timeline, and Syria map;
- strict public-data validation;
- unit/browser checks, CI, and GitHub Pages deployment configuration;
- a scheduled 30-minute RSS refresh that deploys only after validation and a successful static build.

The static client does not fetch publishers directly. GitHub Actions creates the bounded public wire from the committed allowlist, while the local-only analyst backend collects independently into private SQLite storage.

## Active work

Milestone 3 is implemented on `feat/rss-collection` pending review. It adds:

- safe RSS 2.0 and Atom fetching, parsing, canonicalization, and deterministic fingerprints;
- allowlisted English and Arabic Syria-topic feeds;
- per-source health, cursors, conditional requests, bounded retries, and quarantine;
- local scheduling and a private RSS review inbox;
- idempotent promotion and attachment to the existing human-review workflow;
- a versioned, seven-day/500-entry public news-wire contract;
- a bilingual public Live News Wire with source/language filters and stale states;
- `.github/workflows/rss-wire.yml`, scheduled every 30 minutes with manual dispatch.

Telegram collection remains Milestone 4 and is not implemented.

### Review checkpoint on `feat/rss-collection`

Collector, API, analyst-desk, schema, and public-dashboard tests cover the implementation with synthetic fixtures. Local unit, type, policy, and build checks pass. Live publisher verification must run in GitHub Actions or another environment with public DNS; the managed development environment blocks direct DNS to publisher domains. Browser execution also depends on a usable local Chromium binary and is enforced in CI.

The automatic public path is deliberately narrow: only source name, original headline, publication/collection times, language, stable identifier, and canonical publisher link may appear. It never exports article bodies, descriptions, analyst notes, evidence, locations, incident claims, or confidence labels. Reviewed incidents still require explicit human safety and publication actions. Correction and withdrawal tooling remains Milestone 5 scope.

Active plan: `docs/superpowers/plans/2026-09-23-rss-collection.md`; approved design: `docs/superpowers/specs/2026-09-23-rss-collection-design.md`.

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
- RSS operations and source policy: `docs/source-policy/RSS.md`
- Public methodology: `docs/methodology/METHODOLOGY.md`
- Roadmap: `docs/ROADMAP.md`
- Architectural decisions: `docs/DECISIONS.md`
- Agent handoff procedure: `docs/AGENT_HANDOFF.md`

## Continuity rule

Before starting work, an agent must read this file, the handoff document, the relevant design/plan, and the latest commits/PRs. Do not infer project state from chat memory alone.
