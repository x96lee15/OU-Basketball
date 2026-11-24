"""Parser for legacy StatCrew HTML box scores and play-by-play logs (pre-2018-19)."""

from __future__ import annotations

import re
from typing import Any, Optional

from bs4 import BeautifulSoup

from ou_bball.normalize import (
    is_oakland_team_label,
    match_player_to_roster,
    normalize_player_name,
    player_in_roster,
)
from ou_bball.parsers.sidearm import ParsedGameContent

_PERIOD_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"\b1st\s+(?:PERIOD|HALF)\b", re.IGNORECASE), 1),
    (re.compile(r"\b2nd\s+(?:PERIOD|HALF)\b", re.IGNORECASE), 2),
    (re.compile(r"\b(?:1st\s+OT|OT\s*1|OT\s+PERIOD|OVERTIME)\b", re.IGNORECASE), 3),
    (re.compile(r"\b(?:2nd\s+OT|OT\s*2|2OT)\b", re.IGNORECASE), 4),
    (re.compile(r"\b(?:3rd\s+OT|OT\s*3|3OT)\b", re.IGNORECASE), 5),
]

_PRE_LINE_RE = re.compile(
    r"^(?:(?P<home_text>.*?)\s+)?(?P<clock>\d{1,2}:\d{2})\s*(?P<score>\d+-\d+)?\s*(?P<margin>[HVT]\s+\d+)?\s*(?P<vis_text>.*)$"
)


def _detect_period(text: str) -> Optional[int]:
    for pat, num in _PERIOD_PATTERNS:
        if pat.search(text):
            return num
    return None


def _classify_event_legacy(text: str) -> tuple[str, Optional[str], Optional[str]]:
    t = text.lower()
    shot_result: Optional[str] = None
    shot_type: Optional[str] = None
    event_type = "other"

    if re.search(r"\bgood!?\b", t):
        event_type = "shot"
        shot_result = "made"
        if "ft" in re.findall(r"[a-z0-9]+", t) or "free throw" in t:
            shot_type = "ft"
        elif "3 ptr" in t or "3ptr" in t or "3-pt" in t or "3-point" in t:
            shot_type = "3pt"
        else:
            shot_type = "2pt"
    elif re.search(r"\bmiss(?:ed)?\b", t):
        event_type = "shot"
        shot_result = "missed"
        if "ft" in re.findall(r"[a-z0-9]+", t) or "free throw" in t:
            shot_type = "ft"
        elif "3 ptr" in t or "3ptr" in t or "3-pt" in t or "3-point" in t:
            shot_type = "3pt"
        else:
            shot_type = "2pt"
    elif "rebound" in t:
        event_type = "rebound"
    elif "assist" in t:
        event_type = "assist"
    elif "turnover" in t or "turnovr" in t:
        event_type = "turnover"
    elif "foul" in t:
        event_type = "foul"
    elif re.search(r"\bsub\s+(?:in|out)\b", t):
        event_type = "substitution"
    elif "steal" in t:
        event_type = "steal"
    elif "block" in t:
        event_type = "block"
    elif "timeout" in t:
        event_type = "timeout"

    return event_type, shot_result, shot_type


def _extract_player_legacy(text: str) -> Optional[str]:
    if " by " not in text:
        return None
    suffix = text.split(" by ", 1)[1]
    suffix = re.sub(r"\[.*?\]", "", suffix)
    suffix = re.sub(r"\(.*?\)", "", suffix)
    return normalize_player_name(suffix.strip())


def _extract_teams_from_title_or_header(soup: BeautifulSoup) -> tuple[str, str]:
    """Return (home_team_name, vis_team_name) from title or centered <b> heading."""
    candidates: list[str] = []
    if soup.title:
        candidates.append(soup.title.get_text(" ", strip=True))
    for b in soup.find_all(["b", "h1", "h2", "h3"]):
        txt = b.get_text(" ", strip=True)
        if " vs " in txt.lower() or " vs. " in txt.lower():
            candidates.append(txt)
            break

    for text in candidates:
        parts = re.split(r"\s+vs\.?\s+", text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            vis = parts[0].strip()
            home = parts[1].split("(")[0].strip()
            if vis and home and "goldengrizzlies" not in vis.lower():
                return home, vis

    return "Home", "Visitor"


def _extract_pre_boxscore(soup: BeautifulSoup, opponent_name: Optional[str]) -> dict[str, Any]:
    """Extract team 3PT totals and rosters from StatCrew <pre> box score."""
    pre_text = "\n".join(pre.get_text() for pre in soup.find_all("pre"))
    if "TOT-FG" not in pre_text or "Totals" not in pre_text:
        return {}

    sections: list[dict[str, Any]] = []
    current: Optional[dict[str, Any]] = None

    for line in pre_text.splitlines():
        m_team = re.match(r"^\s*(VISITORS|HOME TEAM):\s*(.+?)(?:\s+\d+-\d+)?\s*$", line)
        if m_team:
            if current:
                sections.append(current)
            current = {
                "role": "visitor" if m_team.group(1) == "VISITORS" else "home",
                "team_name": m_team.group(2).strip(),
                "roster": [],
                "three_pm": None,
                "three_pa": None,
                "score": None,
            }
            continue

        if not current:
            continue

        m_tot = re.match(
            r"^\s*Totals\.+\s+(\d+)-(\d+)\s+(\d+)-(\d+)\s+(\d+)-(\d+)\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+)",
            line,
        )
        if m_tot:
            current["three_pm"] = int(m_tot.group(3))
            current["three_pa"] = int(m_tot.group(4))
            current["score"] = int(m_tot.group(7))
            sections.append(current)
            current = None
            continue

        # Player row: "30 Kangas, Erik........ g  6-15   4-11 ..."
        m_pl = re.match(r"^\s*\d{1,2}\s+([A-Za-z][^.\d]+?)\.{2,}", line)
        if m_pl:
            norm = normalize_player_name(m_pl.group(1).strip())
            if norm and norm != "Team":
                current["roster"].append(norm)

    if current and current["three_pm"] is not None:
        sections.append(current)

    return _pick_oakland_boxscore_sections(sections, opponent_name)


def _extract_table_boxscore(soup: BeautifulSoup, opponent_name: Optional[str]) -> dict[str, Any]:
    """Extract team 3PT totals and rosters from StatCrew HTML <table> box score (e.g. msu1227)."""
    sections: list[dict[str, Any]] = []

    for table in soup.find_all("table"):
        txt_low = table.get_text(" ", strip=True).lower()
        if "3-point" not in txt_low and "3-pt" not in txt_low and "3pt" not in txt_low:
            continue
        if "totals" not in txt_low:
            continue

        heading = table.find_previous(["h3", "h4", "b"])
        heading_text = heading.get_text(" ", strip=True) if heading else ""
        score_m = re.search(r"(\d+)\s*$", heading_text)
        team_score = int(score_m.group(1)) if score_m else None
        team_name = re.sub(r"\s*\d+\s*$", "", heading_text).strip()

        roster: list[str] = []
        three_pm: Optional[int] = None
        three_pa: Optional[int] = None

        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) < 5:
                continue
            joined = " ".join(cells)
            if re.search(r"\bTotals\b", joined, re.IGNORECASE):
                # Find the fgm-fga pairs; typically [FG, 3PT, FT] in order
                pairs = re.findall(r"(\d+)-(\d+)", joined)
                if len(pairs) >= 2:
                    three_pm, three_pa = int(pairs[1][0]), int(pairs[1][1])
                continue

            if cells[0].isdigit() and cells[1]:
                norm = normalize_player_name(cells[1])
                if norm and norm != "Team":
                    roster.append(norm)

        if three_pm is not None:
            sections.append(
                {
                    "role": "visitor" if len(sections) == 0 else "home",
                    "team_name": team_name,
                    "roster": roster,
                    "three_pm": three_pm,
                    "three_pa": three_pa,
                    "score": team_score,
                }
            )
        if len(sections) == 2:
            break

    return _pick_oakland_boxscore_sections(sections, opponent_name)


def _pick_oakland_boxscore_sections(
    sections: list[dict[str, Any]],
    opponent_name: Optional[str],
) -> dict[str, Any]:
    if not sections:
        return {}

    oak_idx: Optional[int] = None
    for i, sec in enumerate(sections):
        if is_oakland_team_label(sec["team_name"], opponent_name):
            oak_idx = i
            break

    if oak_idx is None:
        return {}

    oak = sections[oak_idx]
    opp = sections[1 - oak_idx] if len(sections) == 2 else None

    result: dict[str, Any] = {
        "oakland_role": oak["role"],
        "oakland_team_name": oak["team_name"],
        "opponent_team_name": opp["team_name"] if opp else None,
        "oakland_roster": oak["roster"],
        "opponent_roster": opp["roster"] if opp else [],
        "oakland_3pm": oak["three_pm"],
        "oakland_3pa": oak["three_pa"],
        "opponent_3pm": opp["three_pm"] if opp else None,
        "opponent_3pa": opp["three_pa"] if opp else None,
        "oakland_score": oak["score"],
        "opponent_score": opp["score"] if opp else None,
    }
    return result


def _make_legacy_play(
    period: int,
    clock: str,
    team: str,
    text: str,
    score: Optional[str],
    raw: str,
    side_hint: Optional[str] = None,
) -> dict[str, Any]:
    event_type, shot_result, shot_type = _classify_event_legacy(text)
    player = _extract_player_legacy(text)
    return {
        "period": period,
        "clock": clock,
        "team": team,
        "side_hint": side_hint,
        "player": player,
        "event_type": event_type,
        "shot_type": shot_type,
        "shot_result": shot_result,
        "event_detail": text,
        "score": score,
        "raw_text": raw,
    }


def _parse_legacy_table_pbp(
    soup: BeautifulSoup,
    home_team_name: str,
    vis_team_name: str,
) -> list[dict[str, Any]]:
    """Parse legacy HTML where play-by-play is in 4-col or 5-col <table> elements."""
    periods: list[tuple[int, Any]] = []

    for h in soup.find_all(re.compile(r"^h[1-6]$")):
        txt = h.get_text(" ", strip=True)
        if "play-by-play" in txt.lower():
            p_num = _detect_period(txt)
            if p_num:
                next_table = h.find_next("table")
                if next_table:
                    periods.append((p_num, next_table))

    if not periods:
        for table in soup.find_all("table"):
            header_text = table.get_text(" ", strip=True).lower()
            if "home team" in header_text and "visitors" in header_text and "time" in header_text:
                prev = table.find_previous(string=re.compile(r"PERIOD|HALF|OT", re.IGNORECASE))
                p_num = _detect_period(str(prev)) if prev else None
                if p_num:
                    periods.append((p_num, table))

    plays: list[dict[str, Any]] = []
    for period_num, table in periods:
        rows = table.find_all("tr")
        last_time = "20:00" if period_num <= 2 else "05:00"

        is_5_col = False
        tbl_home = home_team_name
        tbl_vis = vis_team_name

        for row in rows[:5]:
            txt = row.get_text(" ", strip=True)
            low = txt.lower()
            if "home team" in low and "visitors" in low:
                is_5_col = True
                m_h = re.search(r"HOME TEAM:\s*(.+?)(?:\s+TIME|\s+SCORE|\s+VISITORS|$)", txt, re.IGNORECASE)
                m_v = re.search(r"VISITORS:\s*(.+?)$", txt, re.IGNORECASE)
                if m_h and m_h.group(1).strip():
                    tbl_home = m_h.group(1).strip()
                if m_v and m_v.group(1).strip():
                    tbl_vis = m_v.group(1).strip()
                break

        for row in rows:
            cells = row.find_all("td")
            if not cells:
                continue
            cell_texts = [c.get_text(" ", strip=True) for c in cells]
            row_low = " ".join(cell_texts).lower()
            if ("home team" in row_low and "visitors" in row_low) or ("score" in row_low and "margin" in row_low):
                continue

            if is_5_col and len(cell_texts) >= 5:
                time_cand = cell_texts[1]
                if re.fullmatch(r"\d{1,2}:\d{2}", time_cand):
                    clock = time_cand
                    last_time = clock
                else:
                    clock = last_time

                home_evt = cell_texts[0]
                score = cell_texts[2] or None
                vis_evt = cell_texts[4]
                raw = " | ".join(cell_texts)

                if home_evt:
                    plays.append(_make_legacy_play(period_num, clock, tbl_home, home_evt, score, raw, side_hint="home"))
                if vis_evt:
                    plays.append(_make_legacy_play(period_num, clock, tbl_vis, vis_evt, score, raw, side_hint="visitor"))
                continue

            # 4-column table: [0] Time, [1] Team, [2] Play, [3] Score
            time_match = re.match(r"^(\d{1,2}:\d{2})$", cell_texts[0])
            if time_match:
                clock = time_match.group(1)
                last_time = clock
            elif not cell_texts[0]:
                clock = last_time
            else:
                continue

            if len(cell_texts) >= 3:
                team_abbr = cell_texts[1] or "Unknown"
                play_text = cell_texts[2]
                score = cell_texts[3] if len(cell_texts) >= 4 and "-" in cell_texts[3] else None
                if play_text and play_text.lower() not in ("score", "play"):
                    plays.append(
                        _make_legacy_play(period_num, clock, team_abbr, play_text, score, " | ".join(cell_texts))
                    )

    return plays


def _parse_legacy_pre_pbp(
    soup: BeautifulSoup,
    home_team_name: str,
    vis_team_name: str,
) -> list[dict[str, Any]]:
    """Parse legacy StatCrew <pre> text-based play-by-play."""
    text_chunks: list[str] = []
    for pre in soup.find_all("pre"):
        txt = pre.get_text()
        if "Play-by-Play" in txt or "HOME TEAM:" in txt:
            text_chunks.append(txt)

    if not text_chunks:
        full_text = soup.get_text()
        if "1st PERIOD" in full_text and "HOME TEAM:" in full_text:
            text_chunks.append(full_text)
        else:
            return []

    lines = "\n".join(text_chunks).splitlines()

    # Extract explicit team names from header line
    for line in lines:
        if "HOME TEAM:" in line and "VISITORS:" in line:
            m = re.search(
                r"HOME TEAM:\s+(?P<home>.+?)\s+(?:TIME|SCORE|MAR).*VISITORS:\s+(?P<vis>.+)",
                line,
            )
            if m:
                home_team_name = m.group("home").strip()
                vis_team_name = m.group("vis").strip()
                break

    plays: list[dict[str, Any]] = []
    current_period = 0

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        detected = _detect_period(line_clean)
        if detected is not None:
            current_period = detected
            continue

        # Never emit plays before entering a real game period (eliminates "7:00 PM" false positives).
        if current_period == 0:
            continue

        match = _PRE_LINE_RE.match(line_clean)
        if not match:
            continue

        home_text = (match.group("home_text") or "").strip()
        clock = match.group("clock")
        score_str = match.group("score")
        vis_text = (match.group("vis_text") or "").strip()

        if "HOME TEAM" in home_text or "VISITORS" in vis_text or "---" in home_text or "---" in vis_text:
            continue

        if home_text:
            plays.append(_make_legacy_play(current_period, clock, home_team_name, home_text, score_str, line_clean, side_hint="home"))
        if vis_text:
            plays.append(_make_legacy_play(current_period, clock, vis_team_name, vis_text, score_str, line_clean, side_hint="visitor"))

    return plays


def _assign_legacy_team_sides(
    plays: list[dict[str, Any]],
    box: dict[str, Any],
    location: str,
    opponent_name: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    """Assign 'team_side' ('oakland' | 'opponent') to every legacy play without false positives."""
    oakland_roster = box.get("oakland_roster", [])
    opponent_roster = box.get("opponent_roster", [])

    # Determine which side_hint ('home' or 'visitor') corresponds to Oakland if plays have side_hints
    oak_role: Optional[str] = box.get("oakland_role")
    if not oak_role:
        home_labels = {p["team"] for p in plays if p.get("side_hint") == "home"}
        vis_labels = {p["team"] for p in plays if p.get("side_hint") == "visitor"}
        if any(is_oakland_team_label(lbl, opponent_name) for lbl in home_labels):
            oak_role = "home"
        elif any(is_oakland_team_label(lbl, opponent_name) for lbl in vis_labels):
            oak_role = "visitor"
        elif oakland_roster:
            h_hits = sum(1 for p in plays if p.get("side_hint") == "home" and player_in_roster(p["player"], oakland_roster))
            v_hits = sum(1 for p in plays if p.get("side_hint") == "visitor" and player_in_roster(p["player"], oakland_roster))
            if h_hits > v_hits:
                oak_role = "home"
            elif v_hits > h_hits:
                oak_role = "visitor"
        elif location == "Home":
            oak_role = "home"
        elif location == "Away":
            oak_role = "visitor"

    # For 4-col tables (no side_hint), determine which distinct team abbreviation maps to Oakland
    oak_abbr: Optional[str] = None
    distinct_teams = sorted({p["team"] for p in plays if p.get("team") and not p.get("side_hint")})
    if distinct_teams:
        for t in distinct_teams:
            if is_oakland_team_label(t, opponent_name):
                oak_abbr = t
                break
        if not oak_abbr and oakland_roster:
            best_t, best_hits = None, 0
            for t in distinct_teams:
                hits = sum(1 for p in plays if p["team"] == t and player_in_roster(p["player"], oakland_roster))
                if hits > best_hits:
                    best_t, best_hits = t, hits
            oak_abbr = best_t

    oak_label: Optional[str] = None
    opp_label: Optional[str] = None

    for p in plays:
        side_hint = p.pop("side_hint", None)
        if side_hint and oak_role:
            team_side = "oakland" if side_hint == oak_role else "opponent"
        elif oak_abbr and not side_hint:
            team_side = "oakland" if p["team"] == oak_abbr else "opponent"
        elif is_oakland_team_label(p["team"], opponent_name):
            team_side = "oakland"
        elif oakland_roster and player_in_roster(p["player"], oakland_roster):
            team_side = "oakland"
        else:
            team_side = "opponent"

        roster_for_play = oakland_roster if team_side == "oakland" else opponent_roster
        if p["player"] and roster_for_play:
            p["player"] = match_player_to_roster(p["player"], roster_for_play)

        p["team_side"] = team_side
        if team_side == "oakland" and not oak_label:
            oak_label = p["team"]
        elif team_side == "opponent" and not opp_label:
            opp_label = p["team"]

    return oak_label, opp_label


def parse_legacy_game(
    html: str,
    location: str = "Unknown",
    opponent_name: Optional[str] = None,
) -> Optional[ParsedGameContent]:
    """Parse a legacy StatCrew HTML page (box score + play-by-play)."""
    soup = BeautifulSoup(html, "lxml")
    home_name, vis_name = _extract_teams_from_title_or_header(soup)

    box = _extract_pre_boxscore(soup, opponent_name)
    if not box:
        box = _extract_table_boxscore(soup, opponent_name)

    if box.get("oakland_role") == "home" and box.get("oakland_team_name"):
        home_name = box["oakland_team_name"]
        if box.get("opponent_team_name"):
            vis_name = box["opponent_team_name"]
    elif box.get("oakland_role") == "visitor" and box.get("oakland_team_name"):
        vis_name = box["oakland_team_name"]
        if box.get("opponent_team_name"):
            home_name = box["opponent_team_name"]

    # Try table-based PBP first if period headings or 5-col headers exist, else <pre> PBP
    plays = _parse_legacy_table_pbp(soup, home_name, vis_name)
    parser_name = "legacy_table"
    if len(plays) < 10:
        pre_plays = _parse_legacy_pre_pbp(soup, home_name, vis_name)
        if len(pre_plays) > len(plays):
            plays = pre_plays
            parser_name = "legacy_pre"

    # Guard against garbage 1-line parses
    if len(plays) < 10:
        plays = []

    if not plays and not box:
        return None

    oak_label, opp_label = _assign_legacy_team_sides(plays, box, location, opponent_name)

    return ParsedGameContent(
        parser=parser_name,
        plays=plays,
        oakland_team_label=oak_label or box.get("oakland_team_name"),
        opponent_team_label=opp_label or box.get("opponent_team_name"),
        oakland_roster=box.get("oakland_roster", []),
        opponent_roster=box.get("opponent_roster", []),
        oakland_3pm=box.get("oakland_3pm"),
        oakland_3pa=box.get("oakland_3pa"),
        opponent_3pm=box.get("opponent_3pm"),
        opponent_3pa=box.get("opponent_3pa"),
        oakland_score=box.get("oakland_score"),
        opponent_score=box.get("opponent_score"),
    )
