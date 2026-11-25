import type {
  GameRecord,
  MinuteBin,
  PlayerGameStreak,
  PlayerSummary,
  SeasonSummary,
  TimingBucket,
} from './types';

export function formatElapsed(sec: number | null): string {
  if (sec === null || Number.isNaN(sec)) return '—';
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export function formatPeriodLabel(period: string | number | null): string {
  if (period === null || period === '') return '—';
  const s = String(period);
  if (s === '1') return '1st Half';
  if (s === '2') return '2nd Half';
  if (s === '3') return 'OT';
  if (/^\d+$/.test(s) && Number(s) > 3) return `${Number(s) - 2}OT`;
  return s;
}

export function formatPeriodShort(period: string | number | null): string {
  if (period === null || period === '') return '—';
  const s = String(period);
  if (s === '1') return '1H';
  if (s === '2') return '2H';
  if (s === '3') return 'OT';
  if (/^\d+$/.test(s) && Number(s) > 3) return `${Number(s) - 2}OT`;
  return s;
}

export function formatClockRange(min: number): string {
  if (min < 20) {
    return `1H ${20 - min}:00–${19 - min}:01`;
  }
  return `2H ${40 - min}:00–${39 - min}:01`;
}

export function computeHeadlineStats(games: GameRecord[]) {
  const pbpGames = games.filter((g) => g.pbpAvailable && g.first3ptElapsedSec !== null);
  const byFastest = [...pbpGames].sort(
    (a, b) => (a.first3ptElapsedSec! - b.first3ptElapsedSec!) || a.gameDate.localeCompare(b.gameDate),
  );
  const fastestSec = byFastest[0]?.first3ptElapsedSec ?? null;
  const fastestGames = fastestSec !== null ? byFastest.filter((g) => g.first3ptElapsedSec === fastestSec) : [];

  const byLongest = [...pbpGames].sort(
    (a, b) => (b.first3ptElapsedSec! - a.first3ptElapsedSec!) || a.gameDate.localeCompare(b.gameDate),
  );
  const longestSec = byLongest[0]?.first3ptElapsedSec ?? null;
  const longestGames = longestSec !== null ? byLongest.filter((g) => g.first3ptElapsedSec === longestSec) : [];

  const with3pm = games.filter((g) => g.oakland3pm !== null);
  const byMost3 = [...with3pm].sort(
    (a, b) => (b.oakland3pm! - a.oakland3pm!) || ((b.oakland3pPct ?? 0) - (a.oakland3pPct ?? 0)) || a.gameDate.localeCompare(b.gameDate),
  );
  const max3pm = byMost3[0]?.oakland3pm ?? null;
  const most3Games = max3pm !== null ? byMost3.filter((g) => g.oakland3pm === max3pm) : [];

  const oneThreeGames = games
    .filter((g) => g.oakland3pm === 1)
    .sort((a, b) => a.gameDate.localeCompare(b.gameDate));

  const elapsedList = pbpGames.map((g) => g.first3ptElapsedSec!).sort((a, b) => a - b);
  const n = elapsedList.length;
  const medianSec = n > 0 ? elapsedList[Math.floor(n / 2)] : null;
  const meanSec = n > 0 ? Math.round(elapsedList.reduce((acc, v) => acc + v, 0) / n) : null;
  const p90Sec = n > 0 ? elapsedList[Math.min(n - 1, Math.floor(n * 0.9))] : null;
  const firstFiveCount = pbpGames.filter((g) => g.first3ptElapsedSec! < 300).length;
  const firstHalfCount = pbpGames.filter((g) => g.first3ptPeriod === '1').length;

  const total3pm = with3pm.reduce((s, g) => s + (g.oakland3pm ?? 0), 0);
  const total3pa = with3pm.reduce((s, g) => s + (g.oakland3pa ?? 0), 0);

  return {
    totalGames: games.length,
    pbpCount: n,
    fastestSec,
    fastestGames,
    fastestTop10: byFastest.slice(0, 10),
    longestSec,
    longestGames,
    longestTop10: byLongest.slice(0, 10),
    max3pm,
    most3Games,
    most3Top10: byMost3.slice(0, 10),
    oneThreeGames,
    medianSec,
    meanSec,
    p90Sec,
    firstFivePct: n > 0 ? (firstFiveCount / n) * 100 : 0,
    firstHalfPct: n > 0 ? (firstHalfCount / n) * 100 : 0,
    total3pm,
    total3pa,
    career3pPct: total3pa > 0 ? total3pm / total3pa : 0,
  };
}

export function computeHistogramBins(games: GameRecord[]): MinuteBin[] {
  const pbp = games.filter((g) => g.pbpAvailable && g.first3ptElapsedSec !== null);
  const map = new Map<number, GameRecord[]>();

  let maxMin = 20;
  for (const g of pbp) {
    const sec = g.first3ptElapsedSec!;
    let m = Math.floor(sec / 60);
    if (sec === 1200 && g.first3ptPeriod === '1') m = 19;
    if (m > maxMin) maxMin = m;
    const arr = map.get(m) ?? [];
    arr.push(g);
    map.set(m, arr);
  }

  const total = pbp.length || 1;
  let running = 0;
  const bins: MinuteBin[] = [];

  for (let m = 0; m <= maxMin; m++) {
    const list = (map.get(m) ?? []).sort(
      (a, b) => (a.first3ptElapsedSec! - b.first3ptElapsedSec!) || a.gameDate.localeCompare(b.gameDate),
    );
    const wins = list.filter((g) => g.result === 'W').length;
    const losses = list.filter((g) => g.result === 'L').length;
    running += list.length;
    bins.push({
      min: m,
      count: list.length,
      wins,
      losses,
      pct: (list.length / total) * 100,
      cumPct: (running / total) * 100,
      games: list,
    });
  }
  return bins;
}

export function computeTimingBuckets(games: GameRecord[]): TimingBucket[] {
  const pbp = games.filter((g) => g.pbpAvailable && g.first3ptElapsedSec !== null);
  const total = pbp.length || 1;
  const defs: Array<{ label: string; sub: string; test: (g: GameRecord) => boolean }> = [
    { label: '0–2 min', sub: '1H 20:00–18:01', test: (g) => g.first3ptElapsedSec! < 120 },
    { label: '2–5 min', sub: '1H 18:00–15:01', test: (g) => g.first3ptElapsedSec! >= 120 && g.first3ptElapsedSec! < 300 },
    { label: '5–10 min', sub: '1H 15:00–10:01', test: (g) => g.first3ptElapsedSec! >= 300 && g.first3ptElapsedSec! < 600 },
    { label: '10–20 min', sub: '1H 10:00–0:00', test: (g) => g.first3ptElapsedSec! >= 600 && g.first3ptPeriod === '1' },
    { label: '2nd Half', sub: '20:00+ elapsed', test: (g) => g.first3ptPeriod !== '1' },
  ];

  return defs.map((d) => {
    const list = pbp.filter(d.test);
    const wins = list.filter((g) => g.result === 'W').length;
    const losses = list.filter((g) => g.result === 'L').length;
    const decided = wins + losses;
    return {
      label: d.label,
      sub: d.sub,
      games: list.length,
      wins,
      losses,
      winPct: decided > 0 ? (wins / decided) * 100 : 0,
      sharePct: (list.length / total) * 100,
    };
  });
}

export function computePlayerSummaries(games: GameRecord[]): PlayerSummary[] {
  const map = new Map<string, GameRecord[]>();
  for (const g of games) {
    if (!g.pbpAvailable || !g.first3ptPlayer) continue;
    const list = map.get(g.first3ptPlayer) ?? [];
    list.push(g);
    map.set(g.first3ptPlayer, list);
  }

  const out: PlayerSummary[] = [];
  for (const [player, list] of map.entries()) {
    const sorted = [...list].sort((a, b) => b.gameDate.localeCompare(a.gameDate));
    const wins = list.filter((g) => g.result === 'W').length;
    const losses = list.filter((g) => g.result === 'L').length;
    const secs = list.map((g) => g.first3ptElapsedSec ?? 0);
    const avg = secs.reduce((a, b) => a + b, 0) / (secs.length || 1);
    const seasons = [...new Set(list.map((g) => g.season))].sort();
    out.push({
      player,
      first3Count: list.length,
      wins,
      losses,
      winPct: wins + losses > 0 ? (wins / (wins + losses)) * 100 : 0,
      avgElapsedSec: Math.round(avg),
      fastestSec: Math.min(...secs),
      latestSec: Math.max(...secs),
      seasons,
      games: sorted,
    });
  }

  return out.sort((a, b) => (b.first3Count - a.first3Count) || a.player.localeCompare(b.player));
}

export function computeSeasonSummaries(games: GameRecord[]): SeasonSummary[] {
  const bySeason = new Map<string, GameRecord[]>();
  for (const g of games) {
    const list = bySeason.get(g.season) ?? [];
    list.push(g);
    bySeason.set(g.season, list);
  }

  const out: SeasonSummary[] = [];
  for (const [season, list] of bySeason.entries()) {
    const wins = list.filter((g) => g.result === 'W').length;
    const losses = list.filter((g) => g.result === 'L').length;
    const with3 = list.filter((g) => g.oakland3pm !== null);
    const total3pm = with3.reduce((s, g) => s + (g.oakland3pm ?? 0), 0);
    const total3pa = with3.reduce((s, g) => s + (g.oakland3pa ?? 0), 0);
    const gp = with3.length || 1;
    const max3pm = with3.length ? Math.max(...with3.map((g) => g.oakland3pm!)) : 0;
    const min3pm = with3.length ? Math.min(...with3.map((g) => g.oakland3pm!)) : 0;

    const secs = list
      .filter((g) => g.pbpAvailable && g.first3ptElapsedSec !== null)
      .map((g) => g.first3ptElapsedSec!)
      .sort((a, b) => a - b);
    const medianFirst3Sec = secs.length ? secs[Math.floor(secs.length / 2)] : null;

    const counts = new Map<string, number>();
    for (const g of list) {
      if (g.first3ptPlayer) counts.set(g.first3ptPlayer, (counts.get(g.first3ptPlayer) ?? 0) + 1);
    }
    let topPlayer = '—';
    let topCount = 0;
    for (const [p, c] of counts.entries()) {
      if (c > topCount || (c === topCount && p < topPlayer)) {
        topPlayer = p;
        topCount = c;
      }
    }

    out.push({
      season,
      games: list.length,
      wins,
      losses,
      total3pm,
      total3pa,
      pct3p: total3pa > 0 ? total3pm / total3pa : 0,
      avg3pm: total3pm / gp,
      avg3pa: total3pa / gp,
      max3pm,
      min3pm,
      medianFirst3Sec,
      topFirst3Player: topPlayer,
      topFirst3Count: topCount,
    });
  }

  return out.sort((a, b) => b.season.localeCompare(a.season));
}

export function computeInGameStreaks(games: GameRecord[]) {
  const withPbp = games.filter((g) => g.pbpAvailable);

  const teamMakes = [...withPbp]
    .filter((g) => (g.maxConsecutive3pm ?? 0) > 0)
    .sort((a, b) => ((b.maxConsecutive3pm ?? 0) - (a.maxConsecutive3pm ?? 0)) || a.gameDate.localeCompare(b.gameDate));

  const teamMisses = [...withPbp]
    .filter((g) => (g.maxConsecutive3pMiss ?? 0) > 0)
    .sort((a, b) => ((b.maxConsecutive3pMiss ?? 0) - (a.maxConsecutive3pMiss ?? 0)) || a.gameDate.localeCompare(b.gameDate));

  const playerMakes: PlayerGameStreak[] = [];
  const playerMisses: PlayerGameStreak[] = [];

  for (const g of withPbp) {
    const oakShots = g.threePtEvents.filter((e) => e.side === 'oakland');
    const byPlayer = new Map<string, typeof oakShots>();
    for (const s of oakShots) {
      const arr = byPlayer.get(s.player) ?? [];
      arr.push(s);
      byPlayer.set(s.player, arr);
    }

    for (const [player, shots] of byPlayer.entries()) {
      let bestM = 0;
      let curM = 0;
      let bestX = 0;
      let curX = 0;
      let made = 0;
      for (const s of shots) {
        if (s.made) {
          made++;
          curM++;
          if (curM > bestM) bestM = curM;
          curX = 0;
        } else {
          curX++;
          if (curX > bestX) bestX = curX;
          curM = 0;
        }
      }
      if (bestM >= 4) {
        playerMakes.push({ player, streak: bestM, made, attempts: shots.length, game: g });
      }
      if (bestX >= 6) {
        playerMisses.push({ player, streak: bestX, made, attempts: shots.length, game: g });
      }
    }
  }

  playerMakes.sort((a, b) => (b.streak - a.streak) || a.game.gameDate.localeCompare(b.game.gameDate));
  playerMisses.sort((a, b) => (b.streak - a.streak) || a.game.gameDate.localeCompare(b.game.gameDate));

  return {
    teamMakes: teamMakes.slice(0, 15),
    teamMisses: teamMisses.slice(0, 15),
    playerMakes: playerMakes.slice(0, 15),
    playerMisses: playerMisses.slice(0, 15),
  };
}

export function downloadFile(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function gamesToCsv(games: GameRecord[]): string {
  const headers = [
    'Season',
    'Game_Date',
    'Location',
    'Opponent',
    'Opponent_Rank',
    'Result',
    'Oakland_Score',
    'Opponent_Score',
    'Oakland_3PM',
    'Oakland_3PA',
    'Oakland_3P_Pct',
    'Opponent_3PM',
    'Opponent_3PA',
    'First_3Pt_Player',
    'First_3Pt_Period',
    'First_3Pt_Clock',
    'First_3Pt_Elapsed_Sec',
    'Max_Consecutive_3PM',
    'Max_Consecutive_3PM_Window',
    'Max_Consecutive_3PMiss',
    'Max_Consecutive_3PMiss_Window',
  ];
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? '' : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [
    headers.join(','),
    ...games.map((g) =>
      [
        g.season,
        g.gameDate,
        g.location,
        g.opponent,
        g.opponentRank ?? '',
        g.result ?? '',
        g.oaklandScore ?? '',
        g.opponentScore ?? '',
        g.oakland3pm ?? '',
        g.oakland3pa ?? '',
        g.oakland3pPct !== null ? g.oakland3pPct.toFixed(3) : '',
        g.opponent3pm ?? '',
        g.opponent3pa ?? '',
        g.first3ptPlayer ?? '',
        g.first3ptPeriod ?? '',
        g.first3ptClock ?? '',
        g.first3ptElapsedSec ?? '',
        g.maxConsecutive3pm ?? '',
        g.maxConsecutive3pmWindow ?? '',
        g.maxConsecutive3pMiss ?? '',
        g.maxConsecutive3pMissWindow ?? '',
      ]
        .map(esc)
        .join(','),
    ),
  ];
  return lines.join('\n');
}
