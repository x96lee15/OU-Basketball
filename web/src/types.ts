export interface ThreePtShotEvent {
  period: number;
  clock: string;
  side: 'oakland' | 'opponent';
  player: string;
  made: boolean;
}

export interface GameRecord {
  season: string;
  gameDate: string;
  gameId: string;
  location: 'Home' | 'Away' | 'Neutral' | 'Unknown';
  opponent: string;
  opponentRank: number | null;
  result: 'W' | 'L' | null;
  oaklandScore: number | null;
  opponentScore: number | null;
  oakland3pm: number | null;
  oakland3pa: number | null;
  oakland3pPct: number | null;
  opponent3pm: number | null;
  opponent3pa: number | null;
  first3ptPlayer: string | null;
  first3ptPeriod: string | null;
  first3ptClock: string | null;
  first3ptElapsedSec: number | null;
  opponentFirst3ptPlayer: string | null;
  opponentFirst3ptPeriod: string | null;
  opponentFirst3ptClock: string | null;
  pbpAvailable: boolean;
  boxscoreUrl: string | null;
  threePtEvents: ThreePtShotEvent[];
}

export interface DatasetPayload {
  generatedAt: string;
  asOfDate: string;
  totalGames: number;
  pbpGames: number;
  seasons: string[];
  games: GameRecord[];
}

export interface MinuteBin {
  min: number;
  count: number;
  wins: number;
  losses: number;
  pct: number;
  cumPct: number;
  games: GameRecord[];
}

export interface TimingBucket {
  label: string;
  sub: string;
  games: number;
  wins: number;
  losses: number;
  winPct: number;
  sharePct: number;
}

export interface PlayerSummary {
  player: string;
  first3Count: number;
  wins: number;
  losses: number;
  winPct: number;
  avgElapsedSec: number;
  fastestSec: number;
  latestSec: number;
  seasons: string[];
  games: GameRecord[];
}

export interface SeasonSummary {
  season: string;
  games: number;
  wins: number;
  losses: number;
  total3pm: number;
  total3pa: number;
  pct3p: number;
  avg3pm: number;
  avg3pa: number;
  max3pm: number;
  min3pm: number;
  medianFirst3Sec: number | null;
  topFirst3Player: string;
  topFirst3Count: number;
}
