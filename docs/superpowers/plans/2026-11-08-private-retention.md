# Private retention implementation plan

> Use subagent-driven implementation for backend then private UI, followed by whole-branch review.

**Spec:** docs/superpowers/specs/2026-11-08-private-retention-design.md
**Goal:** Safe local retention preview/application, holds, daily scheduler and maintenance controls.
**Global constraints:** Synthetic fixtures only, dry-run default, explicit apply gate, fixed30/180-day policy, public/evidence/audit history preserved, no new deps or raw-data AI processing.

### Task 1 — Backend retention service and integration
- [x] TDD migration0008, models, eligibility/planning/apply, descriptor-safe filesystem deletion and bounded aggregate results.
- [x] TDD strict API hold/status/preview/run routes, CLI commands, daily no-overlap scheduler/lifespan and error recovery.
- [x] Full API tests and migration expectations; self-review and commit. API contract is in spec; root consumes it verbatim in Task2.

### Task 2 — Private maintenance and release
- [x] TDD maintenance actions/page: safe errors, counts, apply gate, holds and release; add home navigation.
- [ ] Synthetic browser acceptance: preview and hold/release only; no real data or account cleanup.
- [x] Document activation, dry run, held/linked data, batching, filesystem failures, deletion limitations and no public deployment change.
- [ ] Run API/JS/lint/types/builds/audits/policy, independent whole-branch review, CI and release; update roadmap and handoff.

## Review focus
Live collection/hold races, parent-child protections, mutable filesystem ancestors, DB/file partial failure recovery, dry-run mutation, accidental history erasure, API error leaks and unsafe defaults.

## Verification handoff

Local JS187 and API356 tests passed, along with lint/types, both builds, secret policy and the configured dependency audit gates. Independent review found and prompted fixes for post-download parent races, oversized child batches and reused integer identities; follow-up collector serialization is included. Final independent review passed62 targeted tests and separately verified populated migration/index/foreign-key integrity; no Critical or Important findings remain. A synthetic browser test covers preview and hold/release without deletion. This workspace blocks Chromium launch, so GitHub CI must pass that browser acceptance before merge. The release PR records the final review and CI outcome. No cleanup of owner data or account configuration was performed.
