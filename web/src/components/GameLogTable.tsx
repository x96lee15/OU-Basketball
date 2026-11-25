import { ArrowDown, ArrowUp, Download, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  downloadFile,
  formatElapsed,
  formatPeriodShort,
  gamesToCsv,
} from '../analytics';
import type { GameRecord } from '../types';

type SortKey =
  | 'gameDate'
  | 'opponent'
  | 'oakland3pm'
  | 'oakland3pa'
  | 'oakland3pPct'
  | 'opponent3pm'
  | 'maxConsecutive3pm'
  | 'maxConsecutive3pMiss'
  | 'first3ptElapsedSec'
  | 'first3ptPlayer';

type SpecialFilter = 'all' | 'one3' | 'hot15' | 'secondHalf' | 'ranked';

interface GameLogTableProps {
  games: GameRecord[];
  seasons: string[];
  seasonFilter: string;
  onSeasonFilterChange: (season: string) => void;
  onSelectGame: (game: GameRecord) => void;
  onSelectPlayer: (player: string) => void;
}

export function GameLogTable({
  games,
  seasons,
  seasonFilter,
  onSeasonFilterChange,
  onSelectGame,
  onSelectPlayer,
}: GameLogTableProps) {
  const [search, setSearch] = useState('');
  const [location, setLocation] = useState<'All' | 'Home' | 'Away' | 'Neutral'>('All');
  const [result, setResult] = useState<'All' | 'W' | 'L'>('All');
  const [special, setSpecial] = useState<SpecialFilter>('all');
  const [sortKey, setSortKey] = useState<SortKey>('gameDate');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [pageSize, setPageSize] = useState(50);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      const ascDefault = key === 'opponent' || key === 'first3ptPlayer' || key === 'first3ptElapsedSec';
      setSortDir(ascDefault ? 'asc' : 'desc');
    }
  };

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const list = games.filter((g) => {
      if (seasonFilter !== 'All' && g.season !== seasonFilter) return false;
      if (location !== 'All' && g.location !== location) return false;
      if (result !== 'All' && g.result !== result) return false;
      if (special === 'one3' && g.oakland3pm !== 1) return false;
      if (special === 'hot15' && (g.oakland3pm ?? 0) < 15) return false;
      if (special === 'secondHalf' && (!g.pbpAvailable || g.first3ptPeriod === '1')) return false;
      if (special === 'ranked' && g.opponentRank === null) return false;
      if (!q) return true;
      return (
        g.opponent.toLowerCase().includes(q) ||
        (g.first3ptPlayer?.toLowerCase().includes(q) ?? false) ||
        g.gameDate.includes(q) ||
        g.season.includes(q)
      );
    });

    const dir = sortDir === 'asc' ? 1 : -1;
    return [...list].sort((a, b) => {
      if (sortKey === 'gameDate') return a.gameDate.localeCompare(b.gameDate) * dir;
      if (sortKey === 'opponent') return a.opponent.localeCompare(b.opponent) * dir;
      if (sortKey === 'first3ptPlayer') {
        return (a.first3ptPlayer ?? 'zzz').localeCompare(b.first3ptPlayer ?? 'zzz') * dir;
      }
      const numVal = (g: GameRecord): number => {
        switch (sortKey) {
          case 'oakland3pm':
            return g.oakland3pm ?? -1;
          case 'oakland3pa':
            return g.oakland3pa ?? -1;
          case 'oakland3pPct':
            return g.oakland3pPct ?? -1;
          case 'opponent3pm':
            return g.opponent3pm ?? -1;
          case 'maxConsecutive3pm':
            return g.maxConsecutive3pm ?? -1;
          case 'maxConsecutive3pMiss':
            return g.maxConsecutive3pMiss ?? -1;
          case 'first3ptElapsedSec':
            return g.first3ptElapsedSec ?? (dir === 1 ? 99999 : -1);
        }
      };
      return (numVal(a) - numVal(b)) * dir;
    });
  }, [games, seasonFilter, location, result, special, search, sortKey, sortDir]);

  const visible = filtered.slice(0, pageSize);

  const filteredSummary = useMemo(() => {
    const w = filtered.filter((g) => g.result === 'W').length;
    const l = filtered.filter((g) => g.result === 'L').length;
    const m = filtered.reduce((acc, g) => acc + (g.oakland3pm ?? 0), 0);
    const a = filtered.reduce((acc, g) => acc + (g.oakland3pa ?? 0), 0);
    return { w, l, m, a, pct: a > 0 ? (m / a) * 100 : 0 };
  }, [filtered]);

  const renderSortHeader = (label: string, key: SortKey, isNum = true, title?: string) => {
    const active = sortKey === key;
    return (
      <th
        className={`sortable ${isNum ? 'num' : ''} ${active ? 'sorted' : ''}`}
        onClick={() => handleSort(key)}
        title={title}
      >
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          {label}
          {active && (sortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
        </span>
      </th>
    );
  };

  return (
    <section className="panel" aria-label="Oakland University Men's Basketball 3-Point Game Log">
      <div className="toolbar">
        <div className="toolbar-group">
          <div className="search-wrap">
            <Search size={14} className="search-icon" />
            <input
              type="search"
              className="search-input"
              placeholder="Search opponent, player, date..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPageSize(50);
              }}
            />
          </div>

          <select
            className="select-input"
            aria-label="Filter by season"
            value={seasonFilter}
            onChange={(e) => {
              onSeasonFilterChange(e.target.value);
              setPageSize(50);
            }}
          >
            <option value="All">All Seasons ({seasons.length})</option>
            {seasons.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <div className="filter-pills" role="group" aria-label="Filter by location">
            {(['All', 'Home', 'Away', 'Neutral'] as const).map((loc) => (
              <button
                key={loc}
                type="button"
                className={`pill-btn ${location === loc ? 'active' : ''}`}
                onClick={() => setLocation(loc)}
              >
                {loc}
              </button>
            ))}
          </div>

          <div className="segmented" role="group" aria-label="Filter by result">
            {(['All', 'W', 'L'] as const).map((res) => (
              <button
                key={res}
                type="button"
                className={`segmented-btn ${result === res ? 'active' : ''}`}
                onClick={() => setResult(res)}
              >
                {res === 'All' ? 'W/L' : res}
              </button>
            ))}
          </div>
        </div>

        <div className="toolbar-group">
          <button
            type="button"
            className="btn"
            onClick={() => downloadFile(gamesToCsv(filtered), 'oakland_3pt_filtered.csv', 'text/csv;charset=utf-8')}
          >
            <Download size={13} /> CSV
          </button>
          <button
            type="button"
            className="btn"
            onClick={() =>
              downloadFile(JSON.stringify(filtered, null, 2), 'oakland_3pt_filtered.json', 'application/json')
            }
          >
            <Download size={13} /> JSON
          </button>
        </div>
      </div>

      <div
        className="toolbar"
        style={{ paddingTop: 9, paddingBottom: 9, background: 'hsl(42 22% 98.5%)' }}
      >
        <div className="filter-pills" role="group" aria-label="Preset filters">
          {(
            [
              ['all', 'All Games'],
              ['one3', 'Only 1 Three'],
              ['hot15', '15+ Threes'],
              ['secondHalf', '2nd-Half 1st 3'],
              ['ranked', 'Ranked Opponents'],
            ] as const
          ).map(([k, lbl]) => (
            <button
              key={k}
              type="button"
              className={`pill-btn ${special === k ? 'active' : ''}`}
              onClick={() => {
                setSpecial(k);
                setPageSize(100);
              }}
            >
              {lbl}
            </button>
          ))}
        </div>

        <div style={{ fontSize: 12.5, color: 'var(--ink-secondary)' }}>
          Showing <strong className="mono">{filtered.length}</strong> games ·{' '}
          <span className="mono">
            {filteredSummary.w}-{filteredSummary.l}
          </span>{' '}
          ·{' '}
          <span className="mono">
            {filteredSummary.m}-{filteredSummary.a} ({filteredSummary.pct.toFixed(1)}%)
          </span>
        </div>
      </div>

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              {renderSortHeader('Date', 'gameDate', false)}
              <th>Season</th>
              <th>Loc</th>
              {renderSortHeader('Opponent', 'opponent', false)}
              <th>Score</th>
              {renderSortHeader('OU 3PM', 'oakland3pm')}
              {renderSortHeader('OU 3PA', 'oakland3pa')}
              {renderSortHeader('3P%', 'oakland3pPct')}
              {renderSortHeader('Opp 3PT', 'opponent3pm')}
              {renderSortHeader('Max +', 'maxConsecutive3pm', true, 'Longest consecutive made 3PT run')}
              {renderSortHeader('Max -', 'maxConsecutive3pMiss', true, 'Longest consecutive missed 3PT drought')}
              {renderSortHeader('1st 3 Player', 'first3ptPlayer', false)}
              {renderSortHeader('1st 3 Time', 'first3ptElapsedSec', true, 'Elapsed time from tip-off')}
            </tr>
          </thead>
          <tbody>
            {visible.map((g) => (
              <tr
                key={`${g.season}-${g.gameDate}-${g.gameId}`}
                className="clickable"
                onClick={() => onSelectGame(g)}
              >
                <td className="mono">{g.gameDate}</td>
                <td className="mono" style={{ color: 'var(--ink-secondary)' }}>
                  {g.season}
                </td>
                <td>
                  <span className="loc-tag">{g.location}</span>
                </td>
                <td style={{ fontWeight: 700 }}>
                  {g.opponentRank !== null && <span className="rank-pill">#{g.opponentRank}</span>}
                  {g.opponent}
                </td>
                <td>
                  {g.result && (
                    <span className={`badge ${g.result === 'W' ? 'win' : 'loss'}`} style={{ marginRight: 6 }}>
                      {g.result}
                    </span>
                  )}
                  <span className="mono">
                    {g.oaklandScore ?? '—'}–{g.opponentScore ?? '—'}
                  </span>
                </td>
                <td className="num mono" style={{ fontWeight: 700 }}>
                  {g.oakland3pm ?? '—'}
                </td>
                <td className="num mono" style={{ color: 'var(--ink-secondary)' }}>
                  {g.oakland3pa ?? '—'}
                </td>
                <td className="num mono">
                  {g.oakland3pPct !== null ? `${(g.oakland3pPct * 100).toFixed(1)}%` : '—'}
                </td>
                <td className="num mono" style={{ color: 'var(--ink-secondary)' }}>
                  {g.opponent3pm !== null ? `${g.opponent3pm}-${g.opponent3pa ?? '?'}` : '—'}
                </td>
                <td className="num mono" title={g.maxConsecutive3pmWindow ?? undefined}>
                  {g.maxConsecutive3pm !== null ? (
                    <span className={`badge ${g.maxConsecutive3pm >= 5 ? 'win' : 'neutral'}`}>
                      +{g.maxConsecutive3pm}
                    </span>
                  ) : (
                    '—'
                  )}
                </td>
                <td className="num mono" title={g.maxConsecutive3pMissWindow ?? undefined}>
                  {g.maxConsecutive3pMiss !== null ? (
                    <span className={`badge ${g.maxConsecutive3pMiss >= 10 ? 'loss' : 'neutral'}`}>
                      -{g.maxConsecutive3pMiss}
                    </span>
                  ) : (
                    '—'
                  )}
                </td>
                <td>
                  {g.first3ptPlayer ? (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectPlayer(g.first3ptPlayer!);
                      }}
                      style={{
                        border: 'none',
                        background: 'transparent',
                        padding: 0,
                        color: 'var(--accent-gold)',
                        fontWeight: 600,
                        cursor: 'pointer',
                        textDecoration: 'underline',
                        textUnderlineOffset: 2,
                      }}
                    >
                      {g.first3ptPlayer}
                    </button>
                  ) : (
                    <span style={{ color: 'var(--ink-muted)' }}>Box score only</span>
                  )}
                </td>
                <td className="num mono">
                  {g.pbpAvailable && g.first3ptElapsedSec !== null ? (
                    <span title={`${formatElapsed(g.first3ptElapsedSec)} elapsed`}>
                      <span
                        className={`badge ${g.first3ptPeriod === '1' ? 'neutral' : 'warn'}`}
                        style={{ marginRight: 6 }}
                      >
                        {formatPeriodShort(g.first3ptPeriod)} {g.first3ptClock}
                      </span>
                      <span style={{ color: 'var(--ink-muted)', fontSize: 11.5 }}>
                        {formatElapsed(g.first3ptElapsedSec)}
                      </span>
                    </span>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={13} style={{ textAlign: 'center', padding: 28, color: 'var(--ink-muted)' }}>
                  No games match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        <span>Click any row to open the Game Dossier &amp; chronological 3-point shot log. Click a player name for their Player Dossier.</span>
        {filtered.length > visible.length && (
          <div className="toolbar-group">
            <button type="button" className="btn" onClick={() => setPageSize((p) => p + 100)}>
              Load 100 More ({filtered.length - visible.length} remaining)
            </button>
            <button type="button" className="btn" onClick={() => setPageSize(filtered.length)}>
              Show All {filtered.length}
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
