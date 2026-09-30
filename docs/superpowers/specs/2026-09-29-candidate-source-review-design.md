# Milestone 5: candidate-source review

**Status:** approved by owner on 2026-09-29 (America/Toronto)
**Scope:** first independent Milestone 5 release

## Intent and success

Journalists and OSINT researchers need a private place to record a suggested public source, decide whether it is suitable for later registration, and remember why a suggestion was rejected. A candidate is an untrusted lead. The first release is successful when an analyst can submit a public web/RSS or public Telegram candidate, review it against explicit criteria, see the decision history after an API restart, and find previously rejected suggestions. No candidate submission or decision starts collection or changes the public dashboard.

## Selected approach

Use a separate local `source_candidates` table and append-only `candidate_reviews` table, exposed through the loopback API and a private `/candidates` analyst page. This keeps untrusted suggestions out of the active `sources` table. A simpler Markdown list would not support private review history or deduplication in the desk. Reusing `sources` with a disabled flag risks confusing an accepted suggestion with an approved collection source.

## Candidate record

An analyst manually supplies a public HTTPS URL, platform (`web` or `telegram`), short display name, language (`en`, `ar`, or `mixed`), and a brief reason for suggesting it. For Telegram, only public `https://t.me/<username>` channel-style links are accepted as candidates; invite links, message links, and private handles are refused. The API does not resolve Telegram identity at submission time, visit websites, parse feeds, or copy post text. It normalizes the URL for exact duplicate detection and rejects a candidate already recorded for that platform. It also reports a matching registered source so the analyst can avoid redundant review. Input lengths are bounded; URL validation follows the existing public HTTPS policy and rejects credentials, fragments, local hosts, and IP literals.

Each candidate starts `pending`. A review appends one decision (`accepted` or `rejected`) with a reason and five explicit human checks: public accessibility, Syria relevance, publisher/channel identity and impersonation, provenance, and collection/reuse policy. A check is a human attestation, not an automated credibility score. Acceptance requires all five checks and a reason. Rejection requires a reason and preserves unchecked/failed criteria for future context. The latest decision is displayed with the full timestamped history; a later review may supersede an earlier decision, but never erases it. Duplicate suggestions point to the existing candidate and do not create another record.

`accepted` means suitable to consider for separate source registration. It does **not** insert a `Source`, edit `config/rss-sources.json`, authorize Telegram channel collection, or publish anything. An analyst follows the existing source-specific review and registration path afterward. Rejection is not a claim about editorial quality or truthfulness.

## Components and data flow

1. A new Alembic migration adds candidate and review tables with a unique platform/canonical-URL key, bounded indexed status/list retrieval, and foreign-key review history. Existing databases migrate without changing current sources or intake items.
2. A small candidate service handles normalization, duplicate checks, review transitions, and audit records. The local API exposes `POST /candidates`, `GET /candidates`, `GET /candidates/{id}`, and `POST /candidates/{id}/reviews`. Requests are strict and errors return 422 for invalid data, 404 for unknown IDs, and 409 for duplicate candidates or conflicting registered sources. Review writes are transactional.
3. The private analyst desk adds `/candidates` with a submission form, status filter, candidate details, review checklist and reason, and visible decision history. Forms use the established server action/API pattern; the page renders candidate text as text, never HTML or remote embeds. A navigation link makes the queue discoverable.
4. The public dashboard, scheduled RSS job, Telegram scheduler, and export schemas are untouched. No candidate content enters AI/ML processing, public data, or logs.

## Verification

- API tests cover safe URL and Telegram-link validation, duplicate submissions, conflict with registered sources, acceptance checklist gates, rejection/re-review history, persistence across restart, and zero side effects on active sources, collection, and export.
- Desk tests exercise an empty queue, an accepted and a rejected review, filtering, and server-action error handling. A browser workflow checks submit → review → revisit without real network collection or credentials.
- Run the repository policy, Python and JavaScript tests, lint, typecheck, builds, and browser checks in CI. No live-source gate change is needed because the feature never activates a source.

## Deferred

Automated link discovery, website crawling, Telegram post inspection, source registration from a candidate, trust scoring, grouping suggestions, and public display remain outside this first release. Future additions must keep the same explicit human approval and source-specific activation boundary.
