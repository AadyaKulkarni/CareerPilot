import { useEffect, useState } from 'react';
import { Bar as RBar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../lib/api';
import { Bar, BigScore, Btn, Card, ErrorMsg, errText, Field, PageTitle, Pill } from '../components/ui';

export default function Coding() {
  const [a, setA] = useState<any>(null);
  const [h, setH] = useState({ leetcode: '', codeforces: '', github: '' });
  const [m, setM] = useState({ easy: 0, medium: 0, hard: 0, rating: '', contests: 0 });
  const [errors, setErrors] = useState<any>({});
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get('/coding/analytics').then((r) => setA(r.data)).catch((e) => setErr(errText(e))); }, []);

  async function sync() {
    setBusy(true); setErr(''); setErrors({});
    try { const r = await api.post('/coding/sync', h); setA(r.data.analytics); setErrors(r.data.errors); } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  }
  async function saveManual() {
    setErr('');
    try { setA((await api.post('/coding/manual', { ...m, rating: m.rating ? Number(m.rating) : null })).data); } catch (e) { setErr(errText(e)); }
  }
  async function remove(p: string) { setA((await api.delete(`/coding/${p}`)).data); }
  const mix = a ? [{ n: 'Easy', v: a.difficulty_mix.easy, c: '#34d399' }, { n: 'Medium', v: a.difficulty_mix.medium, c: '#fbbf24' }, { n: 'Hard', v: a.difficulty_mix.hard, c: '#f87171' }] : [];
  const num = (k: string) => <input type="number" min={0} value={(m as any)[k]} onChange={(e) => setM({ ...m, [k]: Number(e.target.value) })} />;
  return (
    <>
      <PageTitle title="Coding Analytics Agent" sub="Pulls public stats from LeetCode, Codeforces and GitHub and turns them into practice advice." />
      <div className="grid lg:grid-cols-2 gap-5 mb-5">
        <Card><h3 className="font-semibold mb-4">Link your profiles</h3>
          <div className="space-y-3">
            {(['leetcode', 'codeforces', 'github'] as const).map((k) => (
              <Field key={k} label={`${k[0].toUpperCase() + k.slice(1)} username or profile URL`}><input value={h[k]} onChange={(e) => setH({ ...h, [k]: e.target.value })} placeholder={k === 'github' ? 'octocat' : 'username'} />
                {errors[k] && <div className="text-red-300 text-xs mt-1">{errors[k]}</div>}</Field>))}
          </div>
          <div className="mt-4"><Btn onClick={sync} disabled={busy || !(h.leetcode || h.codeforces || h.github)}>{busy ? 'Fetching…' : 'Fetch my stats'}</Btn></div>
          <ErrorMsg msg={err} />
        </Card>
        <Card><h3 className="font-semibold mb-1">Or enter stats manually</h3><p className="text-xs text-slate-500 mb-3">Use this for HackerRank, CodeChef, GeeksforGeeks, or if a platform is unreachable.</p>
          <div className="grid grid-cols-3 gap-3"><Field label="Easy">{num('easy')}</Field><Field label="Medium">{num('medium')}</Field><Field label="Hard">{num('hard')}</Field></div>
          <div className="grid grid-cols-2 gap-3 mt-3"><Field label="Contest rating (optional)"><input type="number" value={m.rating} onChange={(e) => setM({ ...m, rating: e.target.value })} /></Field><Field label="Contests attended">{num('contests')}</Field></div>
          <div className="mt-4"><Btn variant="ghost" onClick={saveManual}>Save manual stats</Btn></div></Card>
      </div>
      {a && <>
        <div className="grid md:grid-cols-3 gap-4 mb-4">
          <Card><BigScore value={a.score} label="Coding score" /><div className="mt-2"><Pill tone="cyan">{a.level}</Pill></div></Card>
          <Card><div className="text-slate-400 text-sm">Problems solved</div><div className="text-4xl font-bold mt-2">{a.total_solved}</div><div className="text-sm text-slate-500 mt-2">{a.contests || 0} contests attended</div></Card>
          <Card><div className="h-28"><ResponsiveContainer><BarChart data={mix}><XAxis dataKey="n" stroke="#94a3b8" /><YAxis hide /><Tooltip /><RBar dataKey="v" radius={4}>{mix.map((x) => <Cell key={x.n} fill={x.c} />)}</RBar></BarChart></ResponsiveContainer></div></Card>
        </div>
        {a.assessed && <div className="grid lg:grid-cols-2 gap-4">
          <Card><h3 className="font-semibold mb-3">Score breakdown</h3>{Object.entries(a.score_breakdown).map(([k, v]: any) => <Bar key={k} value={(v / ({ volume: 60, ratings: 15, difficulty_balance: 10, contests: 5, github: 10 } as any)[k]) * 100} label={k.replace('_', ' ')} right={String(v)} />)}
            <h3 className="font-semibold mt-5 mb-2">Linked platforms</h3>{a.platforms.map((p: any) => <div key={p.platform} className="flex justify-between text-sm mb-2"><span>{p.platform} · {p.handle}{p.solved.total ? ` · ${p.solved.total} solved` : ''}{p.rating ? ` · rating ${p.rating}` : ''}</span><button className="text-red-300" onClick={() => remove(p.platform)}>remove</button></div>)}</Card>
          <Card>
            {a.strengths.length > 0 && <><h3 className="font-semibold mb-2">Strengths</h3><ul className="list-disc pl-5 text-sm text-emerald-300 mb-4">{a.strengths.map((s: string) => <li key={s}>{s}</li>)}</ul></>}
            {a.weaknesses.length > 0 && <><h3 className="font-semibold mb-2">Gaps</h3><ul className="list-disc pl-5 text-sm text-amber-300 mb-4">{a.weaknesses.map((s: string) => <li key={s}>{s}</li>)}</ul></>}
            {a.recommendations.length > 0 && <><h3 className="font-semibold mb-2">Recommendations</h3><ul className="list-disc pl-5 text-sm text-slate-300">{a.recommendations.map((s: string) => <li key={s}>{s}</li>)}</ul></>}
          </Card></div>}
        {!a.assessed && <Card><div className="text-slate-400">{a.recommendations[0]}</div></Card>}
      </>}
    </>
  );
}
