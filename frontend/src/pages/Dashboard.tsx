import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Area, AreaChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../lib/api';
import { Bar, BigScore, Card, Pill } from '../components/ui';

export default function Dashboard() {
  const [r, setR] = useState<any>(null);
  const [err, setErr] = useState('');
  useEffect(() => { api.get('/readiness').then((x) => setR(x.data)).catch(() => setErr('Could not load readiness score. Is the backend running?')); }, []);
  if (err) return <Card>{err}</Card>;
  if (!r) return <div className="text-slate-400">Loading your placement cockpit…</div>;
  const radar = r.components.map((c: any) => ({ n: c.label.split(' (')[0].slice(0, 16), v: c.assessed ? c.score : 0 }));
  const hist = (r.history || []).map((h: any, i: number) => ({ i: i + 1, score: h.score }));
  return (
    <>
      <div className="mb-7">
        <div className="text-cyan-300 text-sm font-semibold">PLACEMENT READINESS · {r.target_role?.toUpperCase()}</div>
        <h1 className="text-3xl md:text-4xl font-bold mt-1">Your placement cockpit</h1>
        <p className="text-slate-400 mt-2">One view of readiness, skill gaps, company fit and upskilling.</p>
      </div>
      <div className="grid md:grid-cols-3 gap-4 mb-4">
        <Card><BigScore value={r.score} label="Placement readiness score" /><div className="mt-3"><Pill tone="cyan">{r.band}</Pill></div></Card>
        <Card><div className="text-slate-400 text-sm">Assessment coverage</div><div className="text-4xl font-bold mt-2">{r.confidence}%</div>
          <div className="text-sm text-slate-500 mt-3">{r.note || 'Every area has been assessed.'}</div></Card>
        <Card><div className="text-slate-400 text-sm mb-2">Do next</div>
          {r.next_actions.length ? r.next_actions.slice(0, 3).map((a: any) => <div key={a.area} className="text-sm mb-2"><b>{a.area}:</b> <span className="text-slate-400">{a.action}</span></div>) : <div className="text-sm text-slate-400">You are on track. Keep practising.</div>}
        </Card>
      </div>
      <div className="grid lg:grid-cols-5 gap-4 mb-4">
        <Card className="lg:col-span-3"><h3 className="font-semibold mb-4">Score breakdown</h3>
          {r.components.map((c: any) => (
            <div key={c.key}><Bar value={c.score} label={`${c.label} · weight ${c.weight}`} right={c.assessed ? `${c.score}/100` : 'not assessed'} /><div className="text-xs text-slate-500 -mt-2 mb-3">{c.detail}</div></div>
          ))}
        </Card>
        <Card className="lg:col-span-2"><h3 className="font-semibold mb-4">Readiness radar</h3>
          <div className="h-64"><ResponsiveContainer><RadarChart data={radar}><PolarGrid stroke="#334155" /><PolarAngleAxis dataKey="n" stroke="#94a3b8" fontSize={10} /><PolarRadiusAxis domain={[0, 100]} stroke="#475569" /><Radar dataKey="v" stroke="#22d3ee" fill="#22d3ee" fillOpacity={0.2} /></RadarChart></ResponsiveContainer></div>
        </Card>
      </div>
      {hist.length > 1 && <Card className="mb-4"><h3 className="font-semibold mb-4">Score history</h3>
        <div className="h-48"><ResponsiveContainer><AreaChart data={hist}><XAxis dataKey="i" stroke="#64748b" /><YAxis domain={[0, 100]} stroke="#64748b" /><Tooltip /><Area dataKey="score" stroke="#22d3ee" fill="#22d3ee" fillOpacity={0.15} /></AreaChart></ResponsiveContainer></div></Card>}
      <div className="grid md:grid-cols-3 gap-4">
        {[['/analyzer', 'Resume Agent', 'Upload and score your resume'], ['/skill-gap', 'Skill Gap Agent', 'See what to learn next'], ['/coding', 'Coding Analytics', 'LeetCode, Codeforces, GitHub'],
          ['/jobs', 'Job Matching', 'Company and role matches'], ['/interview', 'Interview Agent', 'Practise a mock interview'], ['/roadmap', 'Learning Roadmap', 'Week-by-week plan']].map(([to, t, d]) => (
          <Link key={to} to={to}><Card><b>{t}</b><div className="text-sm text-slate-400 mt-1">{d}</div></Card></Link>))}
      </div>
    </>
  );
}
