# Milestone 2 — Local Analyst Desk

**Status:** Approved milestone scope, implementation in progress. This document narrows the approved [product architecture](2026-09-22-syosint-design.md) to the first local workflow.

## Purpose and boundaries

A single journalist or OSINT researcher can manually register public sources and evidence, assemble a bilingual incident, document verification and safety decisions, inspect the exact public record, and explicitly export it. There is no live ingestion, Telegram, RSS, AI assessment, or automatic publication in this milestone.

## Architecture

- `services/collector-api`: FastAPI bound to `127.0.0.1`, SQLAlchemy SQLite, Alembic migrations, Pydantic request contracts, and repository-level transactions. CORS is disabled. The local desk uses a server-side proxy so the browser never directly calls the API.
- `apps/analyst-desk`: local Next.js interface using server-side API calls and same-origin state-changing requests. It must not be deployed through the public GitHub Pages workflow.
- `packages/schemas`: existing JSON Schema remains the public contract. A private Python exporter produces only allowlisted fields and checks the public schema before staging an export. Production datasets need `synthetic: false`, while the checked-in fixtures retain `synthetic: true`.
- `data/public`: checked-in synthetic demonstration data. Real export is local and gitignored until an analyst separately chooses to publish it. The public dashboard reads only a validated selected public JSON file.

## Workflow

Lifecycle: `triage → investigating → review-ready → approved → published`; corrections and withdrawals preserve revisions. A source must be a public HTTPS reference. Evidence carries a source URL, original text stored locally, source time, and hash; no original text is in the public record. Every change records action, entity, before/after digest, timestamp, and reason if required.

An incident must have two human-written titles and summaries, categories, source references, uncertainty text, rationale, an explicit checklist covering independence, time, location, contradictions and person/safety risk, and public precision at most governorate/district as applicable. Precise or operationally sensitive coordinates and routes are suppressed. Approval requires checklist completion and a recorded reviewer acknowledgment. Preview builds the exact sanitized record and validates it. Export is a separate explicit action, reevaluates gates, and writes to a gitignored local path atomically. A withdrawn incident is not exportable as a fresh claim.

## Failure behavior and tests

Invalid transitions, missing rationale/translation, unsafe URLs, incomplete checklist, dangerous precision, and unexpected fields fail closed. Tests cover migrations and persistence, audit append behavior, authorization of transitions and export, missing/inconsistent source references, preview/export parity, and absence of private fields. A browser test covers a synthetic intake through preview. The private system stays usable on an M1 Mac without Docker or paid services.
