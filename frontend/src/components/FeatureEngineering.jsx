/**
 * Feature engineering panel - displays computed match features.
 * H2H stats, odds movement, form trends.
 */

function FeatureTile({ label, value, sub, accent = 'white' }) {
  const accentClass = {
    green: 'text-edgeUp',
    red: 'text-edgeDown',
    yellow: 'text-edgeWarn',
    blue: 'text-[#0066FF]',
    white: 'text-ink-100',
    gray: 'text-ink-400',
  }[accent];

  return (
    <div className="bg-ink-900 border border-border p-3">
      <div className="overline text-[10px] mb-1">{label}</div>
      <div className={`font-mono text-lg font-bold ${accentClass}`}>{value}</div>
      {sub && <div className="text-[10px] text-ink-400 mt-0.5 font-mono">{sub}</div>}
    </div>
  );
}

function TrendBadge({ trend }) {
  const config = {
    improving: { label: 'ROSNĄCY', color: 'text-edgeUp', icon: '↗' },
    declining: { label: 'MALEJĄCY', color: 'text-edgeDown', icon: '↘' },
    stable: { label: 'STABILNY', color: 'text-edgeWarn', icon: '→' },
    no_data: { label: 'BRAK DANYCH', color: 'text-ink-500', icon: '·' },
    insufficient_data: { label: 'MAŁO DANYCH', color: 'text-ink-500', icon: '·' },
  };
  const c = config[trend] || config.no_data;
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold ${c.color}`}>
      {c.icon} {c.label}
    </span>
  );
}

function FormString({ form }) {
  if (!form) return <span className="text-ink-500 text-xs">brak</span>;
  return (
    <span className="font-mono font-bold tracking-wider">
      {form.split('').map((r, i) => {
        const color = r === 'W' ? 'text-edgeUp' : r === 'L' ? 'text-edgeDown' : 'text-edgeWarn';
        return <span key={i} className={color}>{r}</span>;
      })}
    </span>
  );
}

function MarketSignalBadge({ signal }) {
  const config = {
    money_to_home: { label: 'KAPITAŁ NA GOSP.', color: 'bg-edgeUp text-black' },
    money_to_away: { label: 'KAPITAŁ NA GOŚCIA', color: 'bg-[#0066FF] text-white' },
    money_to_draw: { label: 'KAPITAŁ NA REMIS', color: 'bg-edgeWarn text-black' },
    stable: { label: 'STABILNY RYNEK', color: 'bg-ink-700 text-ink-200' },
    no_data: { label: 'BRAK DANYCH', color: 'bg-ink-800 text-ink-500' },
  };
  const c = config[signal] || config.no_data;
  return (
    <span className={`inline-block px-2.5 py-1 text-[10px] font-mono font-bold tracking-wider ${c.color}`}>
      {c.label}
    </span>
  );
}

export default function FeatureEngineering({ features, homeTeam, awayTeam }) {
  if (!features) return null;

  const { h2h, odds_movement: om, home_form: hf, away_form: af } = features;

  return (
    <section className="px-8 pb-6" data-testid="feature-engineering-section">
      <div className="overline mb-1">Feature Engineering</div>
      <h3 className="font-display text-xl font-bold mb-5">Zaawansowane metryki · cechy modelowe</h3>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-px bg-border">
        {/* H2H Stats */}
        <div className="bg-ink-800 p-5" data-testid="features-h2h">
          <div className="flex items-center justify-between mb-4">
            <div className="overline">H2H — Statystyki</div>
            <div className="text-[10px] font-mono text-ink-400">{h2h.h2h_matches} meczów</div>
          </div>
          <div className="grid grid-cols-3 gap-2 mb-3">
            <FeatureTile
              label="Wygrane gosp."
              value={h2h.h2h_home_wins}
              sub={`${Math.round((h2h.h2h_home_win_rate || 0) * 100)}%`}
              accent="green"
            />
            <FeatureTile
              label="Remisy"
              value={h2h.h2h_draws}
              sub={`${Math.round((h2h.h2h_draw_rate || 0) * 100)}%`}
              accent="yellow"
            />
            <FeatureTile
              label="Wygrane gości"
              value={h2h.h2h_away_wins}
              sub={`${Math.round((h2h.h2h_away_win_rate || 0) * 100)}%`}
              accent="red"
            />
          </div>
          {h2h.h2h_scored_samples > 0 ? (
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-ink-400">Średnia goli</span>
                <span className="font-mono font-bold text-ink-200">{h2h.h2h_avg_goals?.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-400">BTTS rate</span>
                <span className="font-mono font-bold text-ink-200">
                  {h2h.h2h_btts_rate !== null ? `${Math.round(h2h.h2h_btts_rate * 100)}%` : 'b/d'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-400">Over 2.5 rate</span>
                <span className="font-mono font-bold text-ink-200">
                  {h2h.h2h_over_2_5_rate !== null ? `${Math.round(h2h.h2h_over_2_5_rate * 100)}%` : 'b/d'}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-xs text-ink-500 italic mt-2">
              Brak danych wynikowych — H2H w demo zawiera tylko rezultaty (H/D/A).
            </div>
          )}
        </div>

        {/* Odds Movement */}
        <div className="bg-ink-800 p-5" data-testid="features-odds-movement">
          <div className="flex items-center justify-between mb-4">
            <div className="overline">Ruch kursów</div>
            <MarketSignalBadge signal={om.market_signal} />
          </div>
          {om.odds_open ? (
            <>
              <div className="grid grid-cols-3 gap-2 mb-3">
                <FeatureTile
                  label="Drift 1"
                  value={`${om.odds_movement_pct.home > 0 ? '+' : ''}${om.odds_movement_pct.home}%`}
                  sub={`${om.odds_open.home} → ${om.odds_current.home}`}
                  accent={om.odds_movement_pct.home < 0 ? 'green' : 'red'}
                />
                <FeatureTile
                  label="Drift X"
                  value={`${om.odds_movement_pct.draw > 0 ? '+' : ''}${om.odds_movement_pct.draw}%`}
                  sub={`${om.odds_open.draw} → ${om.odds_current.draw}`}
                  accent={om.odds_movement_pct.draw < 0 ? 'green' : 'red'}
                />
                <FeatureTile
                  label="Drift 2"
                  value={`${om.odds_movement_pct.away > 0 ? '+' : ''}${om.odds_movement_pct.away}%`}
                  sub={`${om.odds_open.away} → ${om.odds_current.away}`}
                  accent={om.odds_movement_pct.away < 0 ? 'green' : 'red'}
                />
              </div>
              <div className="text-xs text-ink-400 font-mono">
                Próbki: {om.samples_count} · Ujemny drift = napływ pieniędzy
              </div>
            </>
          ) : (
            <div className="text-xs text-ink-500 italic">Brak historii kursów</div>
          )}
        </div>

        {/* Form Features */}
        <div className="bg-ink-800 p-5" data-testid="features-form">
          <div className="overline mb-4">Forma · last 5</div>
          <div className="space-y-3">
            <div className="bg-ink-900 border border-border p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] text-ink-300 uppercase tracking-wider">Gospodarz</span>
                <TrendBadge trend={hf.home_form_trend} />
              </div>
              <div className="flex items-baseline justify-between">
                <div className="text-lg"><FormString form={hf.home_form_5} /></div>
                <div className="text-right">
                  <div className="font-mono text-xl font-bold text-edgeUp">{hf.home_form_points}</div>
                  <div className="text-[9px] text-ink-400">PKT/15</div>
                </div>
              </div>
              <div className="text-[10px] text-ink-400 mt-1 font-mono">
                {hf.home_form_wins}W · {hf.home_form_draws}D · {hf.home_form_losses}L
              </div>
            </div>
            <div className="bg-ink-900 border border-border p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] text-ink-300 uppercase tracking-wider">Gość</span>
                <TrendBadge trend={af.away_form_trend} />
              </div>
              <div className="flex items-baseline justify-between">
                <div className="text-lg"><FormString form={af.away_form_5} /></div>
                <div className="text-right">
                  <div className="font-mono text-xl font-bold text-[#0066FF]">{af.away_form_points}</div>
                  <div className="text-[9px] text-ink-400">PKT/15</div>
                </div>
              </div>
              <div className="text-[10px] text-ink-400 mt-1 font-mono">
                {af.away_form_wins}W · {af.away_form_draws}D · {af.away_form_losses}L
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
