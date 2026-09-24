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

### Milestone 2 — Private analyst desk

- localhost-only analyst UI;
- local API and SQLite migrations;
- source registry and incident management;
- lifecycle transitions and verification checklist;
- evidence linkage and written rationale;
- safety review and location-precision controls;
- append-only audit trail;
- sanitized publication preview;
- validated public export.

## Current

### Milestone 3 — RSS collection

Goal: collect reviewed public RSS/Atom feeds into a clearly separated automatic headline wire and a private human-review inbox.

Implemented scope:

- repository-controlled feed allowlist and deterministic Syria-topic filters;
- safe, bounded RSS 2.0 and Atom fetching and parsing;
- fingerprints, duplicate handling, cursors, conditional requests, health and quarantine;
- local 30-minute scheduler and private analyst inbox;
- human promotion or attachment to editable incidents;
- bilingual public Live News Wire, separate from reviewed incidents;
- validated metadata-only Pages refresh every 30 minutes;
- Python 3.14 runtime and security checks.

## Next

### Milestone 4 — Telegram collection

Terms-compliant official Telegram API integration for approved public channels only, read-only ingestion, edits/deletions/rate-limit handling, optional bounded media preservation, and explicit Telegram data-handling controls.

Telegram-derived content must never be processed by AI or machine-learning systems.

### Milestone 5 — Discovery and hardening

Candidate-source review, grouping suggestions, correction/withdrawal tooling, retention jobs, backup documentation, and threat-model review.

## Explicitly out of scope

- private or invite-only source access;
- autonomous publication of incidents or analyst-authored material;
- facial recognition or person tracking;
- offensive-security tooling;
- multi-user cloud collaboration in the MVP;
- paid APIs as a requirement;
- unrestricted scraping;
- live tactical tracking;
- automated credibility verdicts.

The only automatic-publication exception is minimal original headline metadata from reviewed RSS/Atom feeds. Every wire entry is labeled unverified external reporting; it never becomes an incident without human action.
