"""Resilient scraper for Oakland University Men's Basketball schedules and box scores."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ou_bball.config import (
    DEFAULT_BUILD_DIR,
    SCHEDULE_URL_TEMPLATE,
    USER_AGENT,
    build_season_list,
)
from ou_bball.parsers.legacy import parse_legacy_game
from ou_bball.parsers.schedule import (
    ScheduledGame,
    SeasonSchedule,
    build_candidate_boxscore_urls,
    inspect_recap_html,
    parse_schedule_html,
)
from ou_bball.parsers.sidearm import ParsedGameContent, parse_sidearm_game

logger = logging.getLogger(__name__)

# Only used for the legacy FTP host whose hostname contains an underscore.
_INSECURE_SSL_HOSTS = frozenset({"oaklandu_ftp.sidearmsports.com"})
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class SeasonScrapeSummary:
    season: str
    scheduled_completed: int = 0
    exhibitions_skipped: int = 0
    cached_skipped: int = 0
    scraped_ok: int = 0
    no_boxscore_link: int = 0
    parse_failed: int = 0
    official_record: Optional[str] = None
    regular_record: Optional[str] = None
    exhibition_games: list[str] = None

    def __post_init__(self) -> None:
        if self.exhibition_games is None:
            self.exhibition_games = []


def create_session() -> requests.Session:
    """Create a requests.Session configured with retries and connection pooling."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=16)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_url(session: requests.Session, url: str, timeout: int = 25) -> Optional[str]:
    """Fetch URL HTML, returning None on HTTP 404 or network failure."""
    host = urlparse(url).hostname or ""
    verify = host not in _INSECURE_SSL_HOSTS
    try:
        resp = session.get(url, timeout=timeout, verify=verify)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        logger.debug("Fetch failed for %s: %s", url, exc)
        return None


def _is_soft_404(html: str) -> bool:
    low = html.lower()
    if "<title>" in low and "page not found" in low[:5000]:
        return True
    if "404 - page not found" in low[:10000]:
        return True
    return False


def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or "Unknown"


def game_cache_path(build_dir: str, game: ScheduledGame) -> str:
    safe_opp = _sanitize_filename(game.opponent)
    safe_id = _sanitize_filename(game.game_id)
    season_dir = os.path.join(build_dir, game.season)
    return os.path.join(season_dir, f"{game.game_date}_{safe_id}_{safe_opp}.json")


def _parse_html_auto(
    html: str,
    location: str,
    opponent_name: str,
) -> Optional[ParsedGameContent]:
    """Try modern Sidearm parser first, falling back to legacy StatCrew parser."""
    parsed = parse_sidearm_game(html, location=location, opponent_name=opponent_name)
    if parsed and (len(parsed.plays) >= 10 or parsed.oakland_3pm is not None):
        return parsed

    legacy = parse_legacy_game(html, location=location, opponent_name=opponent_name)
    if legacy and (len(legacy.plays) >= 10 or legacy.oakland_3pm is not None):
        return legacy

    return None


def _is_early_november(game_date: str) -> bool:
    """Return True for Nov 1-12 games where unlisted exhibitions sometimes appear."""
    m = re.fullmatch(r"\d{4}-(\d{2})-(\d{2})", game_date)
    if not m:
        return False
    return int(m.group(1)) == 11 and int(m.group(2)) <= 12


def _scrape_single_game(
    session: requests.Session,
    game: ScheduledGame,
    build_dir: str,
    force: bool = False,
    skip_exhibitions: bool = True,
    delay_sec: float = 0.15,
) -> tuple[str, ScheduledGame]:
    """Scrape and cache a single game. Returns (status, game)."""
    cache_file = game_cache_path(build_dir, game)
    if skip_exhibitions and game.is_exhibition:
        if os.path.exists(cache_file):
            os.remove(cache_file)
        return "exhibition", game
    if not force and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict) and existing.get("schema_version") == 2:
                return "cached", game
        except (OSError, json.JSONDecodeError):
            pass

    boxscore_url = game.boxscore_url

    # Fetch recap page if we need a boxscore link OR want to verify an early-Nov game isn't an exhibition.
    need_recap = (not boxscore_url or _is_early_november(game.game_date)) and bool(game.recap_url)
    if need_recap and game.recap_url:
        recap_html = fetch_url(session, game.recap_url)
        if recap_html and not _is_soft_404(recap_html):
            recap_bs_url, is_exh_recap = inspect_recap_html(recap_html)
            if is_exh_recap:
                game.is_exhibition = True
                game.exhibition_reasons.append("recap_headline")
                if skip_exhibitions:
                    if os.path.exists(cache_file):
                        os.remove(cache_file)
                    return "exhibition", game
            if not boxscore_url and recap_bs_url:
                boxscore_url = recap_bs_url
                game.boxscore_url = recap_bs_url

    if not boxscore_url:
        return "no_link", game

    candidate_urls = build_candidate_boxscore_urls(boxscore_url, game.season)
    best_parsed: Optional[ParsedGameContent] = None
    best_source_url: Optional[str] = None

    for cand_url in candidate_urls:
        html = fetch_url(session, cand_url)
        if not html or _is_soft_404(html):
            continue

        parsed = _parse_html_auto(html, location=game.location, opponent_name=game.opponent)
        if not parsed:
            continue

        # Prefer a parse that has full play-by-play over boxscore-only
        if best_parsed is None or len(parsed.plays) > len(best_parsed.plays):
            best_parsed = parsed
            best_source_url = cand_url

        if len(parsed.plays) >= 10:
            break

    if delay_sec > 0:
        time.sleep(delay_sec)

    if not best_parsed:
        return "parse_failed", game

    payload = {
        "schema_version": 2,
        "season": game.season,
        "game_date": game.game_date,
        "game_id": game.game_id,
        "opponent_raw": game.opponent_raw,
        "opponent": game.opponent,
        "opponent_rank": game.opponent_rank,
        "location": game.location,
        "is_exhibition": game.is_exhibition,
        "result": game.result,
        "oakland_score": game.oakland_score if game.oakland_score is not None else best_parsed.oakland_score,
        "opponent_score": game.opponent_score if game.opponent_score is not None else best_parsed.opponent_score,
        "boxscore_url": game.boxscore_url,
        "source_url": best_source_url,
        "parser": best_parsed.parser,
        "pbp_available": len(best_parsed.plays) >= 10,
        "oakland_team_label": best_parsed.oakland_team_label,
        "opponent_team_label": best_parsed.opponent_team_label,
        "oakland_roster": best_parsed.oakland_roster,
        "boxscore_3pt": {
            "oakland_3pm": best_parsed.oakland_3pm,
            "oakland_3pa": best_parsed.oakland_3pa,
            "opponent_3pm": best_parsed.opponent_3pm,
            "opponent_3pa": best_parsed.opponent_3pa,
        },
        "plays": best_parsed.plays,
    }

    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return "ok", game


def scrape_season(
    season: str,
    build_dir: str = DEFAULT_BUILD_DIR,
    force: bool = False,
    skip_exhibitions: bool = True,
    workers: int = 4,
    session: Optional[requests.Session] = None,
) -> SeasonScrapeSummary:
    """Scrape all available completed games for a single season."""
    own_session = session is None
    if session is None:
        session = create_session()

    summary = SeasonScrapeSummary(season=season)
    url = SCHEDULE_URL_TEMPLATE.format(season=season)

    try:
        html = fetch_url(session, url, timeout=30)
        if not html or _is_soft_404(html):
            logger.warning("Season %s: schedule unavailable (%s)", season, url)
            return summary

        schedule: SeasonSchedule = parse_schedule_html(html, season=season, url=url)
        if schedule.official_wins is not None and schedule.official_losses is not None:
            summary.official_record = f"{schedule.official_wins}-{schedule.official_losses}"

        completed_games = [g for g in schedule.games if g.completed or g.boxscore_url]
        summary.scheduled_completed = len(completed_games)

        if not completed_games:
            logger.info("Season %s: 0 completed games found.", season)
            return summary

        # Process games concurrently with bounded workers
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = [
                executor.submit(
                    _scrape_single_game,
                    session,
                    game,
                    build_dir,
                    force,
                    skip_exhibitions,
                )
                for game in completed_games
            ]
            for fut in as_completed(futures):
                status, game = fut.result()
                if status == "exhibition":
                    summary.exhibitions_skipped += 1
                    summary.exhibition_games.append(f"{game.game_date} {game.opponent}")
                elif status == "cached":
                    summary.cached_skipped += 1
                elif status == "ok":
                    summary.scraped_ok += 1
                elif status == "no_link":
                    summary.no_boxscore_link += 1
                elif status == "parse_failed":
                    summary.parse_failed += 1
                    logger.warning("  Failed to parse: %s %s (%s)", game.game_date, game.opponent, game.boxscore_url)

        # Compute non-exhibition W-L record for easy verification against Sidearm official record
        reg_games = [g for g in completed_games if not g.is_exhibition and g.result in ("W", "L")]
        w = sum(1 for g in reg_games if g.result == "W")
        l = sum(1 for g in reg_games if g.result == "L")
        if reg_games:
            summary.regular_record = f"{w}-{l}"

        logger.info(
            "Season %s: %d scraped, %d cached, %d exh skipped, %d no-link, %d failed | record=%s (official=%s)",
            season,
            summary.scraped_ok,
            summary.cached_skipped,
            summary.exhibitions_skipped,
            summary.no_boxscore_link,
            summary.parse_failed,
            summary.regular_record or "n/a",
            summary.official_record or "n/a",
        )
        return summary
    finally:
        if own_session:
            session.close()


def scrape_all_seasons(
    seasons: Optional[list[str]] = None,
    build_dir: str = DEFAULT_BUILD_DIR,
    force: bool = False,
    skip_exhibitions: bool = True,
    workers: int = 4,
) -> list[SeasonScrapeSummary]:
    """Scrape all specified seasons (defaults to all available seasons 2008-09 through 2026-27)."""
    target_seasons = seasons if seasons else build_season_list()
    session = create_session()
    summaries: list[SeasonScrapeSummary] = []
    try:
        for season in target_seasons:
            summaries.append(
                scrape_season(
                    season=season,
                    build_dir=build_dir,
                    force=force,
                    skip_exhibitions=skip_exhibitions,
                    workers=workers,
                    session=session,
                )
            )
    finally:
        session.close()
    return summaries
