# syOSINT

syOSINT is an open-source, bilingual situational-awareness workspace for journalists and OSINT researchers monitoring public reporting about Syria. It is designed around traceable evidence, human verification, explicit uncertainty, and safety-aware publication.

> **Current milestone:** Milestone 2's private analyst desk is complete. Milestone 3 adds a reviewed RSS/Atom allowlist, a local collection inbox and an automatically refreshed public headline wire. The reviewed incident dataset remains synthetic until a human explicitly publishes approved incident records.

## Principles

- Public sources only; no private-channel access or access-control bypassing.
- Human review before publishing incidents or analyst-authored material. The only automatic-publication exception is minimal, unverified headline metadata from reviewed RSS/Atom feeds.
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
- Automatic public RSS/Atom headline collection every 30 minutes, with deterministic Syria-topic filters, safe fetching, bounded retention, and a separate **Unverified external reporting** display.
- Private RSS inbox with source health, quarantine, duplicate handling, and human promotion into the existing triage workflow.

## Architecture

The public side is a statically exported Next.js application that consumes validated, versioned JSON datasets. Map geometry is bundled at build time. There is no dashboard backend and no client-side request to an external data or map service. A scheduled GitHub Actions job fetches allowlisted feeds, projects only source/headline/time/link metadata, validates the wire, and redeploys the static site. New matching headlines normally appear within 30–35 minutes.

The local-only FastAPI service owns SQLite evidence, RSS intake, and the human-gated incident export. The separate local Next.js desk calls the service server-side. Raw feed bodies, evidence, analyst notes, and quarantined payloads never enter the static dashboard or Git repository. Telegram collection remains a later milestone.

The approved documents are:

- [Product and architecture design](docs/superpowers/specs/2026-09-22-syosint-design.md)
- [Foundation and dashboard implementation plan](docs/superpowers/plans/2026-09-22-foundation-public-dashboard.md)
- [Current project state](docs/PROJECT_STATE.md)
- [Roadmap](docs/ROADMAP.md)
- [Architectural decisions](docs/DECISIONS.md)
- [Agent handoff procedure](docs/AGENT_HANDOFF.md)
- [Analyst desk design](docs/superpowers/specs/2026-09-23-analyst-desk-design.md)
- [Analyst desk implementation plan](docs/superpowers/plans/2026-09-23-analyst-desk.md)
- [RSS collection design](docs/superpowers/specs/2026-09-23-rss-collection-design.md)
- [RSS operating and source policy](docs/source-policy/RSS.md)
- [Methodology](docs/methodology/METHODOLOGY.md)

## Development

Use Node.js 24, pnpm 10, and the latest stable Python 3.14 patch release. Python 3.15 prereleases are not supported. On Windows, install Python 3.14 first, then use `py -3.14` in place of `python3.14` below.

```bash
corepack enable
corepack pnpm install
corepack pnpm policy:check
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
python3.14 -m venv .venv314
.venv314/bin/python -m pip install -e './services/collector-api[test]' pip-audit
.venv314/bin/python -m pytest services/collector-api/tests -q
.venv314/bin/python -m pip_audit --local
```

Run the dashboard locally:

```bash
corepack pnpm --dir apps/public-dashboard dev
```

Run the **private desk** in two terminals from the repository root:

```bash
.venv314/bin/python -m syosint
```

```bash
corepack pnpm --filter @syosint/analyst-desk dev
```

Open `http://127.0.0.1:3001`. Both processes listen on loopback only, and the API checks the local Host and mutation Origin. The API documentation is available locally at `http://127.0.0.1:8765/docs`. SQLite stays under gitignored `private-data/`. Back up that directory privately if you need to preserve evidence. An export writes a single-incident, schema-validated JSON dataset to gitignored `pending-exports/incident-ID.json`; it does **not** publish or change the live public dashboard. Exact coordinates are excluded from this release. You must separately review and intentionally publish approved data. Never commit source text, private notes, or local database files.

Open `http://127.0.0.1:3001/rss` to register a public HTTPS RSS/Atom feed, inspect source health, run an immediate collection, and review new, duplicate, promoted, attached, or quarantined records. The scheduler runs while the API is running and polls enabled sources at their configured interval (30 minutes by default). Set `SYOSINT_RSS_SCHEDULER=0` only for controlled tests.

To exercise the reviewed-incident workflow: promote a collected item or register a public HTTPS source manually, create a bilingual case, attach evidence, complete all public fields, move through `investigating` and `review-ready`, record human verification and safety checks, move to `approved`, examine the exact preview, and explicitly export. Promotion never invents a summary, category, confidence, or location. The desk deliberately locks approved cases against further evidence edits. Correction and withdrawal workflows remain future work; don't use this prototype to publish events needing changes after approval.

To test the public collector locally without changing the checked-in dataset:

```bash
.venv314/bin/python -m syosint.rss_cli check-source https://news.un.org/feed/subscribe/en/news/region/middle-east/feed/rss.xml
.venv314/bin/python -m syosint.rss_cli collect-public --config config/rss-sources.json --output /tmp/news-wire.v1.json
.venv314/bin/python -m json.tool /tmp/news-wire.v1.json
```

Live checks require normal public DNS and HTTPS access. Routine tests use local fixtures and do not contact publishers.

Browser verification requires a local Chromium installation:

```bash
corepack pnpm --dir apps/public-dashboard exec playwright install chromium
corepack pnpm test:e2e
```

## Safety and legal boundaries

syOSINT is for lawful public-source research. It does not authorize private-group access, access-control bypassing, person tracking, facial recognition, doxxing, or the publication of precise live tactical locations. It never republishes complete source articles or Telegram posts. Telegram-derived material is excluded from AI and machine-learning processing.

The bundled boundary geometry provides geographic context and expresses no legal or political position. See [NOTICE.md](NOTICE.md) and the [security policy](SECURITY.md).

## GitHub Pages

After merging to `main`, select **Settings → Pages → Source → GitHub Actions**. CI-gated pushes deploy the reviewed repository state. The `Refresh RSS News Wire` workflow also runs every 30 minutes and can be dispatched manually; it collects the allowlist, retains valid recent entries from the last deployed wire when appropriate, validates both public contracts, and publishes `apps/public-dashboard/out` under `/syOSINT/`. A failed collection, validation, or build does not replace the last successful Pages artifact.

## Roadmap

The [approved product design](docs/superpowers/specs/2026-09-22-syosint-design.md) defines the complete local-first system and safety model. RSS collection is implemented in Milestone 3. Terms-compliant public Telegram collection is Milestone 4 and remains unimplemented.

## License

Source code is licensed under Apache-2.0. Demonstration incidents are fictional. News-wire entries link to external publishers and retain their source attribution; syOSINT does not claim ownership of publisher headlines or articles. Future public incident data will carry provenance and reuse requirements alongside the dataset.
