# Public RSS Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the automatic public RSS/Atom wire to 8–12 reviewed Arabic and English sources and make configured, healthy, delayed, and empty coverage understandable on the public dashboard.

**Architecture:** Extend the committed feed configuration with explicit deterministic topic modes, project per-source state into a backward-incompatible `1.1.0` public contract, and render the complete configured source set rather than deriving filters from current entries. Preserve the existing safe fetcher, last-valid fallback, seven-day global retention, and metadata-only public boundary.

**Tech Stack:** Python 3.14.7, dataclasses, pytest, JSON Schema 2020-12, TypeScript 5.9, React/Next.js, Vitest, Testing Library, Playwright, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-24-source-expansion-telegram-design.md`

## Global Constraints

- Use Python 3.14.7 or a newer stable security/maintenance patch in the 3.14 series available before merge.
- Keep the public RSS projection limited to source identity, original headline, canonical URL, language, and publication/collection/refresh metadata.
- Do not add AI/ML topic classification, translation, summarization, or credibility scoring.
- Keep seven-day and 500-entry global retention and add a 100-entry per-source cap.
- Preserve reports from different sources even when their headlines are similar.
- Every enabled source must pass the review checklist in `docs/source-policy/RSS.md`.
- `main` must remain deployable after this pull request.

## Review Focus

- A configured source with zero retained headlines must remain visible and explain that no recent matching report exists.
- An all-delayed refresh must keep the previous valid entries and previous successful-refresh timestamp.
- A high-volume source must not exceed 100 retained entries or remove other sources from the configured status list.
- An invalid topic mode or an empty term list for `keyword-filtered` must fail configuration loading before network access.
- A previous `1.0.0` artifact must be read for one deployment transition and projected into the new `1.1.0` output without losing valid entries.

---

### Task 1: Add explicit RSS topic policies

**Files:**
- Modify: `services/collector-api/syosint/rss_types.py`
- Modify: `services/collector-api/syosint/rss_cli.py`
- Modify: `services/collector-api/syosint/rss_collect.py`
- Modify: `services/collector-api/tests/test_rss_collect.py`
- Modify: `services/collector-api/tests/test_rss_parse.py`

**Interfaces:**
- Consumes: JSON source entries from `config/rss-sources.json`.
- Produces: `FeedSource.topic_mode: Literal["syria-only", "keyword-filtered"]`, `FeedSource.required_terms`, and `FeedSource.excluded_terms`; `headline_matches(source: FeedSource, headline: str) -> bool`.

- [ ] **Step 1: Write failing topic-policy tests**

```python
def test_topic_modes_are_deterministic():
    assert headline_matches(source(topic_mode="syria-only"), "Any headline")
    filtered = source(required_terms=("syria",), excluded_terms=("football",))
    assert headline_matches(filtered, "Syria humanitarian update")
    assert not headline_matches(filtered, "Syria football result")

def test_keyword_mode_requires_terms(tmp_path):
    config = source_config(topicMode="keyword-filtered", requiredTerms=[])
    with pytest.raises(ValueError, match="requiredTerms"):
        load_sources(write_config(tmp_path, config))
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_rss_collect.py services/collector-api/tests/test_rss_parse.py -q`

Expected: FAIL because `topic_mode`, `excluded_terms`, and `headline_matches` do not exist.

- [ ] **Step 3: Implement the minimal topic-policy model and validation**

```python
@dataclass(frozen=True)
class FeedSource:
    id: str
    label: Mapping[str, str]
    feed_url: str
    homepage_url: str
    language: Literal["en", "ar"]
    enabled: bool
    topic_mode: Literal["syria-only", "keyword-filtered"]
    required_terms: tuple[str, ...]
    excluded_terms: tuple[str, ...] = ()
    attribution: str | None = None

def headline_matches(source: FeedSource, headline: str) -> bool:
    normalized = normalize_text(headline)
    if any(normalize_text(term) in normalized for term in source.excluded_terms):
        return False
    return source.topic_mode == "syria-only" or any(
        normalize_text(term) in normalized for term in source.required_terms
    )
```

Make the config loader reject unknown modes and reject `keyword-filtered` with no required terms.

- [ ] **Step 4: Run topic-policy and existing collector tests**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_rss_parse.py services/collector-api/tests/test_rss_collect.py services/collector-api/tests/test_rss_cli.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/collector-api/syosint/rss_types.py services/collector-api/syosint/rss_cli.py services/collector-api/syosint/rss_collect.py services/collector-api/tests/test_rss_collect.py services/collector-api/tests/test_rss_parse.py
git commit -m "feat: add deterministic RSS topic policies"
```

### Task 2: Project per-source state and bounded retention

**Files:**
- Modify: `services/collector-api/syosint/rss_public.py`
- Modify: `services/collector-api/tests/test_rss_public.py`

**Interfaces:**
- Consumes: `CollectionResult.sources`, `CollectionResult.outcomes`, optional `PublicWire`, and UTC `now`.
- Produces: `PublicSourceState`, `PublicWire.source_states`, and `build_public_wire(..., per_source_limit: int = 100) -> dict` using schema version `1.1.0`.

- [ ] **Step 1: Write failing projection tests**

```python
def test_projects_empty_and_delayed_sources():
    wire = build_public_wire(result_with(empty_healthy(), delayed()), None, NOW)
    assert wire["sources"] == {"configured": 2, "healthy": 1, "delayed": 1}
    assert [state["entryCount"] for state in wire["sourceStates"]] == [0, 0]

def test_caps_each_source_without_dropping_source_state():
    wire = build_public_wire(result_with(items=items_for_two_sources(130, 2)), None, NOW)
    assert sum(e["sourceId"] == "busy" for e in wire["entries"]) == 100
    assert {state["id"] for state in wire["sourceStates"]} == {"busy", "quiet"}
```

Add a compatibility test that reads a `1.0.0` previous artifact and retains its seven-day entries.

- [ ] **Step 2: Run tests and verify failure**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_rss_public.py -q`

Expected: FAIL because the current projection has aggregate counts only and no per-source cap.

- [ ] **Step 3: Implement source-state projection and stable per-source limiting**

```python
@dataclass(frozen=True)
class PublicSourceState:
    id: str
    label: Mapping[str, str]
    language: Literal["en", "ar"]
    status: Literal["healthy", "not-modified", "delayed"]
    last_successful_refresh_at: datetime | None
    entry_count: int
```

Group retained entries by `source_id`, keep the newest 100 in each group, merge the groups, sort newest-first, then apply the existing 500-entry cap. Build `sourceStates` from every configured enabled source, not from entries.

- [ ] **Step 4: Run the complete public-wire Python suite**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_rss_public.py services/collector-api/tests/test_rss_cli.py -q`

Expected: PASS, including previous-artifact compatibility and all-delayed fallback.

- [ ] **Step 5: Commit**

```bash
git add services/collector-api/syosint/rss_public.py services/collector-api/tests/test_rss_public.py
git commit -m "feat: expose bounded RSS source health"
```

### Task 3: Version the public RSS contract

**Files:**
- Modify: `packages/schemas/src/public-news-wire.schema.json`
- Modify: `packages/schemas/src/types.ts`
- Modify: `packages/schemas/src/validate.ts`
- Modify: `packages/schemas/src/validate.test.ts`
- Modify: `data/public/news-wire.v1.json`

**Interfaces:**
- Consumes: `1.1.0` JSON emitted by Task 2.
- Produces: `PublicNewsWireSourceState` and `PublicNewsWire` TypeScript types accepted by `validatePublicNewsWire`.

- [ ] **Step 1: Update the valid fixture and add failing forbidden-state tests**

```ts
const validWire = {
  schemaVersion: "1.1.0",
  generatedAt: "2026-09-24T16:00:00Z",
  lastSuccessfulRefreshAt: "2026-09-24T16:00:00Z",
  sources: { configured: 2, healthy: 1, delayed: 1 },
  sourceStates: [{
    id: "bbc-arabic",
    label: { en: "BBC Arabic", ar: "بي بي سي عربي" },
    language: "ar",
    status: "healthy",
    lastSuccessfulRefreshAt: "2026-09-24T16:00:00Z",
    entryCount: 1,
  }],
  entries: [],
};

it("rejects source exception details", () => {
  const input = structuredClone(validWire) as any;
  input.sourceStates[0].error = "socket trace";
  expect(validatePublicNewsWire(input).ok).toBe(false);
});
```

- [ ] **Step 2: Run schema tests and confirm failure**

Run: `corepack pnpm --filter @syosint/schemas test`

Expected: FAIL because schema `1.0.0` rejects the new contract.

- [ ] **Step 3: Implement exact schema and type changes**

```ts
export interface PublicNewsWireSourceState {
  id: string;
  label: LocalizedText;
  language: "en" | "ar";
  status: "healthy" | "not-modified" | "delayed";
  lastSuccessfulRefreshAt: string | null;
  entryCount: number;
}

export interface PublicNewsWire {
  schemaVersion: "1.1.0";
  generatedAt: string;
  lastSuccessfulRefreshAt: string;
  sources: { configured: number; healthy: number; delayed: number };
  sourceStates: PublicNewsWireSourceState[];
  entries: PublicNewsWireEntry[];
}
```

Set `additionalProperties: false` at every new object boundary and require unique source-state IDs in `validatePublicNewsWire`.

- [ ] **Step 4: Run schema and loader tests**

Run: `corepack pnpm --filter @syosint/schemas test && corepack pnpm test -- apps/public-dashboard/src/lib/load-public-news-wire.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/schemas/src/public-news-wire.schema.json packages/schemas/src/types.ts packages/schemas/src/validate.test.ts packages/schemas/src/validate.ts data/public/news-wire.v1.json
git commit -m "feat: version RSS source-state contract"
```

### Task 4: Render complete coverage and mobile pagination

**Files:**
- Modify: `apps/public-dashboard/src/components/NewsWire.tsx`
- Modify: `apps/public-dashboard/src/components/NewsWire.test.tsx`
- Modify: `apps/public-dashboard/src/components/DemoBanner.tsx`
- Modify: `apps/public-dashboard/src/components/DashboardClient.test.tsx`
- Modify: `apps/public-dashboard/src/i18n/types.ts`
- Modify: `apps/public-dashboard/src/i18n/en.ts`
- Modify: `apps/public-dashboard/src/i18n/ar.ts`
- Modify: `apps/public-dashboard/src/app/globals.css`
- Modify: `apps/public-dashboard/e2e/dashboard.spec.ts`

**Interfaces:**
- Consumes: `PublicNewsWire.sourceStates` and filtered entries.
- Produces: `NewsWire` coverage summary, configured-source selector, source-aware empty state, and 25-item incremental pagination.

- [ ] **Step 1: Write failing component tests**

```tsx
expect(screen.getByText("2 configured · 1 healthy · 1 delayed · 1 headline")).toBeVisible();
expect(screen.getByRole("option", { name: /UN News.*delayed/ })).toBeVisible();
fireEvent.change(screen.getByLabelText("Source filter"), { target: { value: "un" } });
expect(screen.getByText("This source is delayed; recent coverage may be incomplete.")).toBeVisible();
expect(screen.getAllByRole("article")).toHaveLength(25);
fireEvent.click(screen.getByRole("button", { name: "Show more" }));
expect(screen.getAllByRole("article")).toHaveLength(50);
```

Also assert the banner says reviewed incidents are fictional while the wire contains real external headlines.

- [ ] **Step 2: Run component tests and verify failure**

Run: `corepack pnpm test -- apps/public-dashboard/src/components/NewsWire.test.tsx apps/public-dashboard/src/components/DashboardClient.test.tsx`

Expected: FAIL because sources are derived from entries and pagination does not exist.

- [ ] **Step 3: Implement the coverage UI**

```tsx
const PAGE_SIZE = 25;
const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
const selectedState = wire.sourceStates.find((source) => source.id === sourceId);
const visibleEntries = entries.slice(0, visibleCount);
```

Reset `visibleCount` when source or language filters change. Use `sourceStates` for options and show localized healthy/delayed/no-match explanations without exposing error details.

- [ ] **Step 4: Run unit and browser tests**

Run: `corepack pnpm test -- apps/public-dashboard && corepack pnpm --dir apps/public-dashboard test:e2e`

Expected: PASS in English, Arabic, desktop, and mobile scenarios.

- [ ] **Step 5: Commit**

```bash
git add apps/public-dashboard/src/components apps/public-dashboard/src/i18n apps/public-dashboard/src/app/globals.css apps/public-dashboard/e2e/dashboard.spec.ts
git commit -m "feat: explain public RSS coverage"
```

### Task 5: Review and enable the balanced source set

**Files:**
- Modify: `config/rss-sources.json`
- Modify: `docs/source-policy/RSS.md`
- Create: `docs/source-policy/RSS-SOURCE-REVIEWS.md`
- Modify: `services/collector-api/tests/test_rss_cli.py`

**Interfaces:**
- Consumes: `python -m syosint.rss_cli check-source URL` and the review checklist.
- Produces: 8–12 enabled reviewed sources with `topicMode`, `requiredTerms`, `excludedTerms`, attribution, and a dated review record.

- [ ] **Step 1: Add a failing configuration-governance test**

```python
def test_public_allowlist_is_balanced_and_reviewed():
    sources = load_sources(REPOSITORY / "config/rss-sources.json")
    enabled = [source for source in sources if source.enabled]
    assert 8 <= len(enabled) <= 12
    assert {source.language for source in enabled} == {"en", "ar"}
    assert all(source.attribution for source in enabled)
```

- [ ] **Step 2: Evaluate the fixed candidate pool**

Run `check-source` and complete ownership/terms/topic notes for these candidates, retaining only candidates that pass every policy check:

```text
UN News — Middle East
BBC Arabic
Al Jazeera English
Al Jazeera Arabic
France 24 English — Middle East
France 24 Arabic
DW Arabic
ReliefWeb — Syrian Arab Republic updates
Syria Direct
Enab Baladi Arabic
Enab Baladi English
Middle East Eye
```

For each retained source, record the exact official feed URL, homepage, access date, ownership evidence, terms/feed evidence, language, topic mode, and check-source result in `RSS-SOURCE-REVIEWS.md`. Do not enable a candidate with an ambiguous feed owner, redirect target, or reuse permission.

- [ ] **Step 3: Commit the reviewed configuration and documentation**

```json
{
  "id": "example-syria-source",
  "label": { "en": "Example", "ar": "مثال" },
  "feedUrl": "https://publisher.example/feed.xml",
  "homepageUrl": "https://publisher.example/",
  "language": "en",
  "enabled": true,
  "topicMode": "keyword-filtered",
  "requiredTerms": ["Syria", "Syrian"],
  "excludedTerms": [],
  "attribution": "Headline © publisher; linked to original"
}
```

Use the shape above with the actual reviewed publisher values recorded in the review document.

- [ ] **Step 4: Run governance, live-check, and policy tests**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_rss_cli.py -q && corepack pnpm policy:check`

Expected: PASS. Every enabled source has a recorded passing review; live network failures are documented and leave the candidate disabled rather than bypassing checks.

- [ ] **Step 5: Commit**

```bash
git add config/rss-sources.json docs/source-policy/RSS.md docs/source-policy/RSS-SOURCE-REVIEWS.md services/collector-api/tests/test_rss_cli.py
git commit -m "feat: expand reviewed RSS source coverage"
```

### Task 6: Improve workflow diagnostics and verify the pull request

**Files:**
- Modify: `services/collector-api/syosint/rss_cli.py`
- Modify: `services/collector-api/tests/test_rss_cli.py`
- Modify: `.github/workflows/rss-wire.yml`
- Modify: `README.md`
- Modify: `docs/PROJECT_STATE.md`

**Interfaces:**
- Consumes: per-source collection outcomes.
- Produces: one safe log line per source in the form `source=<id> status=<state> category=<safe-category-or-none> items=<count>`.

- [ ] **Step 1: Write a failing redacted-log test**

```python
def test_cli_logs_safe_per_source_status(capsys):
    run_collection(fake_result(error_category="timeout"))
    output = capsys.readouterr().out
    assert "source=un-news-middle-east status=delayed category=timeout items=0" in output
    assert "response body" not in output
```

- [ ] **Step 2: Implement bounded log output and workflow summary**

```python
print(
    f"source={outcome.source_id} status={outcome.status} "
    f"category={outcome.error_category or 'none'} items={len(outcome.items)}"
)
```

Add a GitHub step summary containing aggregate configured/healthy/delayed/item counts only.

- [ ] **Step 3: Run the complete verification matrix**

Run:

```bash
.venv314/bin/python -m pytest services/collector-api/tests -q
corepack pnpm policy:check
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
corepack pnpm test:e2e
```

Expected: every command exits 0; generated public JSON validates as `1.1.0`; no secret or private field appears in artifacts.

- [ ] **Step 4: Update operational documentation and project state**

Document the final enabled source count, review record, `1.1.0` schema transition, public status semantics, per-source cap, and recovery steps. Mark PR 1 of Milestone 4 ready for review without marking Telegram work complete.

- [ ] **Step 5: Commit**

```bash
git add services/collector-api/syosint/rss_cli.py services/collector-api/tests/test_rss_cli.py .github/workflows/rss-wire.yml README.md docs/PROJECT_STATE.md
git commit -m "docs: document expanded RSS operations"
```
