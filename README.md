# syOSINT

syOSINT is an open-source, bilingual situational-awareness workspace for journalists and OSINT researchers monitoring public reporting about Syria. It is designed around traceable evidence, human verification, explicit uncertainty, and safety-aware publication.

> **Current milestone:** The repository is building a public dashboard with clearly marked synthetic demonstration data. It does not yet collect live sources.

## Principles

- Public sources only; no private-channel access or access-control bypassing.
- Human review before publication.
- Confidence labels always include uncertainty and supporting sources.
- Precise sensitive locations and ordinary-person identities are withheld.
- Raw evidence, credentials, Telegram sessions, and private analyst notes stay outside Git.
- Telegram-derived content is never processed with AI or machine learning.

## Architecture

The first product milestone contains a versioned public-data schema and a statically exported Next.js dashboard. Later milestones add a local analyst desk, RSS collection, and a terms-compliant public Telegram adapter.

The approved documents are:

- [Product and architecture design](docs/superpowers/specs/2026-09-22-syosint-design.md)
- [Foundation and dashboard implementation plan](docs/superpowers/plans/2026-09-22-foundation-public-dashboard.md)

## Development

Use Node.js 24 and pnpm 10.

```bash
corepack enable
pnpm install
pnpm test
```

Additional commands will become available as the dashboard workspace is added.

## License

Source code is licensed under Apache-2.0. Public incident data has separate provenance and reuse requirements documented alongside the dataset.
