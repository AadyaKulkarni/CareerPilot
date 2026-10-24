import { ReactNode } from 'react';

export const Card = ({ children, className = '' }: { children?: ReactNode; className?: string }) => (
  <div className={`glass rounded-2xl p-5 ${className}`}>{children}</div>
);

export const Field = ({ label, children }: { label: string; children?: ReactNode }) => (
  <label className="text-sm text-slate-400 block">{label}<div className="mt-2">{children}</div></label>
);

export const PageTitle = ({ title, sub }: { title: string; sub?: string }) => (
  <div className="mb-6"><h1 className="text-3xl font-bold">{title}</h1>{sub && <p className="text-slate-400 mt-2">{sub}</p>}</div>
);

export const Btn = ({ children, onClick, disabled, variant = 'primary' }: { children?: ReactNode; onClick?: () => void; disabled?: boolean; variant?: 'primary' | 'ghost' }) => (
  <button onClick={onClick} disabled={disabled}
    className={`rounded-xl px-5 py-3 font-semibold ${variant === 'primary' ? 'bg-cyan-400 text-slate-950' : 'border border-slate-700 text-slate-200'} ${disabled ? 'opacity-50' : ''}`}>
    {children}
  </button>
);

export const scoreColor = (v: number) => (v >= 75 ? '#34d399' : v >= 50 ? '#22d3ee' : v >= 30 ? '#fbbf24' : '#f87171');

export const Bar = ({ value, label, right }: { value: number; label?: string; right?: string }) => (
  <div className="mb-3">
    {(label || right) && <div className="flex justify-between text-sm mb-1"><span>{label}</span><span className="text-slate-400">{right ?? `${Math.round(value)}%`}</span></div>}
    <div className="h-2 bg-slate-800 rounded-full overflow-hidden"><div className="h-2 rounded-full" style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: scoreColor(value) }} /></div>
  </div>
);

export const Pill = ({ children, tone = 'slate' }: { children?: ReactNode; tone?: 'slate' | 'amber' | 'green' | 'cyan' | 'red' }) => {
  const t: any = { slate: 'bg-slate-800 text-slate-300', amber: 'bg-amber-400/10 text-amber-300', green: 'bg-emerald-400/10 text-emerald-300', cyan: 'bg-cyan-400/10 text-cyan-300', red: 'bg-red-400/10 text-red-300' };
  return <span className={`px-3 py-1 rounded-full text-sm ${t[tone]}`}>{children}</span>;
};

export const BigScore = ({ value, label, max = 100 }: { value: number; label: string; max?: number }) => (
  <div>
    <div className="text-slate-400 text-sm">{label}</div>
    <div className="text-5xl font-bold mt-1" style={{ color: scoreColor((value / max) * 100) }}>{Math.round(value)}<span className="text-lg text-slate-500">/{max}</span></div>
  </div>
);

export const ErrorMsg = ({ msg }: { msg: string }) => (msg ? <div className="text-red-300 text-sm mt-3">{msg}</div> : null);
export const errText = (e: any) => e?.response?.data?.detail || e?.message || 'Something went wrong';
export const Chips = ({ items, tone }: { items: string[]; tone?: any }) => (
  <div className="flex flex-wrap gap-2">{items.map((x) => <Pill key={x} tone={tone}>{x}</Pill>)}</div>
);
