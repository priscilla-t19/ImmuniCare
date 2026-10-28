import {useEffect,useState} from 'react';
export default function App(){
 const [status,setStatus]=useState('Checking API...');
 useEffect(()=>{fetch('/api/health').then(r=>{if(!r.ok)throw new Error('API unavailable');return r.json()}).then(d=>setStatus(d.status==='ok'?'API connected':'Unexpected response')).catch(()=>setStatus('API unavailable'));},[]);
 return <main style={{fontFamily:'system-ui',maxWidth:760,margin:'80px auto',padding:24}}><h1>ImmuniCare</h1><p>Multi-clinic immunisation management</p><p><strong>Foundation status:</strong> {status}</p><p>Milestone 1 — infrastructure only. No patient data is stored yet.</p></main>
}
