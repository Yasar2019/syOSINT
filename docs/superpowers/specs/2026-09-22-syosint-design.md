# syOSINT — Product and Architecture Design

**Status:** Approved architecture, pending written-spec review  
**Date:** 2026-09-22  
**Repository:** `Yasar2019/syOSINT`  
**License:** Apache-2.0 for source code

## 1. Purpose

syOSINT is an open-source situational-awareness platform for journalists and OSINT researchers monitoring breaking developments in Syria. It collects lawful public-source reports into a private local workspace, supports a transparent human verification workflow, and publishes only sanitized, approved incident records to a bilingual public dashboard.

The product should feel like a disciplined professional analysis desk: every conclusion exposes its sources, confidence, contradictions, timestamps, corrections, and analyst reasoning. It must not impersonate a government service, claim privileged intelligence access, or imply that uncertain reports are established facts.

## 2. Success criteria

The first production-capable release succeeds when a researcher can:

1. Run the private collector and analyst desk on a MacBook Air M1 with 8 GB RAM.
2. Manage an allowlist of public Telegram channels and RSS feeds.
3. Collect public reports without bypassing access controls.
4. Group exact and likely duplicate reports using deterministic methods.
5. Create, review, corroborate, dispute, approve, correct, and withdraw incidents.
6. Attach evidence references and record a written verification rationale.
7. Export a strictly sanitized public dataset.
8. Publish an Arabic/English responsive dashboard through GitHub Pages at no hosting cost.
9. Audit every material incident change.
10. Operate without paid APIs or mandatory cloud infrastructure.

## 3. Users and access model

### Primary users

- Journalists
- OSINT researchers
- Fact-checkers
- Humanitarian researchers using publicly releasable data

### MVP access

The MVP is single-analyst and local-first. The analyst desk and collector bind to `127.0.0.1` and are not deployed publicly. Multi-user accounts, remote collaboration, and cloud-hosted raw evidence are outside the MVP.

The public dashboard is read-only. It exposes sanitized incidents, methodology, safe source links, confidence labels, correction history, and aggregate statistics. It never exposes the private evidence vault or private analyst notes.

## 4. Legal and ethical boundaries

The following are mandatory product constraints:

- Collect only publicly accessible sources.
- Never access private Telegram groups, invite-only channels, stolen datasets, or content behind authentication not intentionally granted to the analyst.
- Never bypass access controls, rate limits, bans, robots policies, or platform restrictions.
- Never identify, profile, rank, or track ordinary individuals.
- Never implement facial recognition, biometric matching, reverse identity search, doxxing, or social-graph targeting.
- Never publish precise real-time locations of civilians, journalists, medical staff, aid workers, shelters, evacuation routes, or active forces.
- Never publish collected material automatically.
- Never copy full source articles or Telegram posts into the public dataset. Public records use original human-written summaries and link to the source when safe.
- Never process Telegram-derived content with AI or machine-learning systems. This includes automated AI summarization, classification, transcription, translation, computer vision, embedding generation, training, and fine-tuning.
- Use Telegram's official API with an analyst-supplied `api_id` and `api_hash`, comply with its current terms, identify the integration transparently, and never commit session files.
- Preserve corrections and withdrawals instead of silently rewriting history.
- Provide a documented removal and correction-request channel.

## 5. System architecture

```text
syOSINT/
├── apps/
│   ├── analyst-desk/          # Private local Next.js interface
│   └── public-dashboard/      # Static Next.js export for GitHub Pages
├── services/
│   └── collector-api/         # Python FastAPI service and source adapters
├── packages/
│   └── schemas/               # JSON Schema and shared types
├── data/
│   └── public/                # Sanitized, publishable JSON only
├── docs/
│   ├── methodology/
│   ├── source-policy/
│   └── superpowers/specs/
├── tests/
└── .github/workflows/
```

### Local collector and API

A Python service owns ingestion, normalization, persistence, deterministic duplicate detection, publication validation, and the local HTTP API.

- FastAPI provides the localhost API.
- Pydantic validates domain models.
- SQLAlchemy and Alembic manage SQLite persistence and migrations.
- A Telegram MTProto adapter handles approved public channels.
- A standards-based adapter handles RSS and Atom.
- Structured logs omit message bodies and credentials.

The collector runs as a normal user process and does not require Docker.

### Private analyst desk

A local Next.js application communicates only with the localhost API. It provides intake, triage, source management, candidate-source review, incident editing, evidence comparison, verification checklists, location-precision controls, safety review, corrections, withdrawals, and audit history.

It never reads SQLite directly; access passes through explicit API contracts.

### Public dashboard

A separate static Next.js application reads only versioned JSON from `data/public/`. It has no runtime database, secrets, authentication, or private API access.

The MVP map uses an attributed, bundled Syria boundary dataset and generalized incident coordinates. It does not depend on public OpenStreetMap tile servers.

### Shared schemas

A versioned JSON Schema defines the public incident contract. TypeScript types and Python models validate against the same contract. Breaking changes require a new schema version and migration notes.

## 6. Data model

### Source

- internal identifier
- source type and public display name
- canonical public URL
- language and geographic focus
- allowlist and collection status
- reliability notes and correction history
- last successful collection time
- last safe error category

Source reliability and individual-claim confidence are separate concepts.

### Evidence item

- source and source-native identifiers
- canonical URL
- source publication and collection timestamps
- original text stored locally
- optional local media path
- SHA-256 content hash
- deterministic normalized-text fingerprint
- MIME type and file size
- preservation notes
- deletion or correction state

Raw text, media paths, session identifiers, personal data, and private notes are never included in public exports.

### Incident

- stable identifier and categories
- lifecycle state
- human-written Arabic and English titles and summaries
- occurrence-time range and timezone
- public location label
- private and public location precision
- generalized public coordinates when allowed
- linked evidence references
- confidence label and written rationale
- contradictions and unknowns
- safety-review result
- publication timestamps
- correction and withdrawal history

### Audit entry

Every create, edit, state transition, approval, export, correction, and withdrawal produces an append-only audit entry with timestamp, action, affected entity, before-and-after hashes, and a reason when required.

## 7. Incident taxonomy

The MVP supports:

1. Armed clashes, airstrikes, and explosions
2. Political and security developments
3. Humanitarian conditions and displacement
4. Infrastructure outages
5. Border and crossing changes
6. Disinformation and claim verification

Incidents may have multiple categories.

## 8. Lifecycle and verification

Incident lifecycle:

`collected → triage → investigating → corroborated/verified/disputed → approved → published → corrected/withdrawn`

Confidence uses labels instead of a misleading universal score:

- **Unverified:** Collected but lacking independent corroboration.
- **Developing:** Multiple reports exist, but independence or key details remain uncertain.
- **Corroborated:** At least two meaningfully independent sources support the core claim.
- **Verified:** Primary evidence plus independent verification supports material time, place, or event details.
- **Disputed:** Credible evidence materially conflicts with the claim.
- **False:** Available evidence demonstrates that the core claim is incorrect.

No label is assigned solely from source reputation. `Verified` and `False` require written rationales. Public incidents show the label, last review time, source count, and unresolved uncertainty.

The verification checklist records source independence, original-versus-reposted material, time consistency, location consistency, human assessment of visual or documentary support, institutional corroboration when relevant, credible contradictions, circular-reporting risk, manipulation indicators, and remaining unknowns.

## 9. Ingestion

### Telegram

The adapter:

- uses analyst-owned API credentials
- monitors only approved public channel usernames
- performs read-only collection
- stores secrets outside Git with restrictive permissions
- honors platform-directed rate limits
- keeps media download disabled by default
- permits opt-in media preservation per source with size and retention limits
- never joins private or invite-only channels
- never republishes full post text
- never feeds Telegram content into AI or ML tooling

### RSS and public web

RSS and Atom are first-class formats. Each web adapter documents the source's access terms and uses a descriptive user agent. Generic anti-bot bypassing and unrestricted scraping are excluded.

### Candidate-source discovery

Public links and Telegram channel recommendations may create candidate records. Candidates are not collected continuously or trusted before analyst approval. The analyst reviews accessibility, relevance, impersonation risk, provenance, and collection policy. Rejections remain recorded to avoid repeated suggestions.

## 10. Deterministic duplicate detection

The MVP supports:

- exact source-native ID matching
- canonical URL matching
- exact SHA-256 media matching
- normalized-text fingerprint matching
- rule-based temporal and geographic grouping suggestions

Likely matches enter a human merge queue. Similar text alone never triggers an automatic incident merge.

## 11. Publication and safety gate

Publication is an explicit human action and fails closed. Export requires:

- an allowed lifecycle state
- bilingual human-written title and summary
- confidence label and rationale
- at least one safe public source reference
- completed safety checklist
- allowed location precision
- no restricted fields
- schema validation
- acknowledgment of unresolved contradictions

The export removes raw source text, private notes, local paths, credentials, session metadata, ordinary-person identifiers, precise sensitive coordinates, EXIF/device metadata, and operational details that could create imminent harm.

Active military or security locations are generalized to a safe administrative area and publication is delayed when current operational relevance could endanger people. Movement routes, unit positions, non-broadly-public checkpoints, shelters, medical locations, and evacuation routes are withheld. The analyst records the reason for suppression or delay.

## 12. Corrections and withdrawals

Published incidents keep a stable identifier and versioned revisions. Corrections state what changed, why, when, and the current confidence. Withdrawn incidents remain marked as withdrawn unless visibility itself creates a specific safety or legal risk.

## 13. Failure handling

- Ingestion is idempotent.
- Adapters fail independently.
- Retries use bounded exponential backoff with jitter.
- Platform-directed waits are honored.
- Malformed records enter quarantine with a non-sensitive reason.
- Database transactions prevent partial writes.
- Collection cursors advance only after durable persistence.
- Missing translations, incomplete review, schema errors, and forbidden fields block publication.
- Deployment failures leave the last valid public build online.
- Logs redact secrets, headers, session values, raw message bodies, and local paths.
- Source health shows last success, safe error category, and backlog size.

## 14. Security and privacy

- Local services bind to localhost.
- The application stores no GitHub token.
- Environment files, SQLite databases, Telegram sessions, raw media, caches, logs, and pending exports are gitignored.
- Secrets never appear in logs or browser responses.
- Source-derived HTML and Markdown are treated as untrusted plain text.
- Inputs are schema validated.
- State-changing browser requests use same-origin and CSRF protections.
- CI performs dependency pinning checks, secret scanning, static analysis, and dependency auditing.
- Default retention is 30 days for downloaded media and 180 days for private metadata. Documented preservation holds may override deletion for legitimate editorial or evidentiary needs.
- Public revisions and corrections do not expire automatically.

## 15. Localization and accessibility

- Arabic and English ship together.
- Arabic uses right-to-left layout.
- Language switching preserves page and filters.
- Dates include an explicit timezone.
- Color is never the only status signal.
- Keyboard navigation, visible focus, semantic landmarks, reduced motion, and WCAG 2.2 AA contrast are required.
- Graphic media is not mirrored publicly; links carry content warnings when appropriate.

## 16. Testing strategy

### Unit tests

Schema validation, lifecycle transitions, publication authorization, redaction, location generalization, retention decisions, deterministic fingerprints, source-versus-claim reliability separation, and correction versioning.

### Adapter contract tests

Local fixtures and mocked responses cover pagination, cursors, edits, deletions, duplicate delivery, malformed content, rate limits, outages, and unsupported media. CI never connects to live Telegram accounts.

### Integration tests

Collector-to-SQLite persistence, migrations, analyst workflows, public exports, quarantine behavior, and audit completeness.

### End-to-end and UI tests

Synthetic triage-to-publication flow, public filters/map/timeline/detail, Arabic and RTL behavior, keyboard navigation, accessibility, correction display, and GitHub Pages base-path behavior.

### Security tests

Secret-pattern scanning, dependency checks, unsafe HTML fixtures, forbidden public fields, localhost configuration, and log redaction.

## 17. Deployment and cost

The private system runs locally. The static dashboard deploys from the public repository to GitHub Pages through GitHub Actions.

The repository contains source code, synthetic fixtures, documentation, and sanitized public JSON only. Required recurring cost is zero. Optional domains, always-on hardware, remote collaboration, and commercial map providers are outside this guarantee.

## 18. Contribution workflow

- `main` remains releasable.
- Each milestone uses a feature branch and pull request.
- Pull requests document scope, screenshots when relevant, tests, safety impact, and follow-up work.
- Conventional commits are used.
- Apache-2.0 covers source code.
- Public incident data receives a separately documented provenance and reuse policy.
- Synthetic fixtures are labeled and never resemble real vulnerable people.

## 19. Milestones

### Milestone 0 — Foundation

Monorepo tooling, policies, shared schema, synthetic fixtures, CI, and GitHub Pages workflow.

### Milestone 1 — Visible public dashboard

Responsive bilingual interface, bundled Syria map, incident feed, filters, timeline, detail view, methodology, confidence/uncertainty/correction display, static synthetic data, and accessibility baseline.

### Milestone 2 — Private analyst desk

Local interface, SQLite migrations, source and incident management, verification workflow, audit trail, sanitization preview, and public export.

### Milestone 3 — RSS collection

RSS/Atom adapter, cursor handling, source health, deterministic fingerprints, quarantine, and retry behavior.

### Milestone 4 — Telegram collection

Public-channel allowlist, secure setup, read-only ingestion, edit/delete/rate-limit handling, optional media preservation, and Telegram attribution and terms documentation.

### Milestone 5 — Discovery and hardening

Candidate-source review, grouping suggestions, correction/withdrawal tooling, retention jobs, backup documentation, and threat-model review.

## 20. First implementation pull request acceptance criteria

- A documented command installs the monorepo.
- Tests, linting, type checks, and secret scanning pass.
- The public dashboard builds as a static export.
- Arabic/English switching and RTL layout work.
- Synthetic incidents can be filtered by category and confidence.
- The map and timeline require no paid service.
- Details show sources, uncertainty, and corrections.
- No raw evidence, credentials, session artifacts, private fields, or real-person data exist in Git.
- The GitHub Pages workflow validates.
- The README explains purpose, boundaries, architecture, setup, and roadmap.

## 21. Explicitly deferred scope

- private or invite-only collection
- autonomous publication
- AI processing of Telegram-derived data
- facial recognition or person tracking
- offensive-security tooling
- multi-user cloud collaboration
- native mobile applications
- paid APIs
- live tactical tracking
- unrestricted scraping
- automated credibility verdicts
