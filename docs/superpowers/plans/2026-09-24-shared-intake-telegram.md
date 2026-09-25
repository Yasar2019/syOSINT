# Shared Intake and Local Telegram Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate RSS into a platform-neutral private intake workflow and add secure, read-only local collection from manually approved public Telegram channels.

**Architecture:** Keep platform adapters behind narrow protocols and normalize durable items into shared intake tables. Telethon owns transport and its local session, while syOSINT owns source approval, cursors, revisions, quarantine, optional media metadata, audit, and analyst workflows. Telegram setup failure must never prevent RSS or the local API from operating.

**Tech Stack:** Python 3.14.7, Telethon 1.45.0, FastAPI, Pydantic, SQLAlchemy, Alembic, SQLite, pytest, Next.js/React server actions, TypeScript, Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-24-source-expansion-telegram-design.md`

## Global Constraints

- Pin Telethon 1.45.0 unless a newer stable patch passes Python 3.14 compatibility tests and dependency audit before merge.
- Use analyst-owned official Telegram API credentials and store the session only under gitignored `private-data/telegram/`.
- Support approved public channel usernames only; never private/invite-only identifiers or automatic discovery.
- Expose no send, react, moderation, or private-join operation.
- Never send Telegram-derived text or media to AI/ML systems.
- Disable media download by default; when enabled, enforce 10 MB per file and 30-day retention.
- Treat Telegram text as untrusted plain text in every UI.
- Preserve existing RSS item identity, workflow status, and incident links during migration.

## Review Focus

- API startup without Telegram credentials must leave RSS and all non-Telegram endpoints healthy.
- A migration containing existing promoted and attached RSS items must preserve IDs and incident foreign keys.
- A duplicate Telegram delivery with a changed edit timestamp must create one revision, not a second intake item.
- A flood wait on one channel must pause only that source and persist a safe retry deadline.
- A media response larger than 10 MB or with an unapproved MIME type must be rejected before durable file placement.

---

### Task 1: Pin the Telegram dependency and protect session paths

**Files:**
- Modify: `services/collector-api/pyproject.toml`
- Modify: `.gitignore`
- Create: `.env.example`
- Create: `services/collector-api/syosint/telegram_session.py`
- Create: `services/collector-api/tests/test_telegram_session.py`

**Interfaces:**
- Consumes: `SYOSINT_TELEGRAM_API_ID`, `SYOSINT_TELEGRAM_API_HASH`, and optional `SYOSINT_PRIVATE_DIR`.
- Produces: `TelegramSettings.load() -> TelegramSettings`, `session_path(settings) -> Path`, and `safe_auth_state(settings) -> Literal[...]`.

- [ ] **Step 1: Write failing settings and permission tests**

```python
def test_missing_credentials_is_not_configured(monkeypatch, tmp_path):
    monkeypatch.delenv("SYOSINT_TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("SYOSINT_TELEGRAM_API_HASH", raising=False)
    settings = TelegramSettings.load(private_dir=tmp_path)
    assert safe_auth_state(settings) == "not-configured"

def test_session_path_stays_under_private_directory(tmp_path):
    settings = configured_settings(tmp_path)
    assert session_path(settings) == tmp_path / "telegram" / "syosint.session"
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_telegram_session.py -q`

Expected: FAIL because the settings module does not exist.

- [ ] **Step 3: Implement strict local settings**

```python
@dataclass(frozen=True)
class TelegramSettings:
    api_id: int | None
    api_hash: str | None
    private_dir: Path

    @property
    def configured(self) -> bool:
        return self.api_id is not None and bool(self.api_hash)
```

Pin `Telethon==1.45.0`, add only variable names and setup comments to `.env.example`, and ensure `private-data/telegram/`, `*.session`, and `*.session-journal` remain ignored.

- [ ] **Step 4: Run session tests and dependency audit**

Run: `.venv314/bin/python -m pip install -e './services/collector-api[test]' && .venv314/bin/python -m pytest services/collector-api/tests/test_telegram_session.py -q && .venv314/bin/python -m pip_audit --local`

Expected: PASS with no known vulnerability in the pinned dependency graph.

- [ ] **Step 5: Commit**

```bash
git add services/collector-api/pyproject.toml services/collector-api/syosint/telegram_session.py services/collector-api/tests/test_telegram_session.py .gitignore .env.example
git commit -m "feat: secure local Telegram session setup"
```

### Task 2: Migrate RSS records into shared intake tables

**Files:**
- Create: `services/collector-api/alembic/versions/0003_shared_intake.py`
- Modify: `services/collector-api/syosint/models.py`
- Create: `services/collector-api/tests/test_intake_migration.py`
- Modify: `services/collector-api/tests/test_rss_store.py`

**Interfaces:**
- Consumes: existing `sources`, `feed_items`, `feed_cursors`, and `feed_quarantine` tables.
- Produces: Telegram source fields `public_identifier`, `review_notes`, and `media_enabled`; `IntakeItem`, `IntakeRevision`, `IntakeQuarantine`, `TelegramCursor`, and `MediaAsset`; preserves `FeedCursor` for HTTP state.

- [ ] **Step 1: Write a failing migration-preservation test**

```python
def test_0003_preserves_rss_identity_and_incident_link(tmp_path):
    engine = database_at_revision(tmp_path, "0002")
    item_id, incident_id = seed_promoted_feed_item(engine)
    upgrade(engine, "0003")
    with Session(engine) as db:
        item = db.get(IntakeItem, item_id)
        assert (item.platform, item.status, item.incident_id) == (
            "rss", "promoted", incident_id
        )
        columns = {column["name"] for column in inspect(engine).get_columns("sources")}
        assert {"public_identifier", "review_notes", "media_enabled"} <= columns
```

- [ ] **Step 2: Run the migration test and confirm failure**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_intake_migration.py -q`

Expected: FAIL because revision `0003` and shared models do not exist.

- [ ] **Step 3: Implement the migration and models**

```python
class IntakeItem(Base):
    __tablename__ = "intake_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    platform: Mapped[str] = mapped_column(String(20))
    native_id: Mapped[str | None] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64))
    headline: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="new")
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"))
```

Use `INSERT ... SELECT` to preserve RSS numeric IDs before dropping `feed_items`. Create a unique constraint on `(source_id, native_id)` when native ID is present and retain `(source_id, fingerprint)` as deterministic fallback. Add nullable `public_identifier` and `review_notes` source columns plus non-null `media_enabled` defaulting to false; existing RSS/manual sources keep null identifiers and disabled media.

- [ ] **Step 4: Run migration and RSS persistence tests**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_intake_migration.py services/collector-api/tests/test_rss_store.py -q`

Expected: PASS across initial, RSS, and shared-intake schema upgrades.

- [ ] **Step 5: Commit**

```bash
git add services/collector-api/alembic/versions/0003_shared_intake.py services/collector-api/syosint/models.py services/collector-api/tests/test_intake_migration.py services/collector-api/tests/test_rss_store.py
git commit -m "feat: migrate RSS into shared intake"
```

### Task 3: Introduce the shared intake store and keep RSS compatible

**Files:**
- Create: `services/collector-api/syosint/intake_types.py`
- Create: `services/collector-api/syosint/intake_store.py`
- Modify: `services/collector-api/syosint/rss_store.py`
- Modify: `services/collector-api/syosint/api.py`
- Create: `services/collector-api/tests/test_intake_store.py`
- Modify: `services/collector-api/tests/test_rss_api.py`

**Interfaces:**
- Produces: `NormalizedIntakeItem`, `QuarantinedIntakeItem`, `StoreSummary`, and `store_intake_batch(db, source, items, quarantined, cursor_update, now) -> StoreSummary`.
- Preserves: existing `/feed-items` endpoints as compatibility aliases during this pull request; adds `/intake-items`.

- [ ] **Step 1: Write failing shared-store tests**

```python
def test_duplicate_native_id_with_new_digest_creates_revision(db, source):
    first = normalized(native_id="42", text="original", edited_at=None)
    edited = normalized(native_id="42", text="corrected", edited_at=NOW)
    store_intake_batch(db, source, (first,), (), None, NOW)
    store_intake_batch(db, source, (edited,), (), None, LATER)
    assert db.scalar(select(func.count(IntakeItem.id))) == 1
    assert db.scalar(select(func.count(IntakeRevision.id))) == 1
```

Add tests for duplicate unchanged delivery and transaction rollback before cursor advancement.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_intake_store.py services/collector-api/tests/test_rss_api.py -q`

Expected: FAIL because the shared interfaces do not exist.

- [ ] **Step 3: Implement normalization and transactional storage**

```python
@dataclass(frozen=True)
class NormalizedIntakeItem:
    platform: Literal["rss", "telegram"]
    native_id: str | None
    headline: str | None
    url: str
    text: str
    published_at: datetime
    edited_at: datetime | None
    collected_at: datetime
    fingerprint: str
    raw_digest: str
```

Move duplicate/revision/quarantine persistence into `intake_store.py`; adapt RSS outcomes into `NormalizedIntakeItem(platform="rss", ...)`. Commit item changes and cursor updates in one transaction.

- [ ] **Step 4: Run RSS and intake suites**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_intake_store.py services/collector-api/tests/test_rss_store.py services/collector-api/tests/test_rss_api.py services/collector-api/tests/test_rss_scheduler.py -q`

Expected: PASS with compatibility endpoints unchanged.

- [ ] **Step 5: Commit**

```bash
git add services/collector-api/syosint/intake_types.py services/collector-api/syosint/intake_store.py services/collector-api/syosint/rss_store.py services/collector-api/syosint/api.py services/collector-api/tests/test_intake_store.py services/collector-api/tests/test_rss_api.py
git commit -m "refactor: unify private source intake"
```

### Task 4: Add terminal-only Telegram authentication

**Files:**
- Create: `services/collector-api/syosint/telegram_client.py`
- Create: `services/collector-api/syosint/telegram_cli.py`
- Modify: `services/collector-api/syosint/__main__.py`
- Create: `services/collector-api/tests/test_telegram_cli.py`

**Interfaces:**
- Consumes: `TelegramSettings` and injected `TelegramAuthClient` protocol.
- Produces: CLI commands `login`, `status`, `logout`; `TelegramAuthClient.start(phone, code_callback, password_callback) -> Awaitable[None]`.

- [ ] **Step 1: Write failing CLI tests with a fake client**

```python
def test_status_never_prints_phone_or_session(capsys, configured_settings):
    result = run_cli(["status"], settings=configured_settings, client=FakeAuthorized())
    assert result == 0
    assert capsys.readouterr().out.strip() == "authenticated"

def test_login_prompts_are_not_logged(fake_prompts, configured_settings):
    run_cli(["login"], settings=configured_settings, client=FakeLogin(), prompts=fake_prompts)
    assert "12345" not in fake_prompts.captured_output
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_telegram_cli.py -q`

Expected: FAIL because the CLI and client protocol do not exist.

- [ ] **Step 3: Implement terminal-only auth and restrictive session permissions**

```python
class TelegramAuthClient(Protocol):
    async def is_authorized(self) -> bool: ...
    async def login(self, phone: str, code: Callable[[], str], password: Callable[[], str]) -> None: ...
    async def disconnect(self) -> None: ...
```

Use `getpass.getpass` for codes/passwords, print safe state words only, and apply mode `0o600` to the session file after successful login where supported. `logout` requires an interactive confirmation and removes only the resolved session files under the configured private directory.

- [ ] **Step 4: Run CLI/session tests**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_telegram_cli.py services/collector-api/tests/test_telegram_session.py -q`

Expected: PASS with no secret material in captured output.

- [ ] **Step 5: Commit**

```bash
git add services/collector-api/syosint/telegram_client.py services/collector-api/syosint/telegram_cli.py services/collector-api/syosint/__main__.py services/collector-api/tests/test_telegram_cli.py
git commit -m "feat: add secure Telegram authentication CLI"
```

### Task 5: Approve public channels and collect bounded updates

**Files:**
- Create: `services/collector-api/syosint/telegram_types.py`
- Create: `services/collector-api/syosint/telegram_collect.py`
- Create: `services/collector-api/syosint/telegram_scheduler.py`
- Modify: `services/collector-api/syosint/api.py`
- Create: `services/collector-api/tests/test_telegram_collect.py`
- Create: `services/collector-api/tests/test_telegram_scheduler.py`
- Create: `services/collector-api/tests/test_telegram_api.py`

**Interfaces:**
- Produces: `ResolvedPublicChannel`, `TelegramMessage`, `TelegramTransport` protocol, `resolve_public_channel(username)`, and `sync_channel(source_id, transport, now) -> SyncSummary`.
- API: `GET /telegram/status`, `POST /telegram/channels/resolve`, `POST /telegram/channels`, `GET /telegram/channels`, and `POST /telegram/channels/{id}/sync`. Channel approval requires a declared language of `en`, `ar`, or `mixed`.

- [ ] **Step 1: Write failing public-only and bounded-sync tests**

```python
async def test_private_entity_is_rejected():
    transport = FakeTelegramTransport(entity=channel(public=False))
    with pytest.raises(ChannelPolicyError, match="public channel required"):
        await resolve_public_channel("private_name", transport)

async def test_initial_sync_is_bounded():
    summary = await sync_channel(source_id=1, transport=fake_messages(700), now=NOW)
    assert summary.created == 500
    assert summary.oldest_published_at >= NOW - timedelta(days=7)
```

Add tests for invalid usernames, username/entity mismatch, missing credentials, edits, deletion reconciliation, and a flood wait isolated to one source.

- [ ] **Step 2: Run Telegram adapter tests and confirm failure**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_telegram_collect.py services/collector-api/tests/test_telegram_scheduler.py services/collector-api/tests/test_telegram_api.py -q`

Expected: FAIL because collection modules and endpoints do not exist.

- [ ] **Step 3: Implement the read-only transport boundary**

```python
class TelegramTransport(Protocol):
    async def resolve_username(self, username: str) -> ResolvedPublicChannel: ...
    async def iter_messages(self, channel_id: int, *, limit: int, since: datetime) -> AsyncIterator[TelegramMessage]: ...
    async def reconcile_messages(self, channel_id: int, native_ids: tuple[str, ...]) -> tuple[TelegramMessage, ...]: ...
```

The concrete Telethon wrapper may call read APIs only. Normalize links as `https://t.me/{username}/{message_id}`. Store flood-wait deadlines in `TelegramCursor`; never sleep while holding a database transaction. Integrate `TelegramScheduler` into the FastAPI lifespan only when settings are configured and at least one source is enabled; scheduler startup or source failure must not abort API startup.

- [ ] **Step 4: Run collection, scheduler, API, and audit tests**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_telegram_*.py services/collector-api/tests/test_intake_store.py -q`

Expected: PASS, including adapter isolation and durable cursor recovery.

- [ ] **Step 5: Commit**

```bash
git add services/collector-api/syosint/telegram_types.py services/collector-api/syosint/telegram_collect.py services/collector-api/syosint/telegram_scheduler.py services/collector-api/syosint/api.py services/collector-api/tests/test_telegram_collect.py services/collector-api/tests/test_telegram_scheduler.py services/collector-api/tests/test_telegram_api.py
git commit -m "feat: collect approved public Telegram channels"
```

### Task 6: Add bounded optional media preservation

**Files:**
- Create: `services/collector-api/syosint/telegram_media.py`
- Create: `services/collector-api/tests/test_telegram_media.py`
- Modify: `services/collector-api/syosint/telegram_collect.py`
- Modify: `services/collector-api/syosint/telegram_scheduler.py`
- Modify: `services/collector-api/syosint/models.py`

**Interfaces:**
- Produces: `MediaPolicy(enabled: bool, max_bytes: int = 10_000_000, retention_days: int = 30)`, `preserve_media(stream, metadata, policy, destination) -> MediaAsset | None`, and `purge_expired_media(db, now) -> int`.

- [ ] **Step 1: Write failing size, MIME, and path tests**

```python
def test_rejects_oversized_media_before_final_placement(tmp_path):
    with pytest.raises(MediaPolicyError, match="size limit"):
        preserve_media(chunks(total=10_000_001), image_meta(), enabled_policy(), tmp_path)
    assert list(tmp_path.iterdir()) == []

def test_rejects_executable_mime(tmp_path):
    with pytest.raises(MediaPolicyError, match="MIME"):
        preserve_media(chunks(total=10), meta("application/x-msdownload"), enabled_policy(), tmp_path)

def test_expired_media_is_deleted_and_audited(db, tmp_path):
    asset = seed_media(db, tmp_path, expires_at=NOW - timedelta(seconds=1))
    assert purge_expired_media(db, NOW) == 1
    assert not Path(asset.local_path).exists()
    assert latest_audit(db).action == "media.deleted"
```

- [ ] **Step 2: Run media tests and confirm failure**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_telegram_media.py -q`

Expected: FAIL because media policy does not exist.

- [ ] **Step 3: Implement streamed inert storage**

```python
ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "video/mp4", "application/pdf"
}
```

Write into a private temporary file, count bytes while streaming, compute SHA-256, fsync, atomically rename under `private-data/telegram/media/`, and persist `expires_at = collected_at + timedelta(days=30)`. Implement `purge_expired_media` as an idempotent scheduler job that first proves the resolved asset path is beneath the configured media root, then deletes it, marks `deleted_at`, and records `media.deleted`. Never parse, render, transcode, or execute content.

- [ ] **Step 4: Run media and policy tests**

Run: `.venv314/bin/python -m pytest services/collector-api/tests/test_telegram_media.py services/collector-api/tests/test_telegram_collect.py -q && corepack pnpm policy:check`

Expected: PASS; raw media and temporary files remain ignored.

- [ ] **Step 5: Commit**

```bash
git add services/collector-api/syosint/telegram_media.py services/collector-api/syosint/telegram_collect.py services/collector-api/syosint/telegram_scheduler.py services/collector-api/syosint/models.py services/collector-api/tests/test_telegram_media.py
git commit -m "feat: preserve bounded Telegram media locally"
```

### Task 7: Build unified and Telegram-specific analyst views

**Files:**
- Create: `apps/analyst-desk/src/app/intake/page.tsx`
- Create: `apps/analyst-desk/src/app/intake/page.test.tsx`
- Create: `apps/analyst-desk/src/app/telegram/page.tsx`
- Create: `apps/analyst-desk/src/app/telegram/page.test.tsx`
- Modify: `apps/analyst-desk/src/app/rss/page.tsx`
- Modify: `apps/analyst-desk/src/app/actions.ts`
- Modify: `apps/analyst-desk/src/lib/api.ts`
- Modify: `apps/analyst-desk/src/app/style.css`
- Modify: `apps/analyst-desk/e2e/workflow.spec.ts`

**Interfaces:**
- Consumes: `/intake-items`, `/telegram/status`, `/telegram/channels`, channel resolve/create/sync endpoints, and existing promote/attach operations.
- Produces: `/intake` filtered unified queue and `/telegram` safe setup/channel/health/intake view.

- [ ] **Step 1: Write failing UI tests**

```tsx
expect(screen.getByText("Telegram is not configured")).toBeVisible();
expect(screen.queryByText(/api_hash|phone|session/i)).toBeNull();
expect(screen.getByRole("option", { name: "Telegram" })).toBeVisible();
expect(screen.getByText("Stored locally — never public automatically")).toBeVisible();
```

Add an XSS fixture containing `<img src=x onerror=alert(1)>` and assert it appears as text with no rendered image.

- [ ] **Step 2: Run analyst tests and confirm failure**

Run: `corepack pnpm test -- apps/analyst-desk/src/app/intake/page.test.tsx apps/analyst-desk/src/app/telegram/page.test.tsx`

Expected: FAIL because the routes and types do not exist.

- [ ] **Step 3: Implement typed pages and server actions**

```ts
export type IntakeItem = {
  id: number;
  source_id: number;
  platform: "rss" | "telegram";
  status: "new" | "promoted" | "attached" | "duplicate" | "quarantined";
  headline: string | null;
  text?: string;
  url?: string;
  published_at?: string;
  edited_at?: string | null;
  deleted_at?: string | null;
  collected_at: string;
  incident_id?: number | null;
};
```

Render source text with React text nodes only. Do not use `dangerouslySetInnerHTML`, Markdown, embeds, or remote media. Keep authentication itself terminal-only; the page may display safe state and setup instructions.

- [ ] **Step 4: Run unit and end-to-end tests**

Run: `corepack pnpm test -- apps/analyst-desk && corepack pnpm --filter @syosint/analyst-desk test:e2e`

Expected: PASS for offline API, not-configured Telegram, approved channels, filters, sync, promote, attach, and plain-text rendering.

- [ ] **Step 5: Commit**

```bash
git add apps/analyst-desk/src/app/intake apps/analyst-desk/src/app/telegram apps/analyst-desk/src/app/rss/page.tsx apps/analyst-desk/src/app/actions.ts apps/analyst-desk/src/lib/api.ts apps/analyst-desk/src/app/style.css apps/analyst-desk/e2e/workflow.spec.ts
git commit -m "feat: add unified Telegram analyst intake"
```

### Task 8: Document, audit, and verify local Telegram intake

**Files:**
- Create: `docs/source-policy/TELEGRAM.md`
- Modify: `README.md`
- Modify: `SECURITY.md`
- Modify: `docs/PROJECT_STATE.md`
- Modify: `services/collector-api/tests/test_workflow.py`

**Interfaces:**
- Produces: cross-platform login/status/logout, channel review, session rotation, backup exclusions, media retention, safe diagnostics, and AI-exclusion instructions.

- [ ] **Step 1: Add an integration test for graceful Telegram disablement**

```python
def test_missing_telegram_configuration_does_not_break_rss_api(client):
    assert client.get("/telegram/status").json() == {"status": "not-configured"}
    assert client.get("/feeds").status_code == 200
    assert client.get("/incidents").status_code == 200
```

- [ ] **Step 2: Run the complete backend and analyst verification matrix**

Run:

```bash
.venv314/bin/python -m pytest services/collector-api/tests -q
.venv314/bin/python -m pip_audit --local
corepack pnpm policy:check
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build:desk
corepack pnpm --filter @syosint/analyst-desk test:e2e
```

Expected: every command exits 0; tests use fakes only and never contact Telegram.

- [ ] **Step 3: Write the operating and safety documentation**

Include official API credential creation, terminal commands for Windows/macOS/Linux, session permissions, public-only channel review, media defaults, rate-limit states, reauthentication, and this explicit warning: raw Telegram content must not be copied into AI assistants or AI/ML services.

- [ ] **Step 4: Update project state without claiming public Telegram support**

Mark shared intake and local Telegram collection complete, list the exact verification commands, and identify the public Telegram wire plan as the next incomplete work.

- [ ] **Step 5: Commit**

```bash
git add docs/source-policy/TELEGRAM.md README.md SECURITY.md docs/PROJECT_STATE.md services/collector-api/tests/test_workflow.py
git commit -m "docs: document safe Telegram intake"
```
