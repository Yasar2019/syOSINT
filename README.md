# syOSINT

syOSINT is an open-source, bilingual situational-awareness workspace for journalists and OSINT researchers monitoring public reporting about Syria. It is designed around traceable evidence, human verification, explicit uncertainty, and safety-aware publication.

> **Current milestone:** The repository contains a working public dashboard with clearly marked synthetic demonstration data. It does not collect live sources.

## Principles

- Public sources only; no private-channel access or access-control bypassing.
- Human review before publication.
- Confidence labels always include uncertainty and supporting sources.
- Precise sensitive locations and ordinary-person identities are withheld.
- Raw evidence, credentials, Telegram sessions, and private analyst notes stay outside Git.
- Telegram-derived content is never processed with AI or machine learning.

## What works today

- Static English/Arabic dashboard with RTL switching.
- Category, confidence, and text filters that update the map, timeline, and feed together.
- Accessible incident detail with uncertainty, public references, and correction history.
- Bundled Natural Earth-derived Syria geometry with no map tile or paid service calls.
- Strict public-data validation and synthetic fixtures covering all confidence labels and incident categories.
- Automated unit, policy, browser, static-export, and GitHub Pages checks.

## Architecture

The public side is a statically exported Next.js application that consumes only a validated, versioned JSON dataset. Map geometry is bundled at build time. There is no dashboard backend and no client-side request to an external data or map service.

Later milestones add a local-only analyst desk, SQLite evidence vault, source registry, RSS collection, a terms-compliant public Telegram adapter, and an explicit safety-gated export step. Raw evidence never enters the static dashboard or Git repository.

The approved documents are:

- [Product and architecture design](docs/superpowers/specs/2026-09-22-syosint-design.md)
- [Foundation and dashboard implementation plan](docs/superpowers/plans/2026-09-22-foundation-public-dashboard.md)
- [Current project state](docs/PROJECT_STATE.md)
- [Roadmap](docs/ROADMAP.md)
- [Architectural decisions](docs/DECISIONS.md)
- [Agent handoff procedure](docs/AGENT_HANDOFF.md)

## Development

Use Node.js 24 and pnpm 10.

```bash
corepack enable
corepack pnpm install
corepack pnpm policy:check
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
```

Run the dashboard locally:

```bash
corepack pnpm --dir apps/public-dashboard dev
```

Browser verification requires a local Chromium installation:

```bash
corepack pnpm --dir apps/public-dashboard exec playwright install chromium
corepack pnpm test:e2e
```

## Safety and legal boundaries

syOSINT is for lawful public-source research. It does not authorize private-group access, access-control bypassing, person tracking, facial recognition, doxxing, or the publication of precise live tactical locations. It never republishes complete source articles or Telegram posts. Telegram-derived material is excluded from AI and machine-learning processing.

The bundled boundary geometry provides geographic context and expresses no legal or political position. See [NOTICE.md](NOTICE.md) and the [security policy](SECURITY.md).

## GitHub Pages

After merging to `main`, select **Settings → Pages → Source → GitHub Actions**. CI must succeed before the deployment workflow publishes `apps/public-dashboard/out` under the `/syOSINT/` repository path.

## Roadmap

The [approved product design](docs/superpowers/specs/2026-09-22-syosint-design.md) defines the complete local-first system and safety model. The [foundation and public dashboard plan](docs/superpowers/plans/2026-09-22-foundation-public-dashboard.md) records this first implementation slice. Collector, analyst-desk, and live-data work is deliberately deferred.

## License

Source code is licensed under Apache-2.0. Demonstration incidents are fictional. Future public incident data will carry provenance and reuse requirements alongside the dataset.
