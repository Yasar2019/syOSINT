import Link from "next/link";
import { approveTelegramChannel, resolveTelegramChannel, syncTelegramChannel, updateTelegramMediaPolicy } from "../actions";
import { api, type IntakeItem, type TelegramChannel, type TelegramStatus } from "../../lib/api";

export const dynamic = "force-dynamic";
type Params = { candidate?: string; channel_id?: string; title?: string; error?: string };
function stamp(value?: string | null) {
  if (!value) return "Never";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown" : date.toLocaleString("en-GB", { timeZone: "UTC" }) + " UTC";
}

export default async function TelegramPage({ searchParams }: { searchParams: Promise<Params> }) {
  const params = await searchParams;
  let status: TelegramStatus = { state: "not-configured" };
  let channels: TelegramChannel[] = [];
  let posts: IntakeItem[] = [];
  let offline = false;
  try {
    [status, channels, posts] = await Promise.all([
      api<TelegramStatus>("/telegram/status"),
      api<TelegramChannel[]>("/telegram/channels"),
      api<IntakeItem[]>("/intake-items?status=new"),
    ]);
  } catch { offline = true; }
  const telegramPosts = posts.filter((post) => post.platform === "telegram");
  const candidate = params.candidate && /^@?[A-Za-z][A-Za-z0-9_]{4,31}$/.test(params.candidate) ? params.candidate.replace(/^@/, "") : "";
  const channelId = Number(params.channel_id);
  const title = params.title?.trim().slice(0, 250) ?? "";
  const canApprove = status.state === "authenticated" && !!candidate && Number.isSafeInteger(channelId) && channelId > 0 && !!title;

  return <main className="shell">
    <Link href="/" className="back">← Analyst desk</Link>
    <header className="masthead"><span className="eyebrow">LOCAL / PRIVATE</span><h1>Telegram <em>channels</em></h1><p>Approve public channels for bounded read-only collection and review their posts locally.</p></header>
    {offline && <p className="alert" role="alert">Local API unavailable. Start the Python service at 127.0.0.1:8765.</p>}
    {params.error && <p className="alert" role="alert">{params.error}</p>}
    <nav className="status-nav"><Link href="/intake?platform=telegram">Unified intake</Link><Link href="/rss">RSS sources</Link></nav>
    <section className="panel">
      <h2>Connection</h2>
      <p>{status.state === "not-configured" ? "Telegram is not configured" : status.state === "authenticated" ? "Authenticated locally" : "Local login needs attention"}</p>
      {status.state !== "authenticated" && <p>Set up the local account in your terminal with <code>python -m syosint telegram login</code>, then reload this page.</p>}
      <p className="privacy-note">Stored locally — never public automatically</p>
    </section>
    {status.state === "authenticated" && <section className="panel">
      <h2>Resolve a public channel</h2>
      <p>Resolve a public username and confirm the channel identity before allowing collection.</p>
      <form action={resolveTelegramChannel} className="form"><label>Public channel username<input name="username" placeholder="publicnews" required minLength={5} maxLength={32} autoComplete="off" /></label><button>Preview channel</button></form>
      {canApprove && <div className="channel-preview"><p>Resolved channel: <strong>{title}</strong> · @{candidate} · ID {channelId}</p>
        <form action={approveTelegramChannel} className="form"><input type="hidden" name="username" value={candidate} /><input type="hidden" name="channel_id" value={channelId} /><input type="hidden" name="title" value={title} />
          <label>Language<select name="language"><option value="ar">Arabic</option><option value="en">English</option><option value="mixed">Mixed</option></select></label>
          <button>Approve channel for local collection</button>
        </form></div>}
    </section>}
    <section className="panel"><h2>Approved channels · {channels.length}</h2><ul className="list">
      {channels.map((channel) => <li key={channel.id}>
        <span>{channel.name}</span> · @{channel.username} · {channel.language}
        <p>Status: {channel.status ?? "pending"} · Last success: {stamp(channel.last_success_at)}</p>
        <div className="channel-actions">
          <form action={syncTelegramChannel} className="form"><input type="hidden" name="source_id" value={channel.id} /><button>Sync channel now</button></form>
          <form action={updateTelegramMediaPolicy} className="form"><input type="hidden" name="source_id" value={channel.id} /><input type="hidden" name="enabled" value={channel.media_enabled ? "false" : "true"} /><button>{channel.media_enabled ? "Disable local media" : "Enable bounded local media"}</button></form>
        </div>
      </li>)}
      {channels.length === 0 && <li>No channels approved yet.</li>}
    </ul></section>
    <section className="panel"><h2>New posts · {telegramPosts.length}</h2><div className="feed-items">
      {telegramPosts.map((post) => <article key={post.id} className="feed-item">
        <div className="feed-item-head"><span className="pill">unverified report</span><small>{stamp(post.published_at)}</small></div>
        <h3>{post.url ? <a href={post.url} target="_blank" rel="noopener noreferrer">{post.headline || "Original channel post"}</a> : post.headline || "Original channel post"}</h3>
        {post.text && <p className="private-text">{post.text}</p>}
        {post.edited_at && <p>Edited after collection: {stamp(post.edited_at)}</p>}
        {post.deleted_at && <p className="alert">Source post deleted; review before use.</p>}
        <p className="privacy-note">Stored locally — never public automatically</p>
        <Link href="/intake?platform=telegram&status=new">Review in unified intake →</Link>
      </article>)}
      {telegramPosts.length === 0 && <p>No new posts.</p>}
    </div></section>
  </main>;
}
