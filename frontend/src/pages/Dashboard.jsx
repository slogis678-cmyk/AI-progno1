import { useEffect, useMemo, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  ArrowsClockwise,
  MagnifyingGlass,
  Lightning,
  CloudArrowDown,
  Bell,
  X as XIcon,
} from '@phosphor-icons/react';
import { api, formatApiError } from '@/lib/api';
import { PageHeader, StatTile, EdgeBadge } from '@/components/ui-extras';
import { DASHBOARD } from '@/constants/testIds';

const ALERT_THRESHOLD = 0.05; // 5%
const SEEN_ALERTS_KEY = 'edge_ai_seen_alerts';

export default function Dashboard() {
  const [matches, setMatches] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');
  const [leagueFilter, setLeagueFilter] = useState('ALL');
  const [minEdge, setMinEdge] = useState(0); // %
  const [importOpen, setImportOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importMsg, setImportMsg] = useState('');
  const [externalLeagues, setExternalLeagues] = useState({ api_football: [], odds_api: [] });
  const [importChoice, setImportChoice] = useState({ source: 'odds-api', value: '' });
  const [dismissed, setDismissed] = useState(() => {
    try {
      return new Set(JSON.parse(localStorage.getItem(SEEN_ALERTS_KEY) || '[]'));
    } catch (err) {
      console.warn('Could not read dismissed alerts from localStorage:', err);
      return new Set();
    }
  });
  const nav = useNavigate();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/matches');
      setMatches(data);
    } catch (err) {
      console.error('Failed to load matches:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const loadLeagues = async () => {
    try {
      const { data } = await api.get('/external/leagues');
      setExternalLeagues(data);
      if (data.odds_api?.length && !importChoice.value) {
        setImportChoice({ source: 'odds-api', value: data.odds_api[0].key });
      }
    } catch (e) {
      setImportMsg(formatApiError(e?.response?.data?.detail) || 'Błąd pobierania lig');
    }
  };

  const openImport = async () => {
    setImportOpen(true);
    setImportMsg('');
    await loadLeagues();
  };

  const runImport = async () => {
    setImporting(true);
    setImportMsg('');
    try {
      if (importChoice.source === 'odds-api') {
        const { data } = await api.post('/external/import/odds-api', { sport_key: importChoice.value });
        setImportMsg(`Pobrano ${data.total_fetched}, zapisano ${data.inserted}, pominięto duplikatów ${data.skipped}.`);
      } else {
        const { data } = await api.post('/external/import/api-football', { league_id: parseInt(importChoice.value, 10), days_ahead: 7 });
        setImportMsg(`Pobrano ${data.total_fetched}, zapisano ${data.inserted}, pominięto duplikatów ${data.skipped}.`);
      }
      await load();
    } catch (e) {
      setImportMsg(formatApiError(e?.response?.data?.detail) || 'Import nie powiódł się');
    } finally {
      setImporting(false);
    }
  };

  const seed = async () => {
    setLoading(true);
    try {
      await api.post('/seed-demo');
      await load();
    } finally {
      setLoading(false);
    }
  };

  const allLeagues = useMemo(() => {
    const s = new Set();
    (matches || []).forEach((m) => s.add(m.league));
    return Array.from(s).sort();
  }, [matches]);

  const filtered = useMemo(() => {
    const arr = matches || [];
    const q = filter.toLowerCase();
    return arr.filter((m) => {
      if (q && !(m.home_team.toLowerCase().includes(q) || m.away_team.toLowerCase().includes(q) || m.league.toLowerCase().includes(q))) {
        return false;
      }
      if (leagueFilter !== 'ALL' && m.league !== leagueFilter) return false;
      const edgePct = (m.edge_summary?.best_edge || 0) * 100;
      if (edgePct < minEdge) return false;
      return true;
    });
  }, [matches, filter, leagueFilter, minEdge]);

  const positiveEdges = (matches || []).filter((m) => (m.edge_summary?.best_edge || 0) > 0.01);
  const avgEdge = positiveEdges.length
    ? positiveEdges.reduce((s, m) => s + m.edge_summary.best_edge, 0) / positiveEdges.length
    : 0;
  const topMatch = (matches || []).reduce(
    (best, m) => (m.edge_summary && m.edge_summary.best_edge > (best?.edge_summary?.best_edge ?? -1) ? m : best),
    null
  );

  const alerts = (matches || []).filter(
    (m) => (m.edge_summary?.best_edge || 0) >= ALERT_THRESHOLD && !dismissed.has(m.id)
  );

  const dismissAlert = (id) => {
    const next = new Set(dismissed); next.add(id);
    setDismissed(next);
    localStorage.setItem(SEEN_ALERTS_KEY, JSON.stringify(Array.from(next)));
  };

  const dismissAll = () => {
    const next = new Set(dismissed);
    alerts.forEach((m) => next.add(m.id));
    setDismissed(next);
    localStorage.setItem(SEEN_ALERTS_KEY, JSON.stringify(Array.from(next)));
  };

  return (
    <div data-testid={DASHBOARD.root}>
      <PageHeader
        subtitle="Live · Edge detector"
        title="Dashboard meczowy"
        actions={
          <>
            <button
              data-testid="dashboard-import-button"
              onClick={openImport}
              className="border border-border px-3 py-2 text-xs uppercase tracking-wider hover:bg-ink-800 hover:border-[#0066FF] hover:text-[#0066FF] flex items-center gap-2"
            >
              <CloudArrowDown size={14} weight="bold" /> Importuj
            </button>
            <button
              onClick={load}
              className="border border-border px-3 py-2 text-xs uppercase tracking-wider hover:bg-ink-800 flex items-center gap-2"
            >
              <ArrowsClockwise size={14} weight="bold" /> Odśwież
            </button>
          </>
        }
      />

      {/* Alerts banner */}
      {alerts.length > 0 && (
        <div data-testid="dashboard-alerts-banner" className="mx-8 mt-6 border border-edgeUp bg-edgeUp/5 px-4 py-3 flex items-start gap-3 animate-fade-in">
          <Bell size={18} weight="fill" className="text-edgeUp mt-0.5 animate-pulse-dot" />
          <div className="flex-1">
            <div className="overline text-edgeUp mb-2">{alerts.length} value-bet alert(s) · edge ≥ 5%</div>
            <div className="flex flex-wrap gap-2">
              {alerts.slice(0, 6).map((m) => (
                <button
                  key={m.id}
                  onClick={() => nav(`/match/${m.id}`)}
                  className="border border-edgeUp/40 hover:border-edgeUp hover:bg-edgeUp/10 px-3 py-1.5 text-xs flex items-center gap-2"
                >
                  <span className="font-medium">{m.home_team} vs {m.away_team}</span>
                  <span className="font-mono text-edgeUp">+{(m.edge_summary.best_edge * 100).toFixed(1)}%</span>
                  <XIcon
                    size={12}
                    weight="bold"
                    className="text-ink-500 hover:text-white"
                    onClick={(e) => { e.stopPropagation(); dismissAlert(m.id); }}
                  />
                </button>
              ))}
            </div>
          </div>
          <button onClick={dismissAll} className="overline hover:text-white">Ukryj wszystkie</button>
        </div>
      )}

      <div className="px-8 py-6 grid grid-cols-1 md:grid-cols-4 gap-px bg-border">
        <StatTile label="Mecze w analizie" value={(matches || []).length} accent="default" />
        <StatTile label="Value bety (edge > 1%)" value={positiveEdges.length} accent="up" />
        <StatTile label="Średnia przewaga" value={`${(avgEdge * 100).toFixed(2)}%`} accent={avgEdge > 0 ? 'up' : 'default'} />
        <StatTile
          label="Top sygnał"
          value={topMatch?.edge_summary ? `${(topMatch.edge_summary.best_edge * 100).toFixed(1)}%` : '—'}
          accent="blue"
        />
      </div>

      {/* Filters */}
      <div className="px-8 pb-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px] max-w-md">
          <MagnifyingGlass size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-500" />
          <input
            data-testid="dashboard-filter-search"
            placeholder="Filtruj drużynę lub ligę…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full bg-ink-800 border border-border pl-9 pr-3 py-2 text-sm focus:outline-none focus:border-[#0066FF]"
          />
        </div>

        <select
          data-testid="dashboard-league-filter"
          value={leagueFilter}
          onChange={(e) => setLeagueFilter(e.target.value)}
          className="bg-ink-800 border border-border px-3 py-2 text-xs uppercase tracking-wider focus:outline-none focus:border-[#0066FF]"
        >
          <option value="ALL">Wszystkie ligi</option>
          {allLeagues.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>

        <div className="flex items-center gap-3 border border-border px-3 py-2 bg-ink-800">
          <span className="overline">Min edge</span>
          <input
            data-testid="dashboard-min-edge-slider"
            type="range"
            min="-5"
            max="15"
            step="0.5"
            value={minEdge}
            onChange={(e) => setMinEdge(parseFloat(e.target.value))}
            className="accent-[#0066FF] w-32"
          />
          <span className={`font-mono text-xs w-12 text-right ${minEdge > 0 ? 'text-edgeUp' : minEdge < 0 ? 'text-edgeDown' : 'text-ink-300'}`}>
            {minEdge > 0 ? '+' : ''}{minEdge}%
          </span>
        </div>

        <div className="overline ml-auto">{filtered.length} / {(matches || []).length} mecz(y)</div>
      </div>

      {matches && matches.length === 0 && (
        <div data-testid={DASHBOARD.emptyState} className="mx-8 my-12 border border-border p-12 text-center">
          <div className="overline mb-3">Brak meczów</div>
          <h3 className="font-display text-2xl font-bold mb-3">Załaduj demo lub importuj na żywo.</h3>
          <p className="text-ink-300 text-sm mb-6">6 meczów demo lub real-time z API.</p>
          <div className="flex gap-2 justify-center">
            <button
              data-testid={DASHBOARD.seedButton}
              onClick={seed}
              className="bg-[#0066FF] hover:bg-[#3b82f6] px-5 py-3 text-sm font-display font-semibold"
            >
              Załaduj 6 demo meczów
            </button>
            <button
              onClick={openImport}
              className="border border-border hover:bg-ink-800 px-5 py-3 text-sm font-display font-semibold flex items-center gap-2"
            >
              <CloudArrowDown size={16} weight="bold" /> Importuj z API
            </button>
          </div>
        </div>
      )}

      {matches && matches.length > 0 && (
        <div className="px-8 pb-12 animate-fade-in">
          <div className="border border-border">
            <div className="grid grid-cols-12 gap-4 px-4 py-3 bg-ink-800 border-b border-border overline">
              <div className="col-span-3">Mecz</div>
              <div className="col-span-2">Liga</div>
              <div className="col-span-1 text-right">1</div>
              <div className="col-span-1 text-right">X</div>
              <div className="col-span-1 text-right">2</div>
              <div className="col-span-2">Edge AI</div>
              <div className="col-span-2 text-right">Pewność</div>
            </div>
            {filtered.length === 0 ? (
              <div className="px-4 py-8 text-center overline">Brak meczów spełniających filtry</div>
            ) : (
              filtered.map((m) => (
                <MatchRow key={m.id} match={m} onClick={() => nav(`/match/${m.id}`)} />
              ))
            )}
          </div>
        </div>
      )}

      {loading && !matches && (
        <div className="px-8 py-8 overline animate-pulse-dot">Pobieranie danych…</div>
      )}

      {/* Import modal */}
      {importOpen && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-ink-800 border border-border w-full max-w-lg p-6 animate-fade-in">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="overline mb-1">Real-time</div>
                <h3 className="font-display text-xl font-bold">Importuj mecze z API</h3>
              </div>
              <button onClick={() => setImportOpen(false)} className="text-ink-300 hover:text-white"><XIcon size={18} /></button>
            </div>

            <div className="space-y-4">
              <div>
                <div className="overline mb-2">Źródło</div>
                <div className="grid grid-cols-2 gap-px bg-border">
                  <SourceTile
                    selected={importChoice.source === 'odds-api'}
                    onClick={() => setImportChoice({ source: 'odds-api', value: externalLeagues.odds_api?.[0]?.key || '' })}
                    title="The Odds API"
                    sub="Kursy 1X2 (multi-bookmaker)"
                  />
                  <SourceTile
                    selected={importChoice.source === 'api-football'}
                    onClick={() => setImportChoice({ source: 'api-football', value: String(externalLeagues.api_football?.[0]?.id || '') })}
                    title="API-Football"
                    sub="Statystyki, forma, H2H"
                  />
                </div>
              </div>

              <div>
                <div className="overline mb-2">Liga</div>
                <select
                  data-testid="dashboard-import-league-select"
                  value={importChoice.value}
                  onChange={(e) => setImportChoice({ ...importChoice, value: e.target.value })}
                  className="w-full bg-ink-900 border border-border px-3 py-2 text-sm focus:outline-none focus:border-[#0066FF]"
                >
                  {(importChoice.source === 'odds-api' ? externalLeagues.odds_api : externalLeagues.api_football).map((l) =>
                    <option key={l.key ?? l.id} value={l.key ?? l.id}>{l.label || `${l.name} (${l.country})`}</option>
                  )}
                </select>
              </div>

              {importMsg && (
                <div className="border border-border bg-ink-900 text-xs font-mono px-3 py-2">{importMsg}</div>
              )}

              <div className="flex justify-end gap-2">
                <button onClick={() => setImportOpen(false)} className="px-4 py-2 text-xs uppercase tracking-wider border border-border hover:bg-ink-700">Zamknij</button>
                <button
                  data-testid="dashboard-import-submit-button"
                  disabled={importing || !importChoice.value}
                  onClick={runImport}
                  className="px-4 py-2 text-xs uppercase tracking-wider bg-[#0066FF] hover:bg-[#3b82f6] disabled:opacity-60 flex items-center gap-2"
                >
                  <Lightning size={14} weight="fill" />
                  {importing ? 'Importuję…' : 'Importuj'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SourceTile({ selected, onClick, title, sub }) {
  return (
    <button
      onClick={onClick}
      className={`text-left p-4 ${selected ? 'bg-ink-700 border-l-2 border-[#0066FF]' : 'bg-ink-800 hover:bg-ink-700'}`}
    >
      <div className="font-display font-semibold text-sm">{title}</div>
      <div className="overline mt-1">{sub}</div>
    </button>
  );
}

function MatchRow({ match, onClick }) {
  const es = match.edge_summary;
  const conf = es ? Math.round(es.confidence * 100) : 0;
  const kickoff = new Date(match.kickoff);
  return (
    <div
      data-testid={DASHBOARD.matchRow}
      onClick={onClick}
      className="grid grid-cols-12 gap-4 px-4 py-3 border-b border-border hover:bg-ink-800 cursor-pointer transition-colors items-center"
    >
      <div className="col-span-3" data-testid={DASHBOARD.matchTeams}>
        <div className="text-sm font-medium truncate">{match.home_team} <span className="text-ink-500">vs</span> {match.away_team}</div>
        <div className="font-mono text-[11px] text-ink-300 mt-0.5">
          {kickoff.toLocaleDateString('pl-PL')} · {kickoff.toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
      <div className="col-span-2 text-sm text-ink-300 truncate">{match.league}</div>
      <Odd val={match.odds.home} highlight={es?.best_outcome === 'home'} />
      <Odd val={match.odds.draw} highlight={es?.best_outcome === 'draw'} />
      <Odd val={match.odds.away} highlight={es?.best_outcome === 'away'} />
      <div className="col-span-2" data-testid={DASHBOARD.matchEdge}>
        {es ? <EdgeBadge edge={es.best_edge} outcome={es.best_outcome} /> : <span className="overline">—</span>}
      </div>
      <div className="col-span-2 flex items-center justify-end gap-2">
        <div className="w-20 h-1 bg-ink-700">
          <div className="h-full bg-[#0066FF]" style={{ width: `${conf}%` }} />
        </div>
        <span className="font-mono text-xs w-9 text-right">{conf}%</span>
        <ArrowRight size={14} className="text-ink-500" />
      </div>
    </div>
  );
}

function Odd({ val, highlight }) {
  return (
    <div className="col-span-1 text-right" data-testid={DASHBOARD.matchOdds}>
      <span className={`font-mono text-sm ${highlight ? 'text-edgeUp' : 'text-white'}`}>{val.toFixed(2)}</span>
    </div>
  );
}
