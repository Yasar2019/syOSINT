import {beforeEach,expect,it,vi} from 'vitest';
const {apiMock,redirectMock}=vi.hoisted(()=>({apiMock:vi.fn(),redirectMock:vi.fn((url:string):never=>{throw new Error(`REDIRECT:${url}`)})}));
vi.mock('../../lib/api',()=>({api:apiMock}));
vi.mock('next/navigation',()=>({redirect:redirectMock}));
import {previewRetention,applyRetention,placeRetentionHold,releaseRetentionHold} from './actions';
const form=(values:Record<string,string>)=>{const f=new FormData();for(const [k,v] of Object.entries(values))f.set(k,v);return f};
beforeEach(()=>{apiMock.mockReset();redirectMock.mockClear()});
it('previews without applying cleanup',async()=>{
 await expect(previewRetention()).rejects.toThrow('REDIRECT:/maintenance');
 expect(apiMock).toHaveBeenCalledWith('/retention/preview','POST');
});
it('requires acknowledgment before applying and uses an explicit API body',async()=>{
 await expect(applyRetention(form({}))).rejects.toThrow('REDIRECT:/maintenance?error=1');expect(apiMock).not.toHaveBeenCalled();
 await expect(applyRetention(form({acknowledged:'on'}))).rejects.toThrow('REDIRECT:/maintenance?applied=1');expect(apiMock).toHaveBeenCalledWith('/retention/run','POST',{acknowledged:true});
});
it('creates and releases holds with validated positive identifiers',async()=>{
 await expect(placeRetentionHold(form({target_kind:'intake',target_id:'7',reason:' Preserve synthetic evidence '}))).rejects.toThrow('REDIRECT:/maintenance');
 expect(apiMock).toHaveBeenCalledWith('/retention/holds','POST',{target_kind:'intake',target_id:7,reason:'Preserve synthetic evidence'});
 await expect(releaseRetentionHold(form({hold_id:'3',reason:'Review completed'}))).rejects.toThrow('REDIRECT:/maintenance');expect(apiMock).toHaveBeenCalledWith('/retention/holds/3/release','POST',{reason:'Review completed'});
});
it.each(['0','-1','1.5','9007199254740992','secret/path'])('rejects invalid hold target %s without API changes',async(target_id)=>{
 await expect(placeRetentionHold(form({target_kind:'intake',target_id,reason:'Reason'}))).rejects.toThrow('REDIRECT:/maintenance?error=1');expect(apiMock).not.toHaveBeenCalled();
});
it('hides raw API errors and filesystem paths',async()=>{
 apiMock.mockRejectedValue(new Error('/private/vault/session SECRET BODY'));await expect(previewRetention()).rejects.toThrow('REDIRECT:/maintenance?error=1');expect(redirectMock.mock.calls[0][0]).not.toMatch(/SECRET|private|session/);
});
