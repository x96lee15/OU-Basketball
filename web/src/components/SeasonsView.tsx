import { useMemo, useState } from 'react';
import { computeHeadlineStats, computeSeasonSummaries, formatElapsed } from '../analytics';
import type { GameRecord } from '../types';

type MetricKey = 'avg3pm' | 'pct3p' | 'avg3pa' | 'medianFirst3Sec';

interface SeasonsViewProps {
  games: GameRecord[];
  onSelectSeason: (season: string) => void;
  onSelectGame: (game: GameRecord) => void;
}

export function SeasonsView({ games, onSelectSeason, onSelectGame }: SeasonsViewProps) {
  const seasonsDesc = useMemo(() => computeSeasonSummaries(games), [games]);
  const seasonsAsc = useMemo(() => [...seasonsDesc].reverse(), [seasonsDesc]);
  const stats = useMemo(() => computeHeadlineStats(games), [games]);

  const [metric, setMetric] = useState<MetricKey>('avg3pm');
  const [hoveredSeason, setHoveredSeason] = useState<string | null>(null);

  const metricConfig: Record<
    MetricKey,
    { label: string; unit: string; format: (v: number) => string; get: (s: (typeof seasonsAsc)[number]) => number }
  > = {
    avg3pm: { label: 'Avg 3PM / Game', unit: '3PM', format: (v) => v.toFixed(1), get: (s) => s.avg3pm },
    pct3p: { label: 'Team 3P%', unit: '%', format: (v) => `${(v * 100).toFixed(1)}%`, get: (s) => s.pct3p },
    avg3pa: { label: 'Avg 3PA / Game', unit: '3PA', format: (v) => v.toFixed(1), get: (s) => s.avg3pa },
    medianFirst3Sec: {
      label: 'Median Time to 1st 3PT',
      unit: 'sec',
      format: (v) => formatElapsed(Math.round(v)),
      get: (s) => s.medianFirst3Sec ?? 0,
    },
  };

  const cfg = metricConfig[metric];
  const values = seasonsAsc.map(cfg.get);
  const rawMax = Math.max(...values, 0.01);
  const rawMin = metric === 'pct3p' ? Math.max(0.2, Math.min(...values) - 0.03) : 0;
  const span = Math.max(0.01, rawMax * 1.12 - rawMin);

  const W = 920;
  const H = 250;
  const padL = 52;
  const padR = 26;
  const padT = 24;
  const padB = 40;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const stepX = plotW / Math.max(1, seasonsAsc.length - 1);

  const points = seasonsAsc.map((s, i) => {
    const v = cfg.get(s);
    const x = padL + i * stepX;
    const y = padT + plotH - ((v - rawMin) / span) * plotH;
    return { s, v, x, y };
  });

  const polyline = points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const areaPath =
    points.length > 0
      ? `M ${points[0].x},${padT + plotH} ` +
        points.map((p) => `L ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') +
        ` L ${points[points.length - 1].x},${padT + plotH} Z`
      : '';

  return (
    <div className="panel-stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">19-Season Three-Point Trend (2008–09 to 2026–27)</h2>
            <p className="panel-desc">
              Compare volume, accuracy, and speed to first made 3-pointer across every Greg Kampe era season.
            </p>
          </div>
          <div className="segmented" role="group" aria-label="Trend metric">
            {(
              [
                ['avg3pm', '3PM / G'],
                ['pct3p', '3P%'],
                ['avg3pa', '3PA / G'],
                ['medianFirst3Sec', 'Median 1st 3'],
              ] as const
            ).map(([k, lbl]) => (
              <button
                key={k}
                type="button"
                className={`segmented-btn ${metric === k ? 'active' : ''}`}
                onClick={() => setMetric(k)}
              >
                {lbl}
              </button>
            ))}
          </div>
        </div>

        <div className="panel-body">
          <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
            {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
              const y = padT + plotH - frac * plotH;
              const val = rawMin + frac * span;
              return (
                <g key={frac}>
                  <line
                    x1={padL}
                    x2={W - padR}
                    y1={y}
                    y2={y}
                    stroke="var(--border-hairline)"
                    strokeDasharray={frac === 0 ? undefined : '2,3'}
                  />
                  <text
                    x={padL - 8}
                    y={y + 4}
                    textAnchor="end"
                    fill="var(--ink-muted)"
                    fontSize={11}
                    fontFamily="var(--font-mono)"
                  >
                    {cfg.format(val)}
                  </text>
                </g>
              );
            })}

            <path d={areaPath} fill="var(--accent-gold-soft)" opacity={0.65} />
            <polyline points={polyline} fill="none" stroke="var(--accent-gold)" strokeWidth={2.5} strokeLinejoin="round" />

            {points.map(({ s, v, x, y }, i) => {
              const isHover = hoveredSeason === s.season;
              return (
                <g
                  key={s.season}
                  style={{ cursor: 'pointer' }}
                  onMouseEnter={() => setHoveredSeason(s.season)}
                  onMouseLeave={() => setHoveredSeason(null)}
                  onClick={() => onSelectSeason(s.season)}
                >
                  <circle
                    cx={x}
                    cy={y}
                    r={isHover ? 6 : 4}
                    fill={isHover ? 'var(--accent-black)' : 'var(--accent-gold)'}
                    stroke="#ffffff"
                    strokeWidth={2}
                  />
                  {(isHover || i === 0 || i === points.length - 1 || v === Math.max(...values)) && (
                    <text
                      x={x}
                      y={y - 10}
                      textAnchor="middle"
                      fill="var(--ink-primary)"
                      fontSize={11}
                      fontWeight={700}
                      fontFamily="var(--font-mono)"
                    >
                      {cfg.format(v)}
                    </text>
                  )}
                  {(i % 2 === 0 || i === points.length - 1) && (
                    <text
                      x={x}
                      y={padT + plotH + 18}
                      textAnchor="middle"
                      fill="var(--ink-muted)"
                      fontSize={10.5}
                      fontFamily="var(--font-mono)"
                    >
                      {s.season.slice(2)}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Season-by-Season Summary</h2>
            <p className="panel-desc">Click any season to jump into the filtered Game Log.</p>
          </div>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Season</th>
                <th className="num">Games</th>
                <th className="num">Record</th>
                <th className="num">Total 3PM–3PA</th>
                <th className="num">3P%</th>
                <th className="num">3PM / G</th>
                <th className="num">High / Low</th>
                <th className="num">Med 1st 3</th>
                <th>Top First-3 Shooter</th>
              </tr>
            </thead>
            <tbody>
              {seasonsDesc.map((s) => (
                <tr key={s.season} className="clickable" onClick={() => onSelectSeason(s.season)}>
                  <td className="mono" style={{ fontWeight: 700 }}>
                    {s.season}
                  </td>
                  <td className="num mono">{s.games}</td>
                  <td className="num mono">
                    {s.wins}-{s.losses}
                  </td>
                  <td className="num mono">
                    {s.total3pm}–{s.total3pa}
                  </td>
                  <td className="num mono" style={{ fontWeight: 700 }}>
                    {(s.pct3p * 100).toFixed(1)}%
                  </td>
                  <td className="num mono">{s.avg3pm.toFixed(1)}</td>
                  <td className="num mono" style={{ color: 'var(--ink-secondary)' }}>
                    {s.max3pm} / {s.min3pm}
                  </td>
                  <td className="num mono">{formatElapsed(s.medianFirst3Sec)}</td>
                  <td>
                    <strong>{s.topFirst3Player}</strong>{' '}
                    <span className="mono" style={{ color: 'var(--ink-muted)', fontSize: 12 }}>
                      ({s.topFirst3Count})
                    </span>
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
            <h2 className="panel-title">Most 3-Pointers Made in a Single Game (Top 10)</h2>
            <p className="panel-desc">Click any game for the full 3-point shot log</p>
          </div>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th className="num">3PM–3PA</th>
                <th className="num">3P%</th>
                <th>Date</th>
                <th>Season</th>
                <th>Location</th>
                <th>Opponent</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {stats.most3Top10.map((g) => (
                <tr key={`${g.gameDate}-${g.gameId}`} className="clickable" onClick={() => onSelectGame(g)}>
                  <td className="num mono" style={{ fontWeight: 800, color: 'var(--accent-gold)' }}>
                    {g.oakland3pm}–{g.oakland3pa}
                  </td>
                  <td className="num mono">
                    {g.oakland3pPct !== null ? `${(g.oakland3pPct * 100).toFixed(1)}%` : '—'}
                  </td>
                  <td className="mono">{g.gameDate}</td>
                  <td className="mono">{g.season}</td>
                  <td>
                    <span className="loc-tag">{g.location}</span>
                  </td>
                  <td style={{ fontWeight: 700 }}>
                    {g.opponentRank !== null && <span className="rank-pill">#{g.opponentRank}</span>}
                    {g.opponent}
                  </td>
                  <td>
                    <span className={`badge ${g.result === 'W' ? 'win' : 'loss'}`} style={{ marginRight: 6 }}>
                      {g.result}
                    </span>
                    <span className="mono">
                      {g.oaklandScore}–{g.opponentScore}
                    </span>
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
