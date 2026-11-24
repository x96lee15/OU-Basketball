import { ExternalLink, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { formatElapsed, formatPeriodLabel, formatPeriodShort } from '../analytics';
import type { GameRecord } from '../types';

interface GameDossierDrawerProps {
  game: GameRecord | null;
  onClose: () => void;
  onSelectPlayer: (player: string) => void;
}

export function GameDossierDrawer({ game, onClose, onSelectPlayer }: GameDossierDrawerProps) {
  const [shotFilter, setShotFilter] = useState<'oakland' | 'all' | 'made'>('oakland');

  useEffect(() => {
    if (!game) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [game, onClose]);

  if (!game) return null;

  const opp3Pct =
    game.opponent3pm !== null && game.opponent3pa
      ? `${((game.opponent3pm / game.opponent3pa) * 100).toFixed(1)}%`
      : '—';

  const events = game.threePtEvents.filter((ev) => {
    if (shotFilter === 'oakland') return ev.side === 'oakland';
    if (shotFilter === 'made') return ev.made;
    return true;
  });

  // Track Oakland's first made 3PT index to highlight it
  const firstOakMadeIdx = events.findIndex((e) => e.side === 'oakland' && e.made);

  return (
    <div className="drawer-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <aside className="drawer-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              {game.result && (
                <span className={`badge ${game.result === 'W' ? 'win' : 'loss'}`}>{game.result}</span>
              )}
              <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, letterSpacing: '-0.025em' }}>
                Oakland {game.location === 'Away' ? 'at' : 'vs.'}{' '}
                {game.opponentRank !== null ? `#${game.opponentRank} ` : ''}
                {game.opponent}
              </h2>
            </div>
            <div style={{ marginTop: 6, fontSize: 12.5, color: 'var(--ink-secondary)' }}>
              <span className="mono">{game.gameDate}</span> · Season{' '}
              <span className="mono">{game.season}</span> · {game.location} · Final{' '}
              <strong className="mono">
                {game.oaklandScore ?? '—'}–{game.opponentScore ?? '—'}
              </strong>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {game.boxscoreUrl && (
              <a
                href={game.boxscoreUrl}
                target="_blank"
                rel="noreferrer"
                className="btn"
                title="Open official box score"
              >
                <ExternalLink size={13} /> Box Score
              </a>
            )}
            <button type="button" className="btn" onClick={onClose} aria-label="Close drawer">
              <X size={15} /> Close
            </button>
          </div>
        </div>

        <div className="drawer-body">
          <div className="dossier-cards">
            <div className="formula-box">
              <div className="formula-box-head">
                <span className="formula-box-title">Oakland 3-Point Shooting</span>
                <span className="badge gold">
                  {game.oakland3pPct !== null ? `${(game.oakland3pPct * 100).toFixed(1)}%` : '—'}
                </span>
              </div>
              <div className="formula-big">
                {game.oakland3pm ?? '—'}–{game.oakland3pa ?? '—'}
              </div>
              <div style={{ marginTop: 8, fontSize: 12.5, color: 'var(--ink-secondary)' }}>
                {game.pbpAvailable && game.first3ptPlayer ? (
                  <>
                    1st 3PT:{' '}
                    <button
                      type="button"
                      onClick={() => onSelectPlayer(game.first3ptPlayer!)}
                      style={{
                        border: 'none',
                        background: 'transparent',
                        padding: 0,
                        color: 'var(--accent-gold)',
                        fontWeight: 700,
                        cursor: 'pointer',
                        textDecoration: 'underline',
                      }}
                    >
                      {game.first3ptPlayer}
                    </button>{' '}
                    ({formatPeriodLabel(game.first3ptPeriod)}, <span className="mono">{game.first3ptClock}</span> ·{' '}
                    <span className="mono">{formatElapsed(game.first3ptElapsedSec)}</span> elapsed)
                  </>
                ) : (
                  'Play-by-play unavailable on source site (box score totals only).'
                )}
              </div>
            </div>

            <div className="formula-box">
              <div className="formula-box-head">
                <span className="formula-box-title">{game.opponent} 3-Point Shooting</span>
                <span className="badge neutral">{opp3Pct}</span>
              </div>
              <div className="formula-big">
                {game.opponent3pm ?? '—'}–{game.opponent3pa ?? '—'}
              </div>
              <div style={{ marginTop: 8, fontSize: 12.5, color: 'var(--ink-secondary)' }}>
                {game.opponentFirst3ptPlayer ? (
                  <>
                    1st 3PT: <strong>{game.opponentFirst3ptPlayer}</strong> (
                    {formatPeriodLabel(game.opponentFirst3ptPeriod)},{' '}
                    <span className="mono">{game.opponentFirst3ptClock}</span>)
                  </>
                ) : (
                  'No opponent first 3-pointer play-by-play recorded.'
                )}
              </div>
            </div>
          </div>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Chronological 3-Point Shot Log</h3>
                <p className="panel-desc">
                  <span className="mono">{game.threePtEvents.length}</span> total 3-point attempts parsed from
                  play-by-play
                </p>
              </div>
              <div className="segmented">
                {(
                  [
                    ['oakland', 'Oakland'],
                    ['made', 'Made Only'],
                    ['all', 'Both Teams'],
                  ] as const
                ).map(([k, lbl]) => (
                  <button
                    key={k}
                    type="button"
                    className={`segmented-btn ${shotFilter === k ? 'active' : ''}`}
                    onClick={() => setShotFilter(k)}
                  >
                    {lbl}
                  </button>
                ))}
              </div>
            </div>

            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Half</th>
                    <th>Clock</th>
                    <th>Team</th>
                    <th>Player</th>
                    <th>Outcome</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((ev, idx) => {
                    const isFirst = idx === firstOakMadeIdx;
                    return (
                      <tr
                        key={`${ev.period}-${ev.clock}-${idx}`}
                        style={isFirst ? { background: 'var(--accent-gold-soft)' } : undefined}
                      >
                        <td className="mono">{formatPeriodShort(ev.period)}</td>
                        <td className="mono">{ev.clock}</td>
                        <td>
                          <span className={`badge ${ev.side === 'oakland' ? 'gold' : 'neutral'}`}>
                            {ev.side === 'oakland' ? 'Oakland' : game.opponent}
                          </span>
                        </td>
                        <td style={{ fontWeight: ev.made ? 700 : 500 }}>{ev.player}</td>
                        <td>
                          <span className={`shot-dot ${ev.made ? 'made' : 'missed'}`} />
                          {ev.made ? 'Made 3PT' : 'Missed 3PT'}
                          {isFirst && (
                            <span className="badge gold" style={{ marginLeft: 8 }}>
                              1st OU 3PT
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  {events.length === 0 && (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: 20, color: 'var(--ink-muted)' }}>
                        No 3-point play-by-play events for this filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </aside>
    </div>
  );
}
