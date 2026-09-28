# Local Telegram intake

Telegram collection runs only in the private analyst service on your computer. Approving a channel collects posts locally; promoting a post creates a triage case. Public Telegram publication requires separate review of each item and a separate staged data change in Git.

## Setup

Use your own Telegram account and obtain its official API ID and API hash at [Telegram API development tools](https://my.telegram.org/apps). Never commit either value, paste it into a browser form, or pass a phone number, login code, password, or hash as a command argument. The phone, code, and optional two-factor password are requested only in an interactive terminal.

Install the collector API and launch the local service as described in the [README](../../README.md). With the API stopped, configure credentials in the local shell and run the interactive login:

| Platform | Local terminal commands |
| --- | --- |
| macOS/Linux (bash) | `export SYOSINT_TELEGRAM_API_ID="YOUR_ID"` and `export SYOSINT_TELEGRAM_API_HASH="YOUR_HASH"`; then `.venv314/bin/python -m syosint telegram login` |
| Windows (PowerShell) | `$env:SYOSINT_TELEGRAM_API_ID="YOUR_ID"` and `$env:SYOSINT_TELEGRAM_API_HASH="YOUR_HASH"`; then `.venv314\Scripts\python.exe -m syosint telegram login` |

Enter credential values only in a trusted local shell. Shell history and process environment may retain values; use your operating system's protected secret store where possible. Never capture your terminal while entering codes. The optional `SYOSINT_PRIVATE_DIR` overrides the default `private-data/` directory. Store it outside cloud-synced and shared directories.

Run `python -m syosint telegram status` to check your local authorization and `python -m syosint telegram logout` to remove the local session after an interactive confirmation. Use the virtual environment Python shown above in place of `python`. Logout deletes only local session files; revoke the authorization separately in Telegram's device settings if the account or machine is compromised. If the desk shows reauthentication required, stop the API, run the terminal login again, and restart it. The session and its SQLite sidecars are stored under `private-data/telegram/`; on POSIX the directory and files use restrictive permissions. On Windows, use a user-private folder with restrictive account ACLs.

## Approve and review

1. Start the local API and private desk. Open `http://127.0.0.1:3001/telegram` and confirm the connection state.
2. Resolve a **public** username. Verify the preview, including the immutable numeric channel ID and title, against the publisher's official channel. Approve it explicitly; the server resolves it again and rejects a changed identity. Do not enter private, invite-only, or uncertain channels.
3. Sync manually or let the local scheduler run while your API is open. Backfill is capped at seven days and 500 posts; periodic reconciliation checks recent posts for edits and deletions. Rate-limit waits are isolated per channel and shown through safe status values. No collection occurs while your local API is closed.
4. Review the channel health and unverified posts in the private Telegram page, then use `/intake` to filter by platform, status, source, language, and date. Read original source links, revisions, and deletion flags before writing bilingual analyst titles or attaching evidence to a case. Incident approval and export require separate human review.

## Publish an individual report

1. From `/telegram`, open a post's **Review for public publication** link. Review the original locally. Write English and Arabic headlines yourself, check the channel identity, person and operational safety, and confirm your own review. Select **Preview public Telegram lead**.
2. Inspect the exact sanitized public JSON, then explicitly authorize that record and select **Approve public Telegram lead**. A changed or deleted source invalidates the draft. The approval stays local and is not an automatic website update.
3. The private API writes a pending JSON export under its configured export directory after an approval, correction, or withdrawal. Pending exports remain gitignored and private. Find the generated `telegram-pending.v1.json` in that directory and stage it with `python -m syosint.telegram_publish_cli stage --confirm-publication --pending PATH_TO_PENDING_JSON --output data/public/telegram-wire.v1.json`.
4. Review the staged JSON and diff, then submit and merge the public data change. Both Pages workflows validate the RSS and Telegram contracts before deployment. A Telegram correction or withdrawal also requires an explicit local editorial action, a new pending export and staging, and a new public data change. The public site keeps corrections and withdrawal notices within seven days of the original post.

Public records contain a manually written bilingual headline, the approved public channel identity, canonical `t.me` URL, timestamps, and editorial correction history. They carry the label **Reviewed external Telegram report — not independently verified**. No original post text, private notes or media is staged. Telegram-derived material must never be sent to AI or machine-learning systems.

Text is untrusted and displayed as plain text. Do not paste raw Telegram content into AI assistants or AI/ML services. Do not commit the private database, downloaded posts, media, or session files.

Media collection is **off by default** for each channel. Enabling it from the private channel page permits selected types only, streamed into inert local `.bin` files, with a 10 MB per-file limit and a maximum 30-day retention deadline. The public dashboard never receives local media or private paths. Treat local database and media backups as sensitive, exclude them from automated cloud backup and repository sync, and securely clear expired data using the application's retention task.

Status and failures are sanitized; share only safe categories when seeking help. For identity changes, review the channel again rather than following the new username automatically. For persistent rate limits, wait and retry; do not bypass platform controls or expand collection to private groups.
