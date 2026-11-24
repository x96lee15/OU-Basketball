import { X } from 'lucide-react';
import { useEffect, useMemo } from 'react';
import { computePlayerSummaries, formatElapsed, formatPeriodShort } from '../analytics';
import type { GameRecord } from '../types';

interface PlayerDossierDrawerProps {
  playerName: string | null;
  games: GameRecord[];
  onClose: () => void;
  onSelectGame: (game: GameRecord) => void;
}

export function PlayerDossierDrawer({
  playerName,
  games,
  onClose,
  onSelectGame,
}: PlayerDossierDrawerProps) {
  const summary = useMemo(() => {
    if (!playerName) return null;
    return computePlayerSummaries(games).find((p) => p.player === playerName) ?? null;
  }, [playerName, games]);

  const bySeason = useMemo(() => {
    if (!summary) return [];
    const map = new Map<string, number>();
    for (const g of summary.games) {
      map.set(g.season, (map.get(g.season) ?? 0) + 1);
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [summary]);

  useEffect(() => {
    if (!playerName) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [playerName, onClose]);

  if (!playerName || !summary) return null;

  const maxSeasonCnt = Math.max(...bySeason.map(([, c]) => c), 1);

  return (
    <div className="drawer-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <aside className="drawer-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <h2 style={{ margin: 0, fontSize: 21, fontWeight: 800, letterSpacing: '-0.025em' }}>
              {summary.player}
            </h2>
            <div style={{ marginTop: 5, fontSize: 12.5, color: 'var(--ink-secondary)' }}>
              <strong className="mono">{summary.first3Count}</strong> career first 3-pointers · Seasons{' '}
              <span className="mono">
                {summary.seasons[0]}
                {summary.seasons.length > 1 ? `–${summary.seasons[summary.seasons.length - 1]}` : ''}
              </span>{' '}
              · Oakland record{' '}
              <strong className="mono">
                {summary.wins}-{summary.losses} ({summary.winPct.toFixed(0)}%)
              </strong>
            </div>
          </div>

          <button type="button" className="btn" onClick={onClose} aria-label="Close drawer">
            <X size={15} /> Close
          </button>
        </div>

        <div className="drawer-body">
          <div className="dossier-cards">
            <div className="formula-box">
              <div className="formula-box-head">
                <span className="formula-box-title">Timing Profile</span>
              </div>
              <div className="formula-big">{formatElapsed(summary.avgElapsedSec)} avg</div>
              <div style={{ marginTop: 6, fontSize: 12.5, color: 'var(--ink-secondary)' }}>
                Fastest: <strong className="mono">{formatElapsed(summary.fastestSec)}</strong> · Latest:{' '}
                <strong className="mono">{formatElapsed(summary.latestSec)}</strong>
              </div>
            </div>

            <div className="formula-box">
              <div className="formula-box-head">
                <span className="formula-box-title">By Season</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 6 }}>
                {bySeason.map(([season, cnt]) => (
                  <div key={season} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12.5 }}>
                    <span className="mono" style={{ width: 58, color: 'var(--ink-secondary)' }}>
                      {season}
                    </span>
                    <div className="bar-meter" style={{ flex: 1, width: 'auto' }}>
                      <div className="bar-meter-fill" style={{ width: `${(cnt / maxSeasonCnt) * 100}%` }} />
                    </div>
                    <span className="mono" style={{ width: 24, textAlign: 'right', fontWeight: 700 }}>
                      {cnt}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <section className="panel">
            <div className="panel-header">
              <h3 className="panel-title">Games With Oakland&apos;s First 3-Pointer ({summary.games.length})</h3>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Opponent</th>
                    <th>Score</th>
                    <th className="num">1st 3 Time</th>
                    <th className="num">OU 3PT</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.games.map((g) => (
                    <tr
                      key={`${g.gameDate}-${g.gameId}`}
                      className="clickable"
                      onClick={() => onSelectGame(g)}
                    >
                      <td className="mono">{g.gameDate}</td>
                      <td style={{ fontWeight: 600 }}>{g.opponent}</td>
                      <td>
                        <span className={`badge ${g.result === 'W' ? 'win' : 'loss'}`} style={{ marginRight: 6 }}>
                          {g.result}
                        </span>
                        <span className="mono">
                          {g.oaklandScore}–{g.opponentScore}
                        </span>
                      </td>
                      <td className="num mono">
                        {formatPeriodShort(g.first3ptPeriod)} {g.first3ptClock}{' '}
                        <span style={{ color: 'var(--ink-muted)', fontSize: 11.5 }}>
                          ({formatElapsed(g.first3ptElapsedSec)})
                        </span>
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
        </div>
      </aside>
    </div>
  );
}
