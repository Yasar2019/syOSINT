'use server';

import {redirect} from 'next/navigation';
import {api} from '../../lib/api';

function text(form:FormData,key:string){return String(form.get(key)??'').trim()}
function positive(form:FormData,key:string){const value=text(form,key);if(!/^[1-9]\d*$/.test(value)||!Number.isSafeInteger(Number(value)))throw new Error('Invalid identifier');return Number(value)}
function reason(form:FormData){const value=text(form,'reason');if(!value||value.length>1000)throw new Error('Reason required');return value}
function failed():never{redirect('/maintenance?error=1')}
export async function previewRetention(){
 try{await api('/retention/preview','POST')}catch{failed()}
 redirect('/maintenance');
}
export async function applyRetention(form:FormData){
 try{if(form.get('acknowledged')!=='on')throw new Error('Acknowledgment required');await api('/retention/run','POST',{acknowledged:true})}catch{failed()}
 redirect('/maintenance?applied=1');
}
export async function placeRetentionHold(form:FormData){
 try{
  const target_kind=text(form,'target_kind');if(!['intake','media','quarantine'].includes(target_kind))throw new Error('Invalid target');
  await api('/retention/holds','POST',{target_kind,target_id:positive(form,'target_id'),reason:reason(form)});
 }catch{failed()}
 redirect('/maintenance');
}
export async function releaseRetentionHold(form:FormData){
 try{await api(`/retention/holds/${positive(form,'hold_id')}/release`,'POST',{reason:reason(form)})}catch{failed()}
 redirect('/maintenance');
}
