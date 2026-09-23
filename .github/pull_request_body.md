## Summary

- establishes the Apache-2.0 monorepo, contribution policy, security policy, and secret scanning;
- adds a strict versioned public incident schema and six bilingual synthetic fixtures;
- launches a responsive English/Arabic dashboard with RTL support, filters, confidence labels, correction history, incident detail, a bundled Syria map, and an activity timeline;
- adds a bilingual methodology page, unit/browser tests, CI, and GitHub Pages deployment from `main`.

## Safety and data boundaries

- All displayed incidents are fictional synthetic demonstration data.
- The public export contains no raw evidence, private notes, credentials, session material, precise tactical locations, or ordinary-person identifiers.
- Locations are generalized or withheld by schema and map eligibility rules.
- Publication remains a human decision with visible confidence and uncertainty.
- No collector is included in this pull request. RSS and Telegram work is explicitly deferred.
- Future Telegram collection is limited to approved public channels through the official API, read-only, and Telegram-derived material must never be processed by AI/ML systems.

## Verification

- [x] `pnpm policy:check`
- [x] `pnpm lint`
- [x] `pnpm typecheck`
- [x] `pnpm test`
- [x] `pnpm build`
- [x] GitHub Pages base-path export assertion
- [ ] `pnpm test:e2e` locally — Chromium download is blocked by the authoring workspace network allowlist; CI installs Chromium and runs the same three tests.

## Visual review

- Desktop English: pending capture in an environment with Chromium.
- Mobile English: pending capture in an environment with Chromium.
- Desktop Arabic/RTL: pending capture in an environment with Chromium.

No synthetic screenshot is attached in place of a real browser capture.

## Deployment impact

After merge, enable **Settings → Pages → Source → GitHub Actions**. A successful CI run on `main` triggers the Pages workflow and deploys the static export under `/syOSINT/`.

## Deferred

The local analyst desk, evidence vault, source registry, RSS collector, public Telegram adapter, safety-gated exporter, and live data operations remain future milestones described in the approved design.
