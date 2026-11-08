import { beforeEach, expect, it, vi } from 'vitest';
const { apiMock, redirectMock } = vi.hoisted(() => ({ apiMock: vi.fn(), redirectMock: vi.fn((url: string) => { throw new Error(url); }) }));
vi.mock('../lib/api', () => ({ api: apiMock }));
vi.mock('next/navigation', () => ({ redirect: redirectMock }));
import * as actions from './actions';
beforeEach(() => { vi.clearAllMocks(); apiMock.mockResolvedValue({ preview_hash: 'server-hash', version: 3 }); });
function form(fields: Record<string,string>) { const result = new FormData(); for (const [key,value] of Object.entries(fields)) result.set(key,value); return result; }
it('carries exact server version and digest with explicit acknowledgment', async () => {
 await expect(actions.approveIncidentCorrection(form({id:'1',expected_version:'3',preview_hash:'server-hash',acknowledged:'on'}))).rejects.toThrow('/incident/1/publication?approved=1');
 expect(apiMock).toHaveBeenCalledWith('/incidents/1/correction/approve','POST',{expected_version:3,preview_hash:'server-hash',acknowledged:true});
});
it('does not call approval without acknowledgment', async () => {
 await expect(actions.approveIncidentCorrection(form({id:'1',expected_version:'3',preview_hash:'server-hash'}))).rejects.toThrow('error='); expect(apiMock).not.toHaveBeenCalled();
});
it('returns only generic errors without paths or backend bodies', async () => {
 apiMock.mockRejectedValue(new Error('/private/secret credential')); const result = await actions.previewIncidentWithdrawal({}, form({id:'1',expected_version:'3',reason_en:'Synthetic',reason_ar:'تجريبي'})); expect(result.error).toContain('unavailable'); expect(JSON.stringify(result)).not.toContain('secret');
});
it('submits complete correction fields without accepting forged review flags', async()=>{
 const data=form({id:'1',expected_version:'3',title_en:'Synthetic',title_ar:'تجريبي',category:'infrastructure',summary_en:'Synthetic summary',summary_ar:'ملخص',uncertainty_en:'Unknown',uncertainty_ar:'مجهول',location_en:'Withheld',location_ar:'محجوب',precision:'withheld',occurred_at:'2026-10-14T10:00:00Z',confidence:'unverified',reason_en:'Synthetic reason',reason_ar:'سبب',human_approved:'on'});
 await expect(actions.saveIncidentCorrection(data)).rejects.toThrow('saved=1');
 expect(apiMock).toHaveBeenCalledWith('/incidents/1/correction','PUT',expect.objectContaining({expected_version:3,fields:expect.objectContaining({title_en:'Synthetic',private_governorate:null})}));
 expect(apiMock.mock.calls[0][2]).not.toHaveProperty('review');expect(apiMock.mock.calls[0][2].fields).not.toHaveProperty('human_approved');
});
it('records every review flag independently with current version',async()=>{
 await expect(actions.reviewIncidentCorrection(form({id:'1',expected_version:'3',rationale:'Synthetic rationale',human_approved:'on',time_checked:'on'}))).rejects.toThrow('reviewed=1');
 expect(apiMock).toHaveBeenCalledWith('/incidents/1/correction/review','POST',expect.objectContaining({expected_version:3,human_approved:true,time_checked:true,person_safety_checked:false,operational_safety_checked:false,primary_evidence_checked:false}));
});
it('returns only the exact withdrawal preview received from the server',async()=>{
 const preview={record:{title:{en:'Withdrawn report',ar:'تقرير مسحوب'}},preview_hash:'server-digest',version:3};apiMock.mockResolvedValue(preview);
 expect(await actions.previewIncidentWithdrawal({},form({id:'1',expected_version:'3',reason_en:'Synthetic',reason_ar:'تجريبي'}))).toEqual({preview});
});
it('keeps export failures generic without forwarding private paths or raw backend bodies', async () => {
 apiMock.mockRejectedValue(new Error('/private/pending-exports/incident-1.json {"rawText":"SYNTHETIC PRIVATE BODY"}'));
 await expect(actions.exportIncident(form({ id: '1', acknowledged: 'on' }))).rejects.toThrow('/incident/1/publication?error=1');
 const destination = decodeURIComponent(String(redirectMock.mock.calls[0]?.[0]));
 expect(destination).not.toContain('/private/');
 expect(destination).not.toContain('rawText');
 expect(destination).not.toContain('SYNTHETIC PRIVATE BODY');
});
