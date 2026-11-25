import { useMemo } from 'react';
import { computeInGameStreaks } from '../analytics';
import type { GameRecord } from '../types';

interface StreaksViewProps {
  games: GameRecord[];
  onSelectGame: (game: GameRecord) => void;
  onSelectPlayer: (player: string) => void;
}

export function StreaksView({ games, onSelectGame, onSelectPlayer }: StreaksViewProps) {
  const streaks = useMemo(() => computeInGameStreaks(games), [games]);

  const topTeamMake = streaks.teamMakes[0];
  const topTeamMiss = streaks.teamMisses[0];
  const topPlayerMake = streaks.playerMakes[0];
  const topPlayerMiss = streaks.playerMisses[0];

  const tiedTeamMisses = topTeamMiss
    ? streaks.teamMisses.filter((g) => g.maxConsecutive3pMiss === topTeamMiss.maxConsecutive3pMiss)
    : [];
  const tiedPlayerMisses = topPlayerMiss
    ? streaks.playerMisses.filter((s) => s.streak === topPlayerMiss.streak)
    : [];

  return (
    <div className="panel-stack">
      <section className="summary-strip" style={{ marginBottom: 0 }} aria-label="In-game streak highlights">
        <div
          className="summary-cell"
          style={{ cursor: 'pointer' }}
          onClick={() => topTeamMake && onSelectGame(topTeamMake)}
        >
          <div className="summary-label">Team Hot Streak (Game)</div>
          <div className="summary-value">
            <span className="mono" style={{ color: 'var(--accent-green)' }}>
              {topTeamMake?.maxConsecutive3pm ?? '—'} straight
            </span>
          </div>
          <div className="summary-sub">
            {topTeamMake
              ? `${topTeamMake.gameDate} vs ${topTeamMake.opponent} (${topTeamMake.maxConsecutive3pmWindow})`
              : '—'}
          </div>
        </div>

        <div
          className="summary-cell"
          style={{ cursor: 'pointer' }}
          onClick={() => topTeamMiss && onSelectGame(topTeamMiss)}
        >
          <div className="summary-label">Team Cold Streak (Game)</div>
          <div className="summary-value">
            <span className="mono" style={{ color: 'var(--accent-red)' }}>
              {topTeamMiss?.maxConsecutive3pMiss ?? '—'} straight
            </span>
          </div>
          <div className="summary-sub">
            {topTeamMiss
              ? tiedTeamMisses.length > 1
                ? `Tie (${tiedTeamMisses.length}): ${tiedTeamMisses
                    .slice(0, 3)
                    .map((g) => `${g.opponent} (${g.gameDate.slice(0, 4)})`)
                    .join(' · ')}`
                : `${topTeamMiss.gameDate} vs ${topTeamMiss.opponent} (${topTeamMiss.maxConsecutive3pMissWindow})`
              : '—'}
          </div>
        </div>

        <div
          className="summary-cell"
          style={{ cursor: 'pointer' }}
          onClick={() => topPlayerMake && onSelectGame(topPlayerMake.game)}
        >
          <div className="summary-label">Player Hot Streak (Game)</div>
          <div className="summary-value">
            <span className="mono" style={{ color: 'var(--accent-green)' }}>
              {topPlayerMake?.streak ?? '—'} straight
            </span>
          </div>
          <div className="summary-sub">
            {topPlayerMake
              ? `${topPlayerMake.player} (${topPlayerMake.made}-${topPlayerMake.attempts}) vs ${topPlayerMake.game.opponent}`
              : '—'}
          </div>
        </div>

        <div
          className="summary-cell"
          style={{ cursor: 'pointer' }}
          onClick={() => topPlayerMiss && onSelectGame(topPlayerMiss.game)}
        >
          <div className="summary-label">Player Cold Streak (Game)</div>
          <div className="summary-value">
            <span className="mono" style={{ color: 'var(--accent-red)' }}>
              {topPlayerMiss?.streak ?? '—'} straight
            </span>
          </div>
          <div className="summary-sub">
            {topPlayerMiss
              ? tiedPlayerMisses.length > 1
                ? `Tie (${tiedPlayerMisses.length}): ${tiedPlayerMisses
                    .slice(0, 2)
                    .map((s) => `${s.player} vs ${s.game.opponent} (${s.game.gameDate.slice(0, 4)})`)
                    .join(' · ')}`
                : `${topPlayerMiss.player} (${topPlayerMiss.made}-${topPlayerMiss.attempts}) vs ${topPlayerMiss.game.opponent}`
              : '—'}
          </div>
        </div>
      </section>

      <div className="two-col">
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Team: Most Consecutive Made 3s in a Game</h2>
              <p className="panel-desc">Longest uninterrupted team runs of made 3-pointers (click any row for shot log)</p>
            </div>
          </div>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="num">Run</th>
                  <th>Date</th>
                  <th>Opponent</th>
                  <th>Score</th>
                  <th className="num">3PT</th>
                  <th>Window</th>
                </tr>
              </thead>
              <tbody>
                {streaks.teamMakes.map((g) => (
                  <tr key={`${g.gameDate}-${g.gameId}`} className="clickable" onClick={() => onSelectGame(g)}>
                    <td className="num mono">
                      <span className="badge win">+{g.maxConsecutive3pm}</span>
                    </td>
                    <td className="mono">{g.gameDate}</td>
                    <td style={{ fontWeight: 700 }}>{g.opponent}</td>
                    <td className="mono">
                      <span className={`badge ${g.result === 'W' ? 'win' : 'loss'}`} style={{ marginRight: 5 }}>
                        {g.result}
                      </span>
                      {g.oaklandScore}–{g.opponentScore}
                    </td>
                    <td className="num mono">
                      {g.oakland3pm}-{g.oakland3pa}
                    </td>
                    <td className="mono" style={{ fontSize: 11.5, color: 'var(--ink-secondary)' }}>
                      {g.maxConsecutive3pmWindow}
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
              <h2 className="panel-title">Team: Most Consecutive Missed 3s in a Game</h2>
              <p className="panel-desc">Longest team droughts from beyond the arc within a single game</p>
            </div>
          </div>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="num">Run</th>
                  <th>Date</th>
                  <th>Opponent</th>
                  <th>Score</th>
                  <th className="num">3PT</th>
                  <th>Window</th>
                </tr>
              </thead>
              <tbody>
                {streaks.teamMisses.map((g) => (
                  <tr key={`${g.gameDate}-${g.gameId}`} className="clickable" onClick={() => onSelectGame(g)}>
                    <td className="num mono">
                      <span className="badge loss">-{g.maxConsecutive3pMiss}</span>
                    </td>
                    <td className="mono">{g.gameDate}</td>
                    <td style={{ fontWeight: 700 }}>{g.opponent}</td>
                    <td className="mono">
                      <span className={`badge ${g.result === 'W' ? 'win' : 'loss'}`} style={{ marginRight: 5 }}>
                        {g.result}
                      </span>
                      {g.oaklandScore}–{g.opponentScore}
                    </td>
                    <td className="num mono">
                      {g.oakland3pm}-{g.oakland3pa}
                    </td>
                    <td className="mono" style={{ fontSize: 11.5, color: 'var(--ink-secondary)' }}>
                      {g.maxConsecutive3pMissWindow}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <div className="two-col">
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Individual: Most Consecutive Made 3s in a Game</h2>
              <p className="panel-desc">Single-game hot streaks by an Oakland player</p>
            </div>
          </div>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="num">Run</th>
                  <th>Player</th>
                  <th>Date</th>
                  <th>Opponent</th>
                  <th className="num">Player 3PT</th>
                </tr>
              </thead>
              <tbody>
                {streaks.playerMakes.map((s, idx) => (
                  <tr
                    key={`${s.player}-${s.game.gameDate}-${idx}`}
                    className="clickable"
                    onClick={() => onSelectGame(s.game)}
                  >
                    <td className="num mono">
                      <span className="badge win">+{s.streak}</span>
                    </td>
                    <td>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectPlayer(s.player);
                        }}
                        style={{
                          border: 'none',
                          background: 'transparent',
                          padding: 0,
                          color: 'var(--accent-gold)',
                          fontWeight: 700,
                          cursor: 'pointer',
                        }}
                      >
                        {s.player}
                      </button>
                    </td>
                    <td className="mono">{s.game.gameDate}</td>
                    <td style={{ fontWeight: 600 }}>{s.game.opponent}</td>
                    <td className="num mono">
                      {s.made}–{s.attempts}
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
              <h2 className="panel-title">Individual: Most Consecutive Missed 3s in a Game</h2>
              <p className="panel-desc">Longest single-game cold spells by an Oakland player</p>
            </div>
          </div>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="num">Run</th>
                  <th>Player</th>
                  <th>Date</th>
                  <th>Opponent</th>
                  <th className="num">Player 3PT</th>
                </tr>
              </thead>
              <tbody>
                {streaks.playerMisses.map((s, idx) => (
                  <tr
                    key={`${s.player}-${s.game.gameDate}-${idx}`}
                    className="clickable"
                    onClick={() => onSelectGame(s.game)}
                  >
                    <td className="num mono">
                      <span className="badge loss">-{s.streak}</span>
                    </td>
                    <td>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectPlayer(s.player);
                        }}
                        style={{
                          border: 'none',
                          background: 'transparent',
                          padding: 0,
                          color: 'var(--accent-gold)',
                          fontWeight: 700,
                          cursor: 'pointer',
                        }}
                      >
                        {s.player}
                      </button>
                    </td>
                    <td className="mono">{s.game.gameDate}</td>
                    <td style={{ fontWeight: 600 }}>{s.game.opponent}</td>
                    <td className="num mono">
                      {s.made}–{s.attempts}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
