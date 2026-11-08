# Incident corrections and withdrawals

The analyst desk and API run on localhost. Use one API process: approval and export are serialized by a process-local lock. Back up the SQLite vault and private export directory with the application stopped before applying migration `0007` to an existing installation. Startup applies the migration; it preserves existing cases. Never commit the vault, evidence, sessions, or private version history.

## Review, approve, export

Open the case's publication page. The displayed version describes a **local approved snapshot**, not a live deployment. Version zero means no snapshot has been initialized: review the original incident and explicitly export it first. An old approved case does not prove what was deployed previously.

For a correction, edit the complete public fields and enter English and Arabic reasons. Saving creates a private draft; the approved record remains unchanged. Complete a new safety/verification checklist, inspect the exact sanitized preview, then acknowledge and approve it. An edit resets review. Approval rejects stale versions and preview hashes. Public correction history lists the reason, time, and actual changed public fields; the stable incident ID stays the same.

For a withdrawal, enter bilingual reasons, inspect the generic withdrawal notice, then acknowledge and approve. A withdrawal is terminal in this release. It replaces the claim with a generic title, reason and withdrawal time, withheld location, no source links, and no coordinates. Prior sanitized snapshots remain only in private history. Withdrawn entries remain in the public feed but are excluded from active counts, map, and timeline.

Approval updates the local database snapshot and invalidates any prior pending per-incident export. It does not write a new export or deploy. Explicitly export the latest approved snapshot when ready. Repeat export returns that snapshot unchanged.

## Stage by stable ID

Each private `incident-N.json` export is a **one-record dataset**. Never copy it over `data/public/incidents.v1.json`: that would remove all the other incidents. In a separate reviewed data change:

1. Read the existing public dataset and the newly exported one-record dataset locally.
2. Confirm the record ID and revision are the intended approved ones. Inspect bilingual reasons for accidental sensitive details.
3. Replace only the existing `incidents` array member with the matching `id`; for a first publication append that ID only if absent. Reject duplicate IDs. Preserve all unrelated records and dataset metadata. Advance `generatedAt` to the staging time.
4. Use `validatePublicDataset` from `@syosint/schemas` to validate the entire resulting dataset (schema plus duplicate/source consistency checks), run `pnpm --filter @syosint/schemas test`, `pnpm test`, and `pnpm build`. The build loads and validates the staged incident dataset; the wire sync script alone validates RSS/Telegram, not incidents.
5. Review the diff: only the intended incident and refresh time should change. Commit the sanitized dataset through a reviewed PR. Deploy after CI passes, then verify the served record. Local approval/export is not confirmation of that deployment.

Do not publish the history endpoint response, draft, evidence, or the entire vault. Full previous claims must not be placed in the public withdrawal record. Telegram publication uses its separate approved workflow.

## Recoverable errors

An export disk failure retains the durable approved database snapshot and removes stale pending output when possible. Correct local disk permissions/space, inspect and remove any stale per-incident pending file if cleanup failed, then explicitly retry export. Do not stage an older file after approval of a newer version. API/UI errors intentionally omit private paths and raw response bodies; inspect local filesystem state directly. A stale preview requires reloading the latest version and repeating preview/approval; never fabricate a version or hash.
