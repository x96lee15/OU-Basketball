import { useMemo, useState } from 'react';
import {
  computeHeadlineStats,
  computeHistogramBins,
  computeTimingBuckets,
  formatClockRange,
  formatElapsed,
  formatPeriodShort,
} from '../analytics';
import type { GameRecord } from '../types';

interface TimingHistogramViewProps {
  games: GameRecord[];
  onSelectGame: (game: GameRecord) => void;
  onSelectPlayer: (player: string) => void;
}

export function TimingHistogramView({
  games,
  onSelectGame,
  onSelectPlayer,
}: TimingHistogramViewProps) {
  const bins = useMemo(() => computeHistogramBins(games), [games]);
  const buckets = useMemo(() => computeTimingBuckets(games), [games]);
  const stats = useMemo(() => computeHeadlineStats(games), [games]);

  const peakIdx = useMemo(() => {
    let best = 0;
    for (let i = 1; i < bins.length; i++) {
      if (bins[i].count > bins[best].count) best = i;
    }
    return best;
  }, [bins]);

  const [mode, setMode] = useState<'total' | 'wl'>('total');
  const [showCum, setShowCum] = useState(true);
  const [activeIdx, setActiveIdx] = useState(peakIdx);

  const selectedBin = bins[activeIdx] ?? bins[0];
  const maxVal = Math.max(10, Math.ceil((bins[peakIdx]?.count ?? 100) / 10) * 10);
  const medMin = stats.medianSec !== null ? stats.medianSec / 60 : 3.4;

  // SVG layout geometry
  const W = 920;
  const H = 290;
  const padL = 44;
  const padR = 46;
  const padT = 24;
  const padB = 38;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const barStep = plotW / Math.max(1, bins.length);
  const barW = Math.max(10, barStep - 5);

  const yTicks = [0, 25, 50, 75, 100].filter((t) => t <= maxVal);
  const cumPoints = bins
    .map((b, i) => {
      const cx = padL + i * barStep + barStep / 2;
      const cy = padT + plotH - (b.cumPct / 100) * plotH;
      return `${cx.toFixed(1)},${cy.toFixed(1)}`;
    })
    .join(' ');

  return (
    <div className="panel-stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Minute-by-Minute Distribution of Oakland&apos;s First Made 3-Pointer</h2>
            <p className="panel-desc">
              Elapsed game minute from tip-off across <span className="mono">{stats.pbpCount}</span> play-by-play games.
              Click or hover any bar to inspect every game in that minute.
            </p>
          </div>

          <div className="toolbar-group">
            <div className="segmented" role="group" aria-label="Histogram bar mode">
              <button
                type="button"
                className={`segmented-btn ${mode === 'total' ? 'active' : ''}`}
                onClick={() => setMode('total')}
              >
                Total Games
              </button>
              <button
                type="button"
                className={`segmented-btn ${mode === 'wl' ? 'active' : ''}`}
                onClick={() => setMode('wl')}
              >
                Win / Loss Split
              </button>
            </div>
            <label
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                fontSize: 12.5,
                fontWeight: 600,
                color: 'var(--ink-secondary)',
                cursor: 'pointer',
              }}
            >
              <input
                type="checkbox"
                checked={showCum}
                onChange={(e) => setShowCum(e.target.checked)}
                style={{ accentColor: 'var(--accent-blue)' }}
              />
              Cumulative %
            </label>
          </div>
        </div>

        <div className="panel-body">
          <svg
            viewBox={`0 0 ${W} ${H}`}
            style={{ width: '100%', height: 'auto', display: 'block', userSelect: 'none' }}
            role="img"
            aria-label="Histogram of minute of Oakland's first made 3-pointer"
          >
            {yTicks.map((tick) => {
              const y = padT + plotH - (tick / maxVal) * plotH;
              return (
                <g key={tick}>
                  <line
                    x1={padL}
                    x2={W - padR}
                    y1={y}
                    y2={y}
                    stroke="var(--border-hairline)"
                    strokeDasharray={tick === 0 ? undefined : '2,3'}
                  />
                  <text
                    x={padL - 8}
                    y={y + 4}
                    textAnchor="end"
                    fill="var(--ink-muted)"
                    fontSize={11}
                    fontFamily="var(--font-mono)"
                  >
                    {tick}
                  </text>
                </g>
              );
            })}

            {showCum &&
              [0, 50, 100].map((pct) => {
                const y = padT + plotH - (pct / 100) * plotH;
                return (
                  <text
                    key={pct}
                    x={W - padR + 8}
                    y={y + 4}
                    textAnchor="start"
                    fill="var(--accent-blue)"
                    fontSize={11}
                    fontFamily="var(--font-mono)"
                  >
                    {pct}%
                  </text>
                );
              })}

            {/* Halftime divider at minute 20 */}
            {bins.length > 20 && (
              <g>
                <line
                  x1={padL + 20 * barStep}
                  x2={padL + 20 * barStep}
                  y1={padT}
                  y2={padT + plotH}
                  stroke="var(--accent-amber)"
                  strokeWidth={1.5}
                  strokeDasharray="4,3"
                />
                <text
                  x={padL + 20 * barStep + 6}
                  y={padT + 12}
                  fill="var(--accent-amber)"
                  fontSize={11}
                  fontWeight={700}
                >
                  2nd Half →
                </text>
              </g>
            )}

            {/* Median line */}
            <g>
              <line
                x1={padL + medMin * barStep}
                x2={padL + medMin * barStep}
                y1={padT}
                y2={padT + plotH}
                stroke="var(--ink-muted)"
                strokeWidth={1.2}
                strokeDasharray="2,2"
              />
              <text
                x={padL + medMin * barStep + 6}
                y={padT + 12}
                fill="var(--ink-secondary)"
                fontSize={11}
                fontWeight={600}
              >
                Median ({formatElapsed(stats.medianSec)})
              </text>
            </g>

            {/* Bars */}
            {bins.map((b, i) => {
              const x = padL + i * barStep + (barStep - barW) / 2;
              const totalH = (b.count / maxVal) * plotH;
              const y = padT + plotH - totalH;
              const isActive = i === activeIdx;
              const wH = (b.wins / maxVal) * plotH;
              const lH = (b.losses / maxVal) * plotH;

              return (
                <g key={b.min}>
                  {isActive && (
                    <rect
                      x={padL + i * barStep}
                      y={padT}
                      width={barStep}
                      height={plotH}
                      fill="var(--bg-selected)"
                      rx={3}
                    />
                  )}
                  {mode === 'total' ? (
                    <rect
                      x={x}
                      y={y}
                      width={barW}
                      height={Math.max(0, totalH)}
                      rx={3}
                      fill={b.min >= 20 ? 'var(--accent-amber)' : 'var(--accent-gold-bright)'}
                      stroke={isActive ? 'var(--accent-black)' : 'none'}
                      strokeWidth={isActive ? 1.5 : 0}
                      opacity={isActive ? 1 : 0.88}
                    />
                  ) : (
                    <>
                      <rect
                        x={x}
                        y={padT + plotH - wH}
                        width={barW}
                        height={Math.max(0, wH)}
                        rx={2}
                        fill="var(--accent-green)"
                        opacity={isActive ? 1 : 0.86}
                      />
                      <rect
                        x={x}
                        y={padT + plotH - wH - lH}
                        width={barW}
                        height={Math.max(0, lH)}
                        rx={2}
                        fill="var(--accent-red)"
                        opacity={isActive ? 1 : 0.84}
                      />
                    </>
                  )}

                  {(b.count >= 16 || (isActive && b.count > 0)) && (
                    <text
                      x={x + barW / 2}
                      y={y - 5}
                      textAnchor="middle"
                      fill={isActive ? 'var(--ink-primary)' : 'var(--ink-secondary)'}
                      fontSize={10.5}
                      fontWeight={isActive ? 700 : 500}
                      fontFamily="var(--font-mono)"
                    >
                      {b.count}
                    </text>
                  )}

                  {(i % 2 === 0 || i === bins.length - 1) && (
                    <text
                      x={x + barW / 2}
                      y={padT + plotH + 16}
                      textAnchor="middle"
                      fill="var(--ink-muted)"
                      fontSize={11}
                      fontFamily="var(--font-mono)"
                    >
                      {b.min}
                    </text>
                  )}

                  <rect
                    x={padL + i * barStep}
                    y={padT}
                    width={barStep}
                    height={plotH + 20}
                    fill="transparent"
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setActiveIdx(i)}
                    onClick={() => setActiveIdx(i)}
                  />
                </g>
              );
            })}

            {showCum && (
              <g pointerEvents="none">
                <polyline
                  points={cumPoints}
                  fill="none"
                  stroke="var(--accent-blue)"
                  strokeWidth={2.2}
                  strokeLinejoin="round"
                />
                {selectedBin && (
                  <circle
                    cx={padL + activeIdx * barStep + barStep / 2}
                    cy={padT + plotH - (selectedBin.cumPct / 100) * plotH}
                    r={4}
                    fill="var(--accent-blue)"
                    stroke="#ffffff"
                    strokeWidth={1.8}
                  />
                )}
              </g>
            )}

            <text
              x={padL + plotW / 2}
              y={H - 5}
              textAnchor="middle"
              fill="var(--ink-muted)"
              fontSize={11.5}
            >
              Elapsed Game Minute (0 = Tip-Off · 20 = Start of 2nd Half)
            </text>
          </svg>

          {/* Selected Minute Inspector */}
          {selectedBin && (
            <div
              style={{
                marginTop: 14,
                padding: '12px 14px',
                borderRadius: 'var(--radius-sm)',
                background: 'hsl(42 22% 98%)',
                border: '1px solid var(--border-hairline)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 10,
                  marginBottom: selectedBin.games.length ? 10 : 0,
                }}
              >
                <div style={{ fontWeight: 700, fontSize: 13.5 }}>
                  Minute {selectedBin.min}–{selectedBin.min + 1}{' '}
                  <span style={{ fontWeight: 500, color: 'var(--ink-secondary)' }}>
                    ({formatClockRange(selectedBin.min)})
                  </span>
                </div>
                <div className="mono" style={{ fontSize: 12.5, color: 'var(--ink-secondary)' }}>
                  <strong>{selectedBin.count}</strong> games ({selectedBin.pct.toFixed(1)}% · cum{' '}
                  {selectedBin.cumPct.toFixed(1)}%)
                  {selectedBin.count > 0 && (
                    <>
                      {' · '}Record{' '}
                      <strong>
                        {selectedBin.wins}-{selectedBin.losses}
                      </strong>{' '}
                      ({Math.round((selectedBin.wins / selectedBin.count) * 100)}% W)
                    </>
                  )}
                </div>
              </div>

              {selectedBin.games.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {selectedBin.games.slice(0, 12).map((g) => (
                    <button
                      key={`${g.season}-${g.gameDate}-${g.gameId}`}
                      type="button"
                      className="pill-btn"
                      onClick={() => onSelectGame(g)}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                    >
                      <span
                        style={{
                          width: 7,
                          height: 7,
                          borderRadius: '50%',
                          background: g.result === 'W' ? 'var(--accent-green)' : 'var(--accent-red)',
                        }}
                      />
                      <span className="mono">{g.gameDate}</span>
                      <span>{g.opponent}</span>
                      <span style={{ color: 'var(--ink-muted)' }}>
                        ({g.first3ptPlayer}, {g.first3ptClock})
                      </span>
                    </button>
                  ))}
                  {selectedBin.games.length > 12 && (
                    <span style={{ fontSize: 12, color: 'var(--ink-muted)', alignSelf: 'center', paddingLeft: 4 }}>
                      +{selectedBin.games.length - 12} more in this minute
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Timing Buckets */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Oakland Win Rate by First 3-Pointer Timing</h2>
            <p className="panel-desc">
              Hitting an early three correlates with stronger results — Oakland is{' '}
              <span className="mono">
                {buckets[4]?.wins ?? 0}-{buckets[4]?.losses ?? 0}
              </span>{' '}
              when waiting until the 2nd half.
            </p>
          </div>
        </div>
        <div className="panel-body">
          <div className="bucket-grid">
            {buckets.map((b) => (
              <div key={b.label} className="bucket-card">
                <div className="bucket-label">{b.label}</div>
                <div className="bucket-sub">{b.sub}</div>
                <div className="mono" style={{ fontSize: 20, fontWeight: 800 }}>
                  {b.games}{' '}
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-muted)' }}>
                    ({b.sharePct.toFixed(1)}%)
                  </span>
                </div>
                <div className="mono" style={{ fontSize: 12.5, marginTop: 4, color: 'var(--ink-secondary)' }}>
                  {b.wins}-{b.losses} ·{' '}
                  <strong style={{ color: b.winPct >= 55 ? 'var(--accent-green)' : b.winPct < 40 ? 'var(--accent-red)' : 'var(--ink-primary)' }}>
                    {b.winPct.toFixed(1)}% W
                  </strong>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Fastest & Longest side-by-side */}
      <div className="two-col">
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Fastest 1st 3-Pointers (Top 10)</h2>
              <p className="panel-desc">Quickest made 3-pointers after opening tip-off</p>
            </div>
          </div>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Date</th>
                  <th>Opponent</th>
                  <th>Player</th>
                  <th className="num">3PT</th>
                </tr>
              </thead>
              <tbody>
                {stats.fastestTop10.map((g) => (
                  <tr key={`${g.gameDate}-${g.gameId}`} className="clickable" onClick={() => onSelectGame(g)}>
                    <td className="mono">
                      <span className="badge gold">{g.first3ptElapsedSec}s</span>{' '}
                      <span style={{ color: 'var(--ink-muted)', fontSize: 11.5 }}>{g.first3ptClock}</span>
                    </td>
                    <td className="mono">{g.gameDate}</td>
                    <td style={{ fontWeight: 600 }}>{g.opponent}</td>
                    <td>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (g.first3ptPlayer) onSelectPlayer(g.first3ptPlayer);
                        }}
                        style={{ border: 'none', background: 'transparent', padding: 0, color: 'var(--accent-gold)', fontWeight: 600, cursor: 'pointer' }}
                      >
                        {g.first3ptPlayer}
                      </button>
                    </td>
                    <td className="num mono">
                      {g.oakland3pm}-{g.oakland3pa}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Longest Wait Before 1st 3-Pointer (Top 10)</h2>
              <p className="panel-desc">Longest droughts before Oakland&apos;s first made three</p>
            </div>
          </div>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Elapsed</th>
                  <th>Date</th>
                  <th>Opponent</th>
                  <th>Player</th>
                  <th className="num">Result</th>
                </tr>
              </thead>
              <tbody>
                {stats.longestTop10.map((g) => (
                  <tr key={`${g.gameDate}-${g.gameId}`} className="clickable" onClick={() => onSelectGame(g)}>
                    <td className="mono">
                      <span className="badge warn">{formatElapsed(g.first3ptElapsedSec)}</span>{' '}
                      <span style={{ color: 'var(--ink-muted)', fontSize: 11.5 }}>
                        {formatPeriodShort(g.first3ptPeriod)} {g.first3ptClock}
                      </span>
                    </td>
                    <td className="mono">{g.gameDate}</td>
                    <td style={{ fontWeight: 600 }}>{g.opponent}</td>
                    <td>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (g.first3ptPlayer) onSelectPlayer(g.first3ptPlayer);
                        }}
                        style={{ border: 'none', background: 'transparent', padding: 0, color: 'var(--accent-gold)', fontWeight: 600, cursor: 'pointer' }}
                      >
                        {g.first3ptPlayer}
                      </button>
                    </td>
                    <td className="num mono">
                      <span className={`badge ${g.result === 'W' ? 'win' : 'loss'}`}>{g.result}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* Games with only 1 three */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Games With Only 1 Made 3-Pointer ({stats.oneThreeGames.length})</h2>
            <p className="panel-desc">Every game in the dataset where Oakland finished with exactly one made three</p>
          </div>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Season</th>
                <th>Location</th>
                <th>Opponent</th>
                <th>Score</th>
                <th className="num">3PT</th>
                <th>Made By</th>
                <th className="num">Time</th>
              </tr>
            </thead>
            <tbody>
              {stats.oneThreeGames.map((g) => (
                <tr key={`${g.gameDate}-${g.gameId}`} className="clickable" onClick={() => onSelectGame(g)}>
                  <td className="mono">{g.gameDate}</td>
                  <td className="mono">{g.season}</td>
                  <td>
                    <span className="loc-tag">{g.location}</span>
                  </td>
                  <td style={{ fontWeight: 700 }}>{g.opponent}</td>
                  <td>
                    <span className={`badge ${g.result === 'W' ? 'win' : 'loss'}`} style={{ marginRight: 6 }}>
                      {g.result}
                    </span>
                    <span className="mono">
                      {g.oaklandScore}–{g.opponentScore}
                    </span>
                  </td>
                  <td className="num mono">
                    {g.oakland3pm}-{g.oakland3pa}
                  </td>
                  <td style={{ fontWeight: 600 }}>{g.first3ptPlayer}</td>
                  <td className="num mono">
                    {formatPeriodShort(g.first3ptPeriod)} {g.first3ptClock} ({formatElapsed(g.first3ptElapsedSec)})
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
