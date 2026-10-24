import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Bar, BigScore, Btn, Card, Chips, ErrorMsg, errText, PageTitle, Pill } from '../components/ui';

export default function Companies() {
  const [tab, setTab] = useState<'co' | 'jd'>('co');
  const [m, setM] = useState<any[] | null>(null);
  const [note, setNote] = useState('');
  const [jd, setJd] = useState('');
  const [r, setR] = useState<any>(null);
  const [err, setErr] = useState('');
  useEffect(() => { api.get('/companies/matches', { params: { top: 14 } }).then((x) => { setM(x.data.matches); setNote(x.data.note); }).catch((e) => setErr(errText(e))); }, []);
  const tone: any = { 'Strong fit': 'green', 'Good fit': 'cyan', Stretch: 'amber', 'Not yet': 'red' };
  return (
    <>
      <PageTitle title="Job Matching Agent" sub="Company/role matches from your skills, profile similarity, coding strength and CGPA, plus job-description matching." />
      <div className="flex gap-2 mb-5"><Btn variant={tab === 'co' ? 'primary' : 'ghost'} onClick={() => setTab('co')}>Company / role matches</Btn><Btn variant={tab === 'jd' ? 'primary' : 'ghost'} onClick={() => setTab('jd')}>Match a job description</Btn></div>
      <ErrorMsg msg={err} />
      {tab === 'co' && <>
        {!m && !err && <div className="text-slate-400">Matching…</div>}
        <div className="grid lg:grid-cols-2 gap-4">
          {m?.map((x) => (
            <Card key={x.company + x.role}>
              <div className="flex justify-between items-start"><div><b className="text-lg">{x.company}</b><div className="text-sm text-slate-400">{x.role} · {x.category}</div></div>
                <div className="text-right"><div className="text-3xl font-bold text-cyan-300">{x.match_score}%</div><Pill tone={tone[x.fit]}>{x.fit}</Pill></div></div>
              <div className="mt-4"><Bar value={x.breakdown.skills} label="Skills" /><Bar value={x.breakdown.dsa_fit} label="DSA fit" /><Bar value={x.breakdown.academics} label="Academics" /></div>
              {x.missing_skills.length > 0 && <div className="mt-2"><div className="text-xs text-slate-500 mb-2">Missing core skills</div><Chips tone="amber" items={x.missing_skills} /></div>}
              {x.how_to_improve.length > 0 && <ul className="list-disc pl-5 text-sm text-slate-300 mt-3">{x.how_to_improve.map((t: string) => <li key={t}>{t}</li>)}</ul>}
              <div className="text-xs text-slate-500 mt-3">Process: {x.selection_process}</div>
            </Card>))}
        </div>
        {note && <div className="text-xs text-slate-500 mt-4">{note}</div>}
      </>}
      {tab === 'jd' && <Card>
        <textarea className="min-h-64" value={jd} onChange={(e) => setJd(e.target.value)} placeholder="Paste the job description…" />
        <div className="mt-4"><Btn disabled={jd.length < 20} onClick={async () => { setErr(''); try { setR((await api.post('/job/match', { job_description: jd })).data); } catch (e) { setErr(errText(e)); } }}>Match job</Btn></div>
        {r && <div className="mt-6 grid md:grid-cols-2 gap-5"><div><BigScore value={r.match_score} label="Match score" /><div className="mt-2"><Pill tone={tone[r.fit]}>{r.fit}</Pill></div>{r.note && <p className="text-sm text-amber-300 mt-3">{r.note}</p>}</div>
          <div><div className="text-sm text-slate-400 mb-2">You have</div><Chips tone="green" items={r.matched} /><div className="text-sm text-slate-400 mt-4 mb-2">Missing</div><Chips tone="amber" items={r.missing} />
            {r.advice.length > 0 && <ul className="list-disc pl-5 text-sm text-slate-300 mt-4">{r.advice.map((a: string) => <li key={a}>{a}</li>)}</ul>}</div></div>}
      </Card>}
    </>
  );
}
