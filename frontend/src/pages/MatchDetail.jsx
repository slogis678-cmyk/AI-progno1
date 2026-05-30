import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, CartesianGrid,
} from 'recharts';
import { ArrowLeft, Sparkle, Trash, ReceiptX, Clock } from '@phosphor-icons/react';
import { api, formatApiError } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { PageHeader, EdgeBadge, PillarBar, StatTile } from '@/components/ui-extras';
import { MATCH } from '@/constants/testIds';

const MODELS = [
  { key: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet 4.5' },
  { key: 'gpt-5.2', label: 'GPT-5.2' },
  { key: 'gemini-3.1-pro-preview', label: 'Gemini 3 Pro' },
];

export default function MatchDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const [match, setMatch] = useState(null);
  const [model, setModel] = useState(user?.preferred_model || MODELS[0].key);
  const [analysis, setAnalysis] = useState(null);
  const [history, setHistory] = useState([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [err, setErr] = useState('');
  const [bet, setBet] = useState({ stake: 100, outcome: 'home', open: false });

  const loadHistory = useCallback(async () => {
    try {
      const { data } = await api.get(`/matches/${id}/analyses`);
      setHistory(data);
    } catch (error) {
      console.error('Failed to load analysis history:', error);
      // History is optional, don't block main content
    }
  }, [id]);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/matches/${id}`);
      setMatch(data);
      if (data.latest_analysis) setAnalysis(data.latest_analysis);
      await loadHistory();
    } catch (error) {
      console.error('Failed to load match:', error);
      setErr(formatApiError(error?.response?.data?.detail) || 'Błąd ładowania meczu');
    }
  }, [id, loadHistory]);

  useEffect(() => { load(); }, [load]);

  const runAnalysis = async () => {
    setErr('');
    setAnalyzing(true);
    try {
      const { data } = await api.post(`/matches/${id}/analyze`, { model });
      setAnalysis(data);
      await loadHistory();
    } catch (e) {
      setErr(formatApiError(e?.response?.data?.detail) || 'Analiza nie powiodła się');
    } finally {
      setAnalyzing(false);
    }
  };

  const placeBet = async () => {
    try {
      await api.post('/bets', {
        match_id: id,
        outcome: bet.outcome,
        stake: parseFloat(bet.stake),
        odds: match.odds[bet.outcome],
        note: `Edge ${(match.edge_summary?.edges?.[bet.outcome] * 100).toFixed(1)}%`,
      });
      setBet({ ...bet, open: false });
      nav('/bets');
    } catch (e) {
      setErr(formatApiError(e?.response?.data?.detail));
    }
  };

  const removeMatch = async () => {
    if (!window.confirm('Usunąć mecz?')) return;
    await api.delete(`/matches/${id}`);
    nav('/');
  };

  if (!match) {
    return <div className="px-8 py-8 overline animate-pulse-dot">Wczytywanie meczu…</div>;
  }

  const es = match.edge_summary || {};
  const pillars = es.pillars || {};
  const oddsHist = (match.odds_history || []).map((p, i) => ({ idx: i, ...p }));
  const probData = es.model_prob
    ? [
        { name: '1', model: es.model_prob.home * 100, market: es.implied.home * 100 },
        { name: 'X', model: es.model_prob.draw * 100, market: es.implied.draw * 100 },
        { name: '2', model: es.model_prob.away * 100, market: es.implied.away * 100 },
      ]
    : [];

  const kickoff = new Date(match.kickoff);

  return (
    <div data-testid={MATCH.root}>
      <PageHeader
        subtitle={match.league}
        title={`${match.home_team} vs ${match.away_team}`}
        actions={
          <>
            <button
              onClick={() => nav(-1)}
              className="border border-border px-3 py-2 text-xs uppercase tracking-wider hover:bg-ink-800 flex items-center gap-2"
            >
              <ArrowLeft size={14} weight="bold" /> Wstecz
            </button>
            <button
              data-testid={MATCH.deleteButton}
              onClick={removeMatch}
              className="border border-border px-3 py-2 text-xs uppercase tracking-wider hover:bg-ink-800 hover:border-edgeDown hover:text-edgeDown flex items-center gap-2"
            >
              <Trash size={14} weight="bold" /> Usuń
            </button>
          </>
        }
      />

      <div className="px-8 py-6 grid grid-cols-1 lg:grid-cols-3 gap-px bg-border">
        <StatTile label="Edge (najlepsze)" value={es.best_edge != null ? `${(es.best_edge * 100).toFixed(2)}%` : '—'} accent={es.best_edge > 0 ? 'up' : 'down'} />
        <StatTile label="Pewność modelu" value={`${Math.round((es.confidence || 0) * 100)}%`} accent="blue" />
        <StatTile label="Kick-off" value={kickoff.toLocaleString('pl-PL')} mono={false} />
      </div>

      {/* AI panel */}
      <section className="px-8 py-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="overline mb-1">AI Analiza</div>
            <h2 className="font-display text-2xl font-bold">Werdykt modelu</h2>
          </div>
          <div className="flex items-center gap-2">
            <select
              data-testid={MATCH.modelSelect}
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="bg-ink-800 border border-border px-3 py-2 text-xs uppercase tracking-wider focus:outline-none focus:border-[#0066FF]"
            >
              {MODELS.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
            </select>
            <button
              data-testid={MATCH.analyzeButton}
              onClick={runAnalysis}
              disabled={analyzing}
              className="bg-[#0066FF] hover:bg-[#3b82f6] disabled:opacity-60 px-4 py-2 text-xs uppercase tracking-wider flex items-center gap-2 font-display"
            >
              <Sparkle size={14} weight="fill" />
              {analyzing ? 'Analiza…' : 'Uruchom analizę'}
            </button>
          </div>
        </div>

        {err && <div className="border border-edgeDown text-edgeDown text-xs px-3 py-2 mb-4 font-mono">{err}</div>}

        {analysis ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-px bg-border">
            <div className="lg:col-span-2 bg-ink-800 p-6">
              <div className="flex items-center gap-3 mb-4">
                <EdgeBadge edge={es.edges?.[analysis.ai.verdict] || 0} outcome={analysis.ai.verdict} />
                <span className="overline">Pewność AI · {analysis.ai.confidence_pct}%</span>
                <span className="overline ml-auto">{MODELS.find((m) => m.key === analysis.model)?.label || analysis.model}</span>
              </div>
              <p data-testid={MATCH.thesis} className="text-lg leading-relaxed font-display font-medium mb-6">
                {analysis.ai.thesis}
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <Insight title="Tempo gry" text={analysis.ai.tempo_insight} />
                <Insight title="Mikrotrendy kursów" text={analysis.ai.odds_trend_insight} />
                <Insight title="Reakcja zespołów" text={analysis.ai.reaction_insight} />
                <Insight title="Dane historyczne" text={analysis.ai.historical_insight} />
              </div>
              {analysis.ai.risk && (
                <div className="mt-6 border-l-2 border-edgeWarn pl-4">
                  <div className="overline mb-1 text-edgeWarn">Ryzyko</div>
                  <div className="text-sm text-ink-300">{analysis.ai.risk}</div>
                </div>
              )}
            </div>
            <div className="bg-ink-800 p-6 min-w-0">
              <div className="overline mb-3">Prawdopodobieństwa</div>
              <div style={{ width: '100%', height: 192 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={probData}>
                    <CartesianGrid strokeDasharray="2 4" stroke="#222" />
                    <XAxis dataKey="name" stroke="#71717a" fontSize={11} />
                    <YAxis stroke="#71717a" fontSize={11} unit="%" />
                    <Tooltip contentStyle={{ background: '#111', border: '1px solid #222', fontSize: 12 }} />
                    <Area type="monotone" dataKey="market" stroke="#71717a" fill="#71717a22" name="Rynek" />
                    <Area type="monotone" dataKey="model" stroke="#00E676" fill="#00E67622" name="Model" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <button
                data-testid={MATCH.placeBetButton}
                onClick={() => setBet({ ...bet, open: true, outcome: analysis.ai.verdict })}
                className="mt-4 w-full border border-[#0066FF] text-[#0066FF] hover:bg-[#0066FF] hover:text-white py-2.5 text-xs uppercase tracking-wider transition-colors flex items-center justify-center gap-2"
              >
                <ReceiptX size={14} weight="bold" />
                Zaloguj zakład
              </button>
            </div>
          </div>
        ) : (
          <div className="border border-border bg-ink-800 p-8 text-center">
            <div className="overline mb-2">Brak analizy</div>
            <p className="text-sm text-ink-300">Uruchom analizę AI, aby uzyskać werdykt i interpretację 4 filarów.</p>
          </div>
        )}
      </section>

      {/* Pillars */}
      <section className="px-8 pb-6 grid grid-cols-1 lg:grid-cols-2 gap-px bg-border">
        <div className="bg-ink-800 p-6">
          <div className="overline mb-4">Cztery filary edge</div>
          <div className="space-y-4">
            <PillarBar label="Tempo gry · gospodarz" value={pillars.tempo ?? 0.5} mode="up" />
            <PillarBar label="Reakcja gospodarza (last 5)" value={pillars.reaction_home ?? 0.5} />
            <PillarBar label="Reakcja gościa (last 5)" value={pillars.reaction_away ?? 0.5} />
            <PillarBar label="H2H — przewaga gospodarza" value={pillars.h2h ?? 0.5} />
            <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-border">
              <DriftCell label="Drift 1" value={pillars.odds_micro?.home_drift} />
              <DriftCell label="Drift X" value={pillars.odds_micro?.draw_drift} />
              <DriftCell label="Drift 2" value={pillars.odds_micro?.away_drift} />
            </div>
          </div>
        </div>

        <div className="bg-ink-800 p-6 min-w-0">
          <div className="overline mb-4">Mikrotrendy kursów (48h)</div>
          <div style={{ width: '100%', height: 256 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={oddsHist}>
                <CartesianGrid strokeDasharray="2 4" stroke="#222" />
                <XAxis dataKey="idx" stroke="#71717a" fontSize={11} hide />
                <YAxis stroke="#71717a" fontSize={11} domain={['auto', 'auto']} />
                <Tooltip contentStyle={{ background: '#111', border: '1px solid #222', fontSize: 12 }} />
                <Line type="monotone" dataKey="home" stroke="#00E676" strokeWidth={2} dot={false} name="1" />
                <Line type="monotone" dataKey="draw" stroke="#FFEA00" strokeWidth={2} dot={false} name="X" />
                <Line type="monotone" dataKey="away" stroke="#0066FF" strokeWidth={2} dot={false} name="2" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      {/* Form & H2H */}
      <section className="px-8 pb-6 grid grid-cols-1 md:grid-cols-3 gap-px bg-border">
        <FormCard title={`Forma · ${match.home_team}`} form={match.form_home || []} />
        <FormCard title={`Forma · ${match.away_team}`} form={match.form_away || []} />
        <H2HCard h2h={match.h2h || []} />
      </section>

      {/* Analyses history */}
      <section className="px-8 pb-12">
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="overline mb-1">Historia analiz</div>
            <h3 className="font-display text-xl font-bold">Wcześniejsze przebiegi AI</h3>
          </div>
          <div className="overline">{history.length} {history.length === 1 ? 'zapis' : 'zapisów'}</div>
        </div>
        {history.length === 0 ? (
          <div className="border border-border bg-ink-800 p-8 text-center text-sm text-ink-300">
            Brak wcześniejszych analiz. Uruchom analizę powyżej, aby zacząć budować historię.
          </div>
        ) : (
          <div className="border border-border" data-testid="match-history-list">
            <div className="grid grid-cols-12 gap-3 px-4 py-3 bg-ink-800 overline border-b border-border">
              <div className="col-span-3">Czas</div>
              <div className="col-span-3">Model</div>
              <div className="col-span-2">Werdykt</div>
              <div className="col-span-1 text-right">Pewność</div>
              <div className="col-span-3">Teza</div>
            </div>
            {history.map((h) => {
              const created = new Date(h.created_at);
              const verdict = h.ai?.verdict;
              const modelLabel = MODELS.find((m) => m.key === h.model)?.label || h.model;
              const edges = h.stats?.edges || {};
              return (
                <div key={h.id} className="grid grid-cols-12 gap-3 px-4 py-3 border-b border-border items-center hover:bg-ink-800">
                  <div className="col-span-3 font-mono text-xs flex items-center gap-2">
                    <Clock size={12} className="text-ink-500" />
                    {created.toLocaleString('pl-PL')}
                  </div>
                  <div className="col-span-3 text-sm">{modelLabel}</div>
                  <div className="col-span-2">
                    {verdict && <EdgeBadge edge={edges[verdict] || 0} outcome={verdict} />}
                  </div>
                  <div className="col-span-1 text-right font-mono text-sm">{h.ai?.confidence_pct ?? '—'}%</div>
                  <div className="col-span-3 text-xs text-ink-300 truncate" title={h.ai?.thesis}>{h.ai?.thesis}</div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Bet modal */}
      {bet.open && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-ink-800 border border-border w-full max-w-md p-6">
            <div className="overline mb-2">Nowy zakład</div>
            <h3 className="font-display text-xl font-bold mb-6">{match.home_team} vs {match.away_team}</h3>
            <label className="block mb-4">
              <div className="overline mb-2">Wynik</div>
              <select
                value={bet.outcome}
                onChange={(e) => setBet({ ...bet, outcome: e.target.value })}
                className="w-full bg-ink-900 border border-border px-3 py-2 text-sm focus:outline-none focus:border-[#0066FF]"
              >
                <option value="home">1 — {match.home_team} ({match.odds.home})</option>
                <option value="draw">X — Remis ({match.odds.draw})</option>
                <option value="away">2 — {match.away_team} ({match.odds.away})</option>
              </select>
            </label>
            <label className="block mb-6">
              <div className="overline mb-2">Stawka (PLN)</div>
              <input
                type="number"
                step="1"
                value={bet.stake}
                onChange={(e) => setBet({ ...bet, stake: e.target.value })}
                className="w-full bg-ink-900 border border-border px-3 py-2 text-sm font-mono focus:outline-none focus:border-[#0066FF]"
              />
            </label>
            <div className="flex justify-end gap-2">
              <button onClick={() => setBet({ ...bet, open: false })} className="px-4 py-2 text-xs uppercase tracking-wider border border-border hover:bg-ink-700">Anuluj</button>
              <button onClick={placeBet} className="px-4 py-2 text-xs uppercase tracking-wider bg-[#0066FF] hover:bg-[#3b82f6]">Zapisz</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Insight({ title, text }) {
  if (!text) return null;
  return (
    <div>
      <div className="overline mb-2">{title}</div>
      <p className="text-sm text-ink-300 leading-relaxed">{text}</p>
    </div>
  );
}

function DriftCell({ label, value }) {
  const v = value ?? 0;
  const pct = (v * 100).toFixed(0);
  const color = v > 0.05 ? 'text-edgeUp' : v < -0.05 ? 'text-edgeDown' : 'text-ink-300';
  return (
    <div className="text-center border border-border p-2">
      <div className="overline">{label}</div>
      <div className={`font-mono text-sm ${color}`}>{v > 0 ? '+' : ''}{pct}</div>
    </div>
  );
}

function FormCard({ title, form }) {
  return (
    <div className="bg-ink-800 p-6">
      <div className="overline mb-3">{title}</div>
      <div className="flex gap-1">
        {form.length === 0 && <span className="text-ink-500 font-mono text-xs">brak danych</span>}
        {form.map((r, i) => {
          const c = r === 'W' ? 'bg-edgeUp text-black' : r === 'L' ? 'bg-edgeDown text-white' : 'bg-edgeWarn text-black';
          return <span key={i} className={`w-7 h-7 flex items-center justify-center font-mono text-xs ${c}`}>{r}</span>;
        })}
      </div>
    </div>
  );
}

function H2HCard({ h2h }) {
  return (
    <div className="bg-ink-800 p-6">
      <div className="overline mb-3">H2H · ostatnie {h2h.length}</div>
      <div className="flex gap-1">
        {h2h.length === 0 && <span className="text-ink-500 font-mono text-xs">brak danych</span>}
        {h2h.map((r, i) => {
          const v = r.result;
          const c = v === 'H' ? 'bg-edgeUp text-black' : v === 'A' ? 'bg-edgeDown text-white' : 'bg-edgeWarn text-black';
          return <span key={i} className={`w-7 h-7 flex items-center justify-center font-mono text-xs ${c}`}>{v}</span>;
        })}
      </div>
    </div>
  );
}
