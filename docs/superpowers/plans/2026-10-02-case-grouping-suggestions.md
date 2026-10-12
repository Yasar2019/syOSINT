# Case Grouping Suggestions Implementation Plan

**Goal:** Show deterministic, private possible-related-case suggestions using analyst-entered category, UTC event time, and governorate. Suggestions never merge or publish cases.

**Spec:** `docs/superpowers/specs/2026-10-02-case-grouping-suggestions-design.md`

**Architecture:** Extend the existing JSON incident edit with an optional controlled private governorate. A pure matcher compares eligible case facets; a read-only local API route retrieves candidates, and the private case page presents links and caveats. No migration, scheduler, public schema, or Telegram content processing.

## Review focus

- Existing incidents without the new facet remain editable and publishable; the API returns an empty suggestion list.
- Timezone offsets represent instants; the six-hour edge is inclusive, and naive historical values fail closed.
- Same governorate but different category must not imply a match, and a withdrawn case is excluded.
- The new private governorate never appears in a public export, even when public precision is `withheld`.
- The related endpoint and page never mutate case links, evidence, state, or review history.

## Task 1: matching contract and API

**Files:** `services/collector-api/syosint/case_grouping.py` (new), `services/collector-api/syosint/api.py`, `services/collector-api/tests/test_case_grouping.py` (new).

- [x] Add failing API tests for strict governorate values, no metadata, same facet matching within six hours, different category/governorate, timezones, malformed/naive timestamps, withdrawn/self exclusion, ten-result ordering, 404, and side-effect-free repeated reads.
- [x] Run the focused test and observe the absent-field/route failure.
- [x] Implement a 14-value private governorate enum/validation and the pure matcher. Parse UTC instants, use six hours inclusive, and order by `(absolute time difference, case ID)`.
- [x] Add `GET /incidents/{id}/related`, with a database filter for category/governorate and only explicit safe response fields. Keep existing JSON incident storage and export behavior.
- [x] Run focused and full API tests. Commit the API change.

## Task 2: private desk presentation

**Files:** `apps/analyst-desk/src/app/actions.ts`, `apps/analyst-desk/src/app/incident/[id]/page.tsx`, `apps/analyst-desk/src/app/incident/[id]/page.test.tsx` (new or extend existing).

- [x] Add failing page/action tests for the optional governorate select, preserved edit submission, candidate links with time difference, empty/insufficient-data state, API-unavailable state, and clear non-merge wording.
- [x] Run the focused desk tests and observe the expected failure.
- [x] Add the controlled selection and related-case panel to the private case page. Submit the facet through the existing server action. Never display raw evidence in the suggestion panel.
- [x] Run desk tests, lint, typecheck, and build. Commit the desk change.

## Task 3: integrated verification and handoff

**Files:** `apps/analyst-desk/e2e/workflow.spec.ts`, `docs/PROJECT_STATE.md`, `docs/AGENT_HANDOFF.md` if needed.

- [x] Add a synthetic browser case pair with matching facets, inspect suggestion, and verify no merge or public export occurs. Run the browser test against the local API.
- [x] Run repository policy, Python API tests, JavaScript tests, lint, typecheck, builds, and browser workflows. Review the public export assertion.
- [ ] Update project state with completed scope, verification, and next slice. Review the diff and open a PR against the current `main`; wait for CI and code review before merging.

## Self-review

The plan covers every design component and keeps candidate-source review, Telegram collection, and the public pipeline untouched. API fields are consumed by the desk after Task 1. Each review-focus risk has a test step. No code step prescribes a function body or broad refactor.

## Execution evidence — 2026-10-12

Owner approved implementation. API tests 312 pass, JavaScript tests 153 pass; policy, lint/typecheck and both builds pass. Independent review found historical facet-type and historical-offset display failures; regression tests were observed RED then GREEN, followed by full green suites. CI verification run `38241546409` passed on `cdac32f`, including seven desk browser tests and the public browser suite. The live RSS gate passed. The separate audit job fails on unpatched braces CVE-2026-93687. No audit exception is active and PR #21 is not merged. Next action: owner review of `docs/DEPENDENCY_AUDIT.md`; all other implementation steps are complete.
