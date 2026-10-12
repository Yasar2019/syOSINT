import Link from 'next/link';

const governorates = [
  ['aleppo', 'Aleppo / حلب'], ['damascus', 'Damascus / دمشق'], ['rural-damascus', 'Rural Damascus / ريف دمشق'],
  ['daraa', 'Daraa / درعا'], ['deir-ez-zor', 'Deir ez-Zor / دير الزور'], ['hama', 'Hama / حماة'],
  ['hasakah', 'Hasakah / الحسكة'], ['homs', 'Homs / حمص'], ['idlib', 'Idlib / إدلب'],
  ['latakia', 'Latakia / اللاذقية'], ['quneitra', 'Quneitra / القنيطرة'], ['raqqa', 'Raqqa / الرقة'],
  ['suwayda', 'Suwayda / السويداء'], ['tartus', 'Tartus / طرطوس'],
] as const;

export type RelatedCase = { id: number; state: string; title_en: string; title_ar: string; occurred_at: string; private_governorate: string; time_difference_seconds: number };

export function PrivateGovernorate({ value }: { value: unknown }) {
  return <div><label>Private governorate for grouping<select name="private_governorate" aria-describedby="grouping-location-note" defaultValue={typeof value === 'string' ? value : ''}>
    <option value="">Not recorded</option>{governorates.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
  </select></label><small id="grouping-location-note">Local case metadata; excluded from public exports.</small></div>;
}

export function RelatedCases({ matches, unavailable, complete }: { matches: RelatedCase[]; unavailable: boolean; complete: boolean }) {
  return <section className="panel" aria-label="Possible related cases"><h2>Possible related cases</h2>
    <p>Same category and analyst-recorded governorate, with event times within six hours. Suggestions do not establish source independence, corroboration, or duplicate events. Compare evidence before taking any manual action.</p>
    {unavailable ? <p role="status">Related-case suggestions unavailable. Retry when the local API is available.</p> : !complete ? <p>Record a private governorate and a timezone-aware event time to see suggestions.</p> : matches.length === 0 ? <p>No related cases match these rules.</p> :
      <ul className="list">{matches.map((match) => <li key={match.id}><Link href={`/incident/${match.id}`}>{match.title_en}</Link><p lang="ar" dir="rtl">{match.title_ar}</p><small>Case #{match.id} · {match.state} · {match.occurred_at} · {Number((match.time_difference_seconds / 60).toFixed(2))} minutes apart</small></li>)}</ul>}
  </section>;
}
