import Link from "next/link";
import { attachIntakeItem, promoteIntakeItem } from "../actions";
import { api, type FeedItemStatus, type IntakeItem, type Source } from "../../lib/api";

export const dynamic = "force-dynamic";
const statuses: FeedItemStatus[] = ["new", "promoted", "attached", "duplicate", "quarantined"];
const categories = ["political-security", "humanitarian", "infrastructure", "armed-conflict", "border-crossing", "disinformation"];
type Filters = { platform?: string; status?: string; source?: string; language?: string; from?: string; error?: string };

export default async function IntakePage({ searchParams }: { searchParams: Promise<Filters> }) {
  const filters = await searchParams;
  let sources: Source[] = [];
  let items: IntakeItem[] = [];
  let offline = false;
  try {
    const results = await Promise.all([
      api<Source[]>("/sources"),
      ...statuses.map((status) => api<IntakeItem[]>(`/intake-items?status=${status}`)),
    ]);
    sources = results[0] as Source[];
    items = results.slice(1).flat() as IntakeItem[];
  } catch { offline = true; }
  const since = filters.from && /^\d{4}-\d{2}-\d{2}$/.test(filters.from) ? new Date(`${filters.from}T00:00:00Z`) : null;
  const sourceId = Number(filters.source);
  const visible = items.filter((item) =>
    (!filters.platform || !["rss", "telegram"].includes(filters.platform) || item.platform === filters.platform) &&
    (!filters.status || !statuses.includes(filters.status as FeedItemStatus) || item.status === filters.status) &&
    (!filters.source || !Number.isSafeInteger(sourceId) || item.source_id === sourceId) &&
    (!filters.language || !["en", "ar", "mixed"].includes(filters.language) ||
      sources.find((source) => source.id === item.source_id)?.language === filters.language) &&
    (!since || Number.isNaN(since.getTime()) || new Date(item.published_at ?? item.collected_at).getTime() >= since.getTime())
  );
  return <main className="shell">
    <Link href="/" className="back">← Analyst desk</Link>
    <header className="masthead"><span className="eyebrow">LOCAL / PRIVATE</span><h1>Unified <em>intake</em></h1><p>Read collected RSS and public-channel reports before linking them to an incident.</p></header>
    {offline && <p className="alert" role="alert">Local API unavailable. Start the Python service at 127.0.0.1:8765.</p>}
    {filters.error && <p className="alert" role="alert">{filters.error}</p>}
    <nav className="status-nav"><Link href="/rss">RSS sources</Link><Link href="/telegram">Telegram channels</Link></nav>
    <form method="GET" className="panel form intake-filters" aria-label="Intake filters">
      <label>Platform<select name="platform" defaultValue={filters.platform ?? ""}><option value="">All platforms</option><option value="rss">RSS / Atom</option><option value="telegram">Telegram</option></select></label>
      <label>Status<select name="status" defaultValue={filters.status ?? ""}><option value="">All statuses</option>{statuses.map((status) => <option key={status} value={status}>{status}</option>)}</select></label>
      <label>Source<select name="source" defaultValue={filters.source ?? ""}><option value="">All sources</option>{sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}</select></label>
      <label>Language<select name="language" defaultValue={filters.language ?? ""}><option value="">All languages</option><option value="en">English</option><option value="ar">Arabic</option><option value="mixed">Mixed</option></select></label>
      <label>Since (UTC)<input name="from" type="date" defaultValue={filters.from ?? ""} /></label>
      <button type="submit">Apply filters</button>
    </form>
    <section className="panel"><h2>Collected items · {visible.length}</h2><div className="feed-items">
      {visible.map((item) => <article key={`${item.platform}-${item.id}`} className="feed-item">
        <div className="feed-item-head"><span className="pill">{item.platform === "telegram" ? "Telegram" : "RSS / Atom"} · {item.status}</span><small>{item.published_at ? new Date(item.published_at).toLocaleString("en-GB", { timeZone: "UTC" }) + " UTC" : "Time unavailable"}</small></div>
        <h3>{item.url ? <a href={item.url} target="_blank" rel="noopener noreferrer">{item.headline || `Original ${item.platform} post`}</a> : item.headline || "Unavailable headline"}</h3>
        <p>Source: {sources.find((source) => source.id === item.source_id)?.name ?? "Unknown"}</p>
        {item.deleted_at && <p className="alert">Source post was deleted. Review before any action.</p>}
        {item.edited_at && <p>Source post edited; check its revision before use.</p>}
        {item.text && <p className="private-text">{item.text}</p>}
        {item.status === "new" && <p className="privacy-note">Stored locally — never public automatically</p>}
        {item.status === "new" && !item.deleted_at && <div className="review-actions">
          <form action={promoteIntakeItem} className="form compact-form"><input type="hidden" name="item_id" value={item.id} />
            <strong>Promote to a new triage case</strong>
            <label>Analyst English title<input name="title_en" required minLength={3} /></label>
            <label>العنوان الذي كتبه المحلل<input name="title_ar" dir="rtl" required minLength={3} /></label>
            <label>Category<select name="category">{categories.map((category) => <option key={category} value={category}>{category}</option>)}</select></label>
            <button>Promote after review</button>
          </form>
          <form action={attachIntakeItem} className="form compact-form"><input type="hidden" name="item_id" value={item.id} />
            <strong>Attach to an open case</strong><label>Incident ID<input name="incident_id" type="number" min={1} required /></label>
            <button>Attach evidence</button>
          </form>
        </div>}
      </article>)}
      {visible.length === 0 && <p>No items match these filters.</p>}
    </div></section>
  </main>;
}
