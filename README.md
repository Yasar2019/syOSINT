# syOSINT

syOSINT is an open-source, bilingual situational-awareness workspace for journalists and OSINT researchers monitoring public reporting about Syria. It is designed around traceable evidence, human verification, explicit uncertainty, and safety-aware publication.

> **Current milestone:** The public dashboard uses clearly marked synthetic demonstration data. Milestone 2 adds a private local analyst desk for manual source references, evidence review and staged public export. It does not collect live sources.

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
- Local SQLite evidence and audit trail, human safety review, exact sanitized preview, and explicit staged JSON export.

## Architecture

The public side is a statically exported Next.js application that consumes only a validated, versioned JSON dataset. Map geometry is bundled at build time. There is no dashboard backend and no client-side request to an external data or map service.

The local-only FastAPI service owns SQLite evidence and the human-gated export. The separate local Next.js desk calls the service server-side. Later milestones add RSS collection and a terms-compliant public Telegram adapter. Raw evidence never enters the static dashboard or Git repository.

The approved documents are:

- [Product and architecture design](docs/superpowers/specs/2026-09-22-syosint-design.md)
- [Foundation and dashboard implementation plan](docs/superpowers/plans/2026-09-22-foundation-public-dashboard.md)
- [Current project state](docs/PROJECT_STATE.md)
- [Roadmap](docs/ROADMAP.md)
- [Architectural decisions](docs/DECISIONS.md)
- [Agent handoff procedure](docs/AGENT_HANDOFF.md)
- [Analyst desk design](docs/superpowers/specs/2026-09-23-analyst-desk-design.md)
- [Analyst desk implementation plan](docs/superpowers/plans/2026-09-23-analyst-desk.md)

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
python3.12 -m venv .venv
.venv/bin/python -m pip install -e './services/collector-api[test]'
PYTHONPATH=services/collector-api .venv/bin/python -m pytest services/collector-api/tests -q
```

Run the dashboard locally:

```bash
corepack pnpm --dir apps/public-dashboard dev
```

Run the **private desk** in two terminals from the repository root:

```bash
PYTHONPATH=services/collector-api .venv/bin/python -m syosint
```

```bash
corepack pnpm --filter @syosint/analyst-desk dev
```

Open `http://127.0.0.1:3001`. Both processes listen on loopback only, and the API checks the local Host and mutation Origin. The API documentation is available locally at `http://127.0.0.1:8765/docs`. SQLite stays under gitignored `private-data/`. Back up that directory privately if you need to preserve evidence. An export writes a single-incident, schema-validated JSON dataset to gitignored `pending-exports/incident-ID.json`; it does **not** publish or change the live public dashboard. Exact coordinates are excluded from this release. You must separately review and intentionally publish approved data. Never commit source text, private notes, or local database files.

To exercise the workflow: register a public HTTPS source, create a bilingual case, attach a public report reference and local evidence, complete all public fields, move through `investigating` and `review-ready`, record human verification and safety checks, move to `approved`, examine the exact preview, and explicitly export. The desk deliberately locks approved cases against further evidence edits. Correction and withdrawal workflows remain future work; don't use this prototype to publish events needing changes after approval.

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

The [approved product design](docs/superpowers/specs/2026-09-22-syosint-design.md) defines the complete local-first system and safety model. Live RSS and Telegram collection are later milestones; the private desk accepts manual public references only.

## License

Source code is licensed under Apache-2.0. Demonstration incidents are fictional. Future public incident data will carry provenance and reuse requirements alongside the dataset.
