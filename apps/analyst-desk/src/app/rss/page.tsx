import Link from "next/link";
import {
  addFeed,
  attachFeedItem,
  collectFeed,
  promoteFeedItem,
} from "../actions";
import { api, type FeedItem, type FeedSource } from "../../lib/api";

export const dynamic = "force-dynamic";

const categories = [
  ["political-security", "Political / security"],
  ["humanitarian", "Humanitarian"],
  ["infrastructure", "Infrastructure"],
  ["armed-conflict", "Conflict"],
  ["border-crossing", "Border crossing"],
  ["disinformation", "Claim verification"],
] as const;

function timestamp(value?: string | null) {
  return value ? new Date(value).toLocaleString("en-GB", { timeZone: "UTC" }) + " UTC" : "Never";
}

function InboxGroup({ title, items, action }: { title: string; items: FeedItem[]; action?: boolean }) {
  return <section className="panel inbox-group">
    <h2>{title} · {items.length}</h2>
    <div className="feed-items">
      {items.map((item) => <article className={`feed-item status-${item.status}`} key={`${item.status}-${item.id}`}>
        <div className="feed-item-head"><span className="pill">{item.status}</span><small>{timestamp(item.published_at ?? item.collected_at)}</small></div>
        <h3>{item.url ? <a href={item.url} target="_blank" rel="noopener noreferrer">{item.headline}</a> : item.headline ?? "Unavailable headline"}</h3>
        {item.reason && <p><strong>Reason:</strong> <code>{item.reason}</code></p>}
        {item.incident_id && <p>Case <Link href={`/incident/${item.incident_id}`}>#{item.incident_id}</Link></p>}
        {item.text && <details><summary>View stored source text (private)</summary><p className="private-text">{item.text}</p></details>}
        {item.status === "new" && <p className="privacy-note">Stored locally — never public automatically</p>}
        {action && item.status === "new" && <div className="review-actions">
          <form action={promoteFeedItem} className="form compact-form">
            <input type="hidden" name="item_id" value={item.id} />
            <strong>Promote to a new triage case</strong>
            <label>Analyst English title<input name="title_en" required minLength={3} /></label>
            <label>العنوان الذي كتبه المحلل<input name="title_ar" dir="rtl" required minLength={3} /></label>
            <label>Category<select name="category">{categories.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
            <button>Promote after review</button>
          </form>
          <form action={attachFeedItem} className="form compact-form">
            <input type="hidden" name="item_id" value={item.id} />
            <strong>Attach to an open case</strong>
            <label>Incident ID<input name="incident_id" inputMode="numeric" required min={1} /></label>
            <button>Attach evidence</button>
          </form>
        </div>}
      </article>)}
      {items.length === 0 && <p>No items in this group.</p>}
    </div>
  </section>;
}

export default async function RssInbox({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  let feeds: FeedSource[] = [];
  const groups: Record<"new" | "promoted" | "attached" | "duplicate" | "quarantined", FeedItem[]> = { new: [], promoted: [], attached: [], duplicate: [], quarantined: [] };
  let offline = false;
  try {
    const statuses = Object.keys(groups) as Array<keyof typeof groups>;
    const responses = await Promise.all([
      api<FeedSource[]>("/feeds"),
      ...statuses.map((status) => api<FeedItem[]>(`/feed-items?status=${status}`)),
    ]);
    feeds = responses[0] as FeedSource[];
    statuses.forEach((status, index) => { groups[status] = responses[index + 1] as FeedItem[]; });
  } catch { offline = true; }
  const { error } = await searchParams;

  return <main className="shell">
    <Link href="/" className="back">← Analyst desk</Link>
    <header className="masthead"><span className="eyebrow">PRIVATE COLLECTION / جمع خاص</span><h1>RSS <em>inbox</em></h1><p>Automatic source discovery for human triage. Nothing here becomes a verified incident or public record without analyst review.</p></header>
    {offline && <p role="alert" className="alert">Local API unavailable. Start the Python service at 127.0.0.1:8765.</p>}
    {error && <p role="alert" className="alert">{error}</p>}

    <div className="grid rss-controls">
      <section className="panel"><span className="eyebrow">01 / ALLOWLISTED SOURCE</span><h2>Add feed</h2><form action={addFeed} className="form">
        <label>Display name<input name="name" required /></label>
        <label>Public homepage URL<input name="url" type="url" required placeholder="https://example.org" /></label>
        <label>RSS or Atom URL<input name="feed_url" type="url" required placeholder="https://example.org/feed.xml" /></label>
        <label>Language<select name="language"><option value="en">English</option><option value="ar">العربية</option></select></label>
        <label>Polling interval (minutes)<input name="poll_interval_minutes" type="number" min="15" max="1440" defaultValue="30" required /></label>
        <label className="check"><input name="enabled" type="checkbox" defaultChecked />Enabled</label>
        <button>Add private feed</button>
      </form></section>
      <section className="panel"><span className="eyebrow">02 / SOURCE HEALTH</span><h2>Feeds · {feeds.length}</h2><ul className="list feed-health">{feeds.map((feed) => <li key={feed.id}>
        <div><a href={feed.url} target="_blank" rel="noopener noreferrer">{feed.name}</a><span className={`health health-${feed.health.status}`}>{feed.health.status}</span></div>
        <small>Last success: {timestamp(feed.health.last_success_at)} · failures: {feed.health.consecutive_failures}</small>
        {feed.health.last_error_category && <small>Error: {feed.health.last_error_category}</small>}
        <form action={collectFeed}><input type="hidden" name="source_id" value={feed.id} /><button>Collect now</button></form>
      </li>)}{feeds.length === 0 && <li>No feeds registered.</li>}</ul></section>
    </div>

    <nav className="status-nav" aria-label="Inbox groups">
      <a href="#new">New · {groups.new.length}</a><a href="#promoted">Promoted · {groups.promoted.length}</a><a href="#attached">Attached · {groups.attached.length}</a><a href="#duplicate">Duplicate · {groups.duplicate.length}</a><a href="#quarantined">Quarantined · {groups.quarantined.length}</a>
    </nav>
    <div id="new"><InboxGroup title="New" items={groups.new} action /></div>
    <div id="promoted"><InboxGroup title="Promoted" items={groups.promoted} /></div>
    <div id="attached"><InboxGroup title="Attached" items={groups.attached} /></div>
    <div id="duplicate"><InboxGroup title="Duplicate" items={groups.duplicate} /></div>
    <div id="quarantined"><InboxGroup title="Quarantined" items={groups.quarantined} /></div>
    <footer>Loopback only · Collected text remains private · Promotion always requires human judgment</footer>
  </main>;
}
