import { useEffect, useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  BarChart, Bar,
} from 'recharts';
import { api } from '@/lib/api';
import { PageHeader, StatTile } from '@/components/ui-extras';
import { STATS } from '@/constants/testIds';

export default function StatsPage() {
  const [data, setData] = useState(null);
  useEffect(() => {
    api.get('/stats').then((r) => setData(r.data));
  }, []);
  if (!data) return <div className="px-8 py-8 overline animate-pulse-dot">Liczenie statystyk…</div>;

  const timeline = data.timeline.map((t, i) => ({
    idx: i + 1,
    cum: t.cum_profit,
  }));
  const byLeague = Object.entries(data.by_league).map(([league, v]) => ({
    league: league.length > 12 ? league.slice(0, 12) + '…' : league,
    roi: Math.round(v.roi),
    profit: Math.round(v.profit),
  }));

  return (
    <div data-testid={STATS.root}>
      <PageHeader subtitle="Analytics" title="Statystyki skuteczności" />

      <div className="px-8 py-6 grid grid-cols-1 md:grid-cols-4 gap-px bg-border">
        <StatTile testid={STATS.roi} label="ROI" value={`${data.roi.toFixed(2)}%`} accent={data.roi >= 0 ? 'up' : 'down'} />
        <StatTile testid={STATS.hitRate} label="Hit rate" value={`${data.hit_rate.toFixed(1)}%`} accent="blue" />
        <StatTile testid={STATS.totalProfit} label="Zysk netto" value={`${data.total_profit >= 0 ? '+' : ''}${data.total_profit.toFixed(2)} PLN`} accent={data.total_profit >= 0 ? 'up' : 'down'} />
        <StatTile testid={STATS.aiAccuracy} label={`Skuteczność AI (${data.ai_total})`} value={`${data.ai_accuracy.toFixed(1)}%`} accent="up" />
      </div>

      <section className="px-8 py-6 grid grid-cols-1 lg:grid-cols-3 gap-px bg-border">
        <div className="lg:col-span-2 bg-ink-800 p-6 min-w-0">
          <div className="overline mb-3">Kumulowany zysk</div>
          <div style={{ width: '100%', height: 288 }}>
            {timeline.length === 0 ? (
              <div className="h-full flex items-center justify-center overline">Brak rozliczonych zakładów</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timeline}>
                  <defs>
                    <linearGradient id="profitG" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#00E676" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#00E676" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="2 4" stroke="#222" />
                  <XAxis dataKey="idx" stroke="#71717a" fontSize={11} />
                  <YAxis stroke="#71717a" fontSize={11} />
                  <Tooltip contentStyle={{ background: '#111', border: '1px solid #222', fontSize: 12 }} />
                  <Area dataKey="cum" type="monotone" stroke="#00E676" fill="url(#profitG)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="bg-ink-800 p-6">
          <div className="overline mb-3">Wolumen</div>
          <div className="grid grid-cols-2 gap-px bg-border">
            <Mini label="Zakłady" value={data.total_bets} />
            <Mini label="Rozliczone" value={data.settled_bets} />
            <Mini label="Wygrane" value={data.wins} />
            <Mini label="Stawka total" value={`${data.total_stake.toFixed(0)} PLN`} />
          </div>
        </div>
      </section>

      <section className="px-8 pb-12 bg-ink-800 mx-8 border border-border p-6">
        <div className="overline mb-3">ROI / Liga</div>
        <div style={{ width: '100%', height: 288 }}>
          {byLeague.length === 0 ? (
            <div className="h-full flex items-center justify-center overline">Brak danych</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byLeague}>
                <CartesianGrid strokeDasharray="2 4" stroke="#222" />
                <XAxis dataKey="league" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} unit="%" />
                <Tooltip contentStyle={{ background: '#111', border: '1px solid #222', fontSize: 12 }} />
                <Bar dataKey="roi" fill="#0066FF" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>
    </div>
  );
}

function Mini({ label, value }) {
  return (
    <div className="bg-ink-800 p-3">
      <div className="overline">{label}</div>
      <div className="font-mono text-lg mt-1">{value}</div>
    </div>
  );
}
