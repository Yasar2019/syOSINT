# Private retention jobs

The owner requested implementation and completion of the next roadmap step after the retention proposal: expire downloaded media after 30 days and private intake metadata after 180 days, support preservation holds, preserve public revision/audit history. Implement and test with synthetic fixtures only; never execute cleanup on the owner's private data from this session.

## Approach and scope

Use one local Python retention service, CLI and daily API-lifespan scheduler, with a small private maintenance page. No cloud jobs/dependencies. Unlike ad-hoc filesystem cleanup, eligibility is determined by persisted records and relational protections. Unlike hard deletion on upgrade/startup, the default scheduler performs read-only previews; the operator explicitly enables application with SYOSINT_RETENTION_APPLY=1. A manual apply additionally requires acknowledged:true / CLI --apply. This is a conservative implementation choice, not an instruction to erase current user files.

Cleanup only covers MediaAsset, unlinked IntakeItem and its IntakeRevision/MediaAsset/expired TelegramPublicationPreview children, old IntakeQuarantine, and expired publication previews. Never delete Source, Incident, Evidence, candidate reviews, Audit, IncidentPublication*, TelegramPublication*, correction/withdrawal history, credentials, sessions, exported/public datasets. No raw source text inspection or AI processing.

## Eligibility and holds

Media expiry uses expires_at, bounded by collected_at+30 days even if a stored deadline is later. Metadata expires when collected_at (or latest intake revision collected_at) is strictly older than now-180 days. Quarantine uses created_at. Public preview records may be removed after expires_at. Use aware UTC clock and reject naive run times. Preview and apply use the same eligibility predicate. Bound each category batch to 1000 rows; report partial runs/backlog so repeated manual runs can drain it. Recent and exact-cutoff metadata stays.

Protect an intake and its media if incident_id is set, status=promoted, an Evidence reference matches its source_id+url, any TelegramPublication references it, a nonexpired publication preview references it, or an active hold references intake or any child media. Preserve item/media when any child media remains unexpired or fails safe deletion. Apply rechecks under SQLite BEGIN IMMEDIATE so creation/release of holds and collector writes cannot race eligibility. Document one API process; CLI shares database serialization.

Migration0008 preserves existing records while making retention-managed integer identities nonreusable, so released holds and audit entries cannot alias later records. Revision/media child deletion is also bounded per run and a parent remains until all children are drained. Media collection rechecks the same parent identity under a serialized write transaction after asynchronous download, discarding a file if retention removed its parent.

Migration0008 adds RetentionHold (unique active target_kind+target_id; released rows remain, a later hold creates a new row, kind intake/media/quarantine, reason <=1000 trimmed, created_at, released_at) and RetentionRun (timestamp, dry_run, aggregate counts/status only). Active hold blocks deletion until explicitly released. Released holds/audit remain; no private file paths/bodies in output. Reject nonexistent targets, invalid IDs and unknown input keys. Holds have no automatic expiry. Audit hold placement/release and applied deletion of each private record using IDs/hash-only before/after; never log text, URLs, local paths or raw exceptions. Dry-run must not mutate DB, filesystem or run/audit history.

## Filesystem safety/failure

Only unlink regular, single-link, absolute .bin files beneath the configured SYOSINT_PRIVATE_DIR/telegram/media root. Reject symlink root/ancestors/path components, traversal, outside paths, hardlinks and nonregular files; never follow a symlink. Open trusted root via directory descriptors/O_NOFOLLOW and unlink basenames relative to descriptor (safe against ancestor replacement); missing files count as already absent and may be marked deleted. Do not create media dirs during preview. Invalid files remain recorded and their parent metadata is preserved. File deletion and SQLite are not jointly transactional: commit/retry semantics must be conservative, idempotent and documented; audit missing-file recovery, do not call it secure erasure. A failed unlink does not mark its row deleted; other safe items may progress with aggregate failures. Never VACUUM or claim forensic deletion.

## API and operator contract

Local protections apply to all new endpoints. GET /retention/status returns enabled/apply_enabled, media_days=30, metadata_days=180, last_run (safe aggregate/null). POST /retention/preview returns {media,intake,quarantine,previews,protected,failed,bounded} integer aggregate counts (bounded is a boolean), with no mutation. POST /retention/run requires {acknowledged:true} and apply-enabled config, recomputes safely then returns same counters. GET /retention/holds returns bounded list of {id,target_kind,target_id,reason,created_at,released_at}. POST /retention/holds requires {target_kind,target_id,reason}; POST /retention/holds/{id}/release requires {reason}. Repeated active placement or repeated release reject409. All errors generic, no raw exception bodies/paths.

CLI: python -m syosint retention preview; python -m syosint retention run --apply; python -m syosint retention hold --kind intake|media|quarantine --id N --reason TEXT; python -m syosint retention release --id HOLD_ID --reason TEXT. Uses SYOSINT_DB_PATH and SYOSINT_PRIVATE_DIR defaults consistent with API. Apply requires SYOSINT_RETENTION_APPLY=1 in CLI too; preview never creates a missing database. Machine-readable safe aggregate JSON output, bounded errors.

Scheduler uses SYOSINT_RETENTION_SCHEDULER=0 to disable, otherwise starts with API and previews once immediately then every24h. Automatic deletion only if apply-enabled. Non-overlapping run, safe errors/retry on next tick, graceful shutdown without orphan work. Private maintenance page shows policy/mode, preview counts, holds placement/release, and explicit apply acknowledgment when allowed. No deletion of real content in browser acceptance, use dry-run+hold/release synthetic flow.

## Verification

Prove expiry boundaries, all protections, holds lifecycle/reviewed history preservation, no-mutation dry-run, bounded batches, idempotence, unsafe paths/symlink/hardlink/race resistance, unlink failures/retries, migration populated0007, safe errors, scheduler overlap/shutdown and lifespan, CLI no database creation, private UI, and synthetic browser flow. Run full API/JS, lint/types/builds/audits/policy and CI; independent review before merge. Next roadmap step remains backup/recovery.
