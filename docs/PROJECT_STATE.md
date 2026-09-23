# Project State

**Project:** syOSINT  
**Repository:** `Yasar2019/syOSINT`  
**Current branch:** `feat/analyst-desk`  
**Last completed milestone:** Milestone 1 — visible public dashboard  
**Current milestone:** Milestone 2 — private analyst desk  
**Source of truth updated:** 2026-09-23

## Current release state

PR #1, **feat: launch syOSINT public dashboard foundation**, is merged into `main`.

The public dashboard currently provides:

- bilingual English/Arabic UI with RTL support;
- synthetic-only demonstration incidents;
- filters, confidence labels, incident details, correction history, timeline, and Syria map;
- strict public-data validation;
- unit/browser checks, CI, and GitHub Pages deployment configuration.

The dashboard does not collect live sources and has no private analyst backend.

## Active work

Milestone 2 will add the private, localhost-only analyst workflow described in the approved product architecture:

- local analyst interface;
- local API and SQLite persistence;
- source and incident management;
- verification workflow;
- append-only audit history;
- publication safety review;
- sanitized export preview and public export.

No RSS or Telegram collection belongs in Milestone 2. Those are later milestones.

## Safety invariants

These constraints apply to all future work:

- Public sources only.
- No private/invite-only collection or access-control bypassing.
- No autonomous publication.
- No ordinary-person tracking, profiling, doxxing, or facial recognition.
- No precise live tactical locations.
- Raw evidence, credentials, sessions, private notes, local paths, and restricted metadata never enter the public export.
- Telegram-derived content must never be processed by AI or ML systems.
- Publication remains an explicit human action and fails closed.

## Canonical references

- Product architecture: `docs/superpowers/specs/2026-09-22-syosint-design.md`
- Milestone 1 plan: `docs/superpowers/plans/2026-09-22-foundation-public-dashboard.md`
- Roadmap: `docs/ROADMAP.md`
- Architectural decisions: `docs/DECISIONS.md`
- Agent handoff procedure: `docs/AGENT_HANDOFF.md`

## Continuity rule

Before starting work, an agent must read this file, the handoff document, the relevant design/plan, and the latest commits/PRs. Do not infer project state from chat memory alone.
