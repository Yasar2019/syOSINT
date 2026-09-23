import Link from "next/link";
import { notFound } from "next/navigation";
import { addEvidence, editIncident, exportIncident, review, transition } from "../../actions";
import { api, type Evidence, type Incident, type Source } from "../../../lib/api";

export const dynamic = "force-dynamic";

const checks = [
  ["independence_checked", "Source independence assessed"], ["time_checked", "Time consistency assessed"],
  ["location_checked", "Location consistency assessed"], ["contradictions_checked", "Contradictions assessed"],
  ["person_safety_checked", "No ordinary-person identification or exposed civilians"],
  ["operational_safety_checked", "No active tactical positions, routes, shelters or medical sites"],
  ["primary_evidence_checked", "Primary evidence assessed (required for Verified)"],
  ["contradictions_acknowledged", "Remaining uncertainty and contradictions acknowledged"],
] as const;

function Input({ name, label, defaultValue, required = true }: { name: string; label: string; defaultValue?: unknown; required?: boolean }) {
  return <label>{label}<input name={name} defaultValue={typeof defaultValue === "string" ? defaultValue : ""} required={required} dir={name.endsWith("_ar") ? "rtl" : undefined} /></label>;
}

export default async function Case({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ exported?: string }> }) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();
  let incident: Incident;
  try { incident = await api<Incident>(`/incidents/${id}`); } catch { notFound(); }
  const [evidence, sources] = await Promise.all([api<Evidence[]>(`/incidents/${id}/evidence`), api<Source[]>("/sources")]);
  const { exported } = await searchParams;
  let preview: Record<string, unknown> | null = null;
  if (incident.state === "approved") {
    try { preview = await api(`/incidents/${id}/preview`); } catch { /* show gate status below */ }
  }
  const next = ({ triage: "investigating", investigating: "review-ready", "review-ready": "approved" } as Record<string, string>)[incident.state];
  return <main className="shell"><header className="masthead"><Link href="/" className="back">← All case files</Link><span className="eyebrow">PRIVATE CASE {id.padStart(3, "0")} / ملف خاص</span><h1>{incident.title_en}</h1><p lang="ar" dir="rtl">{incident.title_ar}</p><span className="pill">{incident.state}</span></header>
    {exported && <p className="success" role="status">Sanitized JSON saved locally in pending-exports. No public site was changed.</p>}
    <div className="grid"><section className="panel"><span className="eyebrow">01 / EVIDENCE</span><h2>Public references</h2><ul className="list">{evidence.map((item) => <li key={item.id}><a href={item.url} target="_blank" rel="noopener noreferrer">Reference {item.id}</a><small>{item.published_at}</small><p className="private-text">{item.text}</p></li>)}</ul>{incident.state !== "approved" && <form action={addEvidence} className="form"><input type="hidden" name="id" value={id} /><label>Registered public source<select name="source_id" required>{sources.map((s) => <option value={s.id} key={s.id}>{s.name}</option>)}</select></label><Input name="url" label="Exact public report URL" /><Input name="published_at" label="Published at (ISO UTC)" defaultValue="2026-09-23T10:00:00Z" /><label>Original text (private only)<textarea name="text" rows={4} required /></label><button disabled={!sources.length}>Attach evidence</button></form>}</section>
    <section className="panel"><span className="eyebrow">02 / EDITORIAL RECORD</span><h2>Public fields</h2>{incident.state !== "approved" ? <form action={editIncident} className="form"><input type="hidden" name="id" value={id} /><Input name="title_en" label="Title · English" defaultValue={incident.title_en} /><Input name="title_ar" label="العنوان · عربي" defaultValue={incident.title_ar} /><label>Category<select name="category" defaultValue={incident.category}>{["infrastructure", "humanitarian", "political-security", "armed-conflict", "border-crossing", "disinformation"].map((c) => <option key={c}>{c}</option>)}</select></label><Input name="summary_en" label="Original summary · English" defaultValue={incident.summary_en} /><Input name="summary_ar" label="الملخص · عربي" defaultValue={incident.summary_ar} /><Input name="uncertainty_en" label="Unknowns / contradictions · English" defaultValue={incident.uncertainty_en} /><Input name="uncertainty_ar" label="الشكوك · عربي" defaultValue={incident.uncertainty_ar} /><Input name="location_en" label="Safe public location label · English" defaultValue={incident.location_en} /><Input name="location_ar" label="الموقع العام · عربي" defaultValue={incident.location_ar} /><label>Public location precision<select name="precision" defaultValue={String(incident.precision || "withheld")}><option value="withheld">Withheld</option><option value="country">Country</option><option value="governorate">Governorate</option><option value="district">District</option></select></label><Input name="occurred_at" label="Event time · ISO UTC" defaultValue={incident.occurred_at} /><label>Confidence<select name="confidence" defaultValue={String(incident.confidence || "unverified")}>{["unverified", "developing", "corroborated", "verified", "disputed", "false"].map((c) => <option key={c}>{c}</option>)}</select></label><button>Save public fields</button></form> : <p>Approved record locked. Export is a separate explicit action.</p>}</section></div>
    <div className="grid"><section className="panel"><span className="eyebrow">03 / VERIFICATION</span><h2>Human review</h2>{incident.state === "review-ready" && <form action={review} className="form"><input type="hidden" name="id" value={id} /><label>Written rationale<textarea name="rationale" rows={4} minLength={10} required defaultValue={String(incident.review?.rationale ?? "")} /></label>{checks.map(([key, label]) => <label className="check" key={key}><input type="checkbox" name={key} defaultChecked={Boolean(incident.review?.[key])} />{label}</label>)}<label className="check"><input type="checkbox" name="human_approved" defaultChecked={Boolean(incident.review?.human_approved)} />I personally reviewed this case for publication</label><button>Record review</button></form>}{incident.state !== "review-ready" && <p>Move the case to review-ready to document checks. {incident.review?.rationale ? `Rationale: ${incident.review.rationale}` : ""}</p>}</section>
    <section className="panel"><span className="eyebrow">04 / LIFECYCLE</span><h2>Decision</h2>{next ? <form action={transition} className="form"><input type="hidden" name="id" value={id} /><input type="hidden" name="state" value={next} /><label>Reason for transition<input name="reason" minLength={8} required /></label><button>Move to {next}</button></form> : <p>Approval recorded; check the exact publication preview below.</p>}</section></div>
    <section className="panel preview"><span className="eyebrow">05 / PUBLICATION GATE</span><h2>Exact public record</h2>{preview ? <><p>Only the fields below may enter the staged JSON. Verify names, safe location, citations and uncertainty before export.</p><pre>{JSON.stringify(preview, null, 2)}</pre><form action={exportIncident} className="form"><input type="hidden" name="id" value={id} /><label className="check"><input name="acknowledged" type="checkbox" required />I checked this exact public record and authorize a local export</label><button>Export sanitized JSON locally</button></form></> : <p>Preview becomes available after the verification and approval gates pass. No source text is included.</p>}</section><footer>Local only · Raw evidence stays in SQLite · No automatic publication</footer>
  </main>;
}
