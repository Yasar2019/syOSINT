# RSS Collection and Public News Wire Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collect allowlisted RSS/Atom feeds every 30 minutes, show sanitized Syria-related headlines on the public dashboard, and route richer collected records into the private analyst workflow.

**Architecture:** One Python collection core parses and normalizes feeds for two projections. A scheduled GitHub Pages workflow creates a minimal public wire, while the localhost API persists full permitted evidence, health, cursors and quarantine state in SQLite. Shared schemas and explicit promotion endpoints keep automatic headlines separate from reviewed incidents.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy, Alembic, httpx, defusedxml, Pydantic, JSON Schema, Next.js 16, React 19, TypeScript, Vitest, Playwright, GitHub Actions and GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-09-23-rss-collection-design.md`

## Global Constraints

- Target the latest stable Python 3.14 patch with `requires-python = ">=3.14,<3.15"`; do not use Python 3.15 prereleases.
- Public collection runs every 30 minutes and also supports manual workflow dispatch.
- Public wire entries contain only source labels, original headline, canonical URL, publication time, collection time and stable identifiers.
- The public wire is always labeled **Unverified external reporting** and remains separate from reviewed incidents.
- Only enabled sources in `config/rss-sources.json` can enter the public wire.
- Broad feeds require deterministic English or Arabic Syria-topic terms; do not add AI classification or translation.
- Public retention is seven days or 500 newest entries, whichever limit is reached first.
- RSS collection is public HTTPS only, with safe redirect, DNS, timeout, response-size and item-count limits.
- One source failure cannot block healthy sources or erase the last valid deployed dataset.
- Analyst promotion never invents a category, translation, confidence label, location or summary.
- Telegram collection, HTML scraping and correction/withdrawal workflows remain outside this milestone.

## Review Focus

- A hostname that resolves publicly during validation and privately on a later lookup must be rejected before a response body is trusted; Task 3 pins redirect and rebinding checks.
- A feed with a decompression bomb or endless response must stop at the decompressed byte limit without affecting other sources; Task 3 tests the streaming limit.
- Two sources may publish the same URL while one source may reuse IDs; Task 2 tests the specified identity order and source scoping.
- A feed may supply missing, invalid or far-future dates; Task 2 tests fallback collection time and quarantine of unsafe future dates.
- A repeated promote or attach request must not create duplicate evidence or audit history; Task 5 tests idempotency.

---

### Task 1: Python 3.14 baseline and public news-wire contract

**Files:**
- Modify: `services/collector-api/pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Create: `packages/schemas/src/public-news-wire.schema.json`
- Modify: `packages/schemas/src/types.ts`
- Modify: `packages/schemas/src/validate.ts`
- Modify: `packages/schemas/src/index.ts`
- Modify: `packages/schemas/src/validate.test.ts`
- Create: `config/rss-sources.json`
- Create: `data/public/news-wire.v1.json`

**Interfaces:**
- Produces: `PublicNewsWire`, `PublicNewsWireEntry`, `validatePublicNewsWire(value: unknown): NewsWireValidationResult`.
- Produces: repository allowlist records with `id`, `label`, `feedUrl`, `homepageUrl`, `language`, `enabled`, `requiredTerms` and optional `attribution`.
- Consumes: existing AJV 2020 validation conventions from `packages/schemas`.

- [ ] **Step 1: Write failing schema tests**

Add fixtures and assertions to `packages/schemas/src/validate.test.ts`:

```ts
const validWire = {
  schemaVersion: "1.0.0",
  generatedAt: "2026-09-23T16:00:00Z",
  lastSuccessfulRefreshAt: "2026-09-23T16:00:00Z",
  sources: { healthy: 2, delayed: 0 },
  entries: [{
    id: "bbc-arabic:abc123",
    sourceId: "bbc-arabic",
    sourceLabel: { en: "BBC Arabic", ar: "بي بي سي عربي" },
    language: "ar",
    headline: "خبر تجريبي عن سوريا",
    url: "https://www.bbc.com/arabic/articles/example",
    publishedAt: "2026-09-23T15:55:00Z",
    collectedAt: "2026-09-23T16:00:00Z",
  }],
};

it("accepts the bounded public news-wire contract", () => {
  expect(validatePublicNewsWire(validWire)).toEqual({ ok: true, data: validWire });
});

it("rejects duplicate ids and private fields", () => {
  const duplicate = { ...validWire, entries: [validWire.entries[0], validWire.entries[0]] };
  expect(validatePublicNewsWire(duplicate).ok).toBe(false);
  expect(validatePublicNewsWire({ ...validWire, entries: [{ ...validWire.entries[0], body: "private" }] }).ok).toBe(false);
});
```

- [ ] **Step 2: Run the schema tests and confirm the new exports are missing**

Run: `corepack pnpm --filter @syosint/schemas test`

Expected: FAIL because `validatePublicNewsWire` is not exported.

- [ ] **Step 3: Add the JSON Schema, TypeScript types and validator**

Define the public interfaces in `types.ts`:

```ts
export interface PublicNewsWireEntry {
  id: string;
  sourceId: string;
  sourceLabel: LocalizedText;
  language: "en" | "ar";
  headline: string;
  url: string;
  publishedAt: string;
  collectedAt: string;
}

export interface PublicNewsWire {
  schemaVersion: "1.0.0";
  generatedAt: string;
  lastSuccessfulRefreshAt: string;
  sources: { healthy: number; delayed: number };
  entries: PublicNewsWireEntry[];
}
```

Compile `public-news-wire.schema.json` with the existing strict AJV instance, reject duplicate entry IDs after schema validation, and export all new types and functions from `index.ts`.

- [ ] **Step 4: Add safe checked-in defaults and Python 3.14 configuration**

Create `config/rss-sources.json` with the two initial reviewed candidates and deterministic topic filters:

```json
{
  "schemaVersion": "1.0.0",
  "sources": [
    {
      "id": "un-news-middle-east",
      "label": { "en": "UN News — Middle East", "ar": "أخبار الأمم المتحدة — الشرق الأوسط" },
      "feedUrl": "https://news.un.org/feed/subscribe/en/news/region/middle-east/feed/rss.xml",
      "homepageUrl": "https://news.un.org/en/news/region/middle-east",
      "language": "en",
      "enabled": true,
      "requiredTerms": ["Syria", "Syrian"]
    },
    {
      "id": "bbc-arabic",
      "label": { "en": "BBC Arabic", "ar": "بي بي سي عربي" },
      "feedUrl": "https://feeds.bbci.co.uk/arabic/rss.xml",
      "homepageUrl": "https://www.bbc.com/arabic",
      "language": "ar",
      "enabled": true,
      "requiredTerms": ["سوريا", "سوري", "سورية"]
    }
  ]
}
```

Create an empty valid `data/public/news-wire.v1.json`. Change Python metadata to `requires-python = ">=3.14,<3.15"`, add runtime pins for `httpx` and `defusedxml`, and switch CI to `python-version: '3.14'`.

- [ ] **Step 5: Run focused validation and runtime checks**

Run:

```bash
corepack pnpm --filter @syosint/schemas test
corepack pnpm --filter @syosint/schemas typecheck
python3.14 -m venv .venv314
.venv314/bin/python -m pip install --upgrade pip
.venv314/bin/python -m pip install -e './services/collector-api[test]' pip-audit==2.10.1
.venv314/bin/python -m pip_audit --local
```

Expected: schema tests and type checks PASS; dependency installation succeeds on Python 3.14; audit reports no known vulnerabilities other than the local project package being unavailable from PyPI.

- [ ] **Step 6: Commit the contract baseline**

```bash
git add services/collector-api/pyproject.toml .github/workflows/ci.yml packages/schemas config/rss-sources.json data/public/news-wire.v1.json
git commit -m "feat: define RSS wire contract on Python 3.14"
```

---

### Task 2: Deterministic RSS/Atom parsing and identity

**Files:**
- Create: `services/collector-api/syosint/rss_types.py`
- Create: `services/collector-api/syosint/rss_normalize.py`
- Create: `services/collector-api/syosint/rss_parse.py`
- Create: `services/collector-api/tests/fixtures/rss.xml`
- Create: `services/collector-api/tests/fixtures/atom.xml`
- Create: `services/collector-api/tests/test_rss_parse.py`

**Interfaces:**
- Produces: `FeedSource`, `NormalizedFeedItem`, `QuarantinedItem` dataclasses.
- Produces: `canonicalize_url(url: str) -> str`, `matches_topic(headline: str, required_terms: tuple[str, ...]) -> bool`, `fingerprint_item(source_id: str, native_id: str | None, url: str, headline: str, published_at: datetime | None) -> str`.
- Produces: `parse_feed(source: FeedSource, content: bytes, collected_at: datetime) -> ParseResult`.
- Consumes: defused XML parsing and source configuration from Task 1.

- [ ] **Step 1: Add representative RSS and Atom fixtures and failing parser tests**

Create tests for valid entries, relative Atom links, CDATA/HTML headlines, missing IDs, invalid dates, broad-feed topic rejection and Arabic Unicode matching:

```python
def test_parses_rss_and_applies_arabic_topic_terms(fixtures):
    result = parse_feed(ARABIC_SOURCE, fixtures.rss, NOW)
    assert [item.headline for item in result.items] == ["تطور جديد في سوريا"]
    assert result.items[0].url == "https://example.org/reports/1"

def test_identity_prefers_native_id_then_url_then_content():
    assert fingerprint_item("s", "native-1", "https://e.org/a", "Title", NOW) == fingerprint_item(
        "s", "native-1", "https://e.org/changed", "Changed", NOW
    )
    assert fingerprint_item("s", None, "https://e.org/a?utm_source=x", "Title", NOW) == fingerprint_item(
        "s", None, "https://e.org/a", "Changed", NOW
    )

def test_far_future_date_is_quarantined(fixtures):
    result = parse_feed(ENGLISH_SOURCE, fixtures.future_date, NOW)
    assert result.quarantined[0].reason == "future-published-at"
```

- [ ] **Step 2: Run the parser tests and verify they fail**

Run: `PYTHONPATH=services/collector-api .venv314/bin/python -m pytest services/collector-api/tests/test_rss_parse.py -q`

Expected: FAIL because the RSS modules do not exist.

- [ ] **Step 3: Implement focused data types and normalization**

Use frozen dataclasses and explicit results:

```python
@dataclass(frozen=True)
class NormalizedFeedItem:
    source_id: str
    native_id: str | None
    headline: str
    url: str
    published_at: datetime
    collected_at: datetime
    fingerprint: str
    raw_digest: str

@dataclass(frozen=True)
class ParseResult:
    items: tuple[NormalizedFeedItem, ...]
    quarantined: tuple[QuarantinedItem, ...]
```

Canonicalization removes fragments, default ports and only the explicit tracking keys `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `gclid` and `fbclid`. It preserves all other query parameters. Topic matching normalizes Unicode with NFKC and uses `str.casefold()` before literal substring checks.

- [ ] **Step 4: Implement RSS 2.0 and Atom parsing**

Use `defusedxml.ElementTree.fromstring`, reject DTD/entity content, cap parsed entries, normalize HTML entities and strip tags from headlines. Use collection time only when the source date is missing or invalid. Quarantine dates more than 24 hours ahead of collection time.

- [ ] **Step 5: Run parser tests**

Run: `PYTHONPATH=services/collector-api .venv314/bin/python -m pytest services/collector-api/tests/test_rss_parse.py -q`

Expected: PASS.

- [ ] **Step 6: Commit deterministic parsing**

```bash
git add services/collector-api/syosint/rss_*.py services/collector-api/tests/fixtures services/collector-api/tests/test_rss_parse.py
git commit -m "feat: parse and fingerprint RSS and Atom feeds"
```

---

### Task 3: Safe retrieval and public wire generation

**Files:**
- Create: `services/collector-api/syosint/safe_http.py`
- Create: `services/collector-api/syosint/rss_collect.py`
- Create: `services/collector-api/syosint/rss_public.py`
- Create: `services/collector-api/syosint/rss_cli.py`
- Create: `services/collector-api/tests/test_safe_http.py`
- Create: `services/collector-api/tests/test_rss_public.py`

**Interfaces:**
- Produces: `SafeFeedClient.fetch(url: str, validators: HttpValidators | None = None) -> FetchResult`.
- Produces: `PublicWire` dataclass plus `collect_sources(sources: Sequence[FeedSource], previous: PublicWire | None, now: datetime, client: FeedClient) -> CollectionResult`.
- Produces: `build_public_wire(result: CollectionResult, previous: PublicWire | None, now: datetime) -> dict`.
- Produces CLI: `python -m syosint.rss_cli collect-public --config PATH --output PATH [--previous-url URL]` and `check-source URL`.
- Consumes: Task 1 schema and allowlist; Task 2 parser and fingerprints.

- [ ] **Step 1: Write failing safe-retrieval tests**

Use injected DNS and HTTP doubles so tests never contact live services:

```python
def test_rejects_private_dns_and_unsafe_redirect(fake_transport):
    fake_transport.resolve("feed.example").returns("203.0.113.10")
    fake_transport.get("https://feed.example/rss").redirects_to("https://127.0.0.1/private")
    with pytest.raises(UnsafeFeedUrl):
        SafeFeedClient(fake_transport).fetch("https://feed.example/rss")

def test_stops_after_decompressed_limit(fake_transport):
    fake_transport.stream_bytes = [b"x" * 700_000, b"y" * 700_000]
    with pytest.raises(ResponseTooLarge):
        SafeFeedClient(fake_transport, max_bytes=1_000_000).fetch("https://feed.example/rss")

def test_rechecks_dns_for_every_connection(fake_transport):
    fake_transport.resolve_sequence("feed.example", ["203.0.113.10", "127.0.0.1"])
    with pytest.raises(UnsafeFeedUrl):
        SafeFeedClient(fake_transport).fetch("https://feed.example/rss")
```

- [ ] **Step 2: Write failing public-generation tests**

Cover independent failures, three bounded attempts, `Retry-After`, previous valid entries, retention, 500-item cap and exclusion of private fields:

```python
def test_partial_success_keeps_current_previous_entries():
    result = collect_sources([HEALTHY, FAILING], previous=PREVIOUS, now=NOW, client=CLIENT)
    wire = build_public_wire(result, PREVIOUS, NOW)
    assert {item["sourceId"] for item in wire["entries"]} == {"healthy", "failing"}
    assert all(set(item) == PUBLIC_KEYS for item in wire["entries"])
```

- [ ] **Step 3: Run focused tests and verify failure**

Run: `PYTHONPATH=services/collector-api .venv314/bin/python -m pytest services/collector-api/tests/test_safe_http.py services/collector-api/tests/test_rss_public.py -q`

Expected: FAIL because collection modules do not exist.

- [ ] **Step 4: Implement the safe client**

Require HTTPS, no credentials/fragments, port 443, and public DNS results. Follow no more than five redirects manually, revalidating scheme, host and DNS on every hop. Stream decoded bytes into a bounded buffer; allow RSS/Atom XML content types plus `application/xml` and `text/xml`. Return ETag, Last-Modified and `304` without logging sensitive values.

- [ ] **Step 5: Implement isolated collection and public projection**

Represent each source outcome explicitly:

```python
@dataclass(frozen=True)
class SourceOutcome:
    source_id: str
    status: Literal["healthy", "not-modified", "delayed"]
    items: tuple[NormalizedFeedItem, ...]
    error_category: str | None
    validators: HttpValidators | None
```

Retry only timeouts, `408`, `425`, `429` and `5xx`, with at most three attempts. Merge fresh and still-current previous entries by stable ID, sort newest first, expire after seven days and truncate to 500.

- [ ] **Step 6: Implement and test the CLI**

The CLI validates `config/rss-sources.json`, optionally retrieves the current Pages JSON, validates that previous dataset before merging, writes through a temporary file and atomically replaces the output. `check-source` prints only safe metadata and exits nonzero for invalid feeds.

Run the focused tests again; expect PASS.

- [ ] **Step 7: Commit safe public collection**

```bash
git add services/collector-api/syosint services/collector-api/tests/test_safe_http.py services/collector-api/tests/test_rss_public.py
git commit -m "feat: collect feeds into a bounded public wire"
```

---

### Task 4: SQLite feed inbox, cursors, health and scheduler

**Files:**
- Modify: `services/collector-api/syosint/models.py`
- Create: `services/collector-api/alembic/versions/0002_rss_collection.py`
- Create: `services/collector-api/syosint/rss_store.py`
- Create: `services/collector-api/syosint/rss_scheduler.py`
- Modify: `services/collector-api/syosint/api.py`
- Create: `services/collector-api/tests/test_rss_store.py`
- Create: `services/collector-api/tests/test_rss_scheduler.py`

**Interfaces:**
- Produces models: `FeedItem`, `FeedCursor`, `FeedQuarantine` and RSS fields on `Source`.
- Produces: `store_collection(db: Session, source: Source, outcome: SourceOutcome, now: datetime) -> StoreSummary`.
- Produces: `collect_due_sources(engine, collector, now: datetime) -> SchedulerSummary`.
- Consumes: Task 3 `SourceOutcome`; existing audit `record()`.

- [ ] **Step 1: Write migration and persistence tests**

Test upgrade from the initial schema, restart persistence, idempotent fingerprints, cursor validators, health counters, duplicate state and quarantine digests:

```python
def test_collection_is_idempotent_and_persists_cursor(engine):
    first = store_collection(session(engine), SOURCE, OUTCOME, NOW)
    second = store_collection(session(engine), SOURCE, OUTCOME, NOW)
    assert first.created == 1
    assert second.created == 0
    assert second.duplicates == 1
    assert session(engine).get(FeedCursor, SOURCE.id).etag == '"v1"'
```

- [ ] **Step 2: Write scheduler tests**

Use a fake clock and collector to prove due-only polling, 30-minute defaults, no overlap and persisted restart behavior.

- [ ] **Step 3: Run tests and verify failure**

Run: `PYTHONPATH=services/collector-api .venv314/bin/python -m pytest services/collector-api/tests/test_rss_store.py services/collector-api/tests/test_rss_scheduler.py -q`

Expected: FAIL because migration and store modules are absent.

- [ ] **Step 4: Add migration and models**

Extend `sources` with `kind` (`manual` or `rss`), nullable `feed_url`, `enabled`, and `poll_interval_minutes`. Add:

```python
class FeedItem(Base):
    id: Mapped[int]
    source_id: Mapped[int]
    fingerprint: Mapped[str]
    native_id: Mapped[str | None]
    headline: Mapped[str]
    url: Mapped[str]
    text: Mapped[str]
    published_at: Mapped[datetime]
    collected_at: Mapped[datetime]
    raw_digest: Mapped[str]
    status: Mapped[str]  # new, promoted, attached, duplicate
    incident_id: Mapped[int | None]
```

Use a unique constraint on `(source_id, fingerprint)`. `FeedCursor` has one row per source; `FeedQuarantine` stores reason and digest without public projection.

- [ ] **Step 5: Implement transactional storage and scheduling**

Persist items, quarantine, cursor and health in one transaction per source. Audit material source-health changes and item promotion state, but avoid one audit row for an unchanged `304`. Implement the scheduler with `asyncio`, one in-process lock, a stop event and a short tick interval; compute actual due times from persisted cursors.

- [ ] **Step 6: Wire scheduler lifecycle into FastAPI**

Create the scheduler in the FastAPI lifespan, start it after migrations, and always cancel and await it during shutdown. Support `SYOSINT_RSS_SCHEDULER=0` for tests and local troubleshooting; default is enabled.

- [ ] **Step 7: Run migration, store, scheduler and existing API tests**

Run: `PYTHONPATH=services/collector-api .venv314/bin/python -m pytest services/collector-api/tests/test_rss_store.py services/collector-api/tests/test_rss_scheduler.py services/collector-api/tests/test_workflow.py -q`

Expected: PASS with no orphan scheduler tasks.

- [ ] **Step 8: Commit private persistence and scheduling**

```bash
git add services/collector-api/alembic services/collector-api/syosint services/collector-api/tests
git commit -m "feat: persist and schedule private RSS collection"
```

---

### Task 5: Feed-source, inbox, attach and promotion APIs

**Files:**
- Modify: `services/collector-api/syosint/api.py`
- Create: `services/collector-api/tests/test_rss_api.py`

**Interfaces:**
- Produces: `POST /feeds`, `GET /feeds`, `POST /feeds/{id}/collect`.
- Produces: `GET /feed-items?status=new|promoted|attached|duplicate|quarantined`.
- Produces: `POST /feed-items/{id}/promote` and `POST /feed-items/{id}/attach`.
- Consumes: Task 4 models/storage; existing Incident, Evidence and audit contracts.

- [ ] **Step 1: Write failing endpoint tests**

Exercise feed registration, manual collection, status filtering, promotion, attach and prohibited state changes:

```python
def test_promote_creates_triage_case_and_evidence_once(client, collected_item):
    payload = {
        "title_en": "Analyst English title",
        "title_ar": "عنوان المحلل بالعربية",
        "category": "political-security",
    }
    first = client.post(f"/feed-items/{collected_item}/promote", json=payload)
    second = client.post(f"/feed-items/{collected_item}/promote", json=payload)
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["incident_id"] == first.json()["incident_id"]
    assert len(client.get(f"/incidents/{first.json()['incident_id']}/evidence").json()) == 1

def test_attach_rejects_approved_incident(client, collected_item, approved_incident):
    response = client.post(f"/feed-items/{collected_item}/attach", json={"incident_id": approved_incident})
    assert response.status_code == 409
```

- [ ] **Step 2: Run endpoint tests and confirm 404 failures**

Run: `PYTHONPATH=services/collector-api .venv314/bin/python -m pytest services/collector-api/tests/test_rss_api.py -q`

Expected: FAIL because routes are not registered.

- [ ] **Step 3: Add strict request and response models**

Add `FeedSourceInput`, `PromoteFeedItemInput` and `AttachFeedItemInput`. Reuse public HTTPS validation, require `poll_interval_minutes` from 15 through 1440, require analyst-written bilingual titles and an existing category on promotion, and forbid extra fields.

- [ ] **Step 4: Implement endpoints transactionally**

Promotion creates an Incident in `triage`, creates Evidence using the collected local text and provenance, marks the item promoted, and records audit entries in one transaction. Repeated calls return the existing incident. Attach rejects approved/locked incidents and repeated attachment without duplicating evidence.

- [ ] **Step 5: Run RSS and existing workflow API tests**

Run: `PYTHONPATH=services/collector-api .venv314/bin/python -m pytest services/collector-api/tests -q`

Expected: PASS.

- [ ] **Step 6: Commit the RSS analyst API**

```bash
git add services/collector-api/syosint/api.py services/collector-api/tests/test_rss_api.py
git commit -m "feat: expose RSS inbox and promotion APIs"
```

---

### Task 6: Private analyst RSS inbox

**Files:**
- Modify: `apps/analyst-desk/src/lib/api.ts`
- Modify: `apps/analyst-desk/src/app/actions.ts`
- Create: `apps/analyst-desk/src/app/rss/page.tsx`
- Modify: `apps/analyst-desk/src/app/page.tsx`
- Modify: `apps/analyst-desk/src/app/style.css`
- Create: `apps/analyst-desk/src/app/rss/page.test.tsx`
- Modify: `apps/analyst-desk/e2e/workflow.spec.ts`

**Interfaces:**
- Produces UI actions: `addFeed`, `collectFeed`, `promoteFeedItem`, `attachFeedItem`.
- Consumes Task 5 routes and response types: `FeedSource`, `FeedItem`, `FeedHealth`.

- [ ] **Step 1: Write failing component tests**

Mock server-side API responses and assert that new, promoted, duplicate and quarantined groups are distinguishable, raw text is marked private, and promotion requires human titles/category:

```tsx
expect(screen.getByRole("heading", { name: "RSS inbox" })).toBeInTheDocument();
expect(screen.getByText("New · 2")).toBeInTheDocument();
expect(screen.getByLabelText("Analyst English title")).toBeRequired();
expect(screen.getByText("Stored locally — never public automatically")).toBeInTheDocument();
```

- [ ] **Step 2: Run the desk test and verify failure**

Run: `corepack pnpm --filter @syosint/analyst-desk test`

Expected: FAIL because the RSS route does not exist.

- [ ] **Step 3: Add typed API records and server actions**

Extend `api.ts` with exact feed response types. Validate numeric IDs through the existing helper pattern. Each action redirects to `/rss` on success and uses the existing bounded error redirect on failure.

- [ ] **Step 4: Build the inbox interface**

Add a homepage link and a `/rss` page with source health, add-feed form, collect-now control, filters, quarantine reason codes, original public links, private text disclosure, promotion form and attach form. Preserve loopback-only operation and keyboard-visible focus styles.

- [ ] **Step 5: Extend the synthetic browser workflow**

Serve a synthetic feed from the test harness, register it, collect it, promote one item with analyst-written bilingual titles, and assert that the resulting case is in triage with one evidence record.

- [ ] **Step 6: Run desk tests, type checks and build**

Run:

```bash
corepack pnpm --filter @syosint/analyst-desk test
corepack pnpm --filter @syosint/analyst-desk typecheck
corepack pnpm --filter @syosint/analyst-desk build
```

Expected: PASS.

- [ ] **Step 7: Commit the private inbox**

```bash
git add apps/analyst-desk
git commit -m "feat: add private RSS review inbox"
```

---

### Task 7: Bilingual public Live News Wire

**Files:**
- Create: `apps/public-dashboard/src/lib/load-public-news-wire.ts`
- Create: `apps/public-dashboard/src/lib/load-public-news-wire.test.ts`
- Create: `apps/public-dashboard/src/lib/filter-news-wire.ts`
- Create: `apps/public-dashboard/src/lib/filter-news-wire.test.ts`
- Create: `apps/public-dashboard/src/components/NewsWire.tsx`
- Create: `apps/public-dashboard/src/components/NewsWire.test.tsx`
- Create: `apps/public-dashboard/scripts/sync-public-data.mjs`
- Modify: `apps/public-dashboard/package.json`
- Modify: `.gitignore`
- Modify: `apps/public-dashboard/src/components/DashboardClient.tsx`
- Modify: `apps/public-dashboard/src/app/page.tsx`
- Modify: `apps/public-dashboard/src/i18n/types.ts`
- Modify: `apps/public-dashboard/src/i18n/en.ts`
- Modify: `apps/public-dashboard/src/i18n/ar.ts`
- Modify: `apps/public-dashboard/src/app/globals.css`
- Modify: `apps/public-dashboard/e2e/dashboard.spec.ts`

**Interfaces:**
- Produces: `loadPublicNewsWire(): PublicNewsWire`.
- Produces: `filterNewsWire(entries, { sourceIds, languages }): PublicNewsWireEntry[]`.
- Produces: `NewsWire({ wire, locale, dictionary })`.
- Consumes: Task 1 public schema/types and checked-in/generated JSON.

- [ ] **Step 1: Write loader and filter tests**

Assert schema validation, newest-first ordering, source filtering, language filtering and immutable input behavior.

- [ ] **Step 2: Write component tests**

Test both locales, persistent unverified wording, original-language headlines, last refresh, safe external-link attributes, empty state and delayed state:

```tsx
expect(screen.getByRole("heading", { name: "Live News Wire" })).toBeInTheDocument();
expect(screen.getByText("Unverified external reporting")).toBeVisible();
expect(screen.getByRole("link", { name: /خبر تجريبي/ })).toHaveAttribute("rel", "noopener noreferrer");
```

- [ ] **Step 3: Run public tests and verify failure**

Run: `corepack pnpm --filter @syosint/public-dashboard test`

Expected: FAIL because loader, filter and component are missing.

- [ ] **Step 4: Implement loader, filters and translations**

Load `data/public/news-wire.v1.json` at build time and fail closed on schema errors. Add `newsWire` dictionary keys for title, disclosure, refreshed, source filter, language filter, empty, delayed and external-link context in English and Arabic.

Add a prebuild/predev script that validates and copies the same dataset to `apps/public-dashboard/public/news-wire.v1.json`. Ignore that generated copy in Git; the static export exposes it at `/syOSINT/news-wire.v1.json` so the next scheduled run can retrieve the last deployed dataset.

- [ ] **Step 5: Implement the news-wire component and dashboard placement**

Render the wire after the header/demo banner and before incident summary cards. Use semantic `<section>`, `<article>` and `<time>` elements; keep incident search and filters independent. Show a compact source/language filter and newest-first bounded list.

- [ ] **Step 6: Extend browser coverage**

Assert that the wire renders, switches RTL labels with the existing locale control, filters source/language, preserves incident filters, and makes no runtime RSS or map-service requests.

- [ ] **Step 7: Run public tests and build**

Run:

```bash
corepack pnpm --filter @syosint/public-dashboard test
corepack pnpm --filter @syosint/public-dashboard typecheck
corepack pnpm --filter @syosint/public-dashboard build
```

Expected: PASS and static export contains the wire.

- [ ] **Step 8: Commit the public wire UI**

```bash
git add apps/public-dashboard
git commit -m "feat: display bilingual live RSS news wire"
```

---

### Task 8: Scheduled Pages deployment, initial source verification and operations

**Files:**
- Create: `.github/workflows/rss-wire.yml`
- Modify: `.github/workflows/deploy-pages.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `package.json`
- Modify: `README.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/PROJECT_STATE.md`
- Create: `docs/source-policy/RSS.md`
- Modify: `docs/methodology/METHODOLOGY.md`

**Interfaces:**
- Produces workflow: scheduled `cron: '*/30 * * * *'` plus `workflow_dispatch`.
- Produces package commands: `collect:rss:public`, `test:rss`, and existing full verification commands.
- Consumes: Task 3 CLI, Task 7 static dashboard build.

- [ ] **Step 1: Add a workflow-policy test before the workflow**

Extend the repository policy/unit checks to parse `.github/workflows/rss-wire.yml` and assert the schedule, read-only contents permission, Pages-only write permissions, Python 3.14, schema validation before build, and `concurrency.group: pages`.

- [ ] **Step 2: Run the policy test and verify failure**

Run: `corepack pnpm test`

Expected: FAIL because `rss-wire.yml` is missing.

- [ ] **Step 3: Create the scheduled workflow**

The build job must:

```yaml
on:
  schedule:
    - cron: "*/30 * * * *"
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false
```

Check out `main`, set up Python 3.14 and Node 24, install locked dependencies, run the collector with `--previous-url https://yasar2019.github.io/syOSINT/news-wire.v1.json`, validate the generated dataset, build the static site, upload the Pages artifact and deploy it. Preserve the existing CI-gated deployment for pushes to `main`; both workflows share the Pages concurrency group.

- [ ] **Step 4: Validate the initial allowlist with the real CLI**

Run:

```bash
PYTHONPATH=services/collector-api .venv314/bin/python -m syosint.rss_cli check-source https://news.un.org/feed/subscribe/en/news/region/middle-east/feed/rss.xml
PYTHONPATH=services/collector-api .venv314/bin/python -m syosint.rss_cli check-source https://feeds.bbci.co.uk/arabic/rss.xml
```

Expected: both resolve to public HTTPS endpoints, parse as RSS/Atom within limits and return safe source metadata. If either endpoint fails, disable that exact allowlist entry and record its safe failure category in the PR; do not substitute an unreviewed source.

- [ ] **Step 5: Generate a real local public artifact and inspect its projection**

Run:

```bash
PYTHONPATH=services/collector-api .venv314/bin/python -m syosint.rss_cli collect-public --config config/rss-sources.json --output /tmp/news-wire.v1.json
.venv314/bin/python -m json.tool /tmp/news-wire.v1.json
```

Confirm every entry contains exactly the public keys from Task 1 and every headline matches its configured Syria-topic terms. Do not commit the live generated file.

- [ ] **Step 6: Write operating and source-policy documentation**

Document allowlist review, feed ownership/attribution, 30-minute scheduling, deterministic topic filters, local scheduling, health categories, quarantine, stale recovery, Python 3.14 setup and the difference between automatic external headlines and reviewed incidents.

- [ ] **Step 7: Run complete verification**

Run:

```bash
corepack pnpm policy:check
corepack pnpm audit --audit-level high
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
PYTHONPATH=services/collector-api .venv314/bin/python -m pytest services/collector-api/tests -q
.venv314/bin/python -m pip_audit --local
corepack pnpm build:desk
corepack pnpm build
corepack pnpm test:e2e
corepack pnpm --filter @syosint/analyst-desk test:e2e
```

Expected: all commands PASS. JavaScript audit may report lower-severity advisories below the configured high threshold; record them in the PR without weakening the gate.

- [ ] **Step 8: Update state documentation and commit**

Mark Milestone 2 complete, Milestone 3 implemented pending review, identify the new workflow and document the narrow metadata-only automatic-publication exception.

```bash
git add .github/workflows package.json README.md docs
git commit -m "ci: deploy the RSS wire every thirty minutes"
```

---

### Task 9: Review checkpoint and pull request

**Files:**
- Review: all Milestone 3 changes against `docs/superpowers/specs/2026-09-23-rss-collection-design.md`
- Update only if findings require changes: affected implementation, tests and documentation

**Interfaces:**
- Consumes: all prior task deliverables.
- Produces: a clean branch, green CI, review findings addressed and a reviewable pull request stacked on Milestone 2 until PR #2 is merged.

- [ ] **Step 1: Verify repository state and commit history**

Run:

```bash
git status --short
git log --oneline --decorate -12
git diff --check origin/feat/analyst-desk...HEAD
```

Expected: clean worktree, focused commits and no whitespace errors.

- [ ] **Step 2: Request an independent whole-branch review**

Ask the reviewer to prioritize SSRF/DNS behavior, automatic-publication boundaries, schema privacy, scheduler shutdown/idempotency, duplicate evidence, stale artifact handling and the visual separation of wire versus incidents.

- [ ] **Step 3: Reproduce each material finding with a failing test**

For every accepted finding, add the smallest regression test to the owning task’s test file, run it to observe failure, implement the fix, and rerun the focused suite.

- [ ] **Step 4: Rerun complete verification after review fixes**

Run the exact Task 8 Step 7 command set and require all gates to pass.

- [ ] **Step 5: Open the pull request**

Open a draft PR from `feat/rss-collection` to `feat/analyst-desk` while PR #2 is open. Include the architecture, public metadata exception, initial allowlist status, Python version, security review, test counts and scheduled-deployment behavior. Mark it ready only after CI succeeds and review findings are addressed. Retarget it to `main` after PR #2 merges; do not merge without the user’s final approval.
