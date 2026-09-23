# Roadmap

This roadmap summarizes the approved product design. Detailed requirements live in `docs/superpowers/specs/2026-09-22-syosint-design.md`.

## Completed

### Milestone 0 — Foundation

- monorepo tooling and policies;
- shared public incident schema;
- synthetic fixtures;
- CI and GitHub Pages workflow.

### Milestone 1 — Visible public dashboard

- bilingual English/Arabic responsive interface;
- bundled Syria map;
- incident feed, filters, timeline, and detail view;
- methodology and confidence/uncertainty display;
- synthetic-only static data;
- accessibility baseline.

## Current

### Milestone 2 — Private analyst desk

Goal: provide a local-first review and publication workspace without introducing live collectors yet.

Scope:

- localhost-only analyst UI;
- local API and SQLite migrations;
- source registry and incident management;
- lifecycle transitions and verification checklist;
- evidence linkage and written rationale;
- safety review and location-precision controls;
- append-only audit trail;
- sanitized publication preview;
- validated public export.

Exit criteria:

- a synthetic incident can move through triage, investigation, review, approval, and export;
- unsafe/restricted fields are blocked from export;
- every material change is auditable;
- public export validates against the versioned schema;
- tests, lint, type checks, and security checks pass.

## Next

### Milestone 3 — RSS collection

RSS/Atom adapter, source health, cursors, deterministic fingerprints, quarantine, bounded retry behavior, and integration into the analyst workflow.

### Milestone 4 — Telegram collection

Terms-compliant official Telegram API integration for approved public channels only, read-only ingestion, edits/deletions/rate-limit handling, optional bounded media preservation, and explicit Telegram data-handling controls.

Telegram-derived content must never be processed by AI or machine-learning systems.

### Milestone 5 — Discovery and hardening

Candidate-source review, grouping suggestions, correction/withdrawal tooling, retention jobs, backup documentation, and threat-model review.

## Explicitly out of scope

- private or invite-only source access;
- autonomous publication;
- facial recognition or person tracking;
- offensive-security tooling;
- multi-user cloud collaboration in the MVP;
- paid APIs as a requirement;
- unrestricted scraping;
- live tactical tracking;
- automated credibility verdicts.
