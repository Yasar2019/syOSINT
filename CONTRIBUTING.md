# Contributing to syOSINT

Contributions must protect the people represented by the data and keep the verification process auditable.

## Data rule

Only synthetic fixtures or explicitly reviewed, sanitized public data may be committed. Never commit Telegram credentials, API hashes, session files, raw media, copied posts, private notes, precise sensitive coordinates, or identifying information about ordinary people.

## Pull requests

Each pull request must:

1. Explain the user-visible change.
2. State its safety and privacy impact.
3. Include tests and the commands used to run them.
4. Include screenshots for visual changes in English, Arabic, desktop, and mobile layouts.
5. Identify deferred work without implying that synthetic records are live reporting.

Use Conventional Commits and keep `main` releasable.

## Verification

Write a failing test before production code, confirm the expected failure, implement the smallest passing change, then run the whole relevant suite. Source adapters must use local fixtures in CI and must never contact live accounts during tests.

