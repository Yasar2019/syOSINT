# Milestone 4 — Source Expansion and Telegram Intake

**Status:** Approved conversational design; pending written-spec review  
**Date:** 2026-09-24  
**Repository:** `Yasar2019/syOSINT`  
**Target users:** Journalists, OSINT researchers, fact-checkers, and humanitarian researchers

## 1. Purpose

Milestone 4 makes the public dashboard materially more useful while adding lawful public-Telegram monitoring to the private analyst workspace. It has two coordinated outcomes:

1. expand the automatic RSS/Atom headline wire from two sources to a balanced set of 8–12 reviewed Arabic and English sources; and
2. collect approved public Telegram channels locally, route their posts through human review, and permit individually approved, sanitized Telegram leads to appear on the public dashboard.

RSS and Telegram share a private intake workflow but retain different public-publication rules. RSS may automatically publish minimal original headline metadata from repository-reviewed feeds. Telegram never publishes automatically: channel approval authorizes collection only, and every public Telegram item requires a separate human review and explicit approval.

## 2. Success criteria

The milestone is complete when:

- the public allowlist contains 8–12 enabled, reviewed, operational RSS/Atom sources across Arabic and English;
- visitors can see configured, healthy, delayed, and empty source states instead of inferring coverage from current headlines;
- the public dashboard clearly distinguishes synthetic reviewed incidents, automatic RSS headlines, and human-approved Telegram leads;
- an analyst can authenticate to Telegram locally using analyst-owned official API credentials;
- an analyst can manually approve public channel usernames for read-only collection;
- RSS and Telegram items appear in a unified private intake queue and in platform-specific views;
- collection handles Telegram backfill, new posts, edits, deletions, duplicates, rate limits, and bounded optional media preservation;
- an analyst can write bilingual headlines, complete a safety review, preview, and explicitly approve one Telegram item for the public wire;
- later edits or deletions create a correction/withdrawal review instead of silently rewriting public history;
- Telegram-derived content is never sent to AI or machine-learning systems; and
- all work runs on Python 3.14.7, or a newer stable security/maintenance patch in the 3.14 series available before implementation merges, without paid APIs or required cloud infrastructure.

## 3. Non-goals

This milestone does not add:

- private groups, invite-only channels, access-control bypassing, or automated channel discovery;
- automatic public publication from an allowlisted Telegram channel;
- bots that send, react, moderate, or otherwise write to Telegram;
- AI/ML summarization, translation, classification, transcription, OCR, embeddings, computer vision, or credibility scoring for Telegram content;
- public Telegram post text or public Telegram media;
- multi-user accounts or remote storage for private intake data;
- unrestricted web scraping;
- automatic incident creation, merging, verification, or publication; or
- precise live tactical or sensitive locations.

## 4. Delivery structure

The combined milestone is delivered through three independently releasable pull requests:

1. **Public RSS coverage:** reviewed source expansion, source-state schema, dashboard coverage, pagination, and corrected demonstration disclosure.
2. **Shared intake and local Telegram:** database migration, authentication, allowlisting, collection, reconciliation, unified and platform-specific analyst views, and optional media retention.
3. **Human-approved public Telegram wire:** bilingual analyst headlines, safety gate, preview/export, dashboard integration, and the minimum correction/withdrawal workflow required for published Telegram leads.

This sequence improves the public site in the first pull request and keeps Telegram credentials and raw content entirely outside the public deployment path.

## 5. Architecture

The collector API gains a platform-neutral private intake core. RSS and Telegram adapters normalize records into that core, while adapter-specific cursors and health data remain separate.

```text
Reviewed RSS feeds ──> automatic metadata projection ──> public RSS wire
        │
        └────────────> local RSS adapter ─┐
                                           ├─> shared intake ─> human incident workflow
Public Telegram channels ─> local adapter ─┘          │
                                                       └─> per-item Telegram review
                                                            └─> public Telegram wire
```

The public dashboard reads validated static JSON only. It never connects to Telegram, the local API, SQLite, or the analyst's filesystem. GitHub Actions never receives Telegram credentials or session material.

## 6. RSS source expansion and governance

The repository-controlled public allowlist grows to 8–12 sources. The set balances:

- Arabic and English reporting;
- international editorial organizations;
- humanitarian and institutional reporting; and
- Syria-focused independent publishers.

State-affiliated sources may be included for situational awareness when their ownership is disclosed. Source inclusion is not an endorsement and never assigns claim-level confidence.

Before enabling a source, repository review must confirm:

- the publisher owns or clearly operates the feed and homepage;
- the endpoint is public HTTPS and requires no credentials, cookies, private access, or nonstandard port;
- headline attribution and linking are compatible with the publisher's feed terms;
- the endpoint parses within existing byte, item, redirect, and timeout limits;
- the configured language and bilingual labels are accurate;
- the topic rule produces relevant Syria coverage without obvious systematic false matches; and
- the feed is sufficiently stable for scheduled collection.

Each source declares one deterministic topic mode:

- `syria-only`: accept every headline from a genuinely Syria-specific feed; or
- `keyword-filtered`: require at least one configured Arabic or English Syria, location, or institution term.

Optional deterministic exclusion terms may suppress documented false matches. Topic matching performs no semantic or AI classification.

## 7. Public RSS wire and dashboard

The public RSS schema adds a safe state entry for every configured source:

- identifier and bilingual label;
- language;
- `healthy`, `not-modified`, or `delayed` state;
- last successful refresh; and
- retained headline count.

The dashboard summarizes coverage as configured, healthy, delayed, and retained-headline counts. The source selector lists every configured source, including delayed sources and sources with zero recent matches. An empty filtered result explains whether the source is delayed or simply has no matching retained headline.

The wire keeps its seven-day and 500-item global limits and adds a per-source cap so one broad publisher cannot dominate. Duplicate suppression remains source-local; similar reporting from different publishers is preserved because it may support later human corroboration. The client initially renders a bounded page and provides a **Show more** control.

The demonstration disclosure becomes explicit: reviewed incidents are fictional demonstration data, while the Live News Wire contains real, unverified external publisher headlines.

Safe public source state does not include exception messages, response bodies, URLs containing sensitive queries, or infrastructure detail. Workflow logs name the source and a bounded safe error category for maintainers.

## 8. Shared private intake model

An Alembic migration introduces a platform-neutral model while preserving existing RSS records, workflow statuses, and incident links.

### Source

The existing source record gains or formalizes:

- platform kind: `manual`, `rss`, or `telegram`;
- public identifier and canonical public URL;
- language, enabled state, and review notes;
- collection policy and media policy; and
- platform-appropriate health state.

Telegram sources require a confirmed public username. Secrets and Telegram access hashes do not belong in the source record.

### IntakeItem

`IntakeItem` replaces the RSS-specific application concept of `FeedItem` and stores:

- source and platform;
- platform-native identifier;
- canonical public URL;
- original source text in private local storage;
- optional source headline;
- publication, edit, collection, and deletion timestamps;
- raw and normalized digests;
- workflow state; and
- optional incident link.

The uniqueness boundary is source plus native identifier and deterministic fallback fingerprint. Existing RSS feed-item rows migrate without losing identity or resolution state.

### IntakeRevision

Telegram edits create append-only revisions with timestamps and content hashes. Original and revised text stay local. Public history is never rewritten from a collector callback.

### Adapter-specific cursors

RSS retains HTTP validators and next-poll state. Telegram receives a per-channel cursor for the last durable message, reconciliation window, last success, rate-limit deadline, and safe error category. A cursor advances only after the corresponding items and revisions commit successfully.

### MediaAsset

Opt-in Telegram media records contain only local path, safe MIME type, byte size, SHA-256 digest, collection time, retention deadline, and deletion state. Public schemas forbid all media and local-path fields.

## 9. Telegram authentication and session safety

The implementation baseline is pinned Telethon 1.45.0, which supports Python 3.14. A newer stable patch may replace it before implementation merges only after compatibility tests and dependency audit pass. Pyrogram is excluded because its project is archived, and TDLib is deferred because its native build and distribution burden conflicts with the lightweight cross-platform MVP.

Authentication occurs only in an interactive terminal command:

```text
python -m syosint.telegram_cli login
python -m syosint.telegram_cli status
python -m syosint.telegram_cli logout
```

The login command reads `api_id` and `api_hash` from environment variables or secure interactive prompts, then completes phone, code, and optional two-factor authentication locally. Credentials, codes, phone numbers, and session contents never enter SQLite, browser responses, application logs, or Git.

The session lives under `private-data/telegram/`, is gitignored, and receives restrictive file permissions where supported. The analyst desk displays only safe states: `not configured`, `authenticated`, `expired`, or `reauthentication required`.

## 10. Telegram channel approval

The analyst adds a channel manually by public username. The service resolves the username and presents safe channel identity metadata for confirmation. Collection starts only after the analyst confirms that the resolved entity is public and is the intended source.

The adapter refuses private or invite-only identifiers. It exposes no send, react, join-private, moderation, or account-discovery operation. There is no built-in starter allowlist and no automated recommendation or similar-channel discovery.

Channel approval authorizes local collection only. It does not authorize any item for public display.

## 11. Telegram synchronization

For each enabled channel, the adapter:

- performs an initial backfill bounded to seven days and 500 posts;
- receives new posts and edits while the service is running;
- performs periodic bounded reconciliation after startup and during operation;
- preserves revisions for edited posts;
- marks confirmed deletions;
- deduplicates by channel identity, message identity, and digest;
- quarantines malformed records without blocking the channel; and
- honors Telegram-directed waits, pausing only the affected operation.

Interrupted synchronization resumes from the last durable cursor. One unavailable or rate-limited channel cannot block RSS or other Telegram sources. Missing credentials disable only the Telegram subsystem.

## 12. Optional media preservation

Media download is disabled by default and configured per channel. When explicitly enabled:

- each file is limited to 10 MB;
- only documented safe MIME types are accepted;
- content is stored as inert local data and never executed;
- the file receives a SHA-256 digest;
- default retention is 30 days unless a documented preservation hold applies; and
- deletion is audited.

No Telegram media is published or processed with OCR, transcription, translation, facial recognition, computer vision, embeddings, or any other AI/ML system.

## 13. Analyst experience

The private desk provides three coordinated views:

- `/intake`: unified RSS and Telegram queue with platform, source, language, state, and date filters;
- `/rss`: RSS registration, health, collection, and quarantine management; and
- `/telegram`: safe authentication status, channel approval, synchronization health, media policy, and Telegram-only intake.

All views use the same idempotent promote-to-incident and attach-to-incident operations. They preserve the existing audit, locking, safety, and evidence rules. Telegram content is displayed as untrusted plain text and cannot render source HTML, Markdown, scripts, or embeds.

## 14. Human-approved public Telegram wire

Public Telegram publication uses a separate `telegram-wire.v1.json` contract. A channel must be approved for collection, but each individual item must independently pass the publication workflow.

For an eligible item, the analyst must:

1. inspect the original post and source identity;
2. write a short English headline;
3. write a short Arabic headline without AI/ML assistance;
4. confirm the permanent public `t.me` message link;
5. complete person-safety and operational-safety checks;
6. confirm that the headline contains no precise sensitive location, ordinary-person targeting, unsupported embellishment, or restricted field;
7. review the exact sanitized preview; and
8. explicitly approve export.

Approval creates a gitignored pending public artifact. A separate explicit staging command validates and merges approved records into `data/public/telegram-wire.v1.json`. The analyst then reviews the tracked diff and intentionally commits it through the normal pull-request and Pages deployment path. Neither the local collector nor GitHub Actions can pull Telegram data directly.

The public record contains only:

- stable syOSINT record ID;
- approved channel name, public username, and declared `en`, `ar`, or `mixed` language;
- permanent public message URL;
- human-written English and Arabic headlines;
- original publication time;
- collection and editorial approval times; and
- active, corrected, or withdrawn state with safe revision metadata.

The public record never contains original post text, media, private notes, phone numbers, credentials, session data, access hashes, local paths, or automatically generated text.

The dashboard labels each item **Reviewed external Telegram report — not independently verified**. Approval means reviewed for safe display; it is not a claim-verification judgment.

## 15. Telegram corrections and withdrawals

When a collected Telegram post that has a public record is edited or deleted, the system creates an urgent local review item. It never modifies the public record automatically.

The analyst may:

- approve a corrected bilingual headline and record the reason;
- withdraw the public lead while retaining a visible withdrawal marker; or
- leave the current public revision unchanged with a documented reason when the source change is immaterial.

Corrections and withdrawals append history with timestamps and reasons. The seven-day display window does not erase the audit history in the local workspace.

## 16. Public dashboard integration

The public source-reporting area provides:

- **All reporting**;
- **RSS / Atom**; and
- **Approved Telegram**.

Source, language, and date controls apply consistently. RSS entries show their original-language publisher headline. Telegram entries show the analyst-written headline for the selected dashboard language. Every item links directly to its public source and carries its appropriate disclosure.

The dashboard shows RSS refresh health separately from the Telegram wire's last editorial update. It never implies that the local Telegram collector is continuously online.

Active and corrected Telegram leads remain in the public feed for seven days from the source publication time. Withdrawal markers remain visible for the remainder of that item's display window, while the complete revision and audit history stays in the local workspace.

## 17. Failure handling

- Missing or invalid Telegram setup never prevents RSS collection or API startup.
- Session expiry produces a safe reauthentication state.
- Platform-directed waits are honored without busy retrying.
- Database transactions prevent partial item, revision, cursor, approval, and audit writes.
- Adapter failures are isolated by source.
- Public schema or safety validation failure blocks publication and preserves the last valid Pages deployment.
- All-RSS failure retains the last valid RSS artifact.
- Public Telegram changes require a new explicit editorial export.
- Logs and support diagnostics omit source text, media, secrets, headers, session values, phone numbers, and local paths.

## 18. Testing

CI uses synthetic fixtures and fake adapters; it never authenticates to Telegram or contacts a live Telegram account.

### Unit and contract tests

- source topic modes, exclusions, per-source caps, and status projection;
- shared intake normalization and fingerprints;
- Telegram authentication state mapping;
- public-channel validation;
- backfill, cursors, duplicates, edits, deletions, and reconciliation;
- rate-limit and reconnect behavior;
- quarantine and safe errors;
- media size, MIME, hashing, and retention decisions;
- bilingual Telegram headline validation;
- forbidden public fields; and
- correction and withdrawal revision rules.

### Migration and integration tests

- existing RSS sources and feed items migrate without identity, status, or incident-link loss;
- RSS and Telegram adapters store through the shared intake boundary;
- promote and attach operations remain idempotent;
- public Telegram approval writes only the exact validated projection;
- failed writes do not advance cursors or approvals; and
- public builds consume both versioned wire contracts.

### Browser tests

- configured/healthy/delayed/empty RSS presentation;
- clarified demonstration disclosure;
- mobile **Show more** behavior;
- unified intake and Telegram-specific analyst views;
- public Telegram preview and explicit approval;
- public All/RSS/Telegram views;
- Arabic/English switching and RTL layout; and
- correction and withdrawal display.

### Security checks

- session and media paths remain gitignored;
- secret and phone-number fixtures do not appear in logs or responses;
- Telegram text is rendered as plain text;
- public schemas reject raw text, media, local paths, credentials, and session fields;
- dependency audit covers the pinned Telegram client; and
- Python 3.14 and Node/pnpm policy checks continue to pass.

## 19. Documentation and operations

The milestone updates:

- setup instructions for Windows, macOS, and Linux;
- official Telegram API credential creation and terms links;
- local login, logout, backup, and session-rotation procedures;
- channel-review and public-item-review checklists;
- RSS source-review records;
- media retention and preservation-hold procedures;
- correction and withdrawal procedures; and
- a troubleshooting guide containing only safe diagnostic categories.

Operational instructions must state that sharing raw Telegram content with an AI assistant would violate the project's Telegram AI-exclusion rule.

## 20. Acceptance boundary

Milestone 4 does not complete merely because Telegram messages can be fetched. It completes only when source governance, secure local setup, durable intake, human publication review, public separation, correction handling, documentation, and the complete automated test suite work together without weakening the safety invariants established in earlier milestones.

## 21. Primary implementation references

- Telegram API terms: <https://core.telegram.org/api/terms>
- Creating Telegram API credentials: <https://core.telegram.org/api/obtaining_api_id>
- Telegram update handling: <https://core.telegram.org/api/updates>
- Telegram API errors: <https://core.telegram.org/api/errors>
- Telethon stable documentation: <https://docs.telethon.dev/en/stable/>
