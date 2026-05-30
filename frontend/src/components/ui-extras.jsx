// Small reusable UI helpers used across pages.

export function Overline({ children, className = '' }) {
  return <div className={`overline ${className}`}>{children}</div>;
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex items-end justify-between border-b border-border px-8 py-6">
      <div>
        <div className="overline mb-2">{subtitle}</div>
        <h1 className="font-display text-3xl sm:text-4xl font-black tracking-tighter">{title}</h1>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function StatTile({ label, value, accent = 'default', mono = true, testid }) {
  const accentClass = {
    default: 'text-white',
    up: 'text-edgeUp',
    down: 'text-edgeDown',
    warn: 'text-edgeWarn',
    blue: 'text-[#0066FF]',
  }[accent];
  return (
    <div className="border border-border p-5 bg-ink-800" data-testid={testid}>
      <div className="overline mb-3">{label}</div>
      <div className={`${mono ? 'font-mono' : 'font-display'} text-3xl font-medium ${accentClass}`}>{value}</div>
    </div>
  );
}

export function EdgeBadge({ edge, outcome }) {
  const pct = (edge * 100).toFixed(1);
  const isPos = edge > 0.005;
  const isNeg = edge < -0.005;
  const color = isPos ? 'text-edgeUp border-edgeUp' : isNeg ? 'text-edgeDown border-edgeDown' : 'text-ink-300 border-border';
  const label = { home: 'GOSP', draw: 'REMIS', away: 'GOŚĆ' }[outcome] || outcome.toUpperCase();
  return (
    <div className={`inline-flex items-center gap-2 border ${color} px-2 py-1`}>
      <span className="overline">{label}</span>
      <span className="font-mono text-sm">{isPos ? '+' : ''}{pct}%</span>
    </div>
  );
}

export function PillarBar({ label, value, mode = 'neutral' }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const color = mode === 'up' ? 'bg-edgeUp' : mode === 'down' ? 'bg-edgeDown' : 'bg-[#0066FF]';
  return (
    <div>
      <div className="flex justify-between mb-1.5">
        <span className="overline">{label}</span>
        <span className="font-mono text-xs text-white">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1 w-full bg-ink-700">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
