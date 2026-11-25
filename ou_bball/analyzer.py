"""Analyze cached game JSON logs and export clean Oakland 3-point statistics CSV."""

from __future__ import annotations

import csv
import glob
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from ou_bball.config import DEFAULT_BUILD_DIR, DEFAULT_OUTPUT_CSV
from ou_bball.normalize import (
    compute_elapsed_seconds,
    is_oakland_team_label,
    normalize_opponent_name,
    normalize_player_name,
    player_in_roster,
)

logger = logging.getLogger(__name__)

CSV_COLUMNS = [
    "Season",
    "Game_Date",
    "Game_ID",
    "Location",
    "Opponent",
    "Opponent_Rank",
    "Result",
    "Oakland_Score",
    "Opponent_Score",
    "Oakland_3PM",
    "Oakland_3PA",
    "Oakland_3P_Pct",
    "Opponent_3PM",
    "Opponent_3PA",
    "First_3Pt_Player",
    "First_3Pt_Period",
    "First_3Pt_Clock",
    "First_3Pt_Elapsed_Sec",
    "Opponent_First_3Pt_Player",
    "Opponent_First_3Pt_Period",
    "Opponent_First_3Pt_Clock",
    "Max_Consecutive_3PM",
    "Max_Consecutive_3PM_Window",
    "Max_Consecutive_3PMiss",
    "Max_Consecutive_3PMiss_Window",
    "PBP_Available",
    "Boxscore_URL",
]


@dataclass
class AnalysisReport:
    total_files_read: int = 0
    exhibitions_excluded: int = 0
    regular_games_exported: int = 0
    pbp_available_games: int = 0
    boxscore_only_games: int = 0
    zero_3pm_games: list[str] = field(default_factory=list)
    pbp_boxscore_mismatches: list[str] = field(default_factory=list)
    output_csv: str = DEFAULT_OUTPUT_CSV


def _format_period(period: Optional[int]) -> str:
    if not period or period < 1:
        return ""
    if period == 1:
        return "1"
    if period == 2:
        return "2"
    ot_num = period - 2
    return "OT" if ot_num == 1 else f"{ot_num}OT"


def _resolve_play_side(
    play: dict[str, Any],
    oakland_roster: list[str],
    opponent_name: str,
    location: str,
) -> Optional[str]:
    """Determine 'oakland' vs 'opponent' for a play without cross-season surname heuristics."""
    explicit = play.get("team_side")
    if explicit in ("oakland", "opponent"):
        return explicit

    team = play.get("team")
    if is_oakland_team_label(team, opponent_name):
        return "oakland"

    if team and team.strip().lower() in ("home", "visitor", "visitors"):
        t_low = team.strip().lower()
        if location == "Home":
            return "oakland" if t_low == "home" else "opponent"
        if location == "Away":
            return "oakland" if t_low.startswith("visitor") else "opponent"

    if oakland_roster and player_in_roster(play.get("player"), oakland_roster):
        return "oakland"

    # If the play has a concrete non-Oakland team name, it belongs to the opponent.
    if team and team.strip().lower() not in ("", "unknown", "home", "visitor", "visitors"):
        return "opponent"

    return None


def _format_period_short(period: Optional[int]) -> str:
    if not period or period < 1:
        return ""
    if period == 1:
        return "1H"
    if period == 2:
        return "2H"
    ot_num = period - 2
    return "OT" if ot_num == 1 else f"{ot_num}OT"


def _summarize_pbp_threes(
    plays: list[dict[str, Any]],
    oakland_roster: list[str],
    opponent_name: str,
    location: str,
) -> dict[str, Any]:
    """Extract Oakland and Opponent 3PM/3PA, first made 3PT, and in-game make/miss runs."""
    oak_3pm = 0
    oak_3pa = 0
    opp_3pm = 0
    opp_3pa = 0
    oak_first: Optional[dict[str, Any]] = None
    opp_first: Optional[dict[str, Any]] = None

    max_make_run = 0
    cur_make_run = 0
    cur_make_start = ""
    max_make_window = ""

    max_miss_run = 0
    cur_miss_run = 0
    cur_miss_start = ""
    max_miss_window = ""

    for play in plays:
        if play.get("shot_type") != "3pt":
            continue
        result = play.get("shot_result")
        if result not in ("made", "missed"):
            continue
        period = play.get("period")
        if isinstance(period, int) and period < 1:
            continue

        side = _resolve_play_side(play, oakland_roster, opponent_name, location)
        if side == "oakland":
            oak_3pa += 1
            ts = f"{_format_period_short(period)} {play.get('clock') or ''}".strip()
            if result == "made":
                oak_3pm += 1
                if oak_first is None:
                    oak_first = play
                if cur_make_run == 0:
                    cur_make_start = ts
                cur_make_run += 1
                if cur_make_run > max_make_run:
                    max_make_run = cur_make_run
                    max_make_window = f"{cur_make_start} -> {ts}" if cur_make_run > 1 else ts
                cur_miss_run = 0
            else:
                if cur_miss_run == 0:
                    cur_miss_start = ts
                cur_miss_run += 1
                if cur_miss_run > max_miss_run:
                    max_miss_run = cur_miss_run
                    max_miss_window = f"{cur_miss_start} -> {ts}" if cur_miss_run > 1 else ts
                cur_make_run = 0
        elif side == "opponent":
            opp_3pa += 1
            if result == "made":
                opp_3pm += 1
                if opp_first is None:
                    opp_first = play

    return {
        "oak_3pm": oak_3pm,
        "oak_3pa": oak_3pa,
        "opp_3pm": opp_3pm,
        "opp_3pa": opp_3pa,
        "oak_first": oak_first,
        "opp_first": opp_first,
        "max_make_run": max_make_run,
        "max_make_window": max_make_window,
        "max_miss_run": max_miss_run,
        "max_miss_window": max_miss_window,
    }


def _load_v1_fallback(filepath: str, plays: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap a legacy v1 JSON list (play_by_play_YYYY-MM-DD_ID_Opponent.json) in v2 dict shape."""
    base = os.path.basename(filepath).replace(".json", "")
    m = re.match(r"^play_by_play_(\d{4}-\d{2}-\d{2})_([^_]+)_(.+)$", base)
    game_date, game_id, opp_raw = ("Unknown", "Unknown", "Unknown")
    season = "Unknown"
    if m:
        game_date, game_id, opp_raw = m.group(1), m.group(2), m.group(3)
        y, mo, _ = map(int, game_date.split("-"))
        season = f"{y}-{str(y + 1)[-2:]}" if mo >= 8 else f"{y - 1}-{str(y)[-2:]}"

    is_exh = bool(
        re.search(r"exh", base, re.IGNORECASE)
        or (re.match(r"^\d{4}-10-", game_date))
    )

    return {
        "schema_version": 1,
        "season": season,
        "game_date": game_date,
        "game_id": game_id,
        "opponent_raw": opp_raw,
        "opponent": normalize_opponent_name(opp_raw),
        "opponent_rank": None,
        "location": "Unknown",
        "is_exhibition": is_exh,
        "result": None,
        "oakland_score": None,
        "opponent_score": None,
        "boxscore_url": None,
        "pbp_available": len(plays) >= 10,
        "oakland_roster": [],
        "boxscore_3pt": {},
        "plays": plays,
    }


def analyze_game_record(game: dict[str, Any]) -> tuple[dict[str, Any], Optional[str]]:
    """Build a single CSV row dict from a v2 game record, plus an optional mismatch note."""
    season = game.get("season", "Unknown")
    game_date = game.get("game_date", "Unknown")
    game_id = game.get("game_id", "Unknown")
    location = game.get("location", "Unknown")
    opponent = normalize_opponent_name(game.get("opponent_raw") or game.get("opponent"))
    opponent_rank = game.get("opponent_rank")
    result = game.get("result") or ""
    oak_score = game.get("oakland_score")
    opp_score = game.get("opponent_score")
    boxscore_url = game.get("boxscore_url") or ""
    oakland_roster = game.get("oakland_roster") or []
    plays = game.get("plays") or []
    pbp_available = bool(game.get("pbp_available", len(plays) >= 10))

    box3 = game.get("boxscore_3pt") or {}
    box_oak_3pm = box3.get("oakland_3pm")
    box_oak_3pa = box3.get("oakland_3pa")
    box_opp_3pm = box3.get("opponent_3pm")
    box_opp_3pa = box3.get("opponent_3pa")

    pbp_stats = (
        _summarize_pbp_threes(plays, oakland_roster, opponent, location)
        if pbp_available
        else {
            "oak_3pm": None,
            "oak_3pa": None,
            "opp_3pm": None,
            "opp_3pa": None,
            "oak_first": None,
            "opp_first": None,
            "max_make_run": None,
            "max_make_window": "",
            "max_miss_run": None,
            "max_miss_window": "",
        }
    )

    mismatch_note: Optional[str] = None
    if pbp_available and box_oak_3pm is not None and pbp_stats["oak_3pm"] != box_oak_3pm:
        mismatch_note = (
            f"{season} {game_date} vs {opponent} (id={game_id}): "
            f"PBP 3PM={pbp_stats['oak_3pm']} vs BoxScore 3PM={box_oak_3pm}"
        )

    # Prefer official Box Score totals when available; fall back to PBP count.
    oak_3pm = box_oak_3pm if box_oak_3pm is not None else pbp_stats["oak_3pm"]
    oak_3pa = box_oak_3pa if box_oak_3pa is not None else pbp_stats["oak_3pa"]
    opp_3pm = box_opp_3pm if box_opp_3pm is not None else pbp_stats["opp_3pm"]
    opp_3pa = box_opp_3pa if box_opp_3pa is not None else pbp_stats["opp_3pa"]

    oak_3p_pct = ""
    if oak_3pm is not None and oak_3pa:
        oak_3p_pct = f"{oak_3pm / oak_3pa:.3f}"

    oak_first = pbp_stats["oak_first"]
    opp_first = pbp_stats["opp_first"]

    first_player = normalize_player_name(oak_first.get("player")) if oak_first else ""
    first_period = oak_first.get("period") if oak_first else None
    first_clock = oak_first.get("clock") if oak_first else ""
    first_elapsed = compute_elapsed_seconds(first_period, first_clock) if oak_first else None

    opp_first_player = normalize_player_name(opp_first.get("player")) if opp_first else ""
    opp_first_period = opp_first.get("period") if opp_first else None
    opp_first_clock = opp_first.get("clock") if opp_first else ""

    row = {
        "Season": season,
        "Game_Date": game_date,
        "Game_ID": game_id,
        "Location": location,
        "Opponent": opponent,
        "Opponent_Rank": "" if opponent_rank is None else opponent_rank,
        "Result": result,
        "Oakland_Score": "" if oak_score is None else oak_score,
        "Opponent_Score": "" if opp_score is None else opp_score,
        "Oakland_3PM": "" if oak_3pm is None else oak_3pm,
        "Oakland_3PA": "" if oak_3pa is None else oak_3pa,
        "Oakland_3P_Pct": oak_3p_pct,
        "Opponent_3PM": "" if opp_3pm is None else opp_3pm,
        "Opponent_3PA": "" if opp_3pa is None else opp_3pa,
        "First_3Pt_Player": first_player or "",
        "First_3Pt_Period": _format_period(first_period),
        "First_3Pt_Clock": first_clock or "",
        "First_3Pt_Elapsed_Sec": "" if first_elapsed is None else first_elapsed,
        "Opponent_First_3Pt_Player": opp_first_player or "",
        "Opponent_First_3Pt_Period": _format_period(opp_first_period),
        "Opponent_First_3Pt_Clock": opp_first_clock or "",
        "Max_Consecutive_3PM": "" if pbp_stats["max_make_run"] is None else pbp_stats["max_make_run"],
        "Max_Consecutive_3PM_Window": pbp_stats["max_make_window"] or "",
        "Max_Consecutive_3PMiss": "" if pbp_stats["max_miss_run"] is None else pbp_stats["max_miss_run"],
        "Max_Consecutive_3PMiss_Window": pbp_stats["max_miss_window"] or "",
        "PBP_Available": "True" if pbp_available else "False",
        "Boxscore_URL": boxscore_url,
    }

    return row, mismatch_note


def analyze_build_dir(
    build_dir: str = DEFAULT_BUILD_DIR,
    output_csv: str = DEFAULT_OUTPUT_CSV,
    include_exhibitions: bool = False,
) -> AnalysisReport:
    """Read all cached game JSON files under build_dir and write the stats CSV."""
    report = AnalysisReport(output_csv=output_csv)

    json_files = sorted(glob.glob(os.path.join(build_dir, "**", "*.json"), recursive=True))
    report.total_files_read = len(json_files)

    rows_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}

    for filepath in json_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Skipping unreadable JSON %s: %s", filepath, exc)
            continue

        if isinstance(data, list):
            game = _load_v1_fallback(filepath, data)
        elif isinstance(data, dict):
            game = data
        else:
            continue

        # Exclude exhibition games unless explicitly requested
        game_date = str(game.get("game_date", ""))
        is_exh = bool(game.get("is_exhibition")) or bool(re.match(r"^\d{4}-10-", game_date))
        if is_exh and not include_exhibitions:
            report.exhibitions_excluded += 1
            continue

        row, mismatch = analyze_game_record(game)
        if mismatch:
            report.pbp_boxscore_mismatches.append(mismatch)

        if row["PBP_Available"] == "True":
            report.pbp_available_games += 1
        else:
            report.boxscore_only_games += 1

        if str(row["Oakland_3PM"]) == "0":
            report.zero_3pm_games.append(f"{row['Season']} {row['Game_Date']} vs {row['Opponent']} (id={row['Game_ID']})")

        key = (str(row["Season"]), str(row["Game_Date"]), str(row["Game_ID"]))
        rows_by_key[key] = row

    sorted_rows = sorted(
        rows_by_key.values(),
        key=lambda r: (r["Game_Date"], str(r["Game_ID"])),
    )
    report.regular_games_exported = len(sorted_rows)

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(sorted_rows)

    logger.info(
        "Exported %d games to %s (PBP=%d, boxscore-only=%d, exhibitions excluded=%d, mismatches=%d)",
        report.regular_games_exported,
        output_csv,
        report.pbp_available_games,
        report.boxscore_only_games,
        report.exhibitions_excluded,
        len(report.pbp_boxscore_mismatches),
    )
    return report
