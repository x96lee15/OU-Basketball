"""Automated unit tests for the OU Basketball 3-point statistics pipeline."""

from __future__ import annotations

import csv
import os
import tempfile
import unittest

from ou_bball.analyzer import analyze_game_record
from ou_bball.report import compute_three_point_streak, generate_reports
from ou_bball.normalize import (
    compute_elapsed_seconds,
    extract_opponent_rank,
    is_oakland_team_label,
    match_player_to_roster,
    normalize_opponent_name,
    normalize_player_name,
)
from ou_bball.parsers.legacy import parse_legacy_game
from ou_bball.parsers.schedule import (
    build_candidate_boxscore_urls,
    inspect_recap_html,
    parse_schedule_html,
)
from ou_bball.parsers.sidearm import parse_sidearm_game

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class NormalizationTests(unittest.TestCase):
    def test_player_name_normalization(self) -> None:
        cases = {
            "KANGAS, Erik": "Erik Kangas",
            "Kangas, Erik": "Erik Kangas",
            "WALKER,Martez": "Martez Walker",
            "HILL-MAIS,XAVIER": "Xavier Hill-Mais",
            "MADDOX JR.,TRAY": "Tray Maddox Jr.",
            "MADDOX,TRAY": "Tray Maddox Jr.",
            "Felder, Kahlil": "Kay Felder",
            "Felder, Kay": "Kay Felder",
            "BOWMAN II,LORNE": "Lorne Bowman II",
            "COLE,DQ": "DQ Cole",
            "McCUNE, Tommie": "Tommie McCune",
            "Travis Bader": "Travis Bader",
            "DORSEY-WALKER, S.": "S. Dorsey-Walker",
            "WHITE II,BRETT": "Brett White II",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_player_name(raw), expected)

    def test_match_player_to_roster_initial(self) -> None:
        roster = ["Sherron Dorsey-Walker", "Max Hooper", "Kay Felder"]
        self.assertEqual(match_player_to_roster("DORSEY-WALKER, S.", roster), "Sherron Dorsey-Walker")
        self.assertEqual(match_player_to_roster("HOOPER,MAX", roster), "Max Hooper")

    def test_opponent_normalization_and_rank(self) -> None:
        self.assertEqual(normalize_opponent_name("#7Michigan"), "Michigan")
        self.assertEqual(normalize_opponent_name("#11/18 Michigan State"), "Michigan State")
        self.assertEqual(normalize_opponent_name("No. 5 seed IPFW (Semifinals)"), "Purdue Fort Wayne")
        self.assertEqual(normalize_opponent_name("University_of_Illinois_-_Chicago"), "UIC")
        self.assertEqual(normalize_opponent_name("South_Dakota_St."), "South Dakota State")
        self.assertEqual(normalize_opponent_name("Michigan_State_University"), "Michigan State")
        self.assertEqual(normalize_opponent_name("Alma College (Exh.)"), "Alma College")

        self.assertEqual(extract_opponent_rank("#7 Michigan"), 7)
        self.assertEqual(extract_opponent_rank("#11/18 Michigan State"), 11)
        self.assertEqual(extract_opponent_rank("No. 3 Kansas"), 3)
        self.assertIsNone(extract_opponent_rank("#4 seed Texas"))
        self.assertIsNone(extract_opponent_rank("#RV Boise State"))

    def test_team_label_resolution(self) -> None:
        for lbl in ("OAK", "Oak", "Oakland", "Oakland University", "OU", "M-514", "Golden Grizzlies"):
            self.assertTrue(is_oakland_team_label(lbl, "Michigan State"))

        for lbl in ("SIU", "UMKC", "Home", "Visitor", "Unknown", "MSU", ""):
            self.assertFalse(is_oakland_team_label(lbl, "UMKC"))

        # Guard against "OU" colliding with Oklahoma
        self.assertFalse(is_oakland_team_label("OU", "Oklahoma"))
        self.assertTrue(is_oakland_team_label("OU", "Oklahoma State"))

    def test_elapsed_seconds(self) -> None:
        self.assertEqual(compute_elapsed_seconds(1, "19:01"), 59)
        self.assertEqual(compute_elapsed_seconds(1, "00:00"), 1200)
        self.assertEqual(compute_elapsed_seconds(2, "19:45"), 1215)
        self.assertEqual(compute_elapsed_seconds(3, "04:30"), 2430)
        self.assertIsNone(compute_elapsed_seconds(0, "7:00"))
        self.assertIsNone(compute_elapsed_seconds(1, "--"))


class ScheduleAndRecapTests(unittest.TestCase):
    def test_recap_skips_teamstat_and_finds_boxscore(self) -> None:
        html = """
        <html><head><title>Oakland Tops Utah Valley</title></head><body><article>
          <a href="http://www.ougrizzlies.com/sports/m-baskbl/stats/2011-2012/teamstat.html">Season Stats</a>
          <a href="/documents/2018/5/21/boxscore.pdf">Box Score (PDF)</a>
          <a href="http://www.ougrizzlies.com/sports/m-baskbl/stats/2011-2012/uvu1125.html">Box Score</a>
        </article></body></html>
        """
        url, is_exh = inspect_recap_html(html)
        self.assertEqual(url, "http://www.ougrizzlies.com/sports/m-baskbl/stats/2011-2012/uvu1125.html")
        self.assertFalse(is_exh)

    def test_recap_detects_exhibition(self) -> None:
        html = """
        <html><head><title>Oakland Rolls Past GVSU in Exhibition Game</title></head>
        <body><article><h1>Oakland Rolls Past GVSU in Exhibition Game</h1></article></body></html>
        """
        _, is_exh = inspect_recap_html(html)
        self.assertTrue(is_exh)

    def test_migrated_aspx_candidates(self) -> None:
        url = "https://goldengrizzlies.com/sports/2018/5/31/_m_baskbl_stats_2016_2017_gm1bgsu_html.aspx"
        cands = build_candidate_boxscore_urls(url, "2016-17")
        self.assertEqual(
            cands[0],
            "http://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats/2016-2017/gm1bgsu.htm",
        )
        self.assertIn(url, cands)

    def test_schedule_html_exhibition_detection(self) -> None:
        html = """
        <ul>
          <li class="sidearm-schedule-game sidearm-schedule-home-game sidearm-schedule-game-completed" data-game-id="13040">
            <div class="sidearm-schedule-game-opponent-date"><span>Nov 2 (Thu)</span></div>
            <div class="sidearm-schedule-game-opponent-name"><a>Rochester College</a></div>
            <div class="sidearm-schedule-game-result"><span>W,</span><span>91-73</span></div>
          </li>
          <li class="sidearm-schedule-game sidearm-schedule-home-game sidearm-schedule-game-completed" data-game-id="13041">
            <div class="sidearm-schedule-game-opponent-date"><span>Nov 6 (Mon)</span></div>
            <div class="sidearm-schedule-game-opponent-name"><a>Davenport (Exh.)</a></div>
            <div class="sidearm-schedule-game-result"><span>W,</span><span>102-61</span></div>
            <a href="/sports/mens-basketball/stats/2025-26/davenport-exh-/boxscore/13041">Box Score</a>
          </li>
          <li class="sidearm-schedule-game sidearm-schedule-away-game sidearm-schedule-game-completed" data-game-id="13043">
            <div class="sidearm-schedule-game-opponent-date"><span>Nov 10 (Fri)</span></div>
            <div class="sidearm-schedule-game-opponent-name"><a>#7 Michigan</a></div>
            <div class="sidearm-schedule-game-result"><span>L,</span><span>78-121</span></div>
            <a href="/sports/mens-basketball/stats/2025-26/michigan/boxscore/13043">Box Score</a>
          </li>
        </ul>
        """
        sched = parse_schedule_html(html, "2025-26", "https://goldengrizzlies.com/sports/mens-basketball/schedule/2025-26")
        self.assertEqual(len(sched.games), 3)
        # Nov 2 game precedes Nov 6 exhibition -> also flagged as exhibition
        self.assertTrue(sched.games[0].is_exhibition)
        self.assertIn("precedes_exhibition", sched.games[0].exhibition_reasons)
        self.assertTrue(sched.games[1].is_exhibition)
        self.assertFalse(sched.games[2].is_exhibition)
        self.assertEqual(sched.games[2].opponent, "Michigan")
        self.assertEqual(sched.games[2].opponent_rank, 7)
        self.assertEqual(sched.games[2].location, "Away")
        self.assertEqual(sched.games[2].result, "L")
        self.assertEqual(sched.games[2].oakland_score, 78)
        self.assertEqual(sched.games[2].opponent_score, 121)


class AnalyzerRegressionTests(unittest.TestCase):
    def test_no_opponent_player_false_positive(self) -> None:
        """Ensure SIU's Barret Benson and UMKC's Reggie Hamilton are NOT attributed to Oakland."""
        game = {
            "schema_version": 2,
            "season": "2019-20",
            "game_date": "2019-11-10",
            "game_id": "6805",
            "opponent": "Southern Illinois",
            "location": "Neutral",
            "is_exhibition": False,
            "pbp_available": True,
            "oakland_roster": ["Xavier Hill-Mais", "Kevin Kangu", "Blake Lampman"],
            "boxscore_3pt": {"oakland_3pm": 3, "oakland_3pa": 14, "opponent_3pm": 7, "opponent_3pa": 20},
            "plays": [
                {
                    "period": 1,
                    "clock": "19:42",
                    "team": "SIU",
                    "team_side": "opponent",
                    "player": "Barret Benson",
                    "event_type": "shot",
                    "shot_type": "3pt",
                    "shot_result": "made",
                },
                {
                    "period": 1,
                    "clock": "15:10",
                    "team": "Oak",
                    "team_side": "oakland",
                    "player": "Blake Lampman",
                    "event_type": "shot",
                    "shot_type": "3pt",
                    "shot_result": "made",
                },
            ],
        }
        row, _ = analyze_game_record(game)
        self.assertEqual(row["First_3Pt_Player"], "Blake Lampman")
        self.assertEqual(row["First_3Pt_Clock"], "15:10")
        self.assertEqual(row["Opponent_First_3Pt_Player"], "Barret Benson")
        self.assertEqual(row["Oakland_3PM"], 3)
        self.assertEqual(row["Oakland_3PA"], 14)

    def test_legacy_parser_ignores_period_zero_clock(self) -> None:
        html = """
        <html><head><title>Oakland vs Cleveland State</title></head><body>
        <pre>
        Men's Basketball
        02/05/21 7:00 PM at Cleveland, OH
        </pre></body></html>
        """
        parsed = parse_legacy_game(html, location="Away", opponent_name="Cleveland State")
        self.assertIsNone(parsed)


class InlineParserTests(unittest.TestCase):
    """Self-contained parser tests covering modern Sidearm, legacy <pre>, and legacy <table>."""

    def test_sidearm_boxscore_and_pbp(self) -> None:
        html = """
        <html><body>
          <h3>Oakland 78</h3>
          <table>
            <thead><tr><th>##</th><th>Player</th><th>FG</th><th>3PT</th><th>PTS</th></tr></thead>
            <tbody>
              <tr><td>10</td><td><a class="boxscore_player_link" href="/sports/mens-basketball/roster/brett-white-ii/1">White II, Brett</a></td><td>5-9</td><td data-label="3PT">5-8</td><td>15</td></tr>
              <tr><td>55</td><td><a class="boxscore_player_link" href="/sports/mens-basketball/roster/brody-robinson/2">Robinson, Brody</a></td><td>3-7</td><td data-label="3PT">3-7</td><td>9</td></tr>
              <tr><td>Totals</td><td></td><td>8-16</td><td data-label="3PT">8-15</td><td>78</td></tr>
            </tbody>
          </table>
          <h3>Youngstown St. 70</h3>
          <table>
            <thead><tr><th>##</th><th>Player</th><th>FG</th><th>3PT</th><th>PTS</th></tr></thead>
            <tbody>
              <tr><td>01</td><td>Smith, John</td><td>4-10</td><td data-label="3PT">2-6</td><td>10</td></tr>
              <tr><td>Totals</td><td></td><td>20-50</td><td data-label="3PT">6-20</td><td>70</td></tr>
            </tbody>
          </table>
          <div id="period-1">
            <table class="play-by-play">
              <thead><tr><th>Time</th><th>Oak</th><th>Score</th><th>Ind</th><th>Score</th><th>YSU</th></tr></thead>
              <tbody>
                <tr><td>19:10</td><td></td><td>0</td><td></td><td>3</td><td>GOOD 3PTR by SMITH,JOHN</td></tr>
                <tr><td>18:45</td><td>GOOD 3PTR by ROBINSON,BRODY</td><td>3</td><td></td><td>3</td><td></td></tr>
                <tr><td>--</td><td>ASSIST by WHITE II,BRETT</td><td>3</td><td></td><td>3</td><td></td></tr>
              </tbody>
            </table>
          </div>
        </body></html>
        """
        parsed = parse_sidearm_game(html, location="Away", opponent_name="Youngstown State")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.oakland_3pm, 8)
        self.assertEqual(parsed.oakland_3pa, 15)
        self.assertEqual(parsed.opponent_3pm, 6)
        self.assertEqual(parsed.opponent_3pa, 20)
        self.assertEqual(len(parsed.plays), 3)
        self.assertEqual(parsed.plays[0]["team_side"], "opponent")
        self.assertEqual(parsed.plays[1]["team_side"], "oakland")
        self.assertEqual(parsed.plays[1]["player"], "Brody Robinson")
        # "--" clock carries forward last valid clock
        self.assertEqual(parsed.plays[2]["clock"], "18:45")

    def test_legacy_pre_boxscore_and_pbp(self) -> None:
        html = """
        <html><head><title>Oakland University vs Iowa Hawkeyes (11/23/08)</title></head><body>
        <pre>
        VISITORS: Oakland University 1-3
                                  TOT-FG  3-PT         REBOUNDS
        ## Player Name            FG-FGA FG-FGA FT-FTA OF DE TOT PF TP A TO BLK S MIN
        30 Kangas, Erik........ g  6-15   4-11   2-2    1  2  3   1  18 1 1 0 1 36
           Totals..............   22-51   7-19   6-11   9 15 24  20  57 10 11 2 7 200
        HOME TEAM: Iowa Hawkeyes 4-0
                                  TOT-FG  3-PT         REBOUNDS
        ## Player Name            FG-FGA FG-FGA FT-FTA OF DE TOT PF TP A TO BLK S MIN
        01 Tucker, Anthony..... g  7-12   5-10   0-0    1  5  6   1  19 1 1 0 0 35
           Totals..............   22-40  10-25  12-18   7 24 31  12  66 19 16 1 6 200
        </pre>
        <pre>
        Play-by-Play
        11/23/08 5:05 p.m. at Iowa City, IA
        1st PERIOD Play-by-Play (Page 1)
        HOME TEAM: Iowa Hawkeyes                        TIME   SCORE  MAR  VISITORS: Oakland University
        GOOD! 3 PTR by Tucker, Anthony                  17:05   3-0   H 3
                                                        14:09   3-3   T 1  GOOD! 3 PTR by Kangas, Erik
                                                        13:50   3-4   V 1  GOOD! FT SHOT by Kangas, Erik
        MISSED JUMPER by Tucker, Anthony                13:20              REBOUND (DEF) by Kangas, Erik
        FOUL by Tucker, Anthony                         13:00
        TURNOVR by Tucker, Anthony                      12:40              STEAL by Kangas, Erik
        MISSED 3 PTR by Tucker, Anthony                 12:10              REBOUND (DEF) by Kangas, Erik
        </pre></body></html>
        """
        parsed = parse_legacy_game(html, location="Away", opponent_name="Iowa")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.oakland_3pm, 7)
        self.assertEqual(parsed.oakland_3pa, 19)
        oak_3s = [
            p for p in parsed.plays
            if p["team_side"] == "oakland" and p["shot_type"] == "3pt" and p["shot_result"] == "made"
        ]
        self.assertEqual(len(oak_3s), 1)
        self.assertEqual(oak_3s[0]["player"], "Erik Kangas")
        # Free throws must be classified as 'ft', not '2pt'
        fts = [p for p in parsed.plays if p["shot_type"] == "ft"]
        self.assertEqual(len(fts), 1)
        # Period-0 header line ("5:05 p.m.") must not produce any plays
        self.assertTrue(all(p["period"] >= 1 for p in parsed.plays))


class ReportGeneratorTests(unittest.TestCase):
    def test_generate_markdown_and_html_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "stats.csv")
            report_dir = os.path.join(tmp, "reports")
            fieldnames = [
                "Season", "Game_Date", "Game_ID", "Location", "Opponent", "Opponent_Rank",
                "Result", "Oakland_Score", "Opponent_Score", "Oakland_3PM", "Oakland_3PA",
                "Oakland_3P_Pct", "Opponent_3PM", "Opponent_3PA", "First_3Pt_Player",
                "First_3Pt_Period", "First_3Pt_Clock", "First_3Pt_Elapsed_Sec",
                "Opponent_First_3Pt_Player", "Opponent_First_3Pt_Period", "Opponent_First_3Pt_Clock",
                "PBP_Available", "Boxscore_URL",
            ]
            rows = [
                {
                    "Season": "2024-25", "Game_Date": "2025-02-21", "Game_ID": "12052",
                    "Location": "Away", "Opponent": "Purdue Fort Wayne", "Opponent_Rank": "",
                    "Result": "L", "Oakland_Score": "66", "Opponent_Score": "80",
                    "Oakland_3PM": "1", "Oakland_3PA": "21", "Oakland_3P_Pct": "0.048",
                    "Opponent_3PM": "10", "Opponent_3PA": "25", "First_3Pt_Player": "DQ Cole",
                    "First_3Pt_Period": "1", "First_3Pt_Clock": "19:08", "First_3Pt_Elapsed_Sec": "52",
                    "Opponent_First_3Pt_Player": "Opp", "Opponent_First_3Pt_Period": "1",
                    "Opponent_First_3Pt_Clock": "18:00", "PBP_Available": "True", "Boxscore_URL": "",
                },
                {
                    "Season": "2020-21", "Game_Date": "2020-12-13", "Game_ID": "7222",
                    "Location": "Away", "Opponent": "Michigan State", "Opponent_Rank": "4",
                    "Result": "L", "Oakland_Score": "91", "Opponent_Score": "109",
                    "Oakland_3PM": "18", "Oakland_3PA": "34", "Oakland_3P_Pct": "0.529",
                    "Opponent_3PM": "12", "Opponent_3PA": "28", "First_3Pt_Player": "Rashad Williams",
                    "First_3Pt_Period": "2", "First_3Pt_Clock": "12:54", "First_3Pt_Elapsed_Sec": "1626",
                    "Opponent_First_3Pt_Player": "Opp", "Opponent_First_3Pt_Period": "1",
                    "Opponent_First_3Pt_Clock": "19:00", "PBP_Available": "True", "Boxscore_URL": "",
                },
            ]
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(rows)

            web_json = os.path.join(tmp, "ou_3pt_data.json")
            res = generate_reports(csv_path=csv_path, report_dir=report_dir, build_dir="", web_json_path=web_json)
            self.assertEqual(res.total_games, 2)
            self.assertTrue(os.path.exists(res.markdown_path))
            self.assertTrue(os.path.exists(res.html_path))
            self.assertTrue(os.path.exists(web_json))

            with open(res.markdown_path, encoding="utf-8") as f:
                md = f.read()
            self.assertIn("DQ Cole", md)
            self.assertIn("18–34", md)
            self.assertIn("Purdue Fort Wayne", md)

            with open(res.html_path, encoding="utf-8") as f:
                html_txt = f.read()
            self.assertIn("Minute of Oakland's First Made 3-Pointer", html_txt)
            self.assertIn("Rashad Williams", html_txt)

    def test_three_point_streak_increments_and_resets(self) -> None:
        rows = [
            {"Season": "2026-27", "Game_Date": "2026-11-18", "Game_ID": "1", "Opponent": "Arizona State", "Location": "Away", "Oakland_3PM": "7", "Oakland_3PA": "23"},
            {"Season": "2026-27", "Game_Date": "2026-11-20", "Game_ID": "2", "Opponent": "Purdue", "Location": "Away", "Oakland_3PM": "4", "Oakland_3PA": "19"},
            {"Season": "2026-27", "Game_Date": "2026-11-27", "Game_ID": "3", "Opponent": "Houston", "Location": "Away", "Oakland_3PM": "6", "Oakland_3PA": "20"},
        ]
        s = compute_three_point_streak(rows)
        self.assertTrue(s["active"])
        self.assertEqual(s["count"], 1208)
        self.assertEqual(s["gamesSinceAnchor"], 2)

        # If a future game has 0 made 3-pointers, streak resets cleanly
        rows.append({"Season": "2026-27", "Game_Date": "2026-12-02", "Game_ID": "4", "Opponent": "NKU", "Location": "Home", "Oakland_3PM": "0", "Oakland_3PA": "15"})
        s2 = compute_three_point_streak(rows)
        self.assertFalse(s2["active"])
        self.assertEqual(s2["count"], 0)
        self.assertEqual(s2["lastZeroDate"], "2026-12-02")


if __name__ == "__main__":
    unittest.main()
