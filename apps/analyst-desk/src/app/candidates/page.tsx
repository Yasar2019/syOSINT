import Link from "next/link";
import { addCandidate, reviewCandidate } from "../actions";
import { api, type Candidate, type CandidateChecks, type CandidateReview, type CandidateStatus } from "../../lib/api";

export const dynamic = "force-dynamic";
const statuses: CandidateStatus[] = ["pending", "accepted", "rejected"];
const checklist: Array<[keyof CandidateChecks, string]> = [
  ["accessibility_checked", "Public accessibility"],
  ["relevance_checked", "Syria relevance"],
  ["identity_checked", "Publisher/channel identity and impersonation"],
  ["provenance_checked", "Provenance"],
  ["policy_checked", "Collection/reuse policy"],
];
type CandidateDetail = Candidate & { reviews: CandidateReview[] };

// Leads remain untrusted even when received from the local API. Never turn
// credentials, local references, IP literals or active schemes into links.
function safeUrl(value: string, platform: Candidate["platform"]): string | undefined {
  try {
    if (value.length > 2048 || /[\s\\#]/.test(value)) return;
    const url = new URL(value);
    const host = url.hostname.toLowerCase().replace(/\.$/, "");
    const labels = host.split(".");
    if (url.protocol !== "https:" || url.username || url.password || (url.port && url.port !== "443") ||
      labels.length < 2 || host.length > 253 || /\.(local|localhost|internal)$/.test(host) ||
      labels.some((label) => !/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(label)) ||
      /^(?:\d+|0x[0-9a-f]+)$/.test(labels.at(-1) ?? "")) return;
    if (platform === "telegram" && (host !== "t.me" || url.search || !/^\/[a-z][a-z0-9_]{4,31}$/i.test(url.pathname))) return;
    if (platform === "web" && host === "t.me") return;
    return url.href;
  } catch { return; }
}

export default async function Candidates({ searchParams }: { searchParams: Promise<{ status?: string; error?: string; candidate?: string; offset?: string }> }) {
  const params = await searchParams;
  const status = statuses.includes(params.status as CandidateStatus) ? params.status as CandidateStatus : "pending";
  const pageSize = 100;
  const requestedOffset = Number(params.offset);
  const maxOffset = Number.MAX_SAFE_INTEGER - pageSize;
  const offset = Number.isSafeInteger(requestedOffset) && requestedOffset >= 0 && requestedOffset <= maxOffset ? requestedOffset : 0;
  const requestedId = Number(params.candidate);
  const candidateId = Number.isSafeInteger(requestedId) && requestedId > 0 ? requestedId : undefined;
  let candidates: CandidateDetail[] = [];
  let offline = false;
  try {
    if (candidateId) candidates = [await api<CandidateDetail>(`/candidates/${candidateId}`)];
    else {
      const rows = await api<Candidate[]>(`/candidates?status=${status}${offset ? `&offset=${offset}` : ""}`);
      candidates = await Promise.all(rows.map((row) => api<CandidateDetail>(`/candidates/${row.id}`)));
    }
  } catch { offline = true; }
  return <main className="shell">
    <Link href="/" className="back">← Analyst desk</Link>
    <header className="masthead"><span className="eyebrow">PRIVATE LOCAL REVIEW</span><h1>Candidate <em>review</em></h1><p>Manually suggested public sources for documented human review.</p></header>
    <p className="privacy-note">Acceptance means suitable to consider for separate source registration. It does not start collection, register a source, authorize Telegram collection, or publish anything.</p>
    <p>These checks are human attestations. Rejection is not a claim about editorial quality or truthfulness.</p>
    {offline && <p role="alert" className="alert">Local API unavailable. Start the Python service at 127.0.0.1:8765.</p>}
    {params.error && <p role="alert" className="alert">{params.error.slice(0, 200)}</p>}
    {candidateId && <p><Link href={`/candidates?candidate=${candidateId}`}>Existing candidate #{candidateId}</Link></p>}
    <section className="panel"><h2>Suggest a public source</h2><form action={addCandidate} className="form">
      <label>Platform<select name="platform"><option value="web">Public web / RSS</option><option value="telegram">Public Telegram channel</option></select></label>
      <label>Public HTTPS URL<input name="url" type="url" required maxLength={2048} placeholder="https://example.org" /></label>
      <p>Telegram requires https://t.me/username. Invite and message links are not accepted.</p>
      <label>Display name<input name="name" required maxLength={250} /></label>
      <label>Language<select name="language"><option value="en">English</option><option value="ar">العربية</option><option value="mixed">Mixed</option></select></label>
      <label>Suggestion reason<textarea name="suggestion_reason" required maxLength={1000} /></label>
      <button>Submit candidate</button>
    </form></section>
    <nav className="status-nav" aria-label="Candidate status">{statuses.map((filter) => <Link key={filter} href={`/candidates?status=${filter}`} aria-current={status === filter ? "page" : undefined}>{filter[0].toUpperCase() + filter.slice(1)}</Link>)}</nav>
    <section className="panel"><h2>{candidateId ? "Existing candidate" : status[0].toUpperCase() + status.slice(1) + " candidates"}</h2>
      {!offline && candidates.length === 0 && <p>No candidates in this status.</p>}
      {candidates.map((candidate) => {
        const url = safeUrl(candidate.canonical_url, candidate.platform);
        return <article className="feed-item" key={candidate.id}>
          <div className="feed-item-head"><span className="pill">{candidate.status}</span><small>#{candidate.id} · {candidate.platform} · {candidate.language}</small></div>
          <h3>{url ? <a href={url} target="_blank" rel="noopener noreferrer">{candidate.name}</a> : candidate.name}</h3>
          <p>{candidate.canonical_url}</p><p>{candidate.suggestion_reason}</p>
          <p>Suggested: <time dateTime={candidate.created_at}>{candidate.created_at}</time> · Latest status update: <time dateTime={candidate.updated_at}>{candidate.updated_at}</time></p>
          <h4>Decision history</h4>
          {candidate.reviews.length === 0 && <p>No reviews yet.</p>}
          <ol>{candidate.reviews.map((review) => <li key={review.id}>
            <strong>{review.decision}</strong> · <time dateTime={review.created_at}>{review.created_at}</time>
            <p>{review.reason}</p><ul>{checklist.map(([key, label]) => <li key={key}>{label}: {review.checks[key] ? "checked" : "unchecked"}</li>)}</ul>
          </li>)}</ol>
          <form action={reviewCandidate} className="form compact-form">
            <input type="hidden" name="candidate_id" value={candidate.id} />
            <h4>Append a human review</h4><p>Acceptance requires all five checks and a reason. A later decision preserves earlier reviews.</p>
            {checklist.map(([key, label]) => <label className="check" key={key}><input type="checkbox" name={key} />{label}</label>)}
            <label>Review reason<textarea name="reason" required maxLength={1000} /></label>
            <label>Decision<select name="decision" defaultValue="rejected"><option value="rejected">Rejected</option><option value="accepted">Accepted for separate registration consideration</option></select></label>
            <button>Record review</button>
          </form>
        </article>;
      })}
    </section>
    {!candidateId && !offline && <nav className="status-nav" aria-label="Candidate pages">
      {offset > 0 && <Link href={`/candidates?status=${status}&offset=${Math.max(0, offset - pageSize)}`}>← Newer candidates</Link>}
      {candidates.length === pageSize && offset <= maxOffset - pageSize && <Link href={`/candidates?status=${status}&offset=${offset + pageSize}`}>Older candidates →</Link>}
    </nav>}
    <footer>Local only · Append-only review history · Separate source registration required</footer>
  </main>;
}
