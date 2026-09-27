# Security Policy

## Reporting

Do not open a public issue for a vulnerability that could expose credentials, private evidence, sensitive locations, or personal information. Use GitHub's private vulnerability reporting feature for this repository.

Include the affected revision, reproduction steps using synthetic data, expected impact, and any safe mitigation you tested. Do not attach real credentials, Telegram sessions, raw field media, or personal data.

## Supported code

Security fixes target the current `main` branch. The public dashboard is intentionally static and must not gain runtime secrets, a private database connection, or access to the future local evidence vault.

## Out of scope

Requests to access private channels, bypass platform controls, identify individuals, or publish precise live tactical locations are not accepted as product features.


## Private Telegram material

The session under `private-data/telegram/`, local posts, the SQLite database, optional media, and staged exports are private. Keep them outside Git, cloud sync, public issues, and AI/ML services. Restrict the local account and backup permissions. Authentication occurs in an interactive terminal only; report a suspected exposure through private vulnerability reporting and revoke the device authorization in Telegram settings.

Only explicitly approved public channels may be collected. The private desk renders untrusted post text as text, without embeds or remote media. The public dashboard has no automatic Telegram publication path. An analyst must review each future public Telegram item individually.
