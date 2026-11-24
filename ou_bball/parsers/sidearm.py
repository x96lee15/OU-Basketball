"""Parser for modern Sidearm Sports HTML box scores and play-by-play logs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from bs4 import BeautifulSoup

from ou_bball.normalize import (
    is_oakland_team_label,
    match_player_to_roster,
    normalize_player_name,
    player_in_roster,
)


@dataclass
class ParsedGameContent:
    parser: str
    plays: list[dict[str, Any]] = field(default_factory=list)
    oakland_team_label: Optional[str] = None
    opponent_team_label: Optional[str] = None
    oakland_roster: list[str] = field(default_factory=list)
    opponent_roster: list[str] = field(default_factory=list)
    oakland_3pm: Optional[int] = None
    oakland_3pa: Optional[int] = None
    opponent_3pm: Optional[int] = None
    opponent_3pa: Optional[int] = None
    oakland_score: Optional[int] = None
    opponent_score: Optional[int] = None


def _parse_score_cell(cell_text: str) -> Optional[int]:
    text = re.sub(r"\s*\(.*?\)", "", cell_text).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_made_att(text: str) -> tuple[Optional[int], Optional[int]]:
    m = re.search(r"(\d+)\s*-\s*(\d+)", text)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def _detect_shot_type(text: str) -> Optional[str]:
    t = text.lower()
    if "free throw" in t or re.search(r"\bft\b", t):
        return "ft"
    if "3ptr" in t or "3-pt" in t or "3 pt" in t or "3-point" in t or "three point" in t:
        return "3pt"
    if any(x in t for x in ("jumper", "layup", "dunk", "tipin", "tip-in", "hook", "paint", "2pt")):
        return "2pt"
    return None


def _classify_event(text: str) -> tuple[str, Optional[str]]:
    t = text.lower()
    if re.search(r"\bgood\b", t):
        return "shot", "made"
    if re.search(r"\bmiss(?:ed)?\b", t):
        return "shot", "missed"
    if "rebound" in t:
        return "rebound", None
    if "assist" in t:
        return "assist", None
    if "turnover" in t or "turnovr" in t:
        return "turnover", None
    if "steal" in t:
        return "steal", None
    if "block" in t:
        return "block", None
    if "foul" in t:
        return "foul", None
    if "sub" in t and ("in" in t or "out" in t):
        return "substitution", None
    if "timeout" in t:
        return "timeout", None
    return "other", None


def _extract_player_name(text: str) -> Optional[str]:
    if " by " not in text:
        return None
    suffix = text.split(" by ", 1)[1]
    suffix = re.split(r"[\(\[]", suffix, maxsplit=1)[0].strip()
    return normalize_player_name(suffix)


def _extract_sidearm_boxscore(soup: BeautifulSoup, opponent_name: Optional[str]) -> dict[str, Any]:
    """Extract team 3PT totals, scores, and rosters from modern Sidearm box score tables."""
    team_tables: list[dict[str, Any]] = []

    for table in soup.find_all("table"):
        # Skip play-by-play and period-only tables; focus on full-game player stats tables.
        classes = " ".join(table.get("class", []))
        if "play-by-play" in classes:
            continue

        # Must live inside full-game boxscore section (avoid 1st/2nd half split tables)
        parent_id = ""
        for p in table.parents:
            pid = p.get("id") or ""
            if pid:
                parent_id = pid.lower()
                if any(k in parent_id for k in ("period-", "half", "first-half", "second-half")):
                    break
        if any(k in parent_id for k in ("period-", "half", "first-half", "second-half")):
            continue

        thead = table.find("thead")
        if not thead:
            continue
        headers = [th.get_text(" ", strip=True).upper() for th in thead.find_all("th")]
        if "3PT" not in headers or "PTS" not in headers:
            continue

        # Find heading immediately preceding this table (e.g., "Oakland 78")
        heading = table.find_previous(["h3", "h4", "caption"])
        heading_text = heading.get_text(" ", strip=True) if heading else ""
        # Skip half-specific headings like "Oakland 38" inside half tabs if parent missed them
        if re.search(r"\b(?:1st|2nd)\s+half\b", heading_text, re.IGNORECASE):
            continue

        score_match = re.search(r"(\d+)\s*$", heading_text)
        team_score = int(score_match.group(1)) if score_match else None
        team_name = re.sub(r"\s*\d+\s*$", "", heading_text).strip()

        roster: list[str] = []
        has_ou_roster_links = False
        three_pm: Optional[int] = None
        three_pa: Optional[int] = None

        for tr in table.find_all("tr"):
            row_text = tr.get_text(" ", strip=True)
            if not row_text:
                continue

            # Check totals row
            if re.match(r"^Totals\b", row_text, re.IGNORECASE):
                td_3pt = tr.find("td", attrs={"data-label": "3PT"})
                if td_3pt:
                    three_pm, three_pa = _parse_made_att(td_3pt.get_text(" ", strip=True))
                else:
                    tds = tr.find_all("td")
                    idx_3pt = headers.index("3PT")
                    if idx_3pt < len(tds):
                        three_pm, three_pa = _parse_made_att(tds[idx_3pt].get_text(" ", strip=True))
                continue

            # Extract player name
            player_link = tr.find("a", class_="boxscore_player_link")
            if player_link:
                href = player_link.get("href", "")
                if "/sports/mens-basketball/roster/" in href:
                    has_ou_roster_links = True
                norm = normalize_player_name(player_link.get_text(" ", strip=True))
                if norm and norm != "Team":
                    roster.append(norm)
            else:
                # Opponent rows often lack <a> links; player name is in first/second td
                tds = tr.find_all("td")
                if len(tds) >= 3:
                    # Skip Team / Totals rows
                    cand = tds[1].get_text(" ", strip=True) if tds[0].get_text(strip=True).isdigit() else tds[0].get_text(" ", strip=True)
                    cand = re.sub(r"^\d+\s+", "", cand).strip()
                    if cand and not re.match(r"^(?:TM|TEAM|Totals?)\b", cand, re.IGNORECASE):
                        norm = normalize_player_name(cand)
                        if norm and norm != "Team":
                            roster.append(norm)

        if three_pm is not None:
            team_tables.append(
                {
                    "team_name": team_name,
                    "score": team_score,
                    "roster": roster,
                    "has_ou_roster_links": has_ou_roster_links,
                    "three_pm": three_pm,
                    "three_pa": three_pa,
                }
            )
        if len(team_tables) == 2:
            break

    if not team_tables:
        return {}

    oak_idx: Optional[int] = None
    for i, t in enumerate(team_tables):
        if t["has_ou_roster_links"] or is_oakland_team_label(t["team_name"], opponent_name):
            oak_idx = i
            break

    if oak_idx is None:
        return {}

    oak = team_tables[oak_idx]
    opp = team_tables[1 - oak_idx] if len(team_tables) == 2 else None

    return {
        "oakland_roster": oak["roster"],
        "opponent_roster": opp["roster"] if opp else [],
        "oakland_3pm": oak["three_pm"],
        "oakland_3pa": oak["three_pa"],
        "opponent_3pm": opp["three_pm"] if opp else None,
        "opponent_3pa": opp["three_pa"] if opp else None,
        "oakland_score": oak["score"],
        "opponent_score": opp["score"] if opp else None,
    }


def _resolve_oakland_side(
    away_label: str,
    home_label: str,
    oakland_roster: list[str],
    plays_preview: list[tuple[str, Optional[str]]],
    location: str,
    opponent_name: Optional[str],
) -> Optional[str]:
    """Determine whether 'away' or 'home' is Oakland in the Sidearm play-by-play table."""
    away_is_oak = is_oakland_team_label(away_label, opponent_name)
    home_is_oak = is_oakland_team_label(home_label, opponent_name)
    if away_is_oak and not home_is_oak:
        return "away"
    if home_is_oak and not away_is_oak:
        return "home"

    # Match players from PBP against Oakland's box score roster
    if oakland_roster:
        away_hits = sum(1 for side, pl in plays_preview if side == "away" and player_in_roster(pl, oakland_roster))
        home_hits = sum(1 for side, pl in plays_preview if side == "home" and player_in_roster(pl, oakland_roster))
        if away_hits > home_hits:
            return "away"
        if home_hits > away_hits:
            return "home"

    # Final fallback: schedule Home/Away designation
    if location == "Home":
        return "home"
    if location == "Away":
        return "away"
    return None


def parse_sidearm_game(
    html: str,
    location: str = "Unknown",
    opponent_name: Optional[str] = None,
) -> Optional[ParsedGameContent]:
    """Parse a modern Sidearm Sports box score & play-by-play HTML page."""
    soup = BeautifulSoup(html, "lxml")

    box = _extract_sidearm_boxscore(soup, opponent_name)
    periods = soup.find_all("div", id=re.compile(r"^period-\d+$"))

    if not periods and not box:
        return None

    away_team_name = "Away"
    home_team_name = "Home"

    for pdiv in periods:
        table = pdiv.find("table", class_="play-by-play")
        if table and table.find("thead"):
            ths = table.find("thead").find_all("th")
            if len(ths) >= 6:
                cand_away = ths[1].get_text(strip=True)
                cand_home = ths[5].get_text(strip=True)
                if cand_away:
                    away_team_name = cand_away
                if cand_home:
                    home_team_name = cand_home
                break

    raw_events: list[dict[str, Any]] = []
    current_away_score = 0
    current_home_score = 0

    for period_div in periods:
        period_id = period_div.get("id", "")
        period_num = int(period_id.split("-")[-1])
        table = period_div.find("table", class_="play-by-play")
        if not table or not table.find("tbody"):
            continue

        last_clock: Optional[str] = "20:00" if period_num <= 2 else "05:00"

        for row in table.find("tbody").find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            clock_raw = cells[0].get_text(strip=True)
            if clock_raw and re.fullmatch(r"\d{1,2}:\d{2}", clock_raw):
                clock = clock_raw
                last_clock = clock
            else:
                clock = last_clock

            away_text = cells[1].get_text(" ", strip=True)
            away_score_raw = cells[2].get_text(strip=True)
            home_score_raw = cells[4].get_text(strip=True)
            home_text = cells[5].get_text(" ", strip=True)

            a_score = _parse_score_cell(away_score_raw)
            h_score = _parse_score_cell(home_score_raw)
            if a_score is not None:
                current_away_score = a_score
            if h_score is not None:
                current_home_score = h_score

            # Emit both sides if both columns have events on the same row.
            row_events: list[tuple[str, str, str]] = []
            if away_text:
                row_events.append(("away", away_team_name, away_text))
            if home_text:
                row_events.append(("home", home_team_name, home_text))

            for side, team_label, text in row_events:
                event_type, shot_result = _classify_event(text)
                shot_type = _detect_shot_type(text) if event_type == "shot" else None
                player = _extract_player_name(text)
                raw_events.append(
                    {
                        "side": side,
                        "period": period_num,
                        "clock": clock,
                        "team": team_label,
                        "player": player,
                        "event_type": event_type,
                        "shot_type": shot_type,
                        "shot_result": shot_result,
                        "event_detail": text,
                        "score": {
                            away_team_name: current_away_score,
                            home_team_name: current_home_score,
                        },
                        "raw_text": text,
                    }
                )

    oakland_roster = box.get("oakland_roster", [])
    opponent_roster = box.get("opponent_roster", [])

    oak_side = _resolve_oakland_side(
        away_label=away_team_name,
        home_label=home_team_name,
        oakland_roster=oakland_roster,
        plays_preview=[(e["side"], e["player"]) for e in raw_events],
        location=location,
        opponent_name=opponent_name,
    )

    plays: list[dict[str, Any]] = []
    for e in raw_events:
        side = e.pop("side")
        if oak_side:
            team_side = "oakland" if side == oak_side else "opponent"
        else:
            team_side = "oakland" if is_oakland_team_label(e["team"], opponent_name) else "opponent"

        roster_for_play = oakland_roster if team_side == "oakland" else opponent_roster
        if e["player"] and roster_for_play:
            e["player"] = match_player_to_roster(e["player"], roster_for_play)

        e["team_side"] = team_side
        plays.append(e)

    if not plays and not box:
        return None

    oak_label = away_team_name if oak_side == "away" else (home_team_name if oak_side == "home" else None)
    opp_label = home_team_name if oak_side == "away" else (away_team_name if oak_side == "home" else None)

    return ParsedGameContent(
        parser="sidearm",
        plays=plays,
        oakland_team_label=oak_label,
        opponent_team_label=opp_label,
        oakland_roster=oakland_roster,
        opponent_roster=opponent_roster,
        oakland_3pm=box.get("oakland_3pm"),
        oakland_3pa=box.get("oakland_3pa"),
        opponent_3pm=box.get("opponent_3pm"),
        opponent_3pa=box.get("opponent_3pa"),
        oakland_score=box.get("oakland_score"),
        opponent_score=box.get("opponent_score"),
    )
