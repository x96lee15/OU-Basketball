"""CLI entry point for the Oakland University Men's Basketball 3-point stats pipeline.

Usage:
    python main.py run                      # Scrape missing/new games and regenerate CSV
    python main.py scrape --seasons 2025-26 # Scrape specific season(s)
    python main.py scrape --force           # Re-scrape all seasons into schema v2 cache
    python main.py analyze                  # Regenerate CSV from cached JSON files in build/
"""

from __future__ import annotations

import argparse
import logging
import sys

from ou_bball.analyzer import analyze_build_dir
from ou_bball.config import DEFAULT_BUILD_DIR, DEFAULT_OUTPUT_CSV, build_season_list
from ou_bball.scraper import scrape_all_seasons


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def _add_scrape_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--seasons",
        nargs="+",
        default=None,
        help="Season(s) to scrape, e.g. 2025-26 2026-27 (defaults to all available seasons 2008-09..2026-27).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch and overwrite existing cached JSON files.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent HTTP workers per season (default: 4).",
    )
    parser.add_argument(
        "--include-exhibitions",
        action="store_true",
        help="Include exhibition games instead of excluding them.",
    )


def _add_analyze_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_CSV,
        help=f"Output CSV file path (default: {DEFAULT_OUTPUT_CSV}).",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Oakland University Men's Basketball 3-Point Statistics Pipeline",
    )
    parser.add_argument(
        "--build-dir",
        default=DEFAULT_BUILD_DIR,
        help=f"Directory for cached game JSON logs (default: {DEFAULT_BUILD_DIR}).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debug logging.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_scrape = subparsers.add_parser("scrape", help="Scrape schedules and game logs into build/.")
    _add_scrape_args(p_scrape)

    p_analyze = subparsers.add_parser("analyze", help="Analyze cached game logs and generate CSV.")
    _add_analyze_args(p_analyze)
    p_analyze.add_argument(
        "--include-exhibitions",
        action="store_true",
        help="Include exhibition games in the output CSV.",
    )

    p_run = subparsers.add_parser("run", help="Run full pipeline: scrape then analyze.")
    _add_scrape_args(p_run)
    _add_analyze_args(p_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    if args.command in ("scrape", "run"):
        seasons = args.seasons or build_season_list()
        summaries = scrape_all_seasons(
            seasons=seasons,
            build_dir=args.build_dir,
            force=args.force,
            skip_exhibitions=not args.include_exhibitions,
            workers=args.workers,
        )
        total_ok = sum(s.scraped_ok for s in summaries)
        total_cached = sum(s.cached_skipped for s in summaries)
        total_exh = sum(s.exhibitions_skipped for s in summaries)
        total_failed = sum(s.parse_failed for s in summaries)
        print(
            f"\nScrape complete across {len(summaries)} season(s): "
            f"{total_ok} scraped, {total_cached} cached, {total_exh} exhibitions skipped, {total_failed} parse failures."
        )

    if args.command in ("analyze", "run"):
        report = analyze_build_dir(
            build_dir=args.build_dir,
            output_csv=args.output,
            include_exhibitions=args.include_exhibitions,
        )
        print(
            f"\nAnalysis complete -> {report.output_csv}\n"
            f"  Games exported:      {report.regular_games_exported}\n"
            f"  With play-by-play:   {report.pbp_available_games}\n"
            f"  Box-score only:      {report.boxscore_only_games}\n"
            f"  Exhibitions skipped: {report.exhibitions_excluded}\n"
            f"  0-3PM games:         {len(report.zero_3pm_games)}\n"
            f"  PBP/Box mismatches:  {len(report.pbp_boxscore_mismatches)}"
        )
        if report.zero_3pm_games:
            print("  Zero-3PM games:")
            for item in report.zero_3pm_games:
                print(f"    - {item}")
        if report.pbp_boxscore_mismatches:
            print("  PBP vs Box Score mismatches (first 15):")
            for item in report.pbp_boxscore_mismatches[:15]:
                print(f"    - {item}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
