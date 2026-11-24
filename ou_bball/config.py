"""Configuration constants and season definitions for the OU Basketball pipeline."""

from __future__ import annotations

BASE_URL = "https://goldengrizzlies.com"
SCHEDULE_URL_TEMPLATE = f"{BASE_URL}/sports/mens-basketball/schedule/{{season}}"
LEGACY_FTP_BASE = "http://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats"

DEFAULT_BUILD_DIR = "build"
DEFAULT_OUTPUT_CSV = "oakland_complete_3pt_stats.csv"
DEFAULT_REPORT_DIR = "reports"
DEFAULT_WEB_DATA_JSON = "web/public/data/ou_3pt_data.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Earliest season with box score / game log coverage on goldengrizzlies.com is 2008-09.
FIRST_AVAILABLE_SEASON_START = 2008
LATEST_SEASON_START = 2026


def build_season_list(
    start_year: int = FIRST_AVAILABLE_SEASON_START,
    end_year: int = LATEST_SEASON_START,
) -> list[str]:
    """Return season strings (e.g., ['2008-09', ..., '2026-27']) newest-first."""
    seasons = [f"{y}-{str(y + 1)[-2:]}" for y in range(start_year, end_year + 1)]
    return list(reversed(seasons))


# Exact / token-level team labels used for Oakland in modern and legacy game logs.
# Note: 'M-514' is Oakland University's NCAA organization ID used in some Sidearm XML feeds.
OAKLAND_TEAM_ALIASES = frozenset({
    "OAK",
    "OAKL",
    "OAKLAND",
    "OAKLAND UNIVERSITY",
    "OAKLAND UNIV",
    "OAKLAND U",
    "OAKLAND U.",
    "GOLDEN GRIZZLIES",
    "OU",
    "M-514",
})

# Generic placeholder labels emitted by legacy parsers when team names aren't in a column.
GENERIC_SIDE_LABELS = frozenset({"HOME", "VISITOR", "VISITORS", "AWAY", "UNKNOWN", ""})
