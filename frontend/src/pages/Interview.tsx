import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Bar, BigScore, Btn, Card, ErrorMsg, errText, Field, PageTitle, Pill } from '../components/ui';

export default function Interview() {
  const [roles, setRoles] = useState<string[]>([]);
  const [cfg, setCfg] = useState({ role: '', difficulty: 'medium', num_questions: 6, use_llm: true });
  const [s, setS] = useState<any>(null);
  const [idx, setIdx] = useState(0);
  const [ans, setAns] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [err, setErr] = useState('');
  const [past, setPast] = useState<any[]>([]);
  const loadPast = () => api.get('/interview/sessions').then((r) => setPast(r.data)).catch(() => {});
  useEffect(() => { api.get('/roles').then((r) => setRoles(r.data)); loadPast(); }, []);

  async function start() {
    setErr(''); setBusy(true);
    try { const r = await api.post('/interview/start', cfg); setS(r.data); setIdx(0); setAns(''); setNotice(r.data.notice || ''); } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  }
  async function submit() {
    setErr(''); setBusy(true);
    try {
      const r = await api.post(`/interview/${s.id}/answer`, { question_index: idx, answer: ans });
      const qs = s.questions.map((q: any, i: number) => (i === idx ? { ...q, answer: ans, evaluation: r.data.evaluation } : q));
      setS({ ...s, questions: qs }); if (r.data.notice) setNotice(r.data.notice);
    } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  }
  async function finish() {
    setErr(''); try { setS((await api.post(`/interview/${s.id}/finish`)).data); loadPast(); } catch (e) { setErr(errText(e)); }
  }
  async function open(id: number) { const r = await api.get(`/interview/${id}`); setS(r.data); setIdx(0); }

  if (!s) return (
    <>
      <PageTitle title="Interview Agent" sub="A mock interview built from your target role, skills and projects, with feedback on every answer." />
      <div className="grid lg:grid-cols-2 gap-5">
        <Card><div className="space-y-4">
          <Field label="Role"><select value={cfg.role} onChange={(e) => setCfg({ ...cfg, role: e.target.value })}><option value="">My career goal</option>{roles.map((r) => <option key={r}>{r}</option>)}</select></Field>
          <Field label="Difficulty"><select value={cfg.difficulty} onChange={(e) => setCfg({ ...cfg, difficulty: e.target.value })}><option>easy</option><option>medium</option><option>hard</option></select></Field>
          <Field label="Number of questions"><input type="number" min={3} max={10} value={cfg.num_questions} onChange={(e) => setCfg({ ...cfg, num_questions: Number(e.target.value) })} /></Field>
          <label className="flex gap-2 items-center text-sm text-slate-300"><input type="checkbox" style={{ width: 'auto' }} checked={cfg.use_llm} onChange={(e) => setCfg({ ...cfg, use_llm: e.target.checked })} />Use my configured LLM (Settings) for questions and evaluation</label>
          <Btn onClick={start} disabled={busy}>{busy ? 'Preparing…' : 'Start mock interview'}</Btn><ErrorMsg msg={err} />
        </div><p className="text-xs text-slate-500 mt-4">Without an LLM, answers are scored with keyword and structure checks, which is useful practice but cannot judge correctness. Add a key in Settings for deeper feedback.</p></Card>
        <Card><h3 className="font-semibold mb-3">Past sessions</h3>{past.length === 0 && <div className="text-sm text-slate-400">None yet.</div>}
          {past.map((p) => <button key={p.id} onClick={() => open(p.id)} className="w-full flex justify-between text-sm py-2 border-b border-slate-800"><span>{p.role} · {new Date(p.created_at).toLocaleDateString()}</span><span className="text-slate-400">{p.status === 'finished' ? `${p.overall_score}/100` : `${p.answered}/${p.total} answered`}</span></button>)}</Card>
      </div>
    </>
  );

  if (s.status === 'finished') return (
    <>
      <PageTitle title="Interview summary" sub={`${s.role} · ${s.mode === 'llm' ? 'LLM evaluated' : 'keyword-based evaluation'}`} />
      <div className="grid md:grid-cols-3 gap-4 mb-4"><Card><BigScore value={s.overall_score} label="Overall" /><div className="mt-2"><Pill tone="cyan">{s.summary.verdict}</Pill></div></Card>
        <Card className="md:col-span-2"><h3 className="font-semibold mb-3">By category</h3>{Object.entries(s.summary.by_category).map(([k, v]: any) => <Bar key={k} value={v} label={k} />)}</Card></div>
      <div className="grid md:grid-cols-2 gap-4 mb-4"><Card><h3 className="font-semibold mb-2">Strengths</h3><ul className="list-disc pl-5 text-sm text-emerald-300">{s.summary.strengths.map((x: string) => <li key={x}>{x}</li>)}</ul></Card>
        <Card><h3 className="font-semibold mb-2">Work on</h3><ul className="list-disc pl-5 text-sm text-amber-300">{s.summary.improvements.map((x: string) => <li key={x}>{x}</li>)}</ul></Card></div>
      {s.questions.map((q: any) => <Card key={q.id} className="mb-3"><div className="flex justify-between"><b>{q.question}</b><span className="text-cyan-300 ml-3">{q.evaluation ? `${q.evaluation.score}/10` : 'skipped'}</span></div>{q.evaluation && <div className="text-sm text-slate-400 mt-2">{q.evaluation.feedback}</div>}</Card>)}
      <Btn onClick={() => setS(null)}>Back</Btn>
    </>
  );

  const q = s.questions[idx]; const done = !!q.evaluation; const answered = s.questions.filter((x: any) => x.evaluation).length;
  return (
    <>
      <PageTitle title="Mock interview" sub={`${s.role} · question ${idx + 1} of ${s.questions.length} · ${s.mode === 'llm' ? 'LLM evaluated' : 'keyword-based evaluation'}`} />
      {notice && <div className="text-amber-300 text-sm mb-3">{notice}</div>}
      <Card><div className="flex gap-2 mb-3"><Pill tone="cyan">{q.category}</Pill>{q.topic && <Pill>{q.topic}</Pill>}</div>
        <div className="text-xl font-semibold">{q.question}</div>
        <textarea className="min-h-48 mt-5" disabled={done} value={done ? q.answer : ans} onChange={(e) => setAns(e.target.value)} placeholder="Type your answer as you would say it in the interview…" />
        <ErrorMsg msg={err} />
        {!done && <div className="mt-4"><Btn onClick={submit} disabled={busy || ans.trim().length < 1}>{busy ? 'Evaluating…' : 'Submit answer'}</Btn></div>}
        {done && <div className="mt-5 border-t border-slate-800 pt-4"><div className="text-2xl font-bold text-cyan-300">{q.evaluation.score}/10</div><p className="text-slate-300 mt-1">{q.evaluation.feedback}</p>
          {q.evaluation.improvements?.length > 0 && <ul className="list-disc pl-5 text-sm text-amber-300 mt-3">{q.evaluation.improvements.map((x: string) => <li key={x}>{x}</li>)}</ul>}
          {q.evaluation.ideal_answer_points?.length > 0 && <div className="text-sm text-slate-400 mt-3"><b>Strong answers mention:</b> {q.evaluation.ideal_answer_points.join('; ')}</div>}</div>}
      </Card>
      <div className="flex gap-3 mt-4"><Btn variant="ghost" disabled={idx === 0} onClick={() => { setIdx(idx - 1); setAns(''); }}>Previous</Btn>
        {idx < s.questions.length - 1 && <Btn variant="ghost" onClick={() => { setIdx(idx + 1); setAns(''); }}>{done ? 'Next question' : 'Skip'}</Btn>}
        <Btn onClick={finish} disabled={answered === 0}>Finish & get summary</Btn></div>
    </>
  );
}
