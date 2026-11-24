"""Parser for Sidearm Sports schedule pages and recap boxscore link discovery."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ou_bball.config import BASE_URL, LEGACY_FTP_BASE
from ou_bball.normalize import extract_opponent_rank, normalize_opponent_name

_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

# Patterns that unambiguously mark an exhibition game in schedule cards, URLs, or recap titles.
_EXHIBITION_RE = re.compile(
    r"(?:\(exh\.?\)|\bexhibition\b|\bexh\b|in[-_]exhibition|exhibition[-_](?:game|play|win|bout)|/exh[-_0-9])",
    re.IGNORECASE,
)

# URLs to reject when hunting for an individual game box score inside a recap article.
_NON_BOXSCORE_URL_RE = re.compile(
    r"(?:teamstat|season[-_]?stat|cumestat|confstat|leader|roster|schedule|\.pdf$)",
    re.IGNORECASE,
)

# Boxscore URL patterns:
# 1. Modern Sidearm: /sports/mens-basketball/stats/2025-26/michigan/boxscore/13043
# 2. Legacy HTML:    /sports/m-baskbl/stats/2011-2012/uvu1125.html (or .htm)
# 3. Migrated ASPX:  /sports/2018/5/31/_m_baskbl_stats_2016_2017_gm1bgsu_html.aspx
_BOXSCORE_URL_RE = re.compile(
    r"(?:/boxscore/\d+|/stats/[^\"'\s]*\.html?(?:#.*)?$|_m_baskbl_stats_\d{4}_\d{4}_[a-z0-9_-]+_html?\.aspx)",
    re.IGNORECASE,
)


@dataclass
class ScheduledGame:
    season: str
    game_date: str
    game_id: str
    opponent_raw: str
    opponent: str
    opponent_rank: Optional[int]
    location: str  # "Home", "Away", "Neutral", "Unknown"
    is_exhibition: bool
    result: Optional[str] = None
    oakland_score: Optional[int] = None
    opponent_score: Optional[int] = None
    boxscore_url: Optional[str] = None
    recap_url: Optional[str] = None
    completed: bool = False
    exhibition_reasons: list[str] = field(default_factory=list)


@dataclass
class SeasonSchedule:
    season: str
    url: str
    official_wins: Optional[int] = None
    official_losses: Optional[int] = None
    games: list[ScheduledGame] = field(default_factory=list)


def parse_season_years(season: str) -> tuple[int, int]:
    """Return (start_year, end_year) from 'YYYY-YY' (e.g. '2025-26' -> (2025, 2026))."""
    start_year = int(season.split("-")[0])
    return start_year, start_year + 1


def _parse_game_date(date_text: str, start_year: int, end_year: int) -> tuple[str, Optional[int], Optional[int]]:
    """Parse 'Nov 10 (Fri)' into ('2025-11-10', 11, 10)."""
    clean = re.sub(r"\(.*?\)", "", date_text).strip()
    m = re.match(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})\b", clean)
    if not m:
        return "0000-00-00", None, None

    month_num = _MONTHS.get(m.group(1).capitalize())
    day = int(m.group(2))
    if not month_num:
        return "0000-00-00", None, None

    year = start_year if month_num >= 8 else end_year
    return f"{year}-{month_num:02d}-{day:02d}", month_num, day


def _parse_result(game_li) -> tuple[Optional[str], Optional[int], Optional[int]]:
    """Extract (W/L, oakland_score, opponent_score) from Sidearm result block."""
    result_div = game_li.find("div", class_="sidearm-schedule-game-result")
    if not result_div:
        return None, None, None

    text = re.sub(r"\s+", " ", result_div.get_text(" ", strip=True))
    m = re.search(r"\b([WL])\b[,\s]*(\d+)\s*-\s*(\d+)", text)
    if not m:
        return None, None, None
    return m.group(1), int(m.group(2)), int(m.group(3))


def _extract_official_record(soup: BeautifulSoup) -> tuple[Optional[int], Optional[int]]:
    """Extract official overall (wins, losses) from the Sidearm season record bar."""
    rec = soup.find(class_=re.compile(r"schedule-record", re.IGNORECASE))
    if not rec:
        return None, None
    txt = re.sub(r"\s+", " ", rec.get_text(" ", strip=True))
    m = re.search(r"Overall\s+(\d+)\s*-\s*(\d+)", txt, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def _is_valid_boxscore_href(href: Optional[str]) -> bool:
    if not href:
        return False
    low = href.lower().strip()
    if low.endswith(".pdf") or ".pdf?" in low:
        return False
    if _NON_BOXSCORE_URL_RE.search(low):
        return False
    return bool(_BOXSCORE_URL_RE.search(low))


def extract_game_id(game_li, boxscore_url: Optional[str], game_date: str, opponent: str) -> str:
    """Return a clean, stable game identifier (no underscores that break metadata)."""
    # Prefer modern boxscore numeric ID
    if boxscore_url:
        m = re.search(r"/boxscore/(\d+)", boxscore_url)
        if m:
            return m.group(1)

    # Prefer Sidearm data-game-id when present
    data_gid = game_li.get("data-game-id")
    if data_gid and str(data_gid).strip().isdigit():
        return str(data_gid).strip()

    # Fallback to legacy filename stem
    if boxscore_url:
        stem = os.path.splitext(os.path.basename(boxscore_url.split("#")[0].split("?")[0]))[0]
        stem = re.sub(r"[^A-Za-z0-9\-]", "", stem)
        if stem:
            return stem

    slug = re.sub(r"[^A-Za-z0-9]", "", opponent)[:12] or "game"
    return f"{game_date.replace('-', '')}-{slug}"


def parse_schedule_html(html: str, season: str, url: str) -> SeasonSchedule:
    """Parse a Sidearm season schedule page into structured ScheduledGame entries."""
    soup = BeautifulSoup(html, "lxml")
    start_year, end_year = parse_season_years(season)
    wins, losses = _extract_official_record(soup)

    schedule = SeasonSchedule(
        season=season,
        url=url,
        official_wins=wins,
        official_losses=losses,
    )

    for game_li in soup.find_all("li", class_="sidearm-schedule-game"):
        classes = " ".join(game_li.get("class", []))
        completed = "sidearm-schedule-game-completed" in classes

        if "sidearm-schedule-home-game" in classes:
            location = "Home"
        elif "sidearm-schedule-away-game" in classes:
            location = "Away"
        elif "sidearm-schedule-neutral-game" in classes:
            location = "Neutral"
        else:
            location = "Unknown"

        date_div = game_li.find("div", class_="sidearm-schedule-game-opponent-date")
        date_text = date_div.get_text(" ", strip=True) if date_div else ""
        game_date, month_num, _ = _parse_game_date(date_text, start_year, end_year)

        opp_el = game_li.find(["div", "span"], class_="sidearm-schedule-game-opponent-name")
        opponent_raw = opp_el.get_text(" ", strip=True) if opp_el else "Unknown"
        opponent = normalize_opponent_name(opponent_raw)
        opponent_rank = extract_opponent_rank(opponent_raw)

        result, oak_score, opp_score = _parse_result(game_li)
        if result is not None:
            completed = True

        # Find boxscore link (skip teamstat/pdf)
        boxscore_url: Optional[str] = None
        for a in game_li.find_all("a", href=True):
            href = a.get("href", "").strip()
            if _is_valid_boxscore_href(href):
                boxscore_url = urljoin(BASE_URL, href)
                break

        # Find recap link
        recap_url: Optional[str] = None
        recap_li = game_li.find("li", class_="sidearm-schedule-game-links-recap")
        if recap_li and recap_li.find("a", href=True):
            recap_url = urljoin(BASE_URL, recap_li.find("a", href=True)["href"].strip())
        else:
            for a in game_li.find_all("a", href=True):
                if re.fullmatch(r"recap", a.get_text(strip=True), re.IGNORECASE):
                    recap_url = urljoin(BASE_URL, a["href"].strip())
                    break

        # Exhibition detection from schedule card, date, URLs
        reasons: list[str] = []
        if month_num == 10:
            reasons.append("october_game")

        card_text = re.sub(r"\s+", " ", game_li.get_text(" ", strip=True))
        if _EXHIBITION_RE.search(card_text):
            reasons.append("schedule_card_text")
        if boxscore_url and _EXHIBITION_RE.search(boxscore_url):
            reasons.append("boxscore_url")
        if recap_url and _EXHIBITION_RE.search(recap_url):
            reasons.append("recap_url")

        game_id = extract_game_id(game_li, boxscore_url, game_date, opponent)

        schedule.games.append(
            ScheduledGame(
                season=season,
                game_date=game_date,
                game_id=game_id,
                opponent_raw=opponent_raw,
                opponent=opponent,
                opponent_rank=opponent_rank,
                location=location,
                is_exhibition=bool(reasons),
                result=result,
                oakland_score=oak_score,
                opponent_score=opp_score,
                boxscore_url=boxscore_url,
                recap_url=recap_url,
                completed=completed,
                exhibition_reasons=reasons,
            )
        )

    # In NCAA basketball, all preseason exhibition games precede the regular-season opener.
    # If an early-season (Oct/Nov) game is confirmed as an exhibition, any earlier game in
    # the same season is also an exhibition (catches unlabeled games sandwiched before an exhibition).
    last_early_exh_idx = -1
    for idx, g in enumerate(schedule.games):
        if g.is_exhibition and re.match(r"^\d{4}-(?:10|11)-", g.game_date):
            last_early_exh_idx = idx
    for idx in range(last_early_exh_idx):
        if not schedule.games[idx].is_exhibition:
            schedule.games[idx].is_exhibition = True
            schedule.games[idx].exhibition_reasons.append("precedes_exhibition")

    return schedule


def inspect_recap_html(recap_html: str) -> tuple[Optional[str], bool]:
    """Inspect a recap page to find a boxscore link and check if it's an exhibition game.

    Returns:
        (boxscore_url_or_none, is_exhibition_in_recap)
    """
    soup = BeautifulSoup(recap_html, "lxml")

    # Check article title / headline and opening lead paragraph for exhibition indicator
    is_exh = False
    for el in (soup.find("h1"), soup.find("title")):
        if el and _EXHIBITION_RE.search(el.get_text(" ", strip=True)):
            is_exh = True
            break

    # Search inside article body first to avoid sidebar/nav links
    article = soup.find("article") or soup.find("div", class_=re.compile(r"story|article", re.IGNORECASE)) or soup

    if not is_exh:
        lead_text = " ".join(p.get_text(" ", strip=True) for p in article.find_all("p")[:3])
        if re.search(r"\bexhibition\b", lead_text, re.IGNORECASE):
            is_exh = True

    # First pass: links whose text explicitly mentions "Box Score" and have a valid boxscore href
    candidates: list[tuple[int, str]] = []
    for a in article.find_all("a", href=True):
        href = a.get("href", "").strip()
        text = a.get_text(" ", strip=True)
        if not _is_valid_boxscore_href(href):
            continue
        full_url = urljoin(BASE_URL, href)
        priority = 0 if re.search(r"box\s*score", text, re.IGNORECASE) else 1
        candidates.append((priority, full_url))

    if candidates:
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1], is_exh

    return None, is_exh


def build_candidate_boxscore_urls(url: str, season: str) -> list[str]:
    """Build ordered fallback URLs for fetching a boxscore (handles legacy & migrated ASPX links)."""
    start_year, end_year = parse_season_years(season)
    ftp_season = f"{start_year}-{end_year}"

    candidates: list[str] = []

    def _add(u: str) -> None:
        if u and u not in candidates:
            candidates.append(u)

    # Check if this is a migrated Sidearm ASPX URL like:
    # /sports/2018/5/31/_m_baskbl_stats_2016_2017_gm1bgsu_html.aspx
    migrated = re.search(
        r"_m_baskbl_stats_(\d{4})_(\d{4})_([a-z0-9_-]+)_html?\.aspx",
        url,
        re.IGNORECASE,
    )
    if migrated:
        mig_season = f"{migrated.group(1)}-{migrated.group(2)}"
        stem = migrated.group(3)
        # Prefer FTP .htm first since migrated .aspx links typically 404 on goldengrizzlies.com
        _add(f"{LEGACY_FTP_BASE}/{mig_season}/{stem}.htm")
        _add(f"{LEGACY_FTP_BASE}/{mig_season}/{stem}.html")
        _add(url)
        return candidates

    # Standard URL first
    clean_url = url.split("#")[0]
    _add(clean_url)

    # If it's a legacy HTML stats URL, try .htm and Sidearm FTP fallbacks
    if re.search(r"\.html?$", clean_url, re.IGNORECASE):
        if clean_url.lower().endswith(".html"):
            _add(re.sub(r"\.html$", ".htm", clean_url, flags=re.IGNORECASE))
        else:
            _add(re.sub(r"\.htm$", ".html", clean_url, flags=re.IGNORECASE))

        stem = os.path.splitext(os.path.basename(clean_url))[0]
        if stem:
            _add(f"{LEGACY_FTP_BASE}/{ftp_season}/{stem}.htm")
            _add(f"{LEGACY_FTP_BASE}/{ftp_season}/{stem}.html")

    return candidates
