import Link from "next/link";
import {
  approveTelegramPublication, correctTelegramPublication,
  previewTelegramPublication, withdrawTelegramPublication,
} from "../../../actions";
import { api, type TelegramPublication, type TelegramPublicationPreview } from "../../../../lib/api";

export const dynamic = "force-dynamic";

type Params = { error?: string; preview?: string; approved?: string; corrected?: string; withdrawn?: string };
const checks = [
  ["source_identity_checked", "Public channel identity and original link checked"],
  ["person_safety_checked", "Person safety assessed"],
  ["operational_safety_checked", "Operational safety assessed"],
] as const;

export default async function PublicationPage({ params, searchParams }: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Params>;
}) {
  const [{ id }, query] = await Promise.all([params, searchParams]);
  const itemId = Number(id);
  if (!Number.isSafeInteger(itemId) || itemId <= 0) {
    return <main className="shell"><p role="alert">Invalid intake item.</p></main>;
  }
  let published: TelegramPublication | null = null;
  let preview: TelegramPublicationPreview | null = null;
  let unavailable = false;
  try {
    published = await api<TelegramPublication>(`/intake-items/${itemId}/publication`);
  } catch (error) {
    if (!(error instanceof Error) || error.message !== "Publication unavailable") unavailable = true;
  }
  if (!published && query.preview && /^[0-9a-f]{64}$/.test(query.preview)) {
    try {
      const loaded = await api<TelegramPublicationPreview>(`/telegram-publication-previews/${query.preview}`);
      if (loaded.item_id === itemId) preview = loaded;
    } catch { /* Expired previews return to the review form. */ }
  }

  return <main className="shell">
    <Link href="/telegram" className="back">← Telegram channels</Link>
    <header className="masthead"><span className="eyebrow">PRIVATE EDITORIAL REVIEW</span><h1>Telegram <em>publication</em></h1>
      <p>Write both headlines yourself. Each post needs its own safety review and explicit approval.</p></header>
    <p className="privacy-note">Original Telegram text stays private</p>
    <p>Review the source post in <Link href="/intake?platform=telegram&status=new">private intake</Link> before completing the checks below. Telegram-derived material must not be sent to AI services.</p>
    {unavailable && <p className="alert" role="alert">Local API unavailable. Start the Python service at 127.0.0.1:8765.</p>}
    {query.error && <p className="alert" role="alert">{query.error}</p>}
    {(query.approved || query.corrected || query.withdrawn) && <p role="status" className="success">Editorial change saved locally. It still needs manual staging and a reviewed public deployment.</p>}

    {!published && <section className="panel">
      <h2>Prepare a public lead for item #{itemId}</h2>
      <p>Channel approval only permits collection. This item remains private until you approve its exact sanitized preview and stage it for a separate public review.</p>
      <form action={previewTelegramPublication} className="form">
        <input type="hidden" name="item_id" value={itemId} />
        <label>English public headline<input name="headline_en" minLength={3} maxLength={240} required /></label>
        <label>Arabic public headline<input name="headline_ar" dir="rtl" minLength={3} maxLength={240} required /></label>
        {checks.map(([name, label]) => <label className="check" key={name}><input name={name} type="checkbox" required />{label}</label>)}
        <label className="check"><input name="human_approved" type="checkbox" required />I personally reviewed this source for publication</label>
        <button>Preview public Telegram lead</button>
      </form>
    </section>}

    {preview && !published && <section className="panel preview">
      <h2>Exact public preview</h2>
      <p>Reviewed external Telegram report — not independently verified</p>
      <p>{preview.record.channel.name}</p>
      <p>{preview.record.headline.en}</p><p lang="ar" dir="rtl">{preview.record.headline.ar}</p>
      <p><a href={preview.record.url} target="_blank" rel="noopener noreferrer">Original public post</a></p>
      <pre aria-label="Exact sanitized public record">{JSON.stringify(preview.record, null, 2)}</pre>
      <form action={approveTelegramPublication} className="form">
        <input type="hidden" name="item_id" value={itemId} />
        <input type="hidden" name="draft_hash" value={preview.draft_hash} />
        <input type="hidden" name="headline_en" value={preview.record.headline.en} />
        <input type="hidden" name="headline_ar" value={preview.record.headline.ar} />
        {checks.map(([name]) => <input type="hidden" name={name} value="on" key={name} />)}
        <label className="check"><input name="human_approved" type="checkbox" required />I personally authorize this exact public record</label>
        <button>Approve public Telegram lead</button>
      </form>
    </section>}

    {published && <section className="panel preview">
      <h2>Reviewed lead · {published.status}</h2>
      <p>Saved locally. The public dashboard changes only after manual staging, a reviewed PR, and deployment.</p>
      <pre aria-label="Current sanitized public record">{JSON.stringify(published.record, null, 2)}</pre>
      {published.status !== "withdrawn" && <div className="review-actions">
        <form action={correctTelegramPublication} className="form compact-form">
          <input type="hidden" name="item_id" value={itemId} /><input type="hidden" name="publication_id" value={published.id} />
          <strong>Correct the public lead</strong>
          <label>Corrected English headline<input name="headline_en" defaultValue={published.record.headline.en} minLength={3} maxLength={240} required /></label>
          <label>Corrected Arabic headline<input name="headline_ar" defaultValue={published.record.headline.ar} dir="rtl" minLength={3} maxLength={240} required /></label>
          <label>English correction reason<input name="reason_en" minLength={3} maxLength={240} required /></label>
          <label>Arabic correction reason<input name="reason_ar" dir="rtl" minLength={3} maxLength={240} required /></label>
          {checks.map(([name, label]) => <label className="check" key={name}><input type="checkbox" name={name} required />{label}</label>)}
          <label className="check"><input type="checkbox" name="human_approved" required />I approve this correction</label>
          <button>Save explicit correction</button>
        </form>
        <form action={withdrawTelegramPublication} className="form compact-form">
          <input type="hidden" name="item_id" value={itemId} /><input type="hidden" name="publication_id" value={published.id} />
          <strong>Withdraw this lead</strong>
          <label>English withdrawal reason<input name="reason_en" minLength={3} maxLength={240} required /></label>
          <label>Arabic withdrawal reason<input name="reason_ar" dir="rtl" minLength={3} maxLength={240} required /></label>
          <label className="check"><input type="checkbox" name="human_approved" required />I authorize the public withdrawal marker</label>
          <button>Save explicit withdrawal</button>
        </form>
      </div>}
    </section>}
  </main>;
}
