# syOSINT Foundation and Public Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Deliver the first visible syOSINT product: a tested bilingual static situational-awareness dashboard using synthetic data, a bundled Syria map, explicit confidence and correction information, and automated GitHub Pages deployment.

**Architecture:** A pnpm monorepo contains a versioned public-data schema package and one Next.js static-export application. Public incidents are validated at build time, rendered entirely from safe synthetic JSON, and filtered in a client-side dashboard; no collector, private database, Telegram session, AI processing, or server runtime is introduced in this plan.

**Tech Stack:** Node.js 24 LTS, pnpm 10, Next.js 16, React 19, TypeScript 5.9, Ajv 8, Vitest 3, Testing Library 16, Playwright 1, d3-geo 3, world-atlas 2, topojson-client 3, CSS Modules/global CSS, GitHub Actions, GitHub Pages.

**Spec:** docs/superpowers/specs/2026-09-22-syosint-design.md

## Global Constraints

- The site must be a static Next.js export hosted from the public GitHub repository through GitHub Pages.
- Arabic and English ship together; Arabic uses right-to-left layout and changing language preserves current filters.
- The repository contains only source code, documentation, synthetic fixtures, and sanitized public JSON.
- Every demonstration incident must be visibly labeled synthetic and must not identify or resemble a real vulnerable person.
- No paid API, runtime database, authentication service, external tile server, Telegram credential, raw evidence, or AI feature is introduced.
- Source reliability and claim confidence remain separate concepts.
- Public incidents use the exact confidence labels Unverified, Developing, Corroborated, Verified, Disputed, and False.
- Status and confidence are never conveyed by color alone.
- The map uses bundled Natural Earth-derived data and generalized synthetic coordinates.
- User-controlled or source-derived strings render as text, never injected HTML.
- WCAG 2.2 AA contrast, keyboard operation, visible focus, semantic landmarks, and reduced-motion support are required.
- main remains releasable; implementation occurs on a feature branch and enters through a pull request.

## Review Focus

1. Malformed or private-looking fields in public JSON must fail validation and stop the build; Task 2 adds rejection tests and Task 8 runs them in CI.
2. Arabic content missing from any public incident must fail validation rather than silently fall back to English; Task 2 adds a bilingual-required test.
3. Coordinates outside the Syria display bounds must remain in the feed but must not produce a map marker; Task 6 adds the boundary-condition test.
4. HTML-like text in titles, summaries, and source labels must render literally and never become executable markup; Task 5 adds the hostile-string rendering test.
5. GitHub Pages project-path deployment must emit working links and assets under /syOSINT/ while local development remains rooted at /; Task 4 adds the configuration test and Task 8 verifies the exported files.

---

## File map

### Root

- package.json — workspace commands and pinned package manager.
- pnpm-workspace.yaml — workspace package discovery.
- tsconfig.base.json — shared strict TypeScript settings.
- vitest.workspace.ts — workspace test discovery.
- .nvmrc — Node 24 runtime declaration.
- .editorconfig — cross-platform text settings.
- .gitignore — blocks credentials, sessions, databases, evidence, logs, caches, and build output.
- LICENSE — Apache-2.0 text.
- README.md — product purpose, safety boundaries, setup, commands, and roadmap.
- CONTRIBUTING.md — pull-request, test, synthetic-data, and safety rules.
- SECURITY.md — private vulnerability-reporting guidance and prohibited data handling.
- NOTICE.md — Natural Earth/world-atlas attribution and boundary disclaimer.

### Public schema package

- packages/schemas/package.json — schema package metadata and scripts.
- packages/schemas/tsconfig.json — package compiler settings.
- packages/schemas/src/public-incident.schema.json — JSON Schema 2020-12 contract.
- packages/schemas/src/types.ts — TypeScript public-data types.
- packages/schemas/src/validate.ts — Ajv validator and typed result.
- packages/schemas/src/index.ts — stable public exports.
- packages/schemas/src/validate.test.ts — valid and hostile/invalid dataset tests.

### Public dataset

- data/public/incidents.v1.json — explicitly synthetic bilingual incident fixtures.
- data/public/README.md — data contract, synthetic labeling, and prohibition on raw evidence.

### Dashboard application

- apps/public-dashboard/package.json — app dependencies and commands.
- apps/public-dashboard/next.config.ts — static export and GitHub Pages base path.
- apps/public-dashboard/next.config.test.ts — local versus Actions path behavior.
- apps/public-dashboard/tsconfig.json — app compiler settings.
- apps/public-dashboard/vitest.config.ts — jsdom and test setup.
- apps/public-dashboard/src/test/setup.ts — Testing Library cleanup and matchers.
- apps/public-dashboard/src/app/layout.tsx — metadata and root document.
- apps/public-dashboard/src/app/page.tsx — validated build-time data entry.
- apps/public-dashboard/src/app/methodology/page.tsx — methodology, safety, and map disclaimer.
- apps/public-dashboard/src/app/globals.css — tokens, responsive layout, focus, RTL, and reduced motion.
- apps/public-dashboard/src/i18n/types.ts — Locale and dictionary types.
- apps/public-dashboard/src/i18n/en.ts — English interface copy.
- apps/public-dashboard/src/i18n/ar.ts — Arabic interface copy.
- apps/public-dashboard/src/i18n/get-dictionary.ts — exhaustive locale resolver.
- apps/public-dashboard/src/lib/load-public-dataset.ts — build-time JSON validation.
- apps/public-dashboard/src/lib/filter-incidents.ts — pure filtering and ordering.
- apps/public-dashboard/src/lib/filter-incidents.test.ts — filter and unknown-input tests.
- apps/public-dashboard/src/lib/map.ts — Syria feature extraction, projection, and marker eligibility.
- apps/public-dashboard/src/lib/map.test.ts — Syria extraction and coordinate tests.
- apps/public-dashboard/src/components/DashboardClient.tsx — locale, filter, and selection state.
- apps/public-dashboard/src/components/Header.tsx — title, update time, and language control.
- apps/public-dashboard/src/components/DemoBanner.tsx — persistent synthetic-data warning.
- apps/public-dashboard/src/components/FilterBar.tsx — accessible search/category/confidence controls.
- apps/public-dashboard/src/components/SummaryCards.tsx — aggregate counts.
- apps/public-dashboard/src/components/IncidentFeed.tsx — ordered incident list.
- apps/public-dashboard/src/components/IncidentCard.tsx — concise incident presentation.
- apps/public-dashboard/src/components/IncidentDetail.tsx — expanded sources, uncertainty, and corrections.
- apps/public-dashboard/src/components/ConfidenceBadge.tsx — text/icon confidence presentation.
- apps/public-dashboard/src/components/SyriaMap.tsx — local boundary and safe markers.
- apps/public-dashboard/src/components/Timeline.tsx — chronological activity view.
- apps/public-dashboard/src/components/DashboardClient.test.tsx — filtering, locale, selection, and hostile-text tests.
- apps/public-dashboard/e2e/dashboard.spec.ts — keyboard, RTL, filtering, methodology, and exported-path checks.
- apps/public-dashboard/playwright.config.ts — production-build browser test configuration.

### Automation

- .github/workflows/ci.yml — install, policy scan, lint, type check, unit test, build, and browser test.
- .github/workflows/deploy-pages.yml — main-only static artifact deployment.

---

### Task 1: Repository foundation and safety policy

**Files:**
- Create: package.json
- Create: pnpm-workspace.yaml
- Create: tsconfig.base.json
- Create: vitest.workspace.ts
- Create: .nvmrc
- Create: .editorconfig
- Create: .gitignore
- Create: LICENSE
- Create: README.md
- Create: CONTRIBUTING.md
- Create: SECURITY.md
- Create: NOTICE.md
- Test: tests/repository-policy.test.ts

**Interfaces:**
- Consumes: approved design at docs/superpowers/specs/2026-09-22-syosint-design.md.
- Produces: root commands pnpm lint, pnpm typecheck, pnpm test, pnpm build, pnpm test:e2e, and pnpm policy:check; workspace paths apps/* and packages/*.

- [ ] **Step 1: Create the feature branch**

Run:

~~~bash
git switch -c feat/foundation-public-dashboard
~~~

Expected: the active branch is feat/foundation-public-dashboard and main remains unchanged.

- [ ] **Step 2: Write the failing repository-policy test**

Create tests/repository-policy.test.ts:

~~~ts
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const gitignore = readFileSync(".gitignore", "utf8");

describe("repository safety policy", () => {
  it.each([
    ".env",
    "*.session",
    "*.sqlite",
    "evidence/",
    "raw-media/",
    "*.log",
    ".next/",
    "out/",
  ])("ignores %s", (entry) => {
    expect(gitignore).toContain(entry);
  });

  it("documents that only synthetic or sanitized public data belongs in Git", () => {
    const contributing = readFileSync("CONTRIBUTING.md", "utf8");
    expect(contributing).toContain("synthetic");
    expect(contributing).toContain("sanitized public data");
    expect(contributing).toContain("Never commit Telegram credentials");
  });
});
~~~

- [ ] **Step 3: Add the root toolchain and run the test to prove it fails**

Create package.json with packageManager set to pnpm@10.17.1, engines.node set to >=24 <25, private set to true, and these scripts:

~~~json
{
  "scripts": {
    "build": "pnpm --filter @syosint/public-dashboard build",
    "lint": "pnpm -r lint",
    "typecheck": "pnpm -r typecheck",
    "test": "vitest run --workspace vitest.workspace.ts",
    "test:e2e": "pnpm --filter @syosint/public-dashboard test:e2e",
    "policy:check": "secretlint "**/*" --secretlintignore .gitignore"
  }
}
~~~

Add root devDependencies for TypeScript 5.9, Vitest 3, secretlint 10, and @secretlint/secretlint-rule-preset-recommend 10. Create pnpm-workspace.yaml for apps/* and packages/*, strict tsconfig.base.json, and vitest.workspace.ts including tests/**/*.test.ts and workspace configurations.

Run:

~~~bash
corepack enable
pnpm install
pnpm exec vitest run tests/repository-policy.test.ts
~~~

Expected: FAIL because .gitignore and policy documents do not exist.

- [ ] **Step 4: Implement repository policy files**

Create .gitignore containing, at minimum:

~~~gitignore
.env
.env.*
!.env.example
*.session
*.session-journal
*.sqlite
*.sqlite3
evidence/
raw-media/
private-data/
pending-exports/
*.log
.next/
out/
coverage/
playwright-report/
test-results/
node_modules/
.DS_Store
~~~

Create .nvmrc with 24, an EditorConfig using UTF-8/LF/final-newline, Apache-2.0 LICENSE text, and focused README/CONTRIBUTING/SECURITY/NOTICE documents. NOTICE.md must state that the map geometry comes through world-atlas from Natural Earth public-domain data and that displayed boundaries are contextual, not a legal position.

- [ ] **Step 5: Run the policy test and secret scan**

Run:

~~~bash
pnpm exec vitest run tests/repository-policy.test.ts
pnpm policy:check
~~~

Expected: both commands PASS with no detected secret.

- [ ] **Step 6: Commit the foundation**

~~~bash
git add package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json vitest.workspace.ts .nvmrc .editorconfig .gitignore LICENSE README.md CONTRIBUTING.md SECURITY.md NOTICE.md tests/repository-policy.test.ts
git commit -m "chore: establish repository safety foundation"
~~~

### Task 2: Versioned public incident schema

**Files:**
- Create: packages/schemas/package.json
- Create: packages/schemas/tsconfig.json
- Create: packages/schemas/src/public-incident.schema.json
- Create: packages/schemas/src/types.ts
- Create: packages/schemas/src/validate.ts
- Create: packages/schemas/src/index.ts
- Test: packages/schemas/src/validate.test.ts

**Interfaces:**
- Consumes: no application interfaces.
- Produces: PublicDataset, PublicIncident, IncidentCategory, ConfidenceLabel, IncidentStatus, PublicSourceReference, ValidationResult, and validatePublicDataset(value: unknown): ValidationResult.

- [ ] **Step 1: Write failing validator tests**

Create packages/schemas/src/validate.test.ts with these cases:

~~~ts
import { describe, expect, it } from "vitest";
import { validatePublicDataset } from "./validate";

const valid = {
  schemaVersion: "1.0.0",
  generatedAt: "2026-09-22T16:00:00Z",
  synthetic: true,
  incidents: [{
    id: "demo-001",
    status: "published",
    categories: ["infrastructure"],
    confidence: "developing",
    occurredAt: "2026-09-22T12:00:00Z",
    updatedAt: "2026-09-22T13:00:00Z",
    location: {
      en: "Synthetic Northern District",
      ar: "منطقة شمالية تجريبية",
      latitude: 35.1,
      longitude: 38.2,
      precision: "governorate"
    },
    title: { en: "[DEMO] Infrastructure exercise", ar: "[تجريبي] تمرين للبنية التحتية" },
    summary: { en: "Synthetic demonstration record.", ar: "سجل توضيحي تجريبي." },
    uncertainty: { en: "No real event is represented.", ar: "لا يمثل هذا أي حدث حقيقي." },
    sourceCount: 1,
    sources: [{
      id: "demo-source-1",
      label: { en: "Synthetic source", ar: "مصدر تجريبي" },
      url: "https://example.com/demo",
      publishedAt: "2026-09-22T12:00:00Z"
    }],
    corrections: []
  }]
};

describe("validatePublicDataset", () => {
  it("accepts the complete bilingual synthetic dataset", () => {
    expect(validatePublicDataset(valid)).toEqual({ ok: true, data: valid });
  });

  it("rejects a missing Arabic summary", () => {
    const input = structuredClone(valid);
    delete (input.incidents[0].summary as { ar?: string }).ar;
    const result = validatePublicDataset(input);
    expect(result.ok).toBe(false);
  });

  it.each(["rawText", "privateNotes", "telegramSession", "localMediaPath"])(
    "rejects forbidden field %s",
    (field) => {
      const input = structuredClone(valid) as Record<string, unknown>;
      (input.incidents as Array<Record<string, unknown>>)[0][field] = "secret";
      expect(validatePublicDataset(input).ok).toBe(false);
    }
  );

  it("rejects a dataset that is not explicitly synthetic in this milestone", () => {
    expect(validatePublicDataset({ ...valid, synthetic: false }).ok).toBe(false);
  });
});
~~~

- [ ] **Step 2: Run the test to verify it fails**

Run:

~~~bash
pnpm --dir packages/schemas test
~~~

Expected: FAIL because validate.ts and the package configuration do not exist.

- [ ] **Step 3: Define exact TypeScript types**

Create packages/schemas/src/types.ts with string unions:

~~~ts
export type IncidentCategory =
  | "armed-conflict"
  | "political-security"
  | "humanitarian"
  | "infrastructure"
  | "border-crossing"
  | "disinformation";

export type ConfidenceLabel =
  | "unverified"
  | "developing"
  | "corroborated"
  | "verified"
  | "disputed"
  | "false";

export type IncidentStatus =
  | "published"
  | "corrected"
  | "withdrawn";

export type LocalizedText = { en: string; ar: string };

export interface PublicSourceReference {
  id: string;
  label: LocalizedText;
  url: string;
  publishedAt: string;
}

export interface PublicCorrection {
  correctedAt: string;
  reason: LocalizedText;
  changedFields: string[];
}

export interface PublicIncident {
  id: string;
  status: IncidentStatus;
  categories: IncidentCategory[];
  confidence: ConfidenceLabel;
  occurredAt: string;
  updatedAt: string;
  location: LocalizedText & {
    latitude?: number;
    longitude?: number;
    precision: "country" | "governorate" | "district" | "withheld";
  };
  title: LocalizedText;
  summary: LocalizedText;
  uncertainty: LocalizedText;
  sourceCount: number;
  sources: PublicSourceReference[];
  corrections: PublicCorrection[];
}

export interface PublicDataset {
  schemaVersion: "1.0.0";
  generatedAt: string;
  synthetic: true;
  incidents: PublicIncident[];
}
~~~

- [ ] **Step 4: Add strict JSON Schema and validator**

Create public-incident.schema.json using JSON Schema draft 2020-12. Set additionalProperties: false at the dataset, incident, location, localized text, source, and correction levels. Require both en and ar with minLength: 1. Constrain latitude to -90..90, longitude to -180..180, URL to https, sourceCount to a non-negative integer, incidents to unique IDs by application test, and synthetic to const: true.

Create validate.ts:

~~~ts
import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import schema from "./public-incident.schema.json";
import type { PublicDataset } from "./types";

export type ValidationResult =
  | { ok: true; data: PublicDataset }
  | { ok: false; errors: string[] };

const ajv = new Ajv2020({ allErrors: true, strict: true });
addFormats(ajv);
const validate = ajv.compile<PublicDataset>(schema);

export function validatePublicDataset(value: unknown): ValidationResult {
  if (validate(value)) {
    const ids = value.incidents.map((incident) => incident.id);
    if (new Set(ids).size !== ids.length) {
      return { ok: false, errors: ["incident ids must be unique"] };
    }
    return { ok: true, data: value };
  }

  return {
    ok: false,
    errors: (validate.errors ?? []).map(
      (error) => (error.instancePath || "/") + " " + error.message
    ),
  };
}
~~~

Export all stable interfaces from index.ts. Configure resolveJsonModule and declaration output in the package tsconfig. Add Ajv 8 and ajv-formats 3 as dependencies.

- [ ] **Step 5: Run schema tests and type checking**

Run:

~~~bash
pnpm --dir packages/schemas test
pnpm --dir packages/schemas typecheck
~~~

Expected: all validator tests PASS and TypeScript reports no error.

- [ ] **Step 6: Commit the schema package**

~~~bash
git add packages/schemas
git commit -m "feat: define safe public incident schema"
~~~

### Task 3: Synthetic dataset and pure dashboard domain logic

**Files:**
- Create: data/public/incidents.v1.json
- Create: data/public/README.md
- Create: apps/public-dashboard/src/lib/load-public-dataset.ts
- Create: apps/public-dashboard/src/lib/filter-incidents.ts
- Test: apps/public-dashboard/src/lib/load-public-dataset.test.ts
- Test: apps/public-dashboard/src/lib/filter-incidents.test.ts

**Interfaces:**
- Consumes: validatePublicDataset(value) and PublicDataset/PublicIncident from @syosint/schemas.
- Produces: loadPublicDataset(): PublicDataset, DashboardFilters, EMPTY_FILTERS, filterIncidents(incidents, filters): PublicIncident[], and countByConfidence(incidents): Record<ConfidenceLabel, number>.

- [ ] **Step 1: Write failing loader and filter tests**

Create tests proving that loadPublicDataset returns six or more records, covers all six categories and all six confidence labels, and every English title begins [DEMO] while every Arabic title begins [تجريبي].

Create filter-incidents.test.ts:

~~~ts
import { describe, expect, it } from "vitest";
import { filterIncidents } from "./filter-incidents";
import { loadPublicDataset } from "./load-public-dataset";

const incidents = loadPublicDataset().incidents;

describe("filterIncidents", () => {
  it("combines category, confidence, and bilingual search filters", () => {
    const result = filterIncidents(incidents, {
      categories: ["infrastructure"],
      confidence: ["developing"],
      search: "تجريبي",
    });
    expect(result.every((item) => item.categories.includes("infrastructure"))).toBe(true);
    expect(result.every((item) => item.confidence === "developing")).toBe(true);
  });

  it("sorts newest occurrence first without mutating input", () => {
    const before = incidents.map((item) => item.id);
    const result = filterIncidents(incidents, {
      categories: [],
      confidence: [],
      search: "",
    });
    expect(incidents.map((item) => item.id)).toEqual(before);
    expect(Date.parse(result[0].occurredAt)).toBeGreaterThanOrEqual(
      Date.parse(result.at(-1)!.occurredAt)
    );
  });

  it("returns no records for an unmatched query", () => {
    expect(filterIncidents(incidents, {
      categories: [],
      confidence: [],
      search: "no-such-synthetic-record",
    })).toEqual([]);
  });
});
~~~

- [ ] **Step 2: Run tests to verify failure**

Run:

~~~bash
pnpm exec vitest run apps/public-dashboard/src/lib
~~~

Expected: FAIL because the dashboard package, dataset, and functions do not exist.

- [ ] **Step 3: Create the validated synthetic dataset**

Create data/public/incidents.v1.json with at least six incidents. Use one record per primary category, cover every confidence label, use only demonstration descriptions, no casualty claims, no names, no real source reporting, and example.com source URLs. Include one corrected record and one withdrawn record so the UI can demonstrate revision semantics.

Create data/public/README.md stating:

- every committed record is synthetic until the collector/publisher milestone is delivered;
- raw posts, copied articles, personal data, local paths, session data, and private notes are prohibited;
- all changes must pass @syosint/schemas validation.

- [ ] **Step 4: Implement strict loading and pure filtering**

load-public-dataset.ts must import the JSON, call validatePublicDataset, and throw a message beginning Invalid public dataset: followed by joined schema errors when validation fails.

filter-incidents.ts must normalize search with trim().toLocaleLowerCase(), search both languages plus both location labels, apply selected categories as an any-category match, apply confidence as an allowed-set match, copy before sorting, and order descending by occurredAt then id.

- [ ] **Step 5: Run focused tests**

Run:

~~~bash
pnpm exec vitest run apps/public-dashboard/src/lib
~~~

Expected: loader and filter tests PASS.

- [ ] **Step 6: Commit dataset and domain logic**

~~~bash
git add data/public apps/public-dashboard/src/lib
git commit -m "feat: add synthetic incident dataset and filters"
~~~

### Task 4: Static Next.js shell and bilingual direction handling

**Files:**
- Create: apps/public-dashboard/package.json
- Create: apps/public-dashboard/next.config.ts
- Create: apps/public-dashboard/next.config.test.ts
- Create: apps/public-dashboard/tsconfig.json
- Create: apps/public-dashboard/vitest.config.ts
- Create: apps/public-dashboard/src/test/setup.ts
- Create: apps/public-dashboard/src/app/layout.tsx
- Create: apps/public-dashboard/src/i18n/types.ts
- Create: apps/public-dashboard/src/i18n/en.ts
- Create: apps/public-dashboard/src/i18n/ar.ts
- Create: apps/public-dashboard/src/i18n/get-dictionary.ts
- Test: apps/public-dashboard/src/i18n/get-dictionary.test.ts

**Interfaces:**
- Consumes: workspace TypeScript and test configuration.
- Produces: nextConfig, Locale = "en" | "ar", Dictionary, getDictionary(locale): Dictionary, and getDirection(locale): "ltr" | "rtl".

- [ ] **Step 1: Write failing configuration and dictionary tests**

next.config.test.ts:

~~~ts
import { describe, expect, it, vi } from "vitest";

describe("Next.js deployment paths", () => {
  it("uses no base path locally", async () => {
    vi.stubEnv("GITHUB_ACTIONS", "");
    vi.resetModules();
    const { default: config } = await import("./next.config");
    expect(config.basePath).toBe("");
    expect(config.output).toBe("export");
  });

  it("uses the repository path in GitHub Actions", async () => {
    vi.stubEnv("GITHUB_ACTIONS", "true");
    vi.resetModules();
    const { default: config } = await import("./next.config");
    expect(config.basePath).toBe("/syOSINT");
    expect(config.assetPrefix).toBe("/syOSINT");
  });
});
~~~

get-dictionary.test.ts must assert getDirection("ar") is rtl, getDirection("en") is ltr, and both dictionaries contain identical keys.

- [ ] **Step 2: Run tests to verify failure**

Run:

~~~bash
pnpm --filter @syosint/public-dashboard test -- next.config src/i18n
~~~

Expected: FAIL because configuration and dictionaries do not exist.

- [ ] **Step 3: Configure a static GitHub Pages application**

Create next.config.ts:

~~~ts
import type { NextConfig } from "next";

const inGitHubActions = process.env.GITHUB_ACTIONS === "true";
const basePath = inGitHubActions ? "/syOSINT" : "";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  basePath,
  assetPrefix: basePath,
  images: { unoptimized: true },
  reactStrictMode: true,
  transpilePackages: ["@syosint/schemas"],
};

export default nextConfig;
~~~

Create the app package with Next 16, React 19, React DOM 19, @syosint/schemas workspace dependency, and test/dev dependencies. Scripts must include dev, build, lint, typecheck, test, and test:e2e.

- [ ] **Step 4: Implement typed dictionaries and root metadata**

Define a Dictionary interface with keys for navigation, demonstration warning, filters, categories, confidence labels, summary cards, empty state, incident detail, sources, uncertainty, corrections, map, timeline, methodology, and accessibility labels.

Make en.ts the canonical object and type ar.ts with satisfies Dictionary so missing Arabic interface copy fails TypeScript. getDictionary uses an exhaustive switch. Root layout sets metadata title to syOSINT — Syria Open-Source Situation Monitor and description to a public-source, human-verified demonstration dashboard.

- [ ] **Step 5: Run configuration, dictionary, and type tests**

Run:

~~~bash
pnpm --filter @syosint/public-dashboard test -- next.config src/i18n
pnpm --filter @syosint/public-dashboard typecheck
~~~

Expected: all tests PASS and no dictionary key is missing.

- [ ] **Step 6: Commit the app shell**

~~~bash
git add apps/public-dashboard
git commit -m "feat: scaffold bilingual static dashboard"
~~~

### Task 5: Accessible feed, filters, and incident detail

**Files:**
- Create: apps/public-dashboard/src/components/DashboardClient.tsx
- Create: apps/public-dashboard/src/components/Header.tsx
- Create: apps/public-dashboard/src/components/DemoBanner.tsx
- Create: apps/public-dashboard/src/components/FilterBar.tsx
- Create: apps/public-dashboard/src/components/SummaryCards.tsx
- Create: apps/public-dashboard/src/components/IncidentFeed.tsx
- Create: apps/public-dashboard/src/components/IncidentCard.tsx
- Create: apps/public-dashboard/src/components/IncidentDetail.tsx
- Create: apps/public-dashboard/src/components/ConfidenceBadge.tsx
- Test: apps/public-dashboard/src/components/DashboardClient.test.tsx

**Interfaces:**
- Consumes: PublicDataset/PublicIncident, Locale/Dictionary, filterIncidents, and countByConfidence.
- Produces: DashboardClient({ dataset }: { dataset: PublicDataset }): JSX.Element and presentational child components with typed props.

- [ ] **Step 1: Write failing interaction and hostile-text tests**

Create DashboardClient.test.tsx covering:

~~~tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DashboardClient } from "./DashboardClient";
import { loadPublicDataset } from "../lib/load-public-dataset";

describe("DashboardClient", () => {
  it("filters by category and announces the result count", () => {
    render(<DashboardClient dataset={loadPublicDataset()} />);
    fireEvent.click(screen.getByRole("checkbox", { name: /infrastructure/i }));
    expect(screen.getByRole("status")).toHaveTextContent(/incident/i);
  });

  it("switches to Arabic without clearing active filters", () => {
    render(<DashboardClient dataset={loadPublicDataset()} />);
    fireEvent.click(screen.getByRole("checkbox", { name: /infrastructure/i }));
    fireEvent.click(screen.getByRole("button", { name: /العربية/i }));
    expect(screen.getByTestId("dashboard-root")).toHaveAttribute("dir", "rtl");
    expect(screen.getByRole("checkbox", { name: /البنية التحتية/i })).toBeChecked();
  });

  it("renders HTML-like source text without creating executable elements", () => {
    const dataset = structuredClone(loadPublicDataset());
    dataset.incidents[0].title.en = "<img src=x onerror=alert(1)>";
    render(<DashboardClient dataset={dataset} />);
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeVisible();
    expect(document.querySelector("img[src='x']")).toBeNull();
  });

  it("opens and closes incident detail using buttons", () => {
    render(<DashboardClient dataset={loadPublicDataset()} />);
    fireEvent.click(screen.getAllByRole("button", { name: /view details/i })[0]);
    expect(screen.getByRole("complementary")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /close details/i }));
    expect(screen.queryByRole("complementary")).toBeNull();
  });
});
~~~

- [ ] **Step 2: Run the component test to verify failure**

Run:

~~~bash
pnpm --filter @syosint/public-dashboard test -- DashboardClient
~~~

Expected: FAIL because dashboard components do not exist.

- [ ] **Step 3: Implement state and controls**

DashboardClient is the only stateful orchestration component. Store locale, category set, confidence set, search string, and selected incident ID. Derive the dictionary and filtered incidents with useMemo. Do not store derived result arrays in state.

FilterBar uses:

- a labeled search input;
- fieldsets with legends for category and confidence checkboxes;
- a reset button;
- an aria-live status reporting the visible count.

Header uses buttons with aria-pressed for English and العربية. Changing locale updates dir and lang on the dashboard root while preserving filter and selection state.

- [ ] **Step 4: Implement incident presentation**

IncidentCard displays:

- localized title, summary, and location;
- category text;
- ConfidenceBadge containing icon plus localized text;
- absolute occurrence time and explicit UTC indicator;
- source count;
- status text for corrected or withdrawn records;
- a View details button.

IncidentDetail is an aside with a heading, close button, uncertainty section, safe source links using target="_blank" and rel="noopener noreferrer", and correction history. It must never use dangerouslySetInnerHTML.

- [ ] **Step 5: Run component and accessibility-unit tests**

Run:

~~~bash
pnpm --filter @syosint/public-dashboard test -- DashboardClient
pnpm --filter @syosint/public-dashboard typecheck
~~~

Expected: all tests PASS.

- [ ] **Step 6: Commit feed and review interactions**

~~~bash
git add apps/public-dashboard/src/components
git commit -m "feat: add accessible incident review dashboard"
~~~

### Task 6: Bundled Syria map and incident timeline

**Files:**
- Create: apps/public-dashboard/src/lib/map.ts
- Create: apps/public-dashboard/src/lib/map.test.ts
- Create: apps/public-dashboard/src/components/SyriaMap.tsx
- Create: apps/public-dashboard/src/components/Timeline.tsx
- Modify: apps/public-dashboard/package.json
- Modify: NOTICE.md

**Interfaces:**
- Consumes: PublicIncident and Locale.
- Produces: getSyriaFeature(): GeoJSON.Feature, isMarkerEligible(incident): boolean, projectIncident(incident, width, height): [number, number] | null, SyriaMap({ incidents, locale, onSelect }), and Timeline({ incidents, locale, onSelect }).

- [ ] **Step 1: Write failing geography tests**

Create map.test.ts:

~~~ts
import { describe, expect, it } from "vitest";
import { getSyriaFeature, isMarkerEligible, projectIncident } from "./map";
import { loadPublicDataset } from "./load-public-dataset";

describe("map safety", () => {
  it("extracts Syria from the bundled Natural Earth-derived atlas", () => {
    const feature = getSyriaFeature();
    expect(feature.type).toBe("Feature");
    expect(feature.properties).toMatchObject({ name: "Syria" });
  });

  it("suppresses withheld and outside-bounds coordinates", () => {
    const base = structuredClone(loadPublicDataset().incidents[0]);
    base.location.precision = "withheld";
    expect(isMarkerEligible(base)).toBe(false);

    base.location.precision = "governorate";
    base.location.latitude = 0;
    base.location.longitude = 0;
    expect(isMarkerEligible(base)).toBe(false);
    expect(projectIncident(base, 640, 480)).toBeNull();
  });

  it("projects safe synthetic Syria coordinates inside the viewport", () => {
    const incident = loadPublicDataset().incidents.find(
      (item) => item.location.latitude !== undefined
    )!;
    const point = projectIncident(incident, 640, 480);
    expect(point).not.toBeNull();
    expect(point![0]).toBeGreaterThanOrEqual(0);
    expect(point![0]).toBeLessThanOrEqual(640);
    expect(point![1]).toBeGreaterThanOrEqual(0);
    expect(point![1]).toBeLessThanOrEqual(480);
  });
});
~~~

- [ ] **Step 2: Install map dependencies and verify failure**

Add d3-geo 3, world-atlas 2, and topojson-client 3 plus their type packages.

Run:

~~~bash
pnpm install
pnpm --filter @syosint/public-dashboard test -- map.test
~~~

Expected: FAIL because map.ts does not exist.

- [ ] **Step 3: Implement feature extraction and safe projection**

Import countries-110m.json from world-atlas and convert the countries object with topojson-client. Extract numeric ISO 3166-1 code 760. Set feature.properties.name to Syria. Use d3 geoMercator().fitExtent([[24, 24], [width - 24, height - 24]], feature).

isMarkerEligible returns false unless latitude and longitude exist, precision is governorate or district, latitude is within 32.0..37.5, and longitude is within 35.0..42.5. projectIncident returns null for ineligible incidents.

- [ ] **Step 4: Implement accessible map and timeline components**

SyriaMap renders an SVG with:

- a title and description linked through aria-labelledby and aria-describedby;
- the country outline;
- markers as keyboard-focusable buttons represented with SVG groups;
- an adjacent text list offering the same selection actions;
- status/confidence text in each marker's accessible name;
- no external tile or network request.

Timeline groups incidents by UTC date, uses semantic ordered lists, and exposes a button for each event. Both components call onSelect with the stable incident ID.

- [ ] **Step 5: Run geography and type tests**

Run:

~~~bash
pnpm --filter @syosint/public-dashboard test -- map.test
pnpm --filter @syosint/public-dashboard typecheck
~~~

Expected: all tests PASS.

- [ ] **Step 6: Commit map and timeline**

~~~bash
git add apps/public-dashboard/src/lib/map.ts apps/public-dashboard/src/lib/map.test.ts apps/public-dashboard/src/components/SyriaMap.tsx apps/public-dashboard/src/components/Timeline.tsx apps/public-dashboard/package.json pnpm-lock.yaml NOTICE.md
git commit -m "feat: add bundled Syria map and incident timeline"
~~~

### Task 7: Compose and style the visible dashboard

**Files:**
- Create: apps/public-dashboard/src/app/globals.css
- Create: apps/public-dashboard/src/app/page.tsx
- Create: apps/public-dashboard/src/app/methodology/page.tsx
- Modify: apps/public-dashboard/src/app/layout.tsx
- Modify: apps/public-dashboard/src/components/DashboardClient.tsx
- Test: apps/public-dashboard/src/app/page.test.tsx

**Interfaces:**
- Consumes: loadPublicDataset and all dashboard components.
- Produces: statically generated / and /methodology/ routes with responsive English/Arabic experiences.

- [ ] **Step 1: Write failing composition tests**

Create page.test.tsx that renders the page result and asserts:

- one main landmark;
- persistent demonstration-data warning;
- dashboard title;
- map region;
- timeline region;
- incident feed region;
- methodology link;
- no image or script URL beginning http.

- [ ] **Step 2: Run composition test to verify failure**

Run:

~~~bash
pnpm --filter @syosint/public-dashboard test -- page.test
~~~

Expected: FAIL because page composition and styles are incomplete.

- [ ] **Step 3: Compose the static page**

page.tsx calls loadPublicDataset during the build and passes the validated result to DashboardClient. DashboardClient composes:

1. skip link;
2. Header;
3. DemoBanner;
4. main with summary cards and filter bar;
5. responsive situation grid containing SyriaMap, IncidentFeed, and Timeline;
6. IncidentDetail when selected;
7. footer with methodology and repository links.

methodology/page.tsx explains public sources, human verification, confidence labels, corrections, delayed/generalized locations, synthetic data, Natural Earth boundary context, and the prohibition on publishing raw evidence.

- [ ] **Step 4: Implement the visual system**

globals.css defines:

- deep navy/slate background and high-contrast neutral text;
- restrained amber for developing attention, cyan for informational accents, green for corroborated/verified, and red only with text/icons for disputed/false;
- maximum content width of 1440px;
- 12-column desktop grid, 2-column tablet grid, and single-column mobile flow;
- minimum 44px interactive targets;
- visible 3px focus outline;
- RTL logical properties instead of left/right spacing;
- skeleton-free deterministic build rendering;
- prefers-reduced-motion disabling nonessential transition;
- print rules that preserve titles, confidence, sources, and methodology while removing controls.

- [ ] **Step 5: Run unit, type, and production build checks**

Run:

~~~bash
pnpm test
pnpm typecheck
pnpm build
test -f apps/public-dashboard/out/index.html
test -f apps/public-dashboard/out/methodology/index.html
~~~

Expected: all commands PASS and both static HTML files exist.

- [ ] **Step 6: Commit the complete visual dashboard**

~~~bash
git add apps/public-dashboard/src/app apps/public-dashboard/src/components/DashboardClient.tsx
git commit -m "feat: compose responsive syOSINT dashboard"
~~~

### Task 8: Browser verification, CI, and GitHub Pages deployment

**Files:**
- Create: apps/public-dashboard/playwright.config.ts
- Create: apps/public-dashboard/e2e/dashboard.spec.ts
- Create: .github/workflows/ci.yml
- Create: .github/workflows/deploy-pages.yml
- Modify: README.md
- Modify: CONTRIBUTING.md

**Interfaces:**
- Consumes: root workspace commands and static dashboard output.
- Produces: repeatable local/CI verification and a GitHub Pages artifact deployed only from main.

- [ ] **Step 1: Write failing end-to-end tests**

Create e2e/dashboard.spec.ts:

~~~ts
import { expect, test } from "@playwright/test";

test("filters incidents and preserves filters when switching to Arabic", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("checkbox", { name: /infrastructure/i }).check();
  const countBefore = await page.locator("[data-testid='incident-card']").count();
  expect(countBefore).toBeGreaterThan(0);

  await page.getByRole("button", { name: "العربية" }).click();
  await expect(page.getByTestId("dashboard-root")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("checkbox", { name: /البنية التحتية/i })).toBeChecked();
  await expect(page.locator("[data-testid='incident-card']")).toHaveCount(countBefore);
});

test("supports keyboard navigation and exposes methodology", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: /skip to content/i })).toBeFocused();
  await page.getByRole("link", { name: /methodology/i }).click();
  await expect(page.getByRole("heading", { name: /methodology/i })).toBeVisible();
});

test("contains no runtime calls to paid or external map services", async ({ page }) => {
  const externalRequests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (!["127.0.0.1", "localhost"].includes(url.hostname)) externalRequests.push(request.url());
  });
  await page.goto("/");
  await expect(page.getByRole("region", { name: /syria situation map/i })).toBeVisible();
  expect(externalRequests).toEqual([]);
});
~~~

- [ ] **Step 2: Configure Playwright and verify initial failure**

Configure webServer to run pnpm build followed by pnpm exec serve out -l 4173, baseURL http://127.0.0.1:4173, Chromium only, one retry in CI, trace on first retry, and reduced motion.

Run:

~~~bash
pnpm --filter @syosint/public-dashboard exec playwright install chromium
pnpm --filter @syosint/public-dashboard test:e2e
~~~

Expected: at least one test FAIL until accessible names, test IDs, and methodology navigation match the final UI.

- [ ] **Step 3: Make the smallest UI corrections required by browser tests**

Add data-testid="dashboard-root" to the locale-direction container and data-testid="incident-card" to cards. Ensure the skip link is the first focusable control, all region names come from visible headings, and methodology navigation works under static export.

Run:

~~~bash
pnpm --filter @syosint/public-dashboard test:e2e
~~~

Expected: all browser tests PASS.

- [ ] **Step 4: Create CI workflow**

ci.yml triggers on pull_request and pushes to main. Grant contents: read. Use checkout@v4, setup-node@v4 with Node 24 and pnpm cache, corepack enable, pnpm install --frozen-lockfile, then:

~~~bash
pnpm policy:check
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm --filter @syosint/public-dashboard exec playwright install --with-deps chromium
pnpm test:e2e
~~~

Upload Playwright reports only on failure with a seven-day retention.

- [ ] **Step 5: Create Pages deployment workflow**

deploy-pages.yml triggers only after CI succeeds on main through workflow_run, or by workflow_dispatch. Set contents: read, pages: write, id-token: write, and concurrency group pages with cancel-in-progress false.

The build job installs with the same Node/pnpm versions, runs pnpm build with GITHUB_ACTIONS=true, calls actions/configure-pages@v5, and uploads apps/public-dashboard/out through actions/upload-pages-artifact@v3. The deploy job uses actions/deploy-pages@v4 in the github-pages environment.

- [ ] **Step 6: Verify repository documentation and all checks**

Update README with:

- project screenshot location reserved only after a real screenshot is committed;
- exact local commands;
- synthetic-data warning;
- architecture summary;
- safety and legal boundaries;
- GitHub Pages setup instruction: Settings → Pages → Source → GitHub Actions;
- roadmap links to the design and this plan.

Run:

~~~bash
pnpm policy:check
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm test:e2e
GITHUB_ACTIONS=true pnpm build
grep -E '(/syOSINT/_next/|href="/syOSINT/)' apps/public-dashboard/out/index.html
git grep -n -E "api_hash|api_id|\.session|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY" -- . ':!docs/superpowers'
git status --short
~~~

Expected: all commands PASS; the exported HTML contains /syOSINT/ asset or navigation paths; the credential grep returns no material; git status lists only intended plan implementation changes before the final commit.

- [ ] **Step 7: Commit automation and documentation**

~~~bash
git add .github apps/public-dashboard/e2e apps/public-dashboard/playwright.config.ts README.md CONTRIBUTING.md pnpm-lock.yaml
git commit -m "ci: verify and deploy public dashboard"
~~~

- [ ] **Step 8: Run final branch verification**

~~~bash
pnpm policy:check
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm test:e2e
git log --oneline --decorate -8
~~~

Expected: every verification command PASS and the branch contains focused commits for foundation, schema, data/filtering, bilingual shell, incident UI, map/timeline, composition, and automation.

- [ ] **Step 9: Push and open the first product pull request**

~~~bash
git push -u origin feat/foundation-public-dashboard
gh pr create --base main --head feat/foundation-public-dashboard --title "feat: launch syOSINT public dashboard foundation" --body-file .github/pull_request_body.md
~~~

The pull-request body must summarize visible features, safety boundaries, synthetic-only data, verification commands and results, screenshots for desktop/mobile/Arabic, deployment impact, and explicitly deferred collector/Telegram work.
