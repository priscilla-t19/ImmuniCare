import {useState} from 'react';
import './style.css';
type Clinic = {id:string;name:string;slug:string;role:string};
type Profile = {id:string;email:string;full_name:string;clinics:Clinic[]};
const api = async (path:string, method='GET', body?:unknown, token?:string) => {
  const response = await fetch('/api'+path,{method,headers:{...(body?{'Content-Type':'application/json'}:{}),...(token?{'Authorization':'Bearer '+token}:{})},body:body?JSON.stringify(body):undefined});
  if (!response.ok) { const error = await response.json().catch(()=>({})); throw new Error(typeof error.detail==='string'?error.detail:`Request failed (${response.status})`); }
  return response.status===204?null:response.json();
};
export default function App(){
 const [mode,setMode]=useState<'login'|'register'>('login');
 const [email,setEmail]=useState(''); const [password,setPassword]=useState('');
 const [fullName,setFullName]=useState(''); const [clinicName,setClinicName]=useState(''); const [slug,setSlug]=useState('');
 const [token,setToken]=useState(''); const [profile,setProfile]=useState<Profile|null>(null);
 const [selected,setSelected]=useState(''); const [staff,setStaff]=useState<{email:string;full_name:string;role:string}[]>([]);
 const [staffEmail,setStaffEmail]=useState(''); const [staffName,setStaffName]=useState(''); const [staffPassword,setStaffPassword]=useState(''); const [staffRole,setStaffRole]=useState('clinician');
 const [message,setMessage]=useState(''); const [busy,setBusy]=useState(false);
 const submit=async(e:React.FormEvent)=>{e.preventDefault();setBusy(true);setMessage('');try{
   if(mode==='register') {await api('/auth/register-clinic','POST',{clinic_name:clinicName,clinic_slug:slug,full_name:fullName,email,password});}
   const auth=await api('/auth/login','POST',{email,password});
   const me:Profile=await api('/auth/me','GET',undefined,auth.access_token);
   setToken(auth.access_token);setProfile(me);setSelected(me.clinics[0]?.id||'');setPassword('');
  }catch(err){setMessage((err as Error).message);}finally{setBusy(false);}};
 const logout=async()=>{try{await api('/auth/logout','POST',undefined,token);}catch{}setToken('');setProfile(null);setStaff([]);setMessage('');};
 const loadStaff=async()=>{setMessage('');try{const rows=await api(`/clinics/${selected}/staff`,'GET',undefined,token);setStaff(rows);}catch(err){setMessage((err as Error).message);}};
 const addStaff=async(e:React.FormEvent)=>{e.preventDefault();setBusy(true);setMessage('');try{await api(`/clinics/${selected}/staff`,'POST',{full_name:staffName,email:staffEmail,password:staffPassword,role:staffRole},token);setStaffEmail('');setStaffName('');setStaffPassword('');await loadStaff();setMessage('Staff account created. Share the temporary password securely.');}catch(err){setMessage((err as Error).message);}finally{setBusy(false);}};
 const current=profile?.clinics.find(c=>c.id===selected);
 return <div className="shell"><header><div className="brand">✚ ImmuniCare <span>Clinic workspace</span></div>{profile&&<button className="quiet" onClick={logout}>Log out</button>}</header><main>
 {!profile?<section className="panel auth"><div className="eyebrow">MILESTONE 2 · IDENTITY</div><h1>{mode==='login'?'Welcome back':'Register a clinic'}</h1><p>Secure staff access for the ImmuniCare demonstration platform.</p><form onSubmit={submit}>
 {mode==='register'&&<><label>Clinic name<input required minLength={2} maxLength={120} value={clinicName} onChange={e=>setClinicName(e.target.value)}/></label><label>Clinic slug (lowercase letters, numbers and hyphens)<input required pattern="[a-z0-9]+(-[a-z0-9]+)*" minLength={3} value={slug} onChange={e=>setSlug(e.target.value)}/></label><label>Your full name<input required minLength={2} value={fullName} onChange={e=>setFullName(e.target.value)}/></label></>}
 <label>Email<input type="email" required value={email} onChange={e=>setEmail(e.target.value)}/></label><label>Password<input type="password" required minLength={mode==='register'?12:1} value={password} onChange={e=>setPassword(e.target.value)}/></label>
 <button disabled={busy} type="submit">{busy?'Please wait...':mode==='login'?'Sign in':'Create clinic and sign in'}</button></form><button className="link" onClick={()=>{setMode(mode==='login'?'register':'login');setMessage('');}}>{mode==='login'?'Register a new clinic':'Already have an account? Sign in'}</button></section>
 :<section className="panel"><div className="eyebrow">AUTHENTICATED WORKSPACE</div><h1>Hello, {profile.full_name}</h1><p>Signed in as {profile.email}. This is the Milestone 2 identity dashboard; patient records are not implemented yet.</p><label>Clinic workspace<select value={selected} onChange={e=>{setSelected(e.target.value);setStaff([]);}}>{profile.clinics.map(c=><option value={c.id} key={c.id}>{c.name} — {c.role}</option>)}</select></label><div className="stat"><strong>{current?.name}</strong><span>Current role: {current?.role}</span></div>
 {current?.role==='admin'&&<div className="staff"><h2>Staff management</h2><button onClick={loadStaff}>Load staff list</button>{staff.length>0&&<ul>{staff.map(s=><li key={s.email}>{s.full_name} — {s.email} ({s.role})</li>)}</ul>}<h3>Create staff account</h3><form onSubmit={addStaff}><label>Full name<input required minLength={2} value={staffName} onChange={e=>setStaffName(e.target.value)}/></label><label>Email<input type="email" required value={staffEmail} onChange={e=>setStaffEmail(e.target.value)}/></label><label>Temporary password (12+ characters)<input type="password" minLength={12} required value={staffPassword} onChange={e=>setStaffPassword(e.target.value)}/></label><label>Role<select value={staffRole} onChange={e=>setStaffRole(e.target.value)}><option value="clinician">Clinician</option><option value="receptionist">Receptionist</option><option value="admin">Clinic administrator</option></select></label><button disabled={busy}>Create staff account</button></form></div>}
 </section>}
 {message&&<p role="alert" className="notice">{message}</p>}<p className="disclaimer">Development prototype only. Use synthetic demonstration data. Do not enter real patient information.</p>
 </main></div>;
}
