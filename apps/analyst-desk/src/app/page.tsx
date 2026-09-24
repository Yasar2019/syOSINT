import Link from "next/link";
import { addIncident, addSource } from "./actions";
import { api, type Incident, type Source } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function Home({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  let sources: Source[] = [], incidents: Incident[] = [];
  let offline = false;
  try { [sources, incidents] = await Promise.all([api<Source[]>("/sources"), api<Incident[]>("/incidents")]); }
  catch { offline = true; }
  const { error } = await searchParams;
  return <main className="shell">
    <header className="masthead"><span className="eyebrow">PRIVATE LOCAL WORKSPACE / مساحة عمل محلية خاصة</span><h1>syOSINT <em>Analyst desk</em></h1><p>Public-source reporting, documented human judgment, explicit publication review.</p></header>
    {offline && <p role="alert" className="alert">Local API unavailable. Start the Python service at 127.0.0.1:8765.</p>}
    {error && <p role="alert" className="alert">{error}</p>}
    <p className="workspace-link"><Link href="/rss">Open private RSS inbox →</Link><span>Automatic discovery, manual verification.</span></p>
    <div className="grid"><section className="panel"><span className="eyebrow">01 / PUBLIC REFERENCES</span><h2>Sources</h2><form action={addSource} className="form"><label>Display name<input name="name" required /></label><label>Public HTTPS URL<input name="url" type="url" required placeholder="https://example.org" /></label><label>Language<select name="language"><option value="en">English</option><option value="ar">العربية</option></select></label><button>Add public source</button></form><ul className="list">{sources.map((source) => <li key={source.id}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.name}</a><small>{source.language}</small></li>)}</ul></section>
    <section className="panel"><span className="eyebrow">02 / INTAKE</span><h2>New incident</h2><form action={addIncident} className="form"><label>English title<input name="title_en" required /></label><label>العنوان بالعربية<input name="title_ar" dir="rtl" required /></label><label>Category<select name="category"><option value="infrastructure">Infrastructure</option><option value="humanitarian">Humanitarian</option><option value="political-security">Political / security</option><option value="armed-conflict">Conflict</option><option value="border-crossing">Border crossing</option><option value="disinformation">Claim verification</option></select></label><button>Create incident</button></form></section></div>
    <section className="panel index"><span className="eyebrow">03 / CASE FILES</span><h2>Incidents <span className="count">{incidents.length}</span></h2><div className="case-list">{incidents.map((incident) => <Link key={incident.id} href={`/incident/${incident.id}`} className="case"><span className="case-id">CASE {String(incident.id).padStart(3, "0")}</span><strong>{incident.title_en}</strong><span lang="ar" dir="rtl">{incident.title_ar}</span><span className="pill">{incident.state}</span></Link>)}{incidents.length === 0 && <p>No incidents yet. Add a source and open a case file.</p>}</div></section>
    <footer>Local only · Raw evidence stays in SQLite · No automatic publication</footer>
  </main>;
}
