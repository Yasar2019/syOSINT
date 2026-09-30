# Candidate Source Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a private candidate queue where an analyst records public-source suggestions and retains human acceptance/rejection history without activating a source.

**Architecture:** Two local SQL tables hold inert candidates and append-only reviews. A focused service owns URL normalization, duplicate checks, and review writes; the loopback FastAPI app provides strict endpoints; a private Next.js desk page uses the existing server-action pattern. No scheduled collector, public schema, or Pages workflow consumes candidates.

**Tech Stack:** Python 3.14, SQLAlchemy 2, Alembic, FastAPI/Pydantic, pytest; Node 24, Next.js/React, TypeScript, Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-29-candidate-source-review-design.md`

## Global Constraints

- Manual public-source suggestions only; no network fetch, feed parse, Telegram API call, or automatic source activation.
- `accepted` means eligible for later registration; it never modifies `sources`, the committed RSS allowlist, public data, or schedulers.
- No Telegram-derived content enters AI/ML; candidate fields and reviews remain private to the local API and desk.
- Strict bounded input, public HTTPS URLs without local hosts/IPs/credentials/fragments, and public username-form `https://t.me/<username>` links only for Telegram candidates.
- Preserve existing local database and review/audit history; reject duplicates and conflicting registered sources with 409.

## Review Focus

- URL variants (`https://EXAMPLE.org/` and `https://example.org`) must identify one candidate; Task 1 tests canonical identity and duplicate response.
- `t.me/+invite`, `t.me/<username>/<post>`, and an off-domain Telegram-shaped path must be rejected; Task 1 tests each.
- A race between simultaneous duplicate submissions must not create two rows; Task 1 tests database uniqueness and handles its conflict.
- A malformed filter or unbounded list request must not expose arbitrary private rows; Task 1 tests status and pagination limits.
- A rejected review followed by acceptance must preserve both events and never insert a registered source; Task 1 tests re-review and source isolation, Task 2 renders history.

---

### Task 1: Durable private candidate and review API

**Files:**
- Create: `services/collector-api/alembic/versions/0006_source_candidates.py`
- Modify: `services/collector-api/syosint/models.py`
- Create: `services/collector-api/syosint/candidate_review.py`
- Modify: `services/collector-api/syosint/api.py`
- Create: `services/collector-api/tests/test_candidate_review.py`
- Modify: `services/collector-api/tests/test_workflow.py` (existing migration-head assertion)

**Interfaces:**
- `normalize_candidate_url(platform: Literal["web", "telegram"], url: str) -> str` validates public URL policy, lowercases host/Telegram username, removes only a root trailing slash, and preserves a web URL's path/query.
- `create_candidate(db: Session, *, platform: str, url: str, name: str, language: str, suggestion_reason: str) -> dict` writes `SourceCandidate`, records audit, and raises a domain conflict with existing candidate/source ID.
- `review_candidate(db: Session, candidate_id: int, *, decision: str, reason: str, checks: dict[str, bool]) -> dict` appends `CandidateReview`, updates latest candidate status, and records audit in one transaction. The API passes validated fields; the service does not import API schemas.
- API: `POST /candidates` (201), `GET /candidates?status=pending|accepted|rejected&limit=1..100&offset>=0`, `GET /candidates/{id}`, `POST /candidates/{id}/reviews` (201). List returns newest first, bounded; detail includes chronological review history. `POST` conflict returns 409 with a safe existing ID and no external response body.
- Models: `SourceCandidate(id, platform, canonical_url, name, language, suggestion_reason, status, created_at, updated_at)` unique `(platform, canonical_url)`; `CandidateReview(id, candidate_id, decision, reason, checks, created_at)` with foreign key/index. Use `CandidateCreate` and `CandidateReviewCreate` strict Pydantic models in `api.py`; five check keys are `accessibility_checked`, `relevance_checked`, `identity_checked`, `provenance_checked`, `policy_checked`.

- [ ] **Step 1: Write failing API tests.** In `test_candidate_review.py`, assert create/list/detail; `0006` migration and restart persistence; canonical duplicate and registered-source conflict (409, no second row); unsafe URL classes and all three Telegram-link cases (422); unknown ID (404); acceptance requires all five checks and reason (422), rejection records unchecked criteria, subsequent acceptance preserves two timestamped events; list filter, limit 100 ceiling, offset; source count and public export stay unchanged. Add a second-session insertion to exercise the DB unique constraint. Update the `0005` migration assertion only after the new migration exists.
- [ ] **Step 2: Run `python -m pytest services/collector-api/tests/test_candidate_review.py -q`** with the project Python 3.14 environment; confirm expected missing endpoint/table failures.
- [ ] **Step 3: Implement `0006`, models, and `candidate_review.py`.** Use database uniqueness as the final duplicate guard, explicit safe 409 mapping, and transactionally insert review/update status/audit. Never call `safe_http` or Telethon. Match a registered source by normalized platform/URL without changing it.
- [ ] **Step 4: Add strict API schemas and routes in `api.py`.** Validate URL with the candidate service, reject extra fields, cap strings (`name` 250, `suggestion_reason` and review `reason` 1000) and list (`limit` 1–100). Acceptance requires five true checks. Return only explicit candidate/review response fields.
- [ ] **Step 5: Run focused and full API tests.** `python -m pytest services/collector-api/tests/test_candidate_review.py -q` then `python -m pytest services/collector-api/tests -q`; both must pass. Update the existing migration-head test to `0006` and commit `feat: add private candidate review API`.

### Task 2: Private analyst candidate queue

**Files:**
- Modify: `apps/analyst-desk/src/lib/api.ts`
- Modify: `apps/analyst-desk/src/app/actions.ts`
- Modify: `apps/analyst-desk/src/app/page.tsx`
- Create: `apps/analyst-desk/src/app/candidates/page.tsx`
- Create: `apps/analyst-desk/src/app/candidates/page.test.tsx`
- Modify: `apps/analyst-desk/src/app/style.css` (only if existing styles cannot express status/history)

**Interfaces:**
- `Candidate`, `CandidateReview`, and `CandidateStatus` TypeScript types mirror Task 1's API response; no public-dashboard type changes.
- Server actions `addCandidate(form: FormData)` and `reviewCandidate(form: FormData)` POST to Task 1 endpoints, redirect back to `/candidates` with bounded error text and preserve the existing no-store/revalidation pattern.
- `/candidates` is server-rendered, private, lists filtered candidates, and shows each candidate's full review history via detail retrieval. Candidate text is rendered as React text; links use safe validated URLs and `rel="noopener noreferrer"`.

- [ ] **Step 1: Write failing desk tests.** Use the existing desk page test pattern to assert empty/offline states, pending/accepted/rejected filtering, submission and review forms with five named checkboxes, rejection history after acceptance/re-review, no automatic-source wording, and escaped candidate name. Add action tests for safe API errors and a validated positive candidate ID.
- [ ] **Step 2: Run `corepack pnpm exec vitest run apps/analyst-desk/src/app/candidates/page.test.tsx`** and confirm missing route/action failures.
- [ ] **Step 3: Implement API types, actions, page, and nav.** Keep forms and decision history in this one private route; do not add public navigation or remote content embedding.
- [ ] **Step 4: Run `corepack pnpm test`, `corepack pnpm lint`, and `corepack pnpm typecheck`.** All must pass. Commit `feat: add private candidate review desk`.

### Task 3: Browser acceptance and project handoff

**Files:**
- Modify: `apps/analyst-desk/e2e/workflow.spec.ts`
- Modify: `apps/analyst-desk/e2e/api_harness.py` only if the current synthetic fixture cannot support candidate requests
- Modify: `docs/PROJECT_STATE.md`
- Modify: `docs/AGENT_HANDOFF.md` only if the milestone boundary needs correction

**Interfaces:**
- The real local API is exercised with synthetic web and public-channel URLs; no live network, Telegram credentials, post text, or publisher fetch.

- [ ] **Step 1: Write a browser test** for private desk submission, rejection with reason, revisit/preserved history, acceptance after five checks, and confirmation that `/sources` has no new source. Run it and observe the expected missing-flow failure.
- [ ] **Step 2: Finish only the fixture/UI behavior needed to pass; run desk Playwright tests** with the existing `corepack pnpm --filter @syosint/analyst-desk test:e2e` command after browser installation. Confirm all tests pass.
- [ ] **Step 3: Run repository gates:** `corepack pnpm policy:check`, `corepack pnpm lint`, `corepack pnpm typecheck`, `corepack pnpm test`, `corepack pnpm build`, `corepack pnpm build:desk`, and `python -m pytest services/collector-api/tests -q`. Review migration on a pre-`0006` fixture.
- [ ] **Step 4: Update project state** with what shipped and the next Milestone 5 task; explicitly mark real-account Telegram acceptance as still pending. Commit `docs: record candidate review release`, open/update the PR, and check CI and whole-branch review before merge.

## Self-review

The plan covers inert submission, URL/Telegram validation, durable review and re-review, private filtering/history UI, migration, audit, no activation/export, and the synthetic end-to-end path. The five Review Focus cases are each attached to a test step above. Task 1 owns the API contract used verbatim by Task 2; Task 3 exercises the integrated behavior. No live source or public schema changes are included.
