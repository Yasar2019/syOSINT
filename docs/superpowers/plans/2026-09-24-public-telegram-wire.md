# Human-Approved Public Telegram Wire Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an analyst publish individually reviewed Telegram leads with human-written English and Arabic headlines to a separate validated public dashboard wire.

**Architecture:** Add an append-only local publication record linked to shared intake, generate a gitignored pending artifact after an item-specific safety gate, and require a separate CLI staging command to merge sanitized records into tracked `data/public/telegram-wire.v1.json`. The static dashboard loads this contract alongside RSS, while corrections and withdrawals require new explicit editorial actions.

**Tech Stack:** Python 3.14.7, FastAPI, Pydantic, SQLAlchemy/Alembic, jsonschema, pytest, JSON Schema 2020-12, TypeScript, React/Next.js static export, Vitest, Testing Library, Playwright, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-24-source-expansion-telegram-design.md`

## Global Constraints

- Channel approval authorizes collection only; every public Telegram item requires item-specific human approval.
- Public headlines must be written manually in English and Arabic without AI/ML assistance.
- Never export original post text, media, private notes, phone numbers, credentials, session data, access hashes, local paths, or generated text.
- Label public entries **Reviewed external Telegram report — not independently verified**.
- Keep active/corrected/withdrawn public history append-only and never rewrite it from collector callbacks.
- Show active and corrected leads for seven days from source publication time; show withdrawal markers for the remainder of that window.
- The collector and GitHub Actions must not pull Telegram data directly.

## Review Focus

- A collected post edited between preview and approval must invalidate the preview and require a new review.
- A public URL that is not exactly an HTTPS `t.me/{approved_username}/{numeric_id}` link must fail closed.
- A deleted source post must create urgent review but must not automatically delete or rewrite the public artifact.
- A staged dataset containing any raw text, media path, session field, or unknown property must fail validation.
- Repeated approval or staging of the same revision must be idempotent and must not duplicate public IDs.

---

### Task 1: Define the public Telegram wire contract

**Files:**
- Create: `packages/schemas/src/public-telegram-wire.schema.json`
- Modify: `packages/schemas/src/types.ts`
- Modify: `packages/schemas/src/validate.ts`
- Modify: `packages/schemas/src/validate.test.ts`
- Create: `data/public/telegram-wire.v1.json`

**Interfaces:**
- Produces: `PublicTelegramWire`, `PublicTelegramEntry`, `PublicTelegramRevision`, and `validatePublicTelegramWire(value)`.

- [ ] **Step 1: Write failing schema tests**

```ts
const telegramWire = {
  schemaVersion: "1.0.0",
  generatedAt: "2026-09-24T16:00:00Z",
  lastEditorialUpdateAt: "2026-09-24T16:00:00Z",
  entries: [{
    id: "telegram:example:42",
    status: "active",
    channel: { name: "Example channel", username: "example", language: "en" },
    url: "https://t.me/example/42",
    headline: { en: "Analyst headline", ar: "عنوان المحلل" },
    publishedAt: "2026-09-24T15:00:00Z",
    approvedAt: "2026-09-24T16:00:00Z",
    revisions: [],
  }],
};

it.each(["rawText", "mediaPath", "session", "phone"])("rejects %s", (field) => {
  const input = structuredClone(telegramWire) as any;
  input.entries[0][field] = "forbidden";
  expect(validatePublicTelegramWire(input).ok).toBe(false);
});
```

Add tests for duplicate IDs, non-`t.me` URLs, username/link mismatch, empty bilingual headlines, and invalid correction history.

- [ ] **Step 2: Run schema tests and confirm failure**

Run: `corepack pnpm --filter @syosint/schemas test`

Expected: FAIL because the Telegram schema and validator do not exist.

- [ ] **Step 3: Implement the exact contract and validation**

```ts
export interface PublicTelegramEntry {
  id: string;
  status: "active" | "corrected" | "withdrawn";
  channel: { name: string; username: string; language: "en" | "ar" | "mixed" };
  url: string;
  headline: LocalizedText;
  publishedAt: string;
  approvedAt: string;
  revisions: Array<{
    revisedAt: string;
    action: "corrected" | "withdrawn";
    reason: LocalizedText;
    previousHeadline?: LocalizedText;
  }>;
}
```

Use `additionalProperties: false` on all objects, HTTPS `t.me` URL patterns, username patterns, unique IDs, and a semantic validator that confirms the URL username matches `channel.username` case-insensitively. Require `previousHeadline` for `corrected` revisions and forbid it for `withdrawn` revisions so public correction history preserves the superseded wording.

- [ ] **Step 4: Run schema tests**

Run: `corepack pnpm --filter @syosint/schemas test`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/schemas/src/public-telegram-wire.schema.json packages/schemas/src/types.ts packages/schemas/src/validate.ts packages/schemas/src/validate.test.ts data/public/telegram-wire.v1.json
git commit -m "feat: define public Telegram wire contract"
```

### Task 2: Persist append-only publication review

**Files:**
- Create: `services/collector-api/alembic/versions/0004_telegram_publication.py`
- Modify: `services/collector-api/syosint/models.py`
- Create: `services/collector-api/syosint/telegram_publication.py`
- Create: `services/collector-api/tests/test_telegram_publication.py`

**Interfaces:**
- Produces: `TelegramPublication`, `TelegramPublicationRevision`, `PublicationDraft`, `build_publication_preview(db, intake_item_id, payload) -> PublicationDraft`, and `approve_publication(db, draft_hash, payload) -> TelegramPublication`.

- [ ] **Step 1: Write failing preview and stale-review tests**

```python
def test_preview_contains_only_sanitized_fields(db, telegram_item):
    preview = build_publication_preview(db, telegram_item.id, approval_payload())
    assert set(preview.record) == {
        "id", "status", "channel", "url", "headline",
        "publishedAt", "approvedAt", "revisions"
    }
    assert telegram_item.text not in json.dumps(preview.record)

def test_changed_source_digest_invalidates_preview(db, telegram_item):
    preview = build_publication_preview(db, telegram_item.id, approval_payload())
    telegram_item.raw_digest = "f" * 64
    db.commit()
    with pytest.raises(PublicationConflict, match="source changed"):
        approve_publication(db, preview.draft_hash, approval_payload())
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_telegram_publication.py -q`

Expected: FAIL because publication models and services do not exist.

- [ ] **Step 3: Implement append-only records and the safety gate**

```python
@dataclass(frozen=True)
class PublicationPayload:
    headline_en: str
    headline_ar: str
    person_safety_checked: bool
    operational_safety_checked: bool
    source_identity_checked: bool
    human_approved: bool
```

Require a Telegram intake item from an approved public channel, current digest match, a permanent public `t.me` link, nonempty bilingual headlines, every checklist flag, and no deletion marker. Store hashes and audit events, not raw text, in publication tables.

- [ ] **Step 4: Run publication and migration tests**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_telegram_publication.py services/collector-api/tests/test_intake_migration.py -q`

Expected: PASS with idempotent repeated approval of the same draft.

- [ ] **Step 5: Commit**

```bash
git add services/collector-api/alembic/versions/0004_telegram_publication.py services/collector-api/syosint/models.py services/collector-api/syosint/telegram_publication.py services/collector-api/tests/test_telegram_publication.py
git commit -m "feat: gate public Telegram publication"
```

### Task 3: Export pending artifacts and stage tracked public data

**Files:**
- Create: `services/collector-api/syosint/telegram_export.py`
- Create: `services/collector-api/syosint/telegram_publish_cli.py`
- Create: `services/collector-api/tests/test_telegram_export.py`
- Modify: `package.json`

**Interfaces:**
- Produces: `write_pending_telegram_export(directory, records, now) -> Path`, `stage_telegram_wire(pending, current, output, now) -> Path`, and CLI `python -m syosint.telegram_publish_cli stage --pending PATH --output data/public/telegram-wire.v1.json`.

- [ ] **Step 1: Write failing fail-closed staging tests**

```python
def test_stage_rejects_unknown_or_private_fields(tmp_path):
    pending = write_json(tmp_path / "pending.json", wire(extra={"rawText": "secret"}))
    with pytest.raises(PublicSchemaError):
        stage_telegram_wire(pending, empty_wire(), tmp_path / "public.json", NOW)
    assert not (tmp_path / "public.json").exists()

def test_stage_is_idempotent_and_prunes_expired_active_items(tmp_path):
    output = stage_twice(same_record(), expired_record(), tmp_path)
    assert [entry["id"] for entry in output["entries"]] == [same_record()["id"]]
```

- [ ] **Step 2: Run export tests and confirm failure**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_telegram_export.py -q`

Expected: FAIL because export and staging functions do not exist.

- [ ] **Step 3: Implement atomic pending and tracked writes**

```python
def stage_telegram_wire(pending: Path, current: Path, output: Path, now: datetime) -> Path:
    candidate = merge_by_stable_id(load(current), load(pending))
    candidate["entries"] = retain_seven_days(candidate["entries"], now)
    validate_public_telegram_wire(candidate)
    return atomic_json_write(output, candidate)
```

Pending output stays under mode-`0o700` `pending-exports/`. The staging CLI requires `--confirm-publication`, validates before replacement, and prints IDs/counts only.

- [ ] **Step 4: Run export, schema, and secret tests**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_telegram_export.py -q && corepack pnpm --filter @syosint/schemas test && corepack pnpm policy:check`

Expected: PASS; output contains no forbidden fields and repeated staging does not duplicate records.

- [ ] **Step 5: Commit**

```bash
git add services/collector-api/syosint/telegram_export.py services/collector-api/syosint/telegram_publish_cli.py services/collector-api/tests/test_telegram_export.py package.json
git commit -m "feat: stage sanitized Telegram wire"
```

### Task 4: Add preview, approval, correction, and withdrawal endpoints

**Files:**
- Modify: `services/collector-api/syosint/api.py`
- Create: `services/collector-api/tests/test_telegram_publication_api.py`

**Interfaces:**
- API: `POST /intake-items/{id}/publication-preview`, `POST /intake-items/{id}/publication-approve`, `POST /telegram-publications/{id}/correct`, `POST /telegram-publications/{id}/withdraw`, and `GET /telegram-publications/attention`. Approval writes the sanitized record to the configured gitignored pending-export directory after the database transaction commits.

- [ ] **Step 1: Write failing lifecycle API tests**

```python
def test_preview_then_approve_requires_exact_hash(client, telegram_item):
    preview = client.post(f"/intake-items/{telegram_item}/publication-preview", json=payload())
    assert preview.status_code == 200
    rejected = client.post(
        f"/intake-items/{telegram_item}/publication-approve",
        json={**payload(), "draft_hash": "0" * 64},
    )
    assert rejected.status_code == 409

def test_deleted_public_item_enters_attention_without_auto_withdraw(client, published):
    mark_source_deleted(published.intake_item_id)
    assert client.get("/telegram-publications/attention").json()[0]["reason"] == "source-deleted"
    assert public_record(published.id).status == "active"
```

- [ ] **Step 2: Run API tests and confirm failure**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_telegram_publication_api.py -q`

Expected: FAIL because lifecycle endpoints do not exist.

- [ ] **Step 3: Implement strict payloads and audited transitions**

```python
class PublicationApprovalInput(Strict):
    draft_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    headline_en: str = Field(min_length=3, max_length=240)
    headline_ar: str = Field(min_length=3, max_length=240)
    source_identity_checked: bool
    person_safety_checked: bool
    operational_safety_checked: bool
    human_approved: bool
```

Correction requires new bilingual headlines and bilingual reason. Withdrawal requires bilingual reason. Neither endpoint may accept source text, media, or arbitrary metadata.

- [ ] **Step 4: Run lifecycle and general workflow tests**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_telegram_publication_api.py services/collector-api/tests/test_workflow.py -q`

Expected: PASS with complete audit events and no automatic source-change mutation.

- [ ] **Step 5: Commit**

```bash
git add services/collector-api/syosint/api.py services/collector-api/tests/test_telegram_publication_api.py
git commit -m "feat: add Telegram editorial lifecycle API"
```

### Task 5: Build the analyst publication review interface

**Files:**
- Create: `apps/analyst-desk/src/app/telegram/publication/[id]/page.tsx`
- Create: `apps/analyst-desk/src/app/telegram/publication/[id]/page.test.tsx`
- Modify: `apps/analyst-desk/src/app/telegram/page.tsx`
- Modify: `apps/analyst-desk/src/app/actions.ts`
- Modify: `apps/analyst-desk/src/lib/api.ts`
- Modify: `apps/analyst-desk/src/app/style.css`
- Modify: `apps/analyst-desk/e2e/workflow.spec.ts`

**Interfaces:**
- Consumes: Task 4 lifecycle endpoints.
- Produces: exact sanitized preview, safety checklist, explicit approval, correction, withdrawal, and attention queue UI.

- [ ] **Step 1: Write failing analyst UI tests**

```tsx
expect(screen.getByText("Original Telegram text stays private")).toBeVisible();
expect(screen.getByLabelText("English public headline")).toBeRequired();
expect(screen.getByLabelText("Arabic public headline")).toHaveAttribute("dir", "rtl");
expect(screen.getByRole("checkbox", { name: /person safety/i })).not.toBeChecked();
expect(screen.getByRole("button", { name: "Approve public Telegram lead" })).toBeDisabled();
```

Assert the preview displays only the exact public contract and that a stale-draft 409 returns to review with a visible source-changed warning.

- [ ] **Step 2: Run UI tests and confirm failure**

Run: `corepack pnpm test -- apps/analyst-desk/src/app/telegram/publication/[id]/page.test.tsx`

Expected: FAIL because the publication route and actions do not exist.

- [ ] **Step 3: Implement the review UI and server actions**

```ts
export type TelegramPublicationPreview = {
  draft_hash: string;
  record: PublicTelegramEntry;
};
```

Use separate preview and approve actions. Approval posts the preview hash and the exact same form values. Never serialize original Telegram text into hidden inputs, URLs, browser storage, or client logs.

- [ ] **Step 4: Run unit and end-to-end review tests**

Run: `corepack pnpm test -- apps/analyst-desk && corepack pnpm --filter @syosint/analyst-desk test:e2e`

Expected: PASS for preview, stale source, approval, correction, withdrawal, Arabic input, and keyboard use.

- [ ] **Step 5: Commit**

```bash
git add apps/analyst-desk/src/app/telegram apps/analyst-desk/src/app/actions.ts apps/analyst-desk/src/lib/api.ts apps/analyst-desk/src/app/style.css apps/analyst-desk/e2e/workflow.spec.ts
git commit -m "feat: review public Telegram leads"
```

### Task 6: Integrate the Telegram wire into the public dashboard

**Files:**
- Create: `apps/public-dashboard/src/lib/load-public-telegram-wire.ts`
- Create: `apps/public-dashboard/src/lib/load-public-telegram-wire.test.ts`
- Create: `apps/public-dashboard/src/components/SourceReporting.tsx`
- Create: `apps/public-dashboard/src/components/SourceReporting.test.tsx`
- Modify: `apps/public-dashboard/src/components/NewsWire.tsx`
- Modify: `apps/public-dashboard/src/components/DashboardClient.tsx`
- Modify: `apps/public-dashboard/src/app/page.tsx`
- Modify: `apps/public-dashboard/src/i18n/types.ts`
- Modify: `apps/public-dashboard/src/i18n/en.ts`
- Modify: `apps/public-dashboard/src/i18n/ar.ts`
- Modify: `apps/public-dashboard/src/app/globals.css`
- Modify: `apps/public-dashboard/e2e/dashboard.spec.ts`

**Interfaces:**
- Consumes: validated `PublicNewsWire` and `PublicTelegramWire`.
- Produces: All reporting, RSS / Atom, and Approved Telegram views with shared source/language filters and platform-specific disclosures.

- [ ] **Step 1: Write failing loader and component tests**

```tsx
expect(screen.getByRole("tab", { name: "All reporting" })).toBeVisible();
expect(screen.getByRole("tab", { name: "RSS / Atom" })).toBeVisible();
fireEvent.click(screen.getByRole("tab", { name: "Approved Telegram" }));
expect(screen.getByText("Reviewed external Telegram report — not independently verified")).toBeVisible();
expect(screen.getByRole("link", { name: /Analyst headline/ })).toHaveAttribute(
  "href", "https://t.me/example/42"
);
```

Add Arabic assertions showing `headline.ar`, RTL direction, correction history, withdrawal marker, and last editorial update distinct from RSS refresh. Assert English/Arabic source-language filters include `mixed` channels in either language and display each Telegram entry in the selected UI language.

- [ ] **Step 2: Run dashboard tests and confirm failure**

Run: `corepack pnpm test -- apps/public-dashboard/src/lib/load-public-telegram-wire.test.ts apps/public-dashboard/src/components/SourceReporting.test.tsx`

Expected: FAIL because the loader and reporting component do not exist.

- [ ] **Step 3: Implement validated loading and combined presentation**

```tsx
type ReportingMode = "all" | "rss" | "telegram";
const telegramEntries = telegramWire.entries.filter(
  (entry) => Date.parse(entry.publishedAt) >= Date.now() - 7 * 24 * 60 * 60 * 1000,
);
```

Do not display original post text or media. Use selected locale for analyst headlines and expose corrections/withdrawals without implying verification.

- [ ] **Step 4: Run dashboard unit, build, and browser tests**

Run: `corepack pnpm test -- apps/public-dashboard && corepack pnpm build && corepack pnpm test:e2e`

Expected: PASS for static export, base path, mobile pagination, tabs, English/Arabic, RTL, and disclosures.

- [ ] **Step 5: Commit**

```bash
git add apps/public-dashboard/src apps/public-dashboard/e2e/dashboard.spec.ts
git commit -m "feat: show approved Telegram reports publicly"
```

### Task 7: Validate Telegram data in every Pages deployment

**Files:**
- Modify: `apps/public-dashboard/scripts/sync-public-data.mjs`
- Create: `apps/public-dashboard/scripts/sync-public-data.test.ts`
- Modify: `.github/workflows/deploy-pages.yml`
- Modify: `.github/workflows/rss-wire.yml`
- Modify: `package.json`
- Modify: `README.md`
- Modify: `docs/methodology/METHODOLOGY.md`
- Modify: `docs/source-policy/TELEGRAM.md`
- Modify: `docs/PROJECT_STATE.md`

**Interfaces:**
- Consumes: tracked `data/public/telegram-wire.v1.json` only.
- Produces: static `apps/public-dashboard/public/telegram-wire.v1.json`; both Pages workflows validate both public contracts before build/deploy.

- [ ] **Step 1: Add a failing sync-script fixture test**

```js
await expect(syncPublicData({ telegram: invalidPrivateFieldFixture }))
  .rejects.toThrow("Invalid public Telegram wire");
```

The RSS workflow test must assert it never invokes Telegram APIs and only copies the already tracked Telegram artifact.

- [ ] **Step 2: Implement dual-contract validation**

```js
const datasets = [
  ["news-wire.v1.json", "public-news-wire.schema.json"],
  ["telegram-wire.v1.json", "public-telegram-wire.schema.json"],
];
```

Validate both with AJV, enforce unique IDs, and copy only after all validation succeeds. Keep Telegram credentials absent from both workflows.

- [ ] **Step 3: Run the final verification matrix**

Run:

```bash
.venv314/bin/python -m pytest services/collector-api/tests -q
.venv314/bin/python -m pip_audit --local
corepack pnpm policy:check
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
corepack pnpm build:desk
corepack pnpm test:e2e
git diff --check
```

Expected: every command exits 0; static output contains both validated wires; no Telegram credential, session, raw text, or media is present.

- [ ] **Step 4: Update documentation and project state**

Document the two-stage local approval/staging flow, public labels, seven-day display, correction/withdrawal rules, manual PR deployment, and explicit prohibition on sharing Telegram-derived content with AI/ML systems. Mark Milestone 4 complete only after all three pull requests merge and Pages deployment succeeds.

- [ ] **Step 5: Commit**

```bash
git add apps/public-dashboard/scripts/sync-public-data.mjs apps/public-dashboard/scripts/sync-public-data.test.ts .github/workflows/deploy-pages.yml .github/workflows/rss-wire.yml package.json README.md docs/methodology/METHODOLOGY.md docs/source-policy/TELEGRAM.md docs/PROJECT_STATE.md
git commit -m "docs: operate the public Telegram wire"
```
