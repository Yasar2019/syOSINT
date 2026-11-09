import {render,screen,cleanup} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
const {apiMock}=vi.hoisted(()=>({apiMock:vi.fn()}));
vi.mock('../../lib/api',()=>({api:apiMock}));
vi.mock('./actions',()=>({previewRetention:vi.fn(),applyRetention:vi.fn(),placeRetentionHold:vi.fn(),releaseRetentionHold:vi.fn()}));
import Maintenance from './page';
afterEach(()=>{cleanup();apiMock.mockReset()});
function fixture(apply:boolean){apiMock.mockImplementation((path:string)=>Promise.resolve(path==='/retention/status'?{enabled:true,apply_enabled:apply,media_days:30,metadata_days:180,last_run:null}:path==='/retention/holds'?[{id:2,target_kind:'intake',target_id:7,reason:'Synthetic preservation',released_at:null,created_at:'2026-11-08T00:00:00Z'}]:{media:3,intake:4,quarantine:1,previews:2,protected:5,failed:0,bounded:false}));}
it('shows policy, dry-run counts and holds without deletion controls when disabled',async()=>{
 fixture(false);render(await Maintenance({searchParams:Promise.resolve({})}));expect(screen.getByText('Preview mode — deletion disabled')).toBeTruthy();expect(screen.getByText(/30 days/)).toBeTruthy();expect(screen.getByText(/180 days/)).toBeTruthy();expect(screen.getByText('Synthetic preservation')).toBeTruthy();expect(screen.queryByRole('button',{name:'Delete eligible private data'})).toBeNull();expect(screen.getByRole('heading',{name:'Cleanup preview'})).toBeTruthy();
});
it('requires explicit checked acknowledgment for enabled manual cleanup',async()=>{
 fixture(true);render(await Maintenance({searchParams:Promise.resolve({})}));expect(screen.getByLabelText('I reviewed the preview and authorize deletion of eligible private data').hasAttribute('required')).toBe(true);expect(screen.getByRole('button',{name:'Delete eligible private data'})).toBeTruthy();
});
it('renders only safe generic error text',async()=>{
 apiMock.mockRejectedValue(new Error('/private/SECRET'));render(await Maintenance({searchParams:Promise.resolve({error:'SECRET'})}));expect(screen.getByRole('alert').textContent).not.toContain('SECRET');
});
