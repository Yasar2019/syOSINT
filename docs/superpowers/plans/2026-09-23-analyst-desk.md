# Analyst Desk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a localhost analyst workflow with private evidence, human review, and explicit sanitized export.

**Architecture:** FastAPI/SQLAlchemy owns SQLite and gates. Next.js is a local, same-origin analyst UI. The public dashboard remains a static JSON consumer.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, pytest, Next.js, TypeScript, JSON Schema.

**Spec:** `docs/superpowers/specs/2026-09-23-analyst-desk-design.md`

## Global Constraints

- No RSS or Telegram in Milestone 2; no automatic publication; no paid services.
- Local service listens on `127.0.0.1`; no raw evidence or private notes reach public JSON.
- Follow the existing public schema; explicit human safety decision gates every export.

## Review Focus

- Private keys or evidence in arbitrary request fields: Pydantic rejects extras; export allowlists output.
- HTML/script in source text: UI renders text only, never HTML.
- Public URLs with credential fragments or localhost targets: reject at intake.
- Coordinates under withheld precision: fail export and suppress entirely.
- Concurrent or failed export: atomic write and no partially published file.

---

### Task 1: API persistence and audit

**Files:** Create `services/collector-api/{pyproject.toml,alembic.ini,alembic/env.py,alembic/versions/0001_initial.py,syosint/{db.py,models.py,api.py},tests/test_workflow.py}`.

**Interfaces:** `create_app(database_url, export_dir)` creates local API; source/incident/evidence actions are audited. Later tasks use the same DB session and incident models.

- [ ] Write failing pytest for source registration, incident creation, evidence attachment and append-only audit records; run `pytest services/collector-api/tests -q` and observe failure from absent API.
- [ ] Add pinned dependencies and migration, implement minimal CRUD with Pydantic `extra=forbid`, HTTPS public source URLs, local SQLite transactions and audit digest chain.
- [ ] Run test again and whole available Python suite; commit `feat: persist analyst incidents and audit actions`.

### Task 2: Verification, safety, preview and export

**Files:** Modify `services/collector-api/syosint/{api.py,models.py}`; create `services/collector-api/syosint/{workflow.py,export.py}`; extend `tests/test_workflow.py`; modify `packages/schemas/src/{public-incident.schema.json,types.ts,validate.test.ts}`.

**Interfaces:** `POST /incidents/{id}/review`, `/preview`, `/export`; preview/export both call `build_public_record` and validate the public contract.

- [ ] Add failing tests for forbidden transitions, missing review fields, sensitive positions, export allowlist, audit, preview parity and local output.
- [ ] Implement gates and explicit human action, schema validation, atomic local export, and the `synthetic: boolean` production schema allowance.
- [ ] Run Python and pnpm tests, commit `feat: gate and sanitize public incident exports`.

### Task 3: Local analyst desk

**Files:** Create `apps/analyst-desk` Next.js application and tests; modify `pnpm-workspace.yaml`, root `package.json`.

**Interfaces:** Local web UI uses the API through server-only calls and same-origin proxy; it can create/edit evidence, review, preview, and explicitly export.

- [ ] Add failing UI test for intake, source link, review controls, preview and export confirmation.
- [ ] Implement bilingual local screens, CSRF/same-origin checks on mutation proxy, and plain-text evidence rendering.
- [ ] Run UI tests, lint, type checks, and build; commit `feat: add localhost analyst desk`.

### Task 4: Documentation and final verification

**Files:** Modify `README.md`, `docs/{PROJECT_STATE.md,ROADMAP.md,AGENT_HANDOFF.md}`, workflow only if needed.

- [ ] Document installation, migration, localhost start, private data retention, preview/export and safety limitations.
- [ ] Run Python and pnpm suites, security check, inspect generated export and build; commit `docs: document milestone 2 workflow`.
- [ ] Review diff, open PR with safety impact and tests; keep `main` unchanged pending review.
