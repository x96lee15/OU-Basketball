"""Normalization helpers for team labels, player names, opponent names, and game clocks."""

from __future__ import annotations

import re
from typing import Iterable, Optional

from ou_bball.config import GENERIC_SIDE_LABELS, OAKLAND_TEAM_ALIASES

_SUFFIXES = {"JR": "Jr.", "JR.": "Jr.", "SR": "Sr.", "SR.": "Sr.", "II": "II", "III": "III", "IV": "IV", "V": "V"}

# Keep known uppercase initials/acronyms uppercase when title-casing player names.
_UPPER_FIRST_TOKENS = {"DQ", "DJ", "AJ", "CJ", "EJ", "JJ", "JP", "JR", "KJ", "LJ", "MJ", "PJ", "RJ", "TJ"}

# Common opponent name canonicalization rules applied after stripping rankings/notes.
_OPPONENT_EXACT_MAP = {
    "uic": "UIC",
    "illinois - chicago": "UIC",
    "illinois-chicago": "UIC",
    "illinois chicago": "UIC",
    "iupui": "IUPUI",
    "iu indy": "IU Indy",
    "ipfw": "Purdue Fort Wayne",
    "fort wayne": "Purdue Fort Wayne",
    "purdue fort wayne": "Purdue Fort Wayne",
    "umkc": "Kansas City",
    "kansas city": "Kansas City",
    "ucf": "UCF",
    "ucla": "UCLA",
    "unlv": "UNLV",
    "utsa": "UTSA",
    "etsu": "ETSU",
    "nc state": "NC State",
    "uc davis": "UC Davis",
    "uc santa barbara": "UC Santa Barbara",
    "gvsu": "Grand Valley State",
    "grand valley": "Grand Valley State",
    "detroit": "Detroit Mercy",
    "detroit mercy": "Detroit Mercy",
    "south dakota st": "South Dakota State",
    "south dakota st.": "South Dakota State",
    "north dakota st": "North Dakota State",
    "north dakota st.": "North Dakota State",
    "grambling st": "Grambling State",
    "grambling st.": "Grambling State",
    "michigan st": "Michigan State",
    "michigan st.": "Michigan State",
    "ohio st": "Ohio State",
    "ohio st.": "Ohio State",
    "oklahoma st": "Oklahoma State",
    "oklahoma st.": "Oklahoma State",
    "wright st": "Wright State",
    "wright st.": "Wright State",
    "youngstown st": "Youngstown State",
    "youngstown st.": "Youngstown State",
    "cleveland st": "Cleveland State",
    "cleveland st.": "Cleveland State",
    "chicago st": "Chicago State",
    "chicago st.": "Chicago State",
    "georgia st": "Georgia State",
    "georgia st.": "Georgia State",
    "boise st": "Boise State",
    "boise st.": "Boise State",
    "colorado st": "Colorado State",
    "colorado st.": "Colorado State",
    "alcorn st": "Alcorn State",
    "alcorn st.": "Alcorn State",
    "illinois st": "Illinois State",
    "illinois st.": "Illinois State",
    "utah st": "Utah State",
    "utah st.": "Utah State",
    "iowa st": "Iowa State",
    "iowa st.": "Iowa State",
    "kent st": "Kent State",
    "kent st.": "Kent State",
    "morehead st": "Morehead State",
    "morehead st.": "Morehead State",
    "oregon st": "Oregon State",
    "oregon st.": "Oregon State",
    "san jose st": "San Jose State",
    "san jose st.": "San Jose State",
    "missouri st": "Missouri State",
    "missouri st.": "Missouri State",
    "long beach st": "Long Beach State",
    "long beach st.": "Long Beach State",
    "kansas st": "Kansas State",
    "kansas st.": "Kansas State",
    "arizona st": "Arizona State",
    "arizona st.": "Arizona State",
    "rochester college": "Rochester Christian",
    "rochester": "Rochester Christian",
    "rochester christian": "Rochester Christian",
    "st. francis brooklyn": "St. Francis Brooklyn",
    "st. xavier": "St. Xavier",
    "michigan-dearborn": "Michigan-Dearborn",
}


def is_oakland_team_label(team_name: Optional[str], opponent_name: Optional[str] = None) -> bool:
    """Return True if a team label explicitly identifies Oakland University."""
    if not team_name:
        return False

    cleaned = re.sub(r"[^A-Za-z0-9\s\-\.]", " ", team_name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    upper = cleaned.upper()

    if upper in GENERIC_SIDE_LABELS:
        return False

    # Guard against "OU" colliding with Oklahoma if Oakland ever plays Oklahoma.
    if upper == "OU" and opponent_name and "oklahoma" in opponent_name.lower() and "state" not in opponent_name.lower():
        return False

    if upper in OAKLAND_TEAM_ALIASES:
        return True

    # Check word-boundary match for unambiguous Oakland names.
    for token in ("OAKLAND", "GOLDEN GRIZZLIES", "M-514"):
        if re.search(rf"\b{re.escape(token)}\b", upper):
            return True

    return False


def _format_name_token(token: str, is_first_name: bool = False) -> str:
    """Title-case a single name token while respecting Mc/O'/hyphenated names and initials."""
    if not token:
        return ""

    upper = token.upper()
    if upper in _SUFFIXES:
        return _SUFFIXES[upper]

    if is_first_name and upper in _UPPER_FIRST_TOKENS:
        return upper

    # Single or dotted initials like "S.", "S", "L.J.", "C.J."
    if re.fullmatch(r"(?:[A-Za-z]\.){2,}", token):
        return token.upper()
    if re.fullmatch(r"[A-Za-z]\.?", token):
        return f"{token[0].upper()}." if token.endswith(".") or is_first_name else token.upper()

    # Hyphenated tokens like "Hill-Mais" or "Dorsey-Walker"
    if "-" in token:
        return "-".join(_format_name_token(part, is_first_name=is_first_name) for part in token.split("-"))

    # Apostrophe names like "O'Neal" or "D'Angelo"
    if "'" in token:
        parts = token.split("'")
        if len(parts) == 2 and len(parts[0]) <= 2:
            return f"{parts[0].capitalize()}'{parts[1].capitalize()}"
        return "'".join(p.capitalize() for p in parts)

    low = token.lower()
    if low.startswith("mc") and len(low) > 2:
        return "Mc" + low[2:].capitalize()

    return low.capitalize()


def normalize_player_name(raw_name: Optional[str]) -> Optional[str]:
    """Normalize raw boxscore/PBP player names to 'First Last [Suffix]' format.

    Examples:
        'KANGAS, Erik' -> 'Erik Kangas'
        'WALKER,Martez' -> 'Martez Walker'
        'HILL-MAIS,XAVIER' -> 'Xavier Hill-Mais'
        'MADDOX JR.,TRAY' -> 'Tray Maddox Jr.'
        'BOWMAN II,LORNE' -> 'Lorne Bowman II'
        'COLE,DQ' -> 'DQ Cole'
        'Travis Bader' -> 'Travis Bader'
    """
    if not raw_name:
        return None

    name = re.sub(r"\s+", " ", raw_name).strip()
    name = re.sub(r"^\(?TEAM\)?$", "Team", name, flags=re.IGNORECASE)
    if not name or name.lower() == "team":
        return "Team" if name else None

    suffixes: list[str] = []

    if "," in name:
        last_part, first_part = [p.strip() for p in name.split(",", 1)]
        last_tokens = last_part.split()
        first_tokens = first_part.split()

        # Pull suffixes like JR., II, III from end of last_part or first_part.
        clean_last: list[str] = []
        for tok in last_tokens:
            if tok.upper() in _SUFFIXES:
                suffixes.append(_SUFFIXES[tok.upper()])
            else:
                clean_last.append(tok)

        clean_first: list[str] = []
        for tok in first_tokens:
            if tok.upper() in _SUFFIXES:
                suffixes.append(_SUFFIXES[tok.upper()])
            else:
                clean_first.append(tok)

        formatted_first = [_format_name_token(t, is_first_name=True) for t in clean_first]
        formatted_last = [_format_name_token(t, is_first_name=False) for t in clean_last]
        tokens = formatted_first + formatted_last + suffixes
    else:
        raw_tokens = name.split()
        clean_tokens: list[str] = []
        for tok in raw_tokens:
            if tok.upper() in _SUFFIXES:
                suffixes.append(_SUFFIXES[tok.upper()])
            else:
                clean_tokens.append(tok)

        tokens = [
            _format_name_token(t, is_first_name=(i == 0))
            for i, t in enumerate(clean_tokens)
        ] + suffixes

    result = " ".join(t for t in tokens if t).strip()
    return result or None


def match_player_to_roster(player_name: Optional[str], roster: Iterable[str]) -> Optional[str]:
    """Match a normalized or abbreviated player name against a game's normalized roster."""
    if not player_name:
        return None

    norm = normalize_player_name(player_name)
    if not norm:
        return None

    roster_norm = [normalize_player_name(r) for r in roster]
    roster_norm = [r for r in roster_norm if r]
    if not roster_norm:
        return norm

    # Exact case-insensitive match
    norm_low = norm.lower()
    for r in roster_norm:
        if r.lower() == norm_low:
            return r

    # Initial + Last name match (e.g., 'S. Dorsey-Walker' -> 'Sherron Dorsey-Walker')
    parts = norm.split()
    if len(parts) >= 2 and re.fullmatch(r"[A-Za-z]\.?", parts[0]):
        first_initial = parts[0][0].lower()
        last_part = " ".join(parts[1:]).lower()
        matches = [
            r for r in roster_norm
            if r.lower().startswith(first_initial) and r.lower().endswith(" " + last_part)
        ]
        if len(matches) == 1:
            return matches[0]

    return norm


def player_in_roster(player_name: Optional[str], roster: Iterable[str]) -> bool:
    """Return True if player_name belongs to the given game-specific roster."""
    if not player_name:
        return False

    norm = normalize_player_name(player_name)
    if not norm or norm == "Team":
        return False

    roster_norm = [normalize_player_name(r) for r in roster]
    roster_norm = [r for r in roster_norm if r]
    if not roster_norm:
        return False

    norm_low = norm.lower()
    for r in roster_norm:
        if r.lower() == norm_low:
            return True

    # Allow first-initial + exact last-name match against this game's roster only.
    parts = norm.split()
    if len(parts) >= 2:
        first_initial = parts[0][0].lower()
        last_part = " ".join(parts[1:]).lower()
        for r in roster_norm:
            r_parts = r.split()
            if len(r_parts) >= 2 and r_parts[0][0].lower() == first_initial and " ".join(r_parts[1:]).lower() == last_part:
                return True

    return False


def normalize_opponent_name(raw_opponent: Optional[str]) -> str:
    """Clean and normalize an opponent name by removing rankings, seeds, and tourney notes."""
    if not raw_opponent:
        return "Unknown"

    name = raw_opponent.replace("_", " ")
    name = re.sub(r"\s+", " ", name).strip()

    # Strip parenthetical suffixes like (QF), (SF), (Round of 64), (Homecoming), (Exh.), (Ind.)
    name = re.sub(r"\s*\([^)]*\)", "", name).strip()

    # Strip ranking / seed prefixes:
    #   '#7 Michigan', '#11/18 Michigan State', '#RV Boise State', '[7] Northern Kentucky',
    #   'No. 11 Kansas', 'No. 5 seed IPFW', '#4 seed Texas', 'RV/RV Illinois'
    name = re.sub(
        r"^(?:\[\d+\]\s*|#\s*(?:RV|\d+(?:/\d+)?)|No\.?\s*\d+(?:/\d+)?|RV(?:/RV)?)\s*(?:seed\s+)?",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()

    # Handle legacy filename-split prefixes if reading older filenames (e.g. 'nev Nevada')
    name = re.sub(r"\s+", " ", name).strip()

    # Strip generic "University of " prefix or " University" / " College" suffix carefully
    # (keep "College" for names like "Boston College" or "Defiance College" unless canonicalized)
    stripped = re.sub(r"^University\s+of\s+", "", name, flags=re.IGNORECASE).strip()
    stripped = re.sub(r"\s+University$", "", stripped, flags=re.IGNORECASE).strip()

    # Collapse whitespace and check exact canonical map
    stripped = re.sub(r"\s+", " ", stripped).strip()
    key = stripped.lower()
    if key in _OPPONENT_EXACT_MAP:
        return _OPPONENT_EXACT_MAP[key]

    # Expand trailing "St." -> "State" (e.g., "Youngstown St." -> "Youngstown State")
    expanded = re.sub(r"\bSt\.?$", "State", stripped)
    if expanded.lower() in _OPPONENT_EXACT_MAP:
        return _OPPONENT_EXACT_MAP[expanded.lower()]

    return expanded or name


def extract_opponent_rank(raw_opponent: Optional[str]) -> Optional[int]:
    """Extract AP/Coaches poll rank if present in raw opponent name (e.g. '#7 Michigan' -> 7)."""
    if not raw_opponent:
        return None
    text = raw_opponent.replace("_", " ").strip()
    # Ignore tournament seeds like "#4 seed Texas" or "No. 5 seed IPFW"
    if re.search(r"seed\b", text, re.IGNORECASE):
        return None
    m = re.match(r"^(?:#|No\.?\s*)(\d{1,2})(?:/\d{1,2})?\b", text, re.IGNORECASE)
    if m:
        rank = int(m.group(1))
        if 1 <= rank <= 25:
            return rank
    return None


def clock_to_seconds_remaining(clock: Optional[str]) -> Optional[int]:
    """Convert 'MM:SS' game clock string to remaining seconds in the period."""
    if not clock:
        return None
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", str(clock))
    if not m:
        return None
    minutes, seconds = int(m.group(1)), int(m.group(2))
    if seconds >= 60:
        return None
    return minutes * 60 + seconds


def compute_elapsed_seconds(period: Optional[int], clock: Optional[str]) -> Optional[int]:
    """Compute elapsed game seconds from tip-off given NCAA MBB period and clock remaining.

    Periods 1 & 2 are 20 minutes (1200s); OT periods (3+) are 5 minutes (300s).
    """
    if not period or period < 1:
        return None
    remaining = clock_to_seconds_remaining(clock)
    if remaining is None:
        return None

    if period == 1:
        return max(0, 1200 - remaining)
    if period == 2:
        return 1200 + max(0, 1200 - remaining)
    # Overtime periods (period 3 = OT1, period 4 = OT2, ...)
    return 2400 + (period - 3) * 300 + max(0, 300 - remaining)
