import {
  BarChart3,
  CheckCircle2,
  Flame,
  RefreshCw,
  Table2,
  TrendingUp,
  Users,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { computeHeadlineStats, formatElapsed, formatPeriodShort } from './analytics';
import { loadDataset, syncCurrentSeason } from './api';
import { GameDossierDrawer } from './components/GameDossierDrawer';
import { GameLogTable } from './components/GameLogTable';
import { PlayerDossierDrawer } from './components/PlayerDossierDrawer';
import { PlayersView } from './components/PlayersView';
import { SeasonsView } from './components/SeasonsView';
import { TimingHistogramView } from './components/TimingHistogramView';
import type { DatasetPayload, GameRecord } from './types';

type TabKey = 'games' | 'timing' | 'players' | 'seasons';

export default function App() {
  const [tab, setTab] = useState<TabKey>('games');
  const [payload, setPayload] = useState<DatasetPayload | null>(null);
  const [dataMode, setDataMode] = useState<'api' | 'static'>('static');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [seasonFilter, setSeasonFilter] = useState<string>('All');
  const [selectedGame, setSelectedGame] = useState<GameRecord | null>(null);
  const [selectedPlayer, setSelectedPlayer] = useState<string | null>(null);

  const [syncing, setSyncing] = useState(false);
  const [notice, setNotice] = useState<{ text: string; tone?: 'info' | 'warning' } | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    loadDataset()
      .then(({ data, mode }) => {
        if (!cancelled) {
          setPayload(data);
          setDataMode(mode);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load data');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = useMemo(() => (payload ? computeHeadlineStats(payload.games) : null), [payload]);

  const handleSync = async () => {
    setSyncing(true);
    setNotice(null);
    try {
      const latestSeason = payload?.seasons[0] ?? '2026-27';
      const res = await syncCurrentSeason(latestSeason);
      if (res.data) {
        setPayload(res.data);
        setDataMode('api');
      }
      setNotice({ text: res.message, tone: res.synced ? 'info' : 'warning' });
    } catch (err) {
      setNotice({ text: err instanceof Error ? err.message : 'Sync failed', tone: 'warning' });
    } finally {
      setSyncing(false);
    }
  };

  const handleJumpToSeason = (season: string) => {
    setSeasonFilter(season);
    setTab('games');
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <div className="brand-mark" aria-hidden="true">
              OU3
            </div>
            <div className="brand-title">
              <span className="brand-name">GrizzThree</span>
              <span className="brand-sub">Oakland University Men&apos;s Basketball · 3PT Archive</span>
            </div>
          </div>

          <nav className="nav-tabs" aria-label="Primary navigation">
            <button
              type="button"
              className={`nav-tab ${tab === 'games' ? 'active' : ''}`}
              onClick={() => setTab('games')}
            >
              <Table2 size={14} /> Game Log
            </button>
            <button
              type="button"
              className={`nav-tab ${tab === 'timing' ? 'active' : ''}`}
              onClick={() => setTab('timing')}
            >
              <BarChart3 size={14} /> Timing &amp; Histogram
            </button>
            <button
              type="button"
              className={`nav-tab ${tab === 'players' ? 'active' : ''}`}
              onClick={() => setTab('players')}
            >
              <Users size={14} /> Players
            </button>
            <button
              type="button"
              className={`nav-tab ${tab === 'seasons' ? 'active' : ''}`}
              onClick={() => setTab('seasons')}
            >
              <TrendingUp size={14} /> Seasons &amp; Trends
            </button>
          </nav>

          {dataMode === 'api' && (
            <div className="topbar-actions">
              <button
                type="button"
                className="sync-btn"
                onClick={handleSync}
                disabled={syncing}
                title="Scrape latest games from goldengrizzlies.com via local API server"
              >
                <RefreshCw size={13} className={syncing ? 'spin' : ''} />
                {syncing ? 'Syncing...' : `Sync ${payload?.seasons[0] ?? '2026-27'}`}
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="main-container">
        <div className="page-header">
          <div>
            <h1>Oakland University Men&apos;s Basketball 3-Point Statistics</h1>
            <p className="page-subtitle">
              Play-by-play and box score 3-point archive across{' '}
              <span className="mono">{payload?.seasons.length ?? 19}</span> seasons (2008–09 through 2026–27) ·
              Exhibition games excluded · Normalized player &amp; opponent names.
            </p>
          </div>

          {payload && (
            <div className="meta-inline">
              <span className="meta-chip">
                Through <strong className="mono">{payload.asOfDate}</strong> ·{' '}
                <span className="mono">{payload.totalGames}</span> Games
              </span>
              <span className="meta-chip verified">
                <CheckCircle2 size={13} />{' '}
                <span className="mono">
                  {payload.pbpGames}/{payload.totalGames}
                </span>{' '}
                Play-by-Play Verified
              </span>
              {dataMode === 'api' && <span className="meta-chip gold">Live API Connected</span>}
            </div>
          )}
        </div>

        {notice && (
          <div className={`notice-banner ${notice.tone === 'warning' ? 'warning' : ''}`}>
            <span>{notice.text}</span>
            <button type="button" className="notice-close" onClick={() => setNotice(null)}>
              ✕
            </button>
          </div>
        )}

        {error && (
          <div className="notice-banner warning">
            <span>{error}</span>
          </div>
        )}

        {payload?.streak && (
          <section className="streak-banner" aria-label="Oakland consecutive games with a made 3-pointer streak">
            <div className="streak-left">
              <div className="streak-eyebrow">
                <span className="streak-dot" aria-hidden="true" />
                <Flame size={13} />
                {payload.streak.active ? 'Active 3-Pointer Streak' : '3-Pointer Streak Ended'}
                {payload.streak.yearsActive !== null && ` · ${payload.streak.yearsActive} Years`}
              </div>
              <div className="streak-figure">
                <span className="streak-number">{payload.streak.count.toLocaleString()}</span>
                <span className="streak-caption">Consecutive Games With a Made 3-Pointer</span>
              </div>
              <div className="streak-context">
                Last 0-3PT game: <strong>Jan. 30, 1988 vs. {payload.streak.lastZeroOpponent}</strong> ·{' '}
                {payload.streak.ncaaRankNote}
              </div>
            </div>

            {payload.streak.latestGameOpponent && (
              <div className="streak-right">
                <button
                  type="button"
                  className="streak-latest-btn"
                  onClick={() => {
                    const latest = payload.games.find(
                      (g) => g.gameDate === payload.streak!.asOfDate && g.gameId === payload.streak!.latestGameId,
                    );
                    if (latest) setSelectedGame(latest);
                  }}
                >
                  <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#f2d57e', fontWeight: 700 }}>
                    Latest Extension · Game #{payload.streak.count.toLocaleString()}
                  </div>
                  <div style={{ fontSize: 13.5, fontWeight: 700, marginTop: 2 }}>
                    <span className="mono">{payload.streak.asOfDate}</span>{' '}
                    {payload.streak.latestGameLocation === 'Away' ? 'at' : 'vs.'}{' '}
                    {payload.streak.latestGameOpponent} ({payload.streak.latestGame3pm}–{payload.streak.latestGame3pa} 3PT)
                  </div>
                  {payload.streak.latestGameFirst3Player && (
                    <div style={{ fontSize: 12, color: '#cbd5e1', marginTop: 2 }}>
                      1st 3PT: <strong>{payload.streak.latestGameFirst3Player}</strong> ·{' '}
                      <span className="mono">
                        {formatPeriodShort(payload.streak.latestGameFirst3Period)}{' '}
                        {payload.streak.latestGameFirst3Clock}
                      </span>
                    </div>
                  )}
                </button>
              </div>
            )}
          </section>
        )}

        {stats && payload && (
          <section className="summary-strip" aria-label="Archive headline records">
            <div
              className="summary-cell"
              style={{ cursor: 'pointer' }}
              onClick={() => stats.fastestGames[0] && setSelectedGame(stats.fastestGames[0])}
            >
              <div className="summary-label">Fastest 1st 3-Pointer</div>
              <div className="summary-value">
                <span className="mono" style={{ color: 'var(--accent-gold)' }}>
                  {stats.fastestSec}s
                </span>
                <span style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink-secondary)' }}>
                  1H 19:54 (Tie ×{stats.fastestGames.length})
                </span>
              </div>
              <div className="summary-sub">
                {stats.fastestGames.map((g) => `${g.first3ptPlayer} (${g.gameDate.slice(0, 4)})`).join(' · ')}
              </div>
            </div>

            <div
              className="summary-cell"
              style={{ cursor: 'pointer' }}
              onClick={() => stats.longestGames[0] && setSelectedGame(stats.longestGames[0])}
            >
              <div className="summary-label">Longest Wait for 1st 3PT</div>
              <div className="summary-value">
                <span className="mono" style={{ color: 'var(--accent-amber)' }}>
                  {formatElapsed(stats.longestSec)}
                </span>
                <span style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink-secondary)' }}>
                  2H {stats.longestGames[0]?.first3ptClock}
                </span>
              </div>
              <div className="summary-sub">
                {stats.longestGames[0]?.first3ptPlayer} · {stats.longestGames[0]?.gameDate} vs{' '}
                {stats.longestGames[0]?.opponent}
              </div>
            </div>

            <div
              className="summary-cell"
              style={{ cursor: 'pointer' }}
              onClick={() => stats.most3Games[0] && setSelectedGame(stats.most3Games[0])}
            >
              <div className="summary-label">Most 3s in a Game</div>
              <div className="summary-value">
                <span className="mono" style={{ color: 'var(--accent-gold)' }}>
                  {stats.max3pm}
                </span>
                <span style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink-secondary)' }}>
                  (Tie ×{stats.most3Games.length})
                </span>
              </div>
              <div className="summary-sub">
                {stats.most3Games.map((g) => `${g.opponent} (${g.gameDate.slice(0, 4)})`).join(' · ')}
              </div>
            </div>

            <div className="summary-cell" style={{ cursor: 'pointer' }} onClick={() => setTab('timing')}>
              <div className="summary-label">Median Time to 1st 3PT</div>
              <div className="summary-value">
                <span className="mono">{formatElapsed(stats.medianSec)}</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-secondary)' }}>
                  (Mean {formatElapsed(stats.meanSec)})
                </span>
              </div>
              <div className="summary-sub">
                <span className="mono">{stats.firstFivePct.toFixed(1)}%</span> within 5 min ·{' '}
                <span className="mono">{stats.total3pm.toLocaleString()}</span> total 3PM (
                {(stats.career3pPct * 100).toFixed(1)}%)
              </div>
            </div>
          </section>
        )}

        {loading && !payload && (
          <div className="panel">
            <div className="panel-body" style={{ color: 'var(--ink-muted)' }}>
              Loading Oakland University 3-point archive...
            </div>
          </div>
        )}

        {payload && (
          <>
            {tab === 'games' && (
              <GameLogTable
                games={payload.games}
                seasons={payload.seasons}
                seasonFilter={seasonFilter}
                onSeasonFilterChange={setSeasonFilter}
                onSelectGame={(g) => {
                  setSelectedPlayer(null);
                  setSelectedGame(g);
                }}
                onSelectPlayer={(p) => {
                  setSelectedGame(null);
                  setSelectedPlayer(p);
                }}
              />
            )}

            {tab === 'timing' && (
              <TimingHistogramView
                games={payload.games}
                onSelectGame={(g) => {
                  setSelectedPlayer(null);
                  setSelectedGame(g);
                }}
                onSelectPlayer={(p) => {
                  setSelectedGame(null);
                  setSelectedPlayer(p);
                }}
              />
            )}

            {tab === 'players' && (
              <PlayersView
                games={payload.games}
                onSelectPlayer={(p) => {
                  setSelectedGame(null);
                  setSelectedPlayer(p);
                }}
              />
            )}

            {tab === 'seasons' && (
              <SeasonsView
                games={payload.games}
                onSelectSeason={handleJumpToSeason}
                onSelectGame={(g) => {
                  setSelectedPlayer(null);
                  setSelectedGame(g);
                }}
              />
            )}
          </>
        )}
      </main>

      <footer className="app-footer">
        <div className="app-footer-inner">
          <span>GrizzThree · Oakland University Men&apos;s Basketball 3-Point Analytics</span>
          <span>
            Source: goldengrizzlies.com official box scores &amp; play-by-play · Generated via{' '}
            <code className="mono">python main.py run</code>
          </span>
        </div>
      </footer>

      <GameDossierDrawer
        game={selectedGame}
        onClose={() => setSelectedGame(null)}
        onSelectPlayer={(p) => {
          setSelectedGame(null);
          setSelectedPlayer(p);
        }}
      />

      <PlayerDossierDrawer
        playerName={selectedPlayer}
        games={payload?.games ?? []}
        onClose={() => setSelectedPlayer(null)}
        onSelectGame={(g) => {
          setSelectedPlayer(null);
          setSelectedGame(g);
        }}
      />
    </div>
  );
}
