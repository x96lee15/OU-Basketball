import { ArrowDown, ArrowUp, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { computePlayerSummaries, formatElapsed } from '../analytics';
import type { GameRecord, PlayerSummary } from '../types';

type SortKey = 'first3Count' | 'player' | 'winPct' | 'avgElapsedSec' | 'fastestSec';

interface PlayersViewProps {
  games: GameRecord[];
  onSelectPlayer: (player: string) => void;
}

export function PlayersView({ games, onSelectPlayer }: PlayersViewProps) {
  const players = useMemo(() => computePlayerSummaries(games), [games]);
  const [search, setSearch] = useState('');
  const [minCount, setMinCount] = useState(1);
  const [sortKey, setSortKey] = useState<SortKey>('first3Count');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const maxCount = players[0]?.first3Count || 1;

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((p) => (p === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      const ascDefault = key === 'player' || key === 'avgElapsedSec' || key === 'fastestSec';
      setSortDir(ascDefault ? 'asc' : 'desc');
    }
  };

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const list = players.filter((p) => {
      if (p.first3Count < minCount) return false;
      if (!q) return true;
      return p.player.toLowerCase().includes(q) || p.seasons.some((s) => s.includes(q));
    });
    const dir = sortDir === 'asc' ? 1 : -1;
    return [...list].sort((a: PlayerSummary, b: PlayerSummary) => {
      if (sortKey === 'player') return a.player.localeCompare(b.player) * dir;
      return ((a[sortKey] as number) - (b[sortKey] as number)) * dir;
    });
  }, [players, search, minCount, sortKey, sortDir]);

  const renderSortHeader = (label: string, key: SortKey, isNum = true) => {
    const active = sortKey === key;
    return (
      <th className={`sortable ${isNum ? 'num' : ''} ${active ? 'sorted' : ''}`} onClick={() => handleSort(key)}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          {label}
          {active && (sortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
        </span>
      </th>
    );
  };

  return (
    <section className="panel" aria-label="First 3-Pointer Player Leaderboard">
      <div className="toolbar">
        <div className="toolbar-group">
          <div className="search-wrap">
            <Search size={14} className="search-icon" />
            <input
              type="search"
              className="search-input"
              placeholder="Filter player or season..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="filter-pills" role="group" aria-label="Minimum first 3-pointers">
            {[1, 5, 10, 15].map((n) => (
              <button
                key={n}
                type="button"
                className={`pill-btn ${minCount === n ? 'active' : ''}`}
                onClick={() => setMinCount(n)}
              >
                {n === 1 ? 'All Players' : `${n}+ First 3s`}
              </button>
            ))}
          </div>
        </div>

        <span style={{ fontSize: 12.5, color: 'var(--ink-secondary)' }}>
          Showing <strong className="mono">{filtered.length}</strong> of{' '}
          <strong className="mono">{players.length}</strong> players
        </span>
      </div>

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th className="num">#</th>
              {renderSortHeader('Player', 'player', false)}
              <th>Seasons</th>
              {renderSortHeader('First 3s', 'first3Count')}
              <th>Share</th>
              {renderSortHeader('Team Record', 'winPct')}
              {renderSortHeader('Avg Time', 'avgElapsedSec')}
              {renderSortHeader('Fastest', 'fastestSec')}
            </tr>
          </thead>
          <tbody>
            {filtered.map((p, idx) => (
              <tr key={p.player} className="clickable" onClick={() => onSelectPlayer(p.player)}>
                <td className="num mono" style={{ color: 'var(--ink-muted)' }}>
                  {idx + 1}
                </td>
                <td style={{ fontWeight: 700 }}>{p.player}</td>
                <td className="mono" style={{ fontSize: 12, color: 'var(--ink-secondary)' }}>
                  {p.seasons.length === 1
                    ? p.seasons[0]
                    : `${p.seasons[0]} – ${p.seasons[p.seasons.length - 1]}`}
                </td>
                <td className="num mono" style={{ fontWeight: 800, color: 'var(--accent-gold)' }}>
                  {p.first3Count}
                </td>
                <td>
                  <div className="bar-meter">
                    <div
                      className="bar-meter-fill"
                      style={{ width: `${Math.max(4, (p.first3Count / maxCount) * 100)}%` }}
                    />
                  </div>
                </td>
                <td className="num mono">
                  {p.wins}-{p.losses}{' '}
                  <span style={{ color: 'var(--ink-muted)', fontSize: 11.5 }}>({p.winPct.toFixed(0)}%)</span>
                </td>
                <td className="num mono">{formatElapsed(p.avgElapsedSec)}</td>
                <td className="num mono">
                  <span className="badge neutral">{formatElapsed(p.fastestSec)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        <span>Click any player row to inspect every game where they hit Oakland&apos;s first 3-pointer.</span>
        <span>Normalized aliases: Kahlil Felder → Kay Felder · Tray Maddox → Tray Maddox Jr.</span>
      </div>
    </section>
  );
}
