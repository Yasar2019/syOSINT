# Private retention and preservation

Retention runs on the operator's local computer while the collector API is running. It never changes the public dashboard, reviewed incidents, evidence, publication or correction/withdrawal history, sources, audit trail, Telegram credentials or session files. Do not run multiple API workers against the same private database.

## Preview first

The default is **preview only**. Open the analyst desk at `http://127.0.0.1:3001/maintenance` to see eligible counts, blocked files and preservation holds. Loading or refreshing a preview makes no retention writes and deletes nothing. The local scheduler previews immediately on startup and once every 24 hours; set `SYOSINT_RETENTION_SCHEDULER=0` to disable it.

From the existing configured Python environment:

```sh
python -m syosint retention preview
```

The CLI uses the existing migrated database at `SYOSINT_DB_PATH` (default `private-data/syosint.sqlite3`) and media under `SYOSINT_PRIVATE_DIR/telegram/media` (default `private-data/telegram/media`). It refuses a missing database instead of creating one. Start the API normally to apply schema migrations before using these commands. Back up the private database and files before upgrading or enabling deletion; retention is not a backup system.

## Policy and protection

| Private record | Expiry | Protection |
| --- | --- | --- |
| Downloaded media | Earlier of its stored deadline and 30 days after collection | Linked case/evidence, published item, active publication preview, intake or child-media hold |
| Unlinked intake and revisions | More than 180 days since collection or latest collected revision | Same protections; any recent, blocked or failed child media also preserves its parent |
| Quarantine | More than 180 days since creation | Active quarantine hold |
| Publication preview | Stored expiry | Published records and their revision history are never removed |

Exact-cutoff intake and quarantine records remain. Holds do not expire automatically. Place a hold before enabling deletion if material must survive the standard policy. Use the numeric private record identifier, not a public headline or URL:

```sh
python -m syosint retention hold --kind intake --id 123 --reason 'Preserve for case review'
python -m syosint retention hold --kind media --id 456 --reason 'Preserve original media'
python -m syosint retention release --id 1 --reason 'Review completed'
```

The maintenance page supports the same operations. Release uses the **hold ID**, not the target record ID. Duplicate active holds are rejected. A new hold after release creates a separate record; prior holds, release reason hashes in audit, and deletion audit records remain. Keep reasons concise and avoid including source bodies or credentials.

## Enable deletion deliberately

After reviewing the preview and holds, set `SYOSINT_RETENTION_APPLY=1` in the local API environment and restart it. This enables the daily scheduler to apply cleanup, including its immediate startup run. To permit only manual cleanup, also set `SYOSINT_RETENTION_SCHEDULER=0` before restarting.

The maintenance page then shows an acknowledgment checkbox and **Delete eligible private data**. Every request recomputes eligibility under a database write lock. The CLI also requires both the environment opt-in and the explicit apply flag:

```sh
SYOSINT_RETENTION_APPLY=1 python -m syosint retention run --apply
```

Remove the environment opt-in and restart to return the API to preview mode. Manual acknowledgment alone cannot bypass a disabled apply setting. No deletion is performed by the upgrade itself with the default configuration.

## Batches, failures and recovery

Each category, including child revision/metadata rows, processes at most 1,000 candidates per run. A parent remains until its eligible children are drained. Retired identifiers are not reused, preserving hold and audit references. A bounded result means additional candidates may remain; repeat preview/application to drain the backlog. Protected or blocked records can require operator attention. If an entire media batch is blocked by unsafe paths or file errors, resolve those failures before later media can progress; cleanup never skips its safety checks to drain a backlog. Protected counts are bounded samples, not a full inventory. Read-only previews are not persisted as run history; applied runs keep aggregate local status and per-record hash/ID audit entries.

Only absolute, single-link regular `.bin` files inside the configured media directory are eligible for unlinking. Symlinks, traversal, outside paths, hardlinks and nonregular files are rejected. Failed or unsafe files remain recorded, and their intake parent remains. Check local permissions and the configured directory; do not loosen path checks or manually point a media record at another file.

Filesystem removal and SQLite commits are not one transaction. A crash can remove a file before the database update commits. A subsequent run recognizes an already absent safe file, updates its record and audits recovery. A failed unlink never marks the file deleted. Preserve backups until any recovery is checked locally.

This removes eligible active records/files, not forensic copies in SQLite free pages, operating-system storage, snapshots or backups. It does not perform secure erasure or `VACUUM`. Backup/recovery procedures and the final threat-model review remain separate roadmap work.
