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

Before opening a pull request, run:

```bash
corepack pnpm install --frozen-lockfile
corepack pnpm policy:check
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
corepack pnpm test:e2e
```

The browser suite builds and serves the static export on `127.0.0.1`. Tests must not make requests to live sources, Telegram, analytics, paid services, or external map providers.

## Dashboard changes

Keep English and Arabic behavior equivalent, preserve logical CSS properties for RTL layouts, and test keyboard access at desktop and mobile sizes. Do not introduce remote fonts, map tiles, analytics, tracking pixels, or runtime dependencies on a third-party service.

For GitHub Pages changes, also verify the repository base path:

```bash
GITHUB_ACTIONS=true corepack pnpm build
grep -E '(/syOSINT/_next/|href="/syOSINT/)' apps/public-dashboard/out/index.html
```
