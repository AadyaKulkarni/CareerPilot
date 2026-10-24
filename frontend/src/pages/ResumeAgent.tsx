import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Bar, BigScore, Btn, Card, Chips, ErrorMsg, errText, Field, PageTitle } from '../components/ui';

export default function ResumeAgent() {
  const [roles, setRoles] = useState<string[]>([]);
  const [role, setRole] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState('');
  const [apply, setApply] = useState(true);
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    api.get('/roles').then((r) => setRoles(r.data));
    api.get('/resume/latest').then((r) => r.data && setRes(r.data)).catch(() => {});
  }, []);

  async function run(kind: 'file' | 'text') {
    setErr(''); setBusy(true);
    try {
      if (kind === 'file') {
        if (!file) { setErr('Choose a PDF, DOCX or TXT file first.'); return; }
        const fd = new FormData(); fd.append('file', file); fd.append('target_role', role); fd.append('apply_to_profile', String(apply));
        setRes((await api.post('/resume/parse', fd)).data);
      } else {
        setRes((await api.post('/resume/analyze-text', { text, target_role: role })).data);
      }
    } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  }
  const p = res?.parsed;
  return (
    <>
      <PageTitle title="Resume Agent" sub="Upload your resume to extract skills, education and projects, and get an ATS-style score with fixes." />
      <div className="grid lg:grid-cols-2 gap-5">
        <Card>
          <Field label="Target role"><select value={role} onChange={(e) => setRole(e.target.value)}><option value="">Use my profile's career goal</option>{roles.map((r) => <option key={r}>{r}</option>)}</select></Field>
          <div className="mt-4"><Field label="Resume file (PDF, DOCX, TXT · max 5 MB)"><input type="file" accept=".pdf,.docx,.txt,.md" onChange={(e) => setFile(e.target.files?.[0] || null)} /></Field></div>
          <label className="flex items-center gap-2 mt-4 text-sm text-slate-300"><input type="checkbox" style={{ width: 'auto' }} checked={apply} onChange={(e) => setApply(e.target.checked)} />Add newly found skills, projects and CGPA to my profile (never overwrites what you entered)</label>
          <div className="mt-4"><Btn onClick={() => run('file')} disabled={busy}>{busy ? 'Analysing…' : 'Analyse resume file'}</Btn></div>
          <div className="mt-6 pt-5 border-t border-slate-800"><Field label="…or paste resume text"><textarea className="min-h-64" value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste resume text here" /></Field>
            <div className="mt-4"><Btn variant="ghost" onClick={() => run('text')} disabled={busy || text.length < 40}>Analyse pasted text</Btn></div></div>
          <ErrorMsg msg={err} />
        </Card>
        <div className="space-y-4">
          {!res && <Card><div className="text-slate-400">Your analysis will appear here.</div></Card>}
          {res && <>
            <Card><BigScore value={res.ats_score} label={`ATS score · ${res.target_role}`} />
              <div className="mt-4">{res.breakdown.map((b: any) => <Bar key={b.name} value={(b.score / b.max) * 100} label={b.name} right={`${b.score}/${b.max}`} />)}</div>
              {res.profile_fields_added?.length > 0 && <div className="text-sm text-emerald-300 mt-2">Added to your profile: {res.profile_fields_added.join(', ')}</div>}</Card>
            {res.suggestions.length > 0 && <Card><h3 className="font-semibold mb-3">How to improve</h3><ul className="list-disc pl-5 text-sm text-slate-300 space-y-1">{res.suggestions.map((s: string) => <li key={s}>{s}</li>)}</ul></Card>}
            <Card><h3 className="font-semibold mb-3">What the agent extracted</h3>
              <div className="text-sm text-slate-300 space-y-2">
                <div><b>Name:</b> {p.name || '—'} · <b>Email:</b> {p.contact.email || '—'} · <b>Phone:</b> {p.contact.phone || '—'}</div>
                <div><b>Education:</b> {p.education.degree || '—'} · CGPA {p.education.cgpa ?? '—'} · {p.education.graduation_year ?? '—'}</div>
                {Object.keys(p.links).length > 0 && <div><b>Links:</b> {Object.entries(p.links).map(([k, v]) => `${k}: ${v}`).join(' · ')}</div>}
                <div><b>Skills ({p.skills.length}):</b><div className="mt-2"><Chips items={p.skills} tone="cyan" /></div></div>
                {p.projects.length > 0 && <div><b>Projects:</b> {p.projects.map((x: any) => x.title).join('; ')}</div>}
                {p.experience.length > 0 && <div><b>Experience:</b> {p.experience.map((x: any) => x.title).join('; ')}</div>}
              </div></Card>
          </>}
        </div>
      </div>
    </>
  );
}
