import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
const { apiMock } = vi.hoisted(() => ({ apiMock: vi.fn() }));
vi.mock('../../../../lib/api', () => ({ api: apiMock }));
vi.mock('../../../actions', () => ({ approveIncidentCorrection: vi.fn(), exportIncident: vi.fn(), reviewIncidentCorrection: vi.fn(), saveIncidentCorrection: vi.fn(), approveIncidentWithdrawal:vi.fn(),previewIncidentWithdrawal:vi.fn() }));
import Page from './page';
afterEach(cleanup);
let publication: {version:number;record:Record<string,unknown>|null;history:unknown[];draft:unknown};
beforeEach(() => {
 publication={version:2,record:{status:'corrected'},history:[{version:1,action:'published',created_at:'2026-10-14',record:{title:'Synthetic initial'}}],draft:{base_version:2,fields:{title_en:'Synthetic title',precision:'withheld'},review:{},reason_en:'Synthetic correction',reason_ar:'تصحيح'}};
 apiMock.mockImplementation((path:string)=>path.endsWith('/publication')?Promise.resolve(publication):path.endsWith('/correction/preview')?Promise.resolve({record:{status:'corrected'},version:2,preview_hash:'exact-server-digest'}):Promise.resolve({id:1,state:'approved'}));
});
const page=()=>Page({params:Promise.resolve({id:'1'}),searchParams:Promise.resolve({})});
it('renders complete correction editor and all renewed review checks with server preview identity',async()=>{
 const {container}=render(await page());
 for(const name of ['title_en','title_ar','summary_en','summary_ar','uncertainty_en','uncertainty_ar','location_en','location_ar','occurred_at','category','precision','confidence','private_governorate','reason_en','reason_ar','independence_checked','time_checked','location_checked','contradictions_checked','person_safety_checked','operational_safety_checked','primary_evidence_checked','contradictions_acknowledged','human_approved']) expect(container.querySelector(`[name="${name}"]`)).toBeTruthy();
 expect(container.querySelector('[name="preview_hash"]')?.getAttribute('value')).toBe('exact-server-digest');
 expect(container.querySelector('[name="acknowledged"]')?.hasAttribute('required')).toBe(true);
 expect(screen.getByText(/Saving any edit resets review/)).toBeTruthy();expect(screen.getByText(/Version 1 · published/)).toBeTruthy();
});
it('removes correction, withdrawal and restore controls after terminal withdrawal',async()=>{
 publication.record={status:'withdrawn'};render(await page());expect(screen.queryByRole('button',{name:'Save correction draft'})).toBeNull();expect(screen.queryByRole('button',{name:'Preview withdrawal'})).toBeNull();expect(screen.getByText(/Withdrawn is terminal/)).toBeTruthy();
});
it('shows legacy initialization and generic service failures safely',async()=>{
 publication={version:0,record:null,history:[],draft:null};const {unmount}=render(await page());expect(screen.getByText(/No export snapshot exists/)).toBeTruthy();unmount();apiMock.mockRejectedValue(new Error('/private/secret'));render(await page());expect(screen.getByRole('alert').textContent).toContain('unavailable');expect(screen.queryByText(/secret/)).toBeNull();
});
it('fails closed when correction review cannot produce an exact preview',async()=>{
 const implementation=apiMock.getMockImplementation()!;apiMock.mockImplementation((path:string)=>path.endsWith('/correction/preview')?Promise.reject(new Error('PRIVATE secret')):implementation(path));
 render(await page());expect(screen.queryByRole('button',{name:'Approve correction locally'})).toBeNull();expect(screen.getByText(/Complete the full publication safety review/)).toBeTruthy();expect(screen.queryByText(/PRIVATE secret/)).toBeNull();
});
