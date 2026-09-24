# Architectural Decisions

This file records project decisions that future agents must preserve unless the user explicitly changes them.

## ADR-001 — Local-first private workspace

**Decision:** The collector API, evidence vault, and analyst desk run locally and bind to `127.0.0.1`.

**Reason:** Raw evidence and analyst notes should not require cloud infrastructure, and the MVP is single-analyst.

**Consequence:** The public dashboard never connects to the private API or SQLite database.

## ADR-002 — Static public dashboard

**Decision:** The public dashboard is a statically exported Next.js application that consumes only validated JSON from `data/public/`.

**Reason:** This keeps hosting free, auditable, and isolated from secrets and raw evidence.

**Consequence:** Publication is a build/export workflow, not a live database view.

## ADR-003 — Human publication gate

**Decision:** No incident, evidence, analyst summary, or confidence judgment is published automatically. Publication is an explicit analyst action and fails closed. ADR-011 defines the sole metadata-only exception for the public RSS/Atom wire.

**Reason:** Source reports may be incomplete, contradictory, sensitive, or unsafe to publish.

**Consequence:** Confidence alone never authorizes publication; safety and schema checks must also pass.

## ADR-004 — Confidence labels, not universal scores

**Decision:** Use named confidence states such as Unverified, Developing, Corroborated, Verified, Disputed, and False.

**Reason:** A single numeric score would imply precision the evidence does not support.

**Consequence:** Verified and False require written rationales, and public records retain unresolved uncertainty.

## ADR-005 — Deterministic duplicate detection first

**Decision:** MVP duplicate handling uses source IDs, canonical URLs, hashes, normalized text fingerprints, and simple temporal/geographic rules.

**Reason:** These methods are inspectable and reproducible.

**Consequence:** Similarity suggestions require human review; no automatic incident merge occurs from textual similarity alone.

## ADR-006 — Telegram is public-only and AI-excluded

**Decision:** Future Telegram support uses the official API for approved public channels only and remains read-only. Telegram-derived content is excluded from AI/ML processing.

**Reason:** This is a core legal, privacy, and platform-policy boundary of the product.

**Consequence:** No private groups, invite-only access, credential sharing, automated AI summarization, embeddings, transcription, translation, image analysis, or model training on Telegram-derived material.

## ADR-007 — Safety-sensitive location handling

**Decision:** Public location precision is distinct from private analyst precision. Sensitive or operationally relevant locations are generalized, delayed, or withheld.

**Reason:** The public product must not create avoidable harm.

**Consequence:** Precise live positions of civilians, aid workers, medical sites, shelters, evacuation routes, journalists, or active forces are not publishable.

## ADR-008 — Append-only audit history

**Decision:** Material creates, edits, state transitions, approvals, exports, corrections, and withdrawals produce audit entries.

**Reason:** Journalistic and OSINT workflows require traceability and accountability.

**Consequence:** Corrections and withdrawals preserve history rather than silently rewriting it.

## ADR-009 — Milestones remain separated

**Decision:** Milestone 2 implements the analyst desk and publication workflow without live RSS or Telegram collection.

**Reason:** Separating persistence/workflow from ingestion keeps testing and review manageable.

**Consequence:** RSS starts in Milestone 3; Telegram starts in Milestone 4.

## ADR-010 — GitHub is the continuity source of truth

**Decision:** Project state, roadmap, designs, plans, decisions, tests, branches, commits, and PRs must contain enough information for another agent to resume.

**Reason:** Chat-agent runtime state is temporary and may disappear.

**Consequence:** Hidden scratchpads, uncommitted files, or chat-only decisions must not be required to continue development.

## ADR-011 — Automatic RSS metadata is a narrow public-wire exception

**Decision:** A scheduled GitHub Actions workflow may automatically publish minimal metadata from reviewed, committed RSS/Atom allowlist entries: source label, original headline, language, stable identifier, publication/collection time, and canonical publisher URL.

**Reason:** A timely public headline wire is useful before an analyst can verify and model every report, provided it cannot be confused with a syOSINT finding.

**Consequence:** Every wire entry is labeled unverified external reporting and remains visually separate from reviewed incidents. Article bodies, descriptions, locations, media, analyst text, evidence, confidence labels, and incident records stay behind ADR-003's human publication gate. Adding or changing a public source requires repository review.
