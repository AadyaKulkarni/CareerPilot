import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bar as RBar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../lib/api';
import { Bar, BigScore, Btn, Card, Chips, ErrorMsg, errText, Field, PageTitle, Pill } from '../components/ui';

export default function SkillGap() {
  const [roles, setRoles] = useState<string[]>([]);
  const [role, setRole] = useState('');
  const [r, setR] = useState<any>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const load = (role_: string) => api.get('/skills/gap', { params: { target_role: role_ } }).then((x) => { setR(x.data); if (!role_) setRole(x.data.target_role); }).catch((e) => setErr(errText(e)));
  useEffect(() => { api.get('/roles').then((x) => setRoles(x.data)); load(''); }, []);
  async function roadmap() {
    setErr(''); setMsg('');
    try { const x = await api.post('/roadmap/generate', { hours_per_week: 10, target_role: role }); setMsg(`Roadmap created: ${x.data.count} tasks, ${x.data.total_hours}h in total.`); } catch (e) { setErr(errText(e)); }
  }
  if (!r) return <div className="text-slate-400">{err || 'Analysing your skills…'}</div>;
  const tone: any = { High: 'red', Medium: 'amber', Low: 'slate' };
  return (
    <>
      <PageTitle title="Skill Gap Agent" sub="Evidence from your profile, resume, projects and coding activity compared with what the role needs." />
      <div className="grid md:grid-cols-3 gap-4 mb-4">
        <Card><Field label="Target role"><select value={role} onChange={(e) => { setRole(e.target.value); load(e.target.value); }}>{roles.map((x) => <option key={x}>{x}</option>)}</select></Field></Card>
        <Card><BigScore value={r.coverage} label="Role skill coverage" /><div className="mt-2"><Pill tone="cyan">{r.band}</Pill></div></Card>
        <Card><div className="text-slate-400 text-sm">Estimated effort to close gaps</div><div className="text-4xl font-bold mt-2">{r.total_gap_hours}h</div>
          <div className="mt-3"><Btn onClick={roadmap}>Build my roadmap</Btn></div></Card>
      </div>
      <Card className="mb-4"><p className="text-slate-300">{r.summary}</p>{msg && <div className="text-emerald-300 text-sm mt-3">{msg} <Link to="/roadmap" className="underline">Open roadmap →</Link></div>}<ErrorMsg msg={err} /></Card>
      <div className="grid lg:grid-cols-2 gap-4 mb-4">
        <Card><h3 className="font-semibold mb-4">Skill-gap report</h3>
          {r.gaps.length === 0 && <div className="text-slate-400 text-sm">No gaps found for this role.</div>}
          {r.gaps.map((g: any) => (
            <div key={g.skill} className="mb-4"><div className="flex items-center justify-between"><b>{g.label}</b><Pill tone={tone[g.priority]}>{g.priority} · {g.estimated_hours}h</Pill></div>
              <div className="text-sm text-slate-400 mt-1">{g.how}</div></div>))}
        </Card>
        <Card><h3 className="font-semibold mb-4">Requirement by requirement</h3>
          {r.skills.map((s: any) => <Bar key={s.skill} value={s.proficiency * 100} label={`${s.label}${s.tier === 'nice' ? ' (bonus)' : ''}`} right={s.level || 'missing'} />)}
        </Card>
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <Card><h3 className="font-semibold mb-3">Strengths</h3>{r.strengths.length ? <Chips tone="green" items={r.strengths.map((s: any) => `${s.label} · ${s.level}`)} /> : <div className="text-sm text-slate-400">Add skills or upload your resume.</div>}</Card>
        <Card><h3 className="font-semibold mb-3">Closest roles for your skills</h3>
          <div className="h-56"><ResponsiveContainer><BarChart data={r.role_comparison} layout="vertical" margin={{ left: 30 }}><XAxis type="number" domain={[0, 100]} stroke="#64748b" /><YAxis type="category" dataKey="role" width={150} stroke="#94a3b8" fontSize={11} /><Tooltip /><RBar dataKey="coverage" fill="#22d3ee" radius={4} /></BarChart></ResponsiveContainer></div></Card>
      </div>
    </>
  );
}
