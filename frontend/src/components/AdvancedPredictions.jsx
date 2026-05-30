/**
 * Advanced match predictions panel.
 * Displays Poisson-based predictions: correct score, BTS, corners, halves.
 */

function PredictionTile({ label, value, sub, accent = 'green', testId }) {
  const accentClass = {
    green: 'text-edgeUp',
    red: 'text-edgeDown',
    yellow: 'text-edgeWarn',
    blue: 'text-[#0066FF]',
    white: 'text-ink-100',
  }[accent];

  return (
    <div className="bg-ink-900 border border-border p-4" data-testid={testId}>
      <div className="overline mb-1.5">{label}</div>
      <div className={`font-mono text-2xl font-bold ${accentClass}`}>{value}</div>
      {sub && <div className="text-xs text-ink-400 mt-1 font-mono">{sub}</div>}
    </div>
  );
}

function ScoreBar({ score, pct, isTop }) {
  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className={`w-14 text-center font-mono font-bold ${isTop ? 'text-edgeUp text-lg' : 'text-ink-200 text-sm'}`}>
        {score}
      </div>
      <div className="flex-1 bg-ink-900 h-2 relative overflow-hidden">
        <div
          className={`h-full ${isTop ? 'bg-edgeUp' : 'bg-ink-500'}`}
          style={{ width: `${Math.min(100, pct * 4)}%` }}
        />
      </div>
      <div className="w-14 text-right font-mono text-xs text-ink-200">{pct.toFixed(1)}%</div>
    </div>
  );
}

export default function AdvancedPredictions({ predictions }) {
  if (!predictions) return null;

  const {
    expected_goals: xg,
    top_scores: scores,
    bts,
    over_under: ou,
    halves,
    corners,
  } = predictions;

  return (
    <section
      className="px-8 pb-6"
      data-testid="advanced-predictions-section"
    >
      <div className="overline mb-1">Zaawansowane predykcje</div>
      <h3 className="font-display text-xl font-bold mb-5">Model Poissona · pełne typy</h3>

      {/* Expected Goals row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-border mb-px">
        <PredictionTile
          label="Oczekiwane gole · gospodarz"
          value={xg.home.toFixed(2)}
          sub="xG home"
          accent="green"
          testId="prediction-xg-home"
        />
        <PredictionTile
          label="Oczekiwane gole · gość"
          value={xg.away.toFixed(2)}
          sub="xG away"
          accent="blue"
          testId="prediction-xg-away"
        />
        <PredictionTile
          label="Suma goli (xG total)"
          value={xg.total.toFixed(2)}
          sub={xg.total > 2.5 ? 'Over 2.5 prawdopodobne' : 'Under 2.5 prawdopodobne'}
          accent={xg.total > 2.5 ? 'green' : 'yellow'}
          testId="prediction-xg-total"
        />
      </div>

      {/* Predictions Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-border">
        {/* Top Scores */}
        <div className="bg-ink-800 p-6" data-testid="prediction-scores-panel">
          <div className="flex items-baseline justify-between mb-4">
            <div className="overline">Prawidłowy wynik · TOP 5</div>
            <div className="text-xs text-ink-400 font-mono">prawdopodobieństwo</div>
          </div>
          <div className="space-y-1">
            {scores.map((s, i) => (
              <ScoreBar
                key={s.score}
                score={s.score}
                pct={s.probability_pct}
                isTop={i === 0}
              />
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-border text-xs text-ink-400">
            Najbardziej prawdopodobny wynik: <span className="text-edgeUp font-mono font-bold">{scores[0]?.score}</span>
          </div>
        </div>

        {/* BTS + Over/Under */}
        <div className="bg-ink-800 p-6" data-testid="prediction-bts-ou-panel">
          <div className="overline mb-4">BTS &amp; Over/Under</div>

          {/* BTS */}
          <div className="bg-ink-900 border border-border p-4 mb-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs uppercase tracking-wider text-ink-300">BTS (oba zespoły strzelą)</span>
              <span className={`font-mono text-xs font-bold ${
                bts.recommendation === 'TAK' ? 'text-edgeUp' :
                bts.recommendation === 'NIE' ? 'text-edgeDown' : 'text-edgeWarn'
              }`}>
                {bts.recommendation}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-xs text-ink-400 mb-1">TAK</div>
                <div className="font-mono text-xl font-bold text-edgeUp">{bts.bts_yes_pct}%</div>
              </div>
              <div>
                <div className="text-xs text-ink-400 mb-1">NIE</div>
                <div className="font-mono text-xl font-bold text-edgeDown">{bts.bts_no_pct}%</div>
              </div>
            </div>
          </div>

          {/* Over/Under */}
          <div className="space-y-2">
            {[1.5, 2.5, 3.5].map((th) => {
              const over = ou[`over_${th}`];
              const under = ou[`under_${th}`];
              return (
                <div key={th} className="flex items-center gap-3 text-sm">
                  <div className="w-12 font-mono text-ink-300">{th}</div>
                  <div className="flex-1 grid grid-cols-2 gap-2">
                    <div className="bg-ink-900 px-3 py-2 flex justify-between">
                      <span className="text-xs text-ink-400">Over</span>
                      <span className={`font-mono font-bold ${over >= 60 ? 'text-edgeUp' : 'text-ink-200'}`}>
                        {over.toFixed(1)}%
                      </span>
                    </div>
                    <div className="bg-ink-900 px-3 py-2 flex justify-between">
                      <span className="text-xs text-ink-400">Under</span>
                      <span className={`font-mono font-bold ${under >= 60 ? 'text-edgeUp' : 'text-ink-200'}`}>
                        {under.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Corners */}
        <div className="bg-ink-800 p-6" data-testid="prediction-corners-panel">
          <div className="overline mb-4">Rzuty rożne</div>
          <div className="bg-ink-900 border border-border p-4 mb-3">
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <div className="text-xs text-ink-400 mb-1">GOSP</div>
                <div className="font-mono text-xl font-bold text-edgeUp">{corners.expected_home_corners}</div>
              </div>
              <div className="border-x border-border">
                <div className="text-xs text-ink-400 mb-1">SUMA</div>
                <div className="font-mono text-2xl font-bold text-ink-100">{corners.expected_total_corners}</div>
              </div>
              <div>
                <div className="text-xs text-ink-400 mb-1">GOŚĆ</div>
                <div className="font-mono text-xl font-bold text-[#0066FF]">{corners.expected_away_corners}</div>
              </div>
            </div>
          </div>
          <div className="space-y-2">
            {[
              { label: 'Over 8.5', val: corners.over_8_5_pct },
              { label: 'Over 9.5', val: corners.over_9_5_pct },
              { label: 'Over 10.5', val: corners.over_10_5_pct },
            ].map((c) => (
              <div key={c.label} className="flex items-center justify-between bg-ink-900 px-3 py-2">
                <span className="text-xs text-ink-300 font-mono">{c.label}</span>
                <span className={`font-mono font-bold ${c.val >= 60 ? 'text-edgeUp' : 'text-ink-200'}`}>
                  {c.val.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Halves */}
        <div className="bg-ink-800 p-6" data-testid="prediction-halves-panel">
          <div className="overline mb-4">Gole · 1 połowa vs 2 połowa</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-ink-900 border border-border p-4">
              <div className="overline mb-2 text-[10px]">1 POŁOWA</div>
              <div className="font-mono text-3xl font-bold text-edgeUp mb-1">{halves.expected_goals_1h}</div>
              <div className="text-xs text-ink-400">xG 1H</div>
              <div className="mt-3 space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-ink-400">Gol w 1H</span>
                  <span className="font-mono font-bold text-ink-200">{halves.goal_in_1h_pct}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-400">Over 1.5 1H</span>
                  <span className="font-mono font-bold text-ink-200">{halves.over_1_5_1h_pct}%</span>
                </div>
              </div>
            </div>
            <div className="bg-ink-900 border border-border p-4">
              <div className="overline mb-2 text-[10px]">2 POŁOWA</div>
              <div className="font-mono text-3xl font-bold text-[#0066FF] mb-1">{halves.expected_goals_2h}</div>
              <div className="text-xs text-ink-400">xG 2H</div>
              <div className="mt-3 space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-ink-400">Gol w 2H</span>
                  <span className="font-mono font-bold text-ink-200">{halves.goal_in_2h_pct}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-400">Over 1.5 2H</span>
                  <span className="font-mono font-bold text-ink-200">{halves.over_1_5_2h_pct}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
