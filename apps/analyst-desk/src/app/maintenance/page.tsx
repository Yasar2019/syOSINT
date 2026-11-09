import Link from 'next/link';
import {api} from '../../lib/api';
import {previewRetention,applyRetention,placeRetentionHold,releaseRetentionHold} from './actions';

export const dynamic='force-dynamic';
type Counts={media:number;intake:number;quarantine:number;previews:number;protected:number;failed:number;bounded:boolean};
type Status={enabled:boolean;apply_enabled:boolean;media_days:number;metadata_days:number;last_run:object|null};
type Hold={id:number;target_kind:string;target_id:number;reason:string;created_at:string;released_at:string|null};
const labels:Record<Exclude<keyof Counts,'bounded'>,string>={media:'Expired media files',intake:'Expired intake records',quarantine:'Expired quarantine records',previews:'Expired previews',protected:'Protected records',failed:'Blocked or failed files'};

export default async function Maintenance({searchParams}:{searchParams:Promise<{error?:string;applied?:string}>}){
 let status:Status,counts:Counts,holds:Hold[];
 try{
  [status,counts,holds]=await Promise.all([api<Status>('/retention/status'),api<Counts>('/retention/preview','POST'),api<Hold[]>('/retention/holds')]);
 }catch{return <main className="shell"><Link href="/">← Analyst desk</Link><h1>Private data maintenance</h1><p role="alert">Maintenance unavailable. Check the local API and retry. No cleanup was requested by this page.</p></main>}
 const query=await searchParams;
 return <main className="shell"><Link href="/">← Analyst desk</Link><h1>Private data maintenance</h1><p lang="ar" dir="rtl">إدارة الاحتفاظ بالبيانات الخاصة وحماية الأدلة</p>
 <p>{status.apply_enabled?'Deletion enabled locally':'Preview mode — deletion disabled'}</p><p>{status.enabled?'Daily retention scheduler enabled':'Daily retention scheduler disabled'}</p>
 <p>Media expires after {status.media_days} days. Unlinked private intake metadata expires after {status.metadata_days} days. Case-linked evidence, publication history and preservation holds are protected.</p>
 {query.error&&<p role="alert">Maintenance action failed. Check the local settings and identifiers, then refresh the preview.</p>}
 {query.applied&&<p role="status">Cleanup request completed. Review the latest preview and local run history for remaining or blocked records.</p>}
 <section className="panel"><h2>Cleanup preview</h2><p>This preview does not delete or change private data. Applying cleanup recomputes eligibility.</p><dl>{Object.entries(labels).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{counts[key as keyof typeof labels]}</dd></div>)}</dl>
 {counts.bounded&&<p role="status">This preview is bounded. Additional expired records may remain for later runs. Expired child revision or media metadata may be removed while its parent remains for a later batch.</p>}
 <form action={previewRetention}><button>Refresh cleanup preview</button></form>
 {status.apply_enabled?<form action={applyRetention} className="form"><label className="check"><input type="checkbox" name="acknowledged" required/>I reviewed the preview and authorize deletion of eligible private data</label><button>Delete eligible private data</button></form>:<p>To activate deletion, configure SYOSINT_RETENTION_APPLY=1 locally and restart the API after reviewing holds and the preview.</p>}
 <p>{status.last_run?'Applied cleanup history is recorded locally in the audit trail.':'No applied cleanup runs recorded.'}</p></section>
 <section className="panel"><h2>Preservation holds</h2><p>Holds have no automatic expiry. Use the numeric intake, media or quarantine identifier from your private workspace.</p>
 <form action={placeRetentionHold} className="form"><label>Record type<select name="target_kind"><option value="intake">Intake record</option><option value="media">Media file</option><option value="quarantine">Quarantine record</option></select></label><label>Record ID<input name="target_id" type="number" min="1" step="1" required/></label><label>Preservation reason<textarea name="reason" required maxLength={1000}/></label><button>Place preservation hold</button></form>
 <p>Showing the most recent holds returned by the local API.</p><ul className="list">{holds.map(hold=><li key={hold.id}><article aria-label={`Hold ${hold.id}`}><h3>Hold {hold.id} · {hold.target_kind} {hold.target_id}</h3><p>{hold.reason}</p><time>{hold.created_at}</time>{hold.released_at?<p>Released · {hold.released_at}</p>:<form action={releaseRetentionHold} className="form"><input type="hidden" name="hold_id" value={hold.id}/><label>Release reason<textarea name="reason" required maxLength={1000}/></label><button>Release hold</button></form>}</article></li>)}</ul>{holds.length===0&&<p>No preservation holds recorded.</p>}</section>
 <footer>Local only · No public records are changed by private retention jobs</footer></main>;
}
