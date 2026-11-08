import { render, screen, cleanup } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';
import type { PublicIncident } from '@syosint/schemas';
import { IncidentCard } from './IncidentCard';
import { IncidentDetail } from './IncidentDetail';
import { Timeline } from './Timeline';
import { SummaryCards } from './SummaryCards';
import { SyriaMap } from './SyriaMap';
import { en } from '../i18n/en';
afterEach(cleanup);
const withdrawn = { id: 'synthetic', status: 'withdrawn', confidence: 'verified', title: { en: 'OLD CLAIM', ar: 'قديم' }, summary: { en: 'OLD SUMMARY', ar: 'قديم' }, uncertainty: { en: 'OLD UNCERTAINTY', ar: 'قديم' }, occurredAt: '2026-10-14T10:00:00Z', updatedAt: '2026-10-14T10:00:00Z', categories: ['infrastructure'], location: { en: 'OLD LOCATION', ar: 'قديم', precision: 'governorate', longitude: 37.1, latitude: 36.2 }, sourceCount: 1, sources: [{ id: 'old', url: 'https://example.com/old', publishedAt: '2026-10-14T10:00:00Z', label: { en: 'OLD SOURCE', ar: 'قديم' } }], corrections: [{ correctedAt:'2026-10-14T10:00:00Z', reason: { en: 'Synthetic withdrawal reason', ar: 'سبب السحب' }, changedFields:['status'] }] } as PublicIncident;
it('suppresses withdrawn claim, source, location and confidence in feed and detail', () => {
 render(<><IncidentCard incident={withdrawn} locale="en" dictionary={en} onSelect={() => {}} /><IncidentDetail incident={withdrawn} locale="en" dictionary={en} onClose={() => {}} /></>);
 expect(screen.queryByText(/OLD/)).toBeNull(); expect(screen.queryByText('Verified')).toBeNull();
 expect(screen.getAllByText('Synthetic withdrawal reason').length).toBeGreaterThan(0);
});
it('excludes withdrawn records from active counts, map and timeline', () => {
 const {container} = render(<><SummaryCards incidents={[withdrawn]} dictionary={en}/><SyriaMap incidents={[withdrawn]} locale="en" dictionary={en} onSelect={() => {}}/><Timeline incidents={[withdrawn]} locale="en" dictionary={en} onSelect={() => {}}/></>);
 expect(container.querySelector('.summary-grid strong')?.textContent).toBe('0');
 expect(container.querySelector('.map-marker')).toBeNull(); expect(container.querySelector('.timeline-days')?.textContent).toBe('');
});
it('shows corrected reason, time and localized changed fields in both languages',async()=>{
 const {ar}=await import('../i18n/ar');
 const corrected={...withdrawn,status:'corrected',corrections:[{...withdrawn.corrections[0],changedFields:['summary','location'] }]} as PublicIncident;
 const {unmount}=render(<IncidentDetail incident={corrected} locale="en" dictionary={en} onClose={()=>{}}/>);
 expect(screen.getByText('Changed fields: Summary, Location')).toBeTruthy();expect(screen.getByText('Synthetic withdrawal reason')).toBeTruthy();unmount();
 render(<IncidentDetail incident={corrected} locale="ar" dictionary={ar} onClose={()=>{}}/>);expect(screen.getByText('الحقول المعدلة: الملخص, الموقع')).toBeTruthy();expect(screen.getByText('سبب السحب')).toBeTruthy();
});

it('preserves active markers and timeline entries alongside a discoverable withdrawal',()=>{
 const active={...withdrawn,id:'active-synthetic',status:'published',title:{en:'Active synthetic claim',ar:'تقرير تجريبي'}} as PublicIncident;
 const {container}=render(<><SyriaMap incidents={[withdrawn,active]} locale="en" dictionary={en} onSelect={()=>{}}/><Timeline incidents={[withdrawn,active]} locale="en" dictionary={en} onSelect={()=>{}}/><SummaryCards incidents={[withdrawn,active]} dictionary={en}/></>);
 expect(container.querySelectorAll('.map-marker')).toHaveLength(1);expect(container.querySelectorAll('.timeline-days button')).toHaveLength(1);expect(container.querySelector('.summary-grid strong')?.textContent).toBe('1');
});
