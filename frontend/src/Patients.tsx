import {useEffect, useState} from 'react';

type Patient={id:string;full_name:string;birth_certificate_number:string;date_of_birth:string;guardians?:Array<Guardian&{relationship_type:string}>};
type Guardian={id:string;full_name:string;phone:string|null};
async function request(path:string,token:string,method='GET',data?:unknown){
 const res=await fetch('/api'+path,{method,headers:{Authorization:'Bearer '+token,...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined});
 if(!res.ok){const error=await res.json().catch(()=>({}));throw new Error(typeof error.detail==='string'?error.detail:`Request failed: ${res.status}`)}
 return res.status===204?null:res.json();
}
export default function Patients({clinicId,token}:{clinicId:string;token:string}){
 const [patients,setPatients]=useState<Patient[]>([]);const [guardians,setGuardians]=useState<Guardian[]>([]);
 const [search,setSearch]=useState('');const [selected,setSelected]=useState<Patient|null>(null);
 const [name,setName]=useState('');const [certificate,setCertificate]=useState('');const [dob,setDob]=useState('');
 const [guardianName,setGuardianName]=useState('');const [phone,setPhone]=useState('');
 const [guardianId,setGuardianId]=useState('');const [relationship,setRelationship]=useState('parent');
 const [message,setMessage]=useState('');const [busy,setBusy]=useState(false);
 const base=`/clinics/${clinicId}`;
 const refresh=async()=>{const [p,g]=await Promise.all([request(base+'/patients',token),request(base+'/guardians',token)]);setPatients(p);setGuardians(g)};
 useEffect(()=>{setSelected(null);setSearch('');refresh().catch(e=>setMessage(e.message))},[clinicId,token]);
 const perform=async(action:()=>Promise<void>)=>{setBusy(true);setMessage('');try{await action();await refresh()}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}};
 const view=async(id:string)=>{try{setSelected(await request(`${base}/patients/${id}`,token))}catch(e){setMessage((e as Error).message)}};
 return <div className="patient-module"><h2>Patients and guardians</h2><p>Demo records only. Records are restricted to the selected clinic.</p>
 <div className="module-grid"><div className="module-card"><h3>Register patient</h3><form onSubmit={e=>{e.preventDefault();perform(async()=>{await request(base+'/patients',token,'POST',{full_name:name,birth_certificate_number:certificate,date_of_birth:dob});setName('');setCertificate('');setDob('');setMessage('Patient registered')})}}>
 <label>Infant full name<input required minLength={2} maxLength={120} value={name} onChange={e=>setName(e.target.value)}/></label>
 <label>Birth certificate number (demo)<input required minLength={2} maxLength={60} value={certificate} onChange={e=>setCertificate(e.target.value)}/></label>
 <label>Date of birth<input required type="date" value={dob} max={new Date().toISOString().slice(0,10)} onChange={e=>setDob(e.target.value)}/></label>
 <button disabled={busy}>Register patient</button></form></div>
 <div className="module-card"><h3>Register guardian</h3><form onSubmit={e=>{e.preventDefault();perform(async()=>{await request(base+'/guardians',token,'POST',{full_name:guardianName,phone:phone||null});setGuardianName('');setPhone('');setMessage('Guardian registered')})}}>
 <label>Guardian full name<input required minLength={2} maxLength={120} value={guardianName} onChange={e=>setGuardianName(e.target.value)}/></label>
 <label>Phone (optional)<input maxLength={32} value={phone} onChange={e=>setPhone(e.target.value)}/></label>
 <button disabled={busy}>Register guardian</button></form></div></div>
 <div className="module-card"><h3>Patient directory</h3><label>Search patients<input placeholder="Search by name" value={search} onChange={e=>setSearch(e.target.value)}/></label>
 <ul className="record-list">{patients.filter(p=>p.full_name.toLowerCase().includes(search.toLowerCase())).map(p=><li key={p.id}><span>{p.full_name} · {p.date_of_birth}</span><button type="button" onClick={()=>view(p.id)}>View</button></li>)}</ul>
 {patients.length===0&&<p>No patients registered yet.</p>}</div>
 {selected&&<div className="module-card"><h3>{selected.full_name}</h3><p>Birth certificate: {selected.birth_certificate_number} · Born: {selected.date_of_birth}</p><h4>Linked guardians</h4><ul>{selected.guardians?.map(g=><li key={g.id}>{g.full_name} ({g.relationship_type}) <button className="quiet" onClick={()=>perform(async()=>{await request(`${base}/patients/${selected.id}/guardians/${g.id}`,token,'DELETE');await view(selected.id)})}>Unlink</button></li>)}</ul>
 <form onSubmit={e=>{e.preventDefault();perform(async()=>{await request(`${base}/patients/${selected.id}/guardians`,token,'POST',{guardian_id:guardianId,relationship_type:relationship});await view(selected.id);setGuardianId('')})}}>
 <label>Guardian<select required value={guardianId} onChange={e=>setGuardianId(e.target.value)}><option value="">Select guardian</option>{guardians.map(g=><option key={g.id} value={g.id}>{g.full_name}</option>)}</select></label>
 <label>Relationship<select value={relationship} onChange={e=>setRelationship(e.target.value)}><option value="parent">Parent</option><option value="guardian">Legal guardian</option><option value="other">Other</option></select></label>
 <button disabled={busy||!guardianId}>Link guardian</button></form></div>}
 {message&&<p role="alert" className="notice">{message}</p>}</div>;
}
