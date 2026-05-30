import { useEffect, useState, useCallback } from 'react';
import { Check, X, Trash } from '@phosphor-icons/react';
import { api, formatApiError } from '@/lib/api';
import { PageHeader, StatTile } from '@/components/ui-extras';
import { BETS } from '@/constants/testIds';

const OUTCOME_LABEL = { home: 'GOSP', draw: 'REMIS', away: 'GOŚĆ' };
const STATUS_LABEL = { pending: 'OCZEKUJE', won: 'WYGRANY', lost: 'PRZEGRANY', void: 'ZWROT' };
const STATUS_COLOR = { pending: 'text-edgeWarn', won: 'text-edgeUp', lost: 'text-edgeDown', void: 'text-ink-300' };

export default function BetTracker() {
  const [bets, setBets] = useState([]);
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/bets');
      setBets(data);
    } catch (error) {
      console.error('Failed to load bets:', error);
      setErr('Błąd ładowania zakładów');
    }
  }, []);
  
  useEffect(() => {
    load();
  }, [load]);

  const settle = async (id, result) => {
    try {
      await api.patch(`/bets/${id}`, { result });
      await load();
    } catch (e) {
      setErr(formatApiError(e?.response?.data?.detail));
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Usunąć zakład?')) return;
    await api.delete(`/bets/${id}`);
    await load();
  };

  const settled = bets.filter((b) => b.status !== 'pending');
  const stake = settled.reduce((s, b) => s + b.stake, 0);
  const profit = settled.reduce((s, b) => s + b.profit, 0);
  const wins = settled.filter((b) => b.status === 'won').length;
  const roi = stake > 0 ? (profit / stake) * 100 : 0;

  return (
    <div data-testid={BETS.root}>
      <PageHeader subtitle="Tracker" title="Twoje zakłady" />

      <div className="px-8 py-6 grid grid-cols-1 md:grid-cols-4 gap-px bg-border">
        <StatTile label="Wszystkie zakłady" value={bets.length} />
        <StatTile label="Rozliczone" value={settled.length} />
        <StatTile label="Zysk netto" value={`${profit >= 0 ? '+' : ''}${profit.toFixed(2)} PLN`} accent={profit >= 0 ? 'up' : 'down'} />
        <StatTile label="ROI" value={`${roi.toFixed(2)}%`} accent={roi >= 0 ? 'up' : 'down'} />
      </div>

      {err && <div className="mx-8 mb-4 border border-edgeDown text-edgeDown text-xs px-3 py-2 font-mono">{err}</div>}

      <div className="px-8 pb-12">
        {bets.length === 0 ? (
          <div className="border border-border p-12 text-center">
            <div className="overline mb-3">Brak zakładów</div>
            <p className="text-sm text-ink-300">Otwórz analizę meczu i kliknij „Zaloguj zakład", aby śledzić swoje typy tu.</p>
          </div>
        ) : (
          <div className="border border-border">
            <div className="grid grid-cols-12 gap-3 px-4 py-3 bg-ink-800 overline border-b border-border">
              <div className="col-span-3">Mecz</div>
              <div className="col-span-2">Liga</div>
              <div className="col-span-1">Typ</div>
              <div className="col-span-1 text-right">Kurs</div>
              <div className="col-span-1 text-right">Stawka</div>
              <div className="col-span-1 text-right">Zysk</div>
              <div className="col-span-1">Status</div>
              <div className="col-span-2 text-right">Akcje</div>
            </div>
            {bets.map((b) => (
              <div data-testid={BETS.betRow} key={b.id} className="grid grid-cols-12 gap-3 px-4 py-3 border-b border-border items-center hover:bg-ink-800">
                <div className="col-span-3 text-sm truncate">{b.match_label}</div>
                <div className="col-span-2 text-sm text-ink-300 truncate">{b.league}</div>
                <div className="col-span-1 overline">{OUTCOME_LABEL[b.outcome]}</div>
                <div className="col-span-1 text-right font-mono text-sm">{b.odds.toFixed(2)}</div>
                <div className="col-span-1 text-right font-mono text-sm">{b.stake.toFixed(2)}</div>
                <div className={`col-span-1 text-right font-mono text-sm ${b.profit > 0 ? 'text-edgeUp' : b.profit < 0 ? 'text-edgeDown' : ''}`}>
                  {b.status === 'pending' ? '—' : `${b.profit >= 0 ? '+' : ''}${b.profit.toFixed(2)}`}
                </div>
                <div className={`col-span-1 overline ${STATUS_COLOR[b.status]}`}>{STATUS_LABEL[b.status]}</div>
                <div className="col-span-2 flex items-center justify-end gap-1">
                  {b.status === 'pending' && (
                    <>
                      <button data-testid={BETS.settleWonButton} onClick={() => settle(b.id, 'won')} className="border border-border p-1.5 hover:bg-edgeUp/20 hover:border-edgeUp hover:text-edgeUp"><Check size={14} weight="bold" /></button>
                      <button data-testid={BETS.settleLostButton} onClick={() => settle(b.id, 'lost')} className="border border-border p-1.5 hover:bg-edgeDown/20 hover:border-edgeDown hover:text-edgeDown"><X size={14} weight="bold" /></button>
                    </>
                  )}
                  <button data-testid={BETS.deleteButton} onClick={() => remove(b.id)} className="border border-border p-1.5 hover:bg-ink-700 text-ink-300"><Trash size={14} weight="bold" /></button>
                </div>
              </div>
            ))}
            <div className="px-4 py-3 bg-ink-800 grid grid-cols-12 gap-3 items-center overline">
              <div className="col-span-7">Razem (rozliczone)</div>
              <div className="col-span-1 text-right font-mono text-white">{stake.toFixed(2)}</div>
              <div className={`col-span-1 text-right font-mono ${profit >= 0 ? 'text-edgeUp' : 'text-edgeDown'}`}>{profit.toFixed(2)}</div>
              <div className="col-span-3 text-right">Hit rate · {settled.length ? ((wins / settled.length) * 100).toFixed(1) : 0}%</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
