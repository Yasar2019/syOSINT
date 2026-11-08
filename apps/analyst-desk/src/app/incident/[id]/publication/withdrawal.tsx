"use client";
import { useActionState } from 'react';
import { approveIncidentWithdrawal, previewIncidentWithdrawal, type WithdrawalState } from '../../../actions';
export function Withdrawal({ id, version }: { id: string; version: number }) {
 const [state, action, pending] = useActionState<WithdrawalState, FormData>(previewIncidentWithdrawal, {});
 return <section className="panel"><h2>Withdraw report</h2><p>Withdrawal is terminal. Inspect the exact tombstone before approving.</p>
 <form action={action} className="form"><input type="hidden" name="id" value={id}/><input type="hidden" name="expected_version" value={version}/><label>Withdrawal reason · English<textarea name="reason_en" required maxLength={1000}/></label><label>سبب السحب · عربي<textarea name="reason_ar" dir="rtl" required maxLength={1000}/></label><button disabled={pending}>Preview withdrawal</button></form>
 {state.error && <p role="alert">{state.error}</p>}
 {state.preview && <><h3>Exact withdrawal preview</h3><pre>{JSON.stringify(state.preview.record,null,2)}</pre><form action={approveIncidentWithdrawal} className="form"><input type="hidden" name="id" value={id}/><input type="hidden" name="expected_version" value={state.preview.version}/><input type="hidden" name="preview_hash" value={state.preview.preview_hash}/><label className="check"><input type="checkbox" name="acknowledged" required/>I reviewed this exact withdrawal preview and approve the local revision</label><button>Approve withdrawal locally</button></form></>}
 </section>;
}
