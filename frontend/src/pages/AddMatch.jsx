import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, ArrowLeft } from '@phosphor-icons/react';
import { api, formatApiError } from '@/lib/api';
import { PageHeader } from '@/components/ui-extras';
import { ADD_MATCH } from '@/constants/testIds';

const FORM_OPTIONS = ['W', 'D', 'L'];
const H2H_OPTIONS = ['H', 'D', 'A'];

export default function AddMatch() {
  const nav = useNavigate();
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    home_team: '',
    away_team: '',
    league: '',
    kickoff: new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 16),
    odds: { home: 2.0, draw: 3.3, away: 3.5 },
    tempo: { possession_home: 50, shots_home: 12, shots_away: 12, ppda_home: 10, ppda_away: 10 },
    form_home: ['W', 'D', 'W', 'L', 'W'],
    form_away: ['D', 'W', 'D', 'W', 'L'],
    h2h: ['H', 'D', 'A', 'H', 'D'],
  });

  const set = (path, val) => {
    setForm((prev) => {
      const next = { ...prev };
      const keys = path.split('.');
      let ref = next;
      for (let i = 0; i < keys.length - 1; i++) {
        ref[keys[i]] = { ...ref[keys[i]] };
        ref = ref[keys[i]];
      }
      ref[keys[keys.length - 1]] = val;
      return next;
    });
  };

  const submit = async (e) => {
    e.preventDefault();
    setErr('');
    setBusy(true);
    try {
      const payload = {
        ...form,
        kickoff: new Date(form.kickoff).toISOString(),
        odds: {
          home: parseFloat(form.odds.home),
          draw: parseFloat(form.odds.draw),
          away: parseFloat(form.odds.away),
        },
        tempo: {
          possession_home: parseFloat(form.tempo.possession_home),
          shots_home: parseFloat(form.tempo.shots_home),
          shots_away: parseFloat(form.tempo.shots_away),
          ppda_home: parseFloat(form.tempo.ppda_home),
          ppda_away: parseFloat(form.tempo.ppda_away),
        },
        h2h: form.h2h.map((r) => ({ result: r })),
      };
      const { data } = await api.post('/matches', payload);
      nav(`/match/${data.id}`);
    } catch (e2) {
      setErr(formatApiError(e2?.response?.data?.detail) || 'Nie udało się zapisać meczu');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid={ADD_MATCH.root}>
      <PageHeader
        subtitle="Manual entry"
        title="Dodaj nowy mecz"
        actions={
          <button onClick={() => nav(-1)} className="border border-border px-3 py-2 text-xs uppercase tracking-wider hover:bg-ink-800 flex items-center gap-2">
            <ArrowLeft size={14} weight="bold" /> Wstecz
          </button>
        }
      />
      <form onSubmit={submit} className="px-8 py-6 max-w-4xl">
        {err && <div className="border border-edgeDown text-edgeDown text-xs px-3 py-2 mb-4 font-mono">{err}</div>}

        <Section title="Drużyny i liga">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label="Gospodarz" testid={ADD_MATCH.homeInput}>
              <input data-testid={ADD_MATCH.homeInput} required value={form.home_team} onChange={(e) => set('home_team', e.target.value)} className={inputCls} />
            </Field>
            <Field label="Gość" testid={ADD_MATCH.awayInput}>
              <input data-testid={ADD_MATCH.awayInput} required value={form.away_team} onChange={(e) => set('away_team', e.target.value)} className={inputCls} />
            </Field>
            <Field label="Liga" testid={ADD_MATCH.leagueInput}>
              <input data-testid={ADD_MATCH.leagueInput} required value={form.league} onChange={(e) => set('league', e.target.value)} className={inputCls} />
            </Field>
          </div>
          <div className="mt-4 max-w-xs">
            <Field label="Kick-off">
              <input data-testid={ADD_MATCH.kickoffInput} type="datetime-local" value={form.kickoff} onChange={(e) => set('kickoff', e.target.value)} className={inputCls} />
            </Field>
          </div>
        </Section>

        <Section title="Kursy bukmacherskie 1X2">
          <div className="grid grid-cols-3 gap-4">
            <Field label="Kurs 1"><input data-testid={ADD_MATCH.oddsHomeInput} type="number" step="0.01" min="1.01" value={form.odds.home} onChange={(e) => set('odds.home', e.target.value)} className={`${inputCls} font-mono`} /></Field>
            <Field label="Kurs X"><input data-testid={ADD_MATCH.oddsDrawInput} type="number" step="0.01" min="1.01" value={form.odds.draw} onChange={(e) => set('odds.draw', e.target.value)} className={`${inputCls} font-mono`} /></Field>
            <Field label="Kurs 2"><input data-testid={ADD_MATCH.oddsAwayInput} type="number" step="0.01" min="1.01" value={form.odds.away} onChange={(e) => set('odds.away', e.target.value)} className={`${inputCls} font-mono`} /></Field>
          </div>
        </Section>

        <Section title="Tempo gry">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Field label="Posiadanie % (gosp)"><input type="number" min="0" max="100" value={form.tempo.possession_home} onChange={(e) => set('tempo.possession_home', e.target.value)} className={`${inputCls} font-mono`} /></Field>
            <Field label="Strzały (gosp)"><input type="number" min="0" value={form.tempo.shots_home} onChange={(e) => set('tempo.shots_home', e.target.value)} className={`${inputCls} font-mono`} /></Field>
            <Field label="Strzały (gość)"><input type="number" min="0" value={form.tempo.shots_away} onChange={(e) => set('tempo.shots_away', e.target.value)} className={`${inputCls} font-mono`} /></Field>
            <Field label="PPDA gosp"><input type="number" step="0.1" min="0" value={form.tempo.ppda_home} onChange={(e) => set('tempo.ppda_home', e.target.value)} className={`${inputCls} font-mono`} /></Field>
            <Field label="PPDA gość"><input type="number" step="0.1" min="0" value={form.tempo.ppda_away} onChange={(e) => set('tempo.ppda_away', e.target.value)} className={`${inputCls} font-mono`} /></Field>
          </div>
        </Section>

        <Section title="Forma ostatnich 5 meczów">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <PickRow label="Gospodarz" values={form.form_home} options={FORM_OPTIONS} onChange={(v) => set('form_home', v)} />
            <PickRow label="Gość" values={form.form_away} options={FORM_OPTIONS} onChange={(v) => set('form_away', v)} />
          </div>
        </Section>

        <Section title="Head-to-head (ostatnie 5)">
          <PickRow label="Wyniki" values={form.h2h} options={H2H_OPTIONS} onChange={(v) => set('h2h', v)} hint="H = wygrana gospodarza · D = remis · A = wygrana gościa" />
        </Section>

        <button
          data-testid={ADD_MATCH.submitButton}
          disabled={busy}
          className="bg-[#0066FF] hover:bg-[#3b82f6] disabled:opacity-60 px-6 py-3 text-sm font-display font-semibold tracking-wide flex items-center gap-2"
        >
          <Plus size={16} weight="bold" />
          {busy ? 'Zapisywanie…' : 'Zapisz i analizuj'}
        </button>
      </form>
    </div>
  );
}

const inputCls = 'w-full bg-ink-800 border border-border px-3 py-2 text-sm focus:outline-none focus:border-[#0066FF]';

function Section({ title, children }) {
  return (
    <div className="mb-8 border border-border bg-ink-800 p-6">
      <div className="overline mb-4">{title}</div>
      {children}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <div className="overline mb-2">{label}</div>
      {children}
    </label>
  );
}

function PickRow({ label, values, options, onChange, hint }) {
  return (
    <div>
      <div className="overline mb-2">{label}</div>
      <div className="flex gap-2">
        {values.map((v, i) => (
          <select
            key={i}
            value={v}
            onChange={(e) => {
              const copy = [...values];
              copy[i] = e.target.value;
              onChange(copy);
            }}
            className="bg-ink-900 border border-border px-2 py-2 text-sm font-mono focus:outline-none focus:border-[#0066FF]"
          >
            {options.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        ))}
      </div>
      {hint && <div className="overline mt-2">{hint}</div>}
    </div>
  );
}
