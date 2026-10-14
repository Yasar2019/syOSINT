# Incident revisions implementation plan

> For agentic workers: use superpowers:subagent-driven-development task-by-task.

**Goal:** Correct and withdraw exported incidents with exact human review and immutable history.
**Architecture:** Local versioned sanitized publication snapshots, isolated correction drafts, hashed previews, explicit approval/export; static public correction and withdrawal presentation.
**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy/SQLite/Alembic; existing Next.js/TypeScript, Vitest and Playwright.
**Spec:** `docs/superpowers/specs/2026-10-14-incident-revisions-design.md`

## Global constraints

- Localhost-only private services; static public Pages consumes only validated JSON.
- No Telegram-derived material in AI/ML; synthetic tests only.
- Full existing publication gate applies to corrected records; explicit acknowledgment and exact preview digest for every revision approval.
- Stable original incident IDs, immutable version snapshots; withdrawn is terminal in this slice.
- No raw text, private fields, paths, credentials, or exact coordinates in public snapshots.
- Python 3.14, existing dependencies only; preserve schema 1.0.0 and automatic RSS path.

## Review focus

- Legacy exported incidents without snapshots require explicit initialization export, with no inferred deployment status.
- Stale draft or preview version/hash, edits after review, and parallel approvals fail closed without duplicate revisions.
- Withdrawal tombstones suppress old claim text, links and location; active visuals/counts exclude withdrawn records.
- Private-only field edits cannot masquerade as public corrections; exported history excludes private facets.
- Disk failure leaves a recoverable approved database state and removes stale incident pending output; retries use latest snapshot.

### Task 1: Versioned private publication API

**Files:** models.py, new migration0007, export.py, api.py, new incident_publication.py, test_incident_publication.py, migration coverage.
**Consumes:** Existing IncidentEdit, ReviewInput, build_public_record, write_export, digest and audit protections.
**Produces:** All exact API paths/response contracts defined in spec; legacy preview/export compatibility.
- [ ] Write failing synthetic tests for complete initial-export/correction/review/preview/approve/export/withdrawal flow and five review-focus inputs.
- [ ] Observe expected absent models/routes failure.
- [ ] Implement three version/draft models plus withdrawal preview model and migration; pure snapshot helpers and serialized route integration as specified.
- [ ] Run focused and full API tests, migration upgrade test, commit and report red/green evidence.

### Task 2: Private analyst and public revision presentation

**Files:** incident/[id]/publication/page.tsx (new), desk actions.ts and tests, incident/[id]/page.tsx, public DashboardClient/IncidentCard/IncidentDetail/SummaryCards/SyriaMap/Timeline and relevant tests/i18n only as needed.
**Consumes:** Task1 paths; GET publication returns version/record/history/draft; correction review/preview/approve and withdrawal preview/approve exact contracts.
**Produces:** Complete private correction/withdrawal controls and safe public tombstone/correction displays.
- [ ] Write failing desk page/action tests for complete editor, review reset, preview hashes/version, explicit acknowledgment, withdrawn disabled controls and safe errors; public tests for claim suppression and active map/timeline/count exclusion.
- [ ] Observe missing controls/unsafe existing withdrawn behavior.
- [ ] Implement accessible server actions and private editor/review/preview/approve page; public localized statuses/reasons/changed fields; exclude withdrawn from active visuals while preserving feed.
- [ ] Run focused and full JS suites, lint/typecheck and both builds, commit and report.

### Task 3: Integrated acceptance and operations

**Files:** analyst desk e2e/workflow.spec.ts, synthetic public browser tests as needed, docs/source-policy/INCIDENT-PUBLICATION.md (new), PROJECT_STATE.md, AGENT_HANDOFF.md, ROADMAP.md.
**Consumes:** Task1/2 UI and routes.
**Produces:** End-to-end synthetic regression and accurate operations/handoff.
- [ ] Add synthetic browser flow from initial export through corrected approval/export and withdrawal/export; assert stable ID/history, no silent publication, public tombstone behavior.
- [ ] Run browser workflows, full API/JS suites, policy, lint/typecheck, both builds; use CI browser acceptance if local Chromium unavailable.
- [ ] Document manual safe merge-by-ID staging and validation preserving other incidents, local-only export labels, single-process locking, export failure recovery, migration and backup requirement.
- [ ] Update release state/ledger and commit; independent whole-branch review, fix findings, open PR, verify all CI before merge/release.

## Authorization

Owner approved the design direction and explicitly instructed implementation on 2026-10-13 America/Toronto. Spec and plan capture that direction; proceed under the retained subagent-driven method without further approval loops for reversible implementation.
