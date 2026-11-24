# Oakland University Men's Basketball — 3-Point Statistics Pipeline

Scrapes all available Oakland University Men's Basketball game logs (`2008-09` through the current season) from `goldengrizzlies.com`, excludes exhibition games, normalizes player and opponent names, cross-validates play-by-play against official box scores, and exports `oakland_complete_3pt_stats.csv`.

## Quick Start

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the full pipeline (scrape missing/new games + regenerate CSV):
```bash
python main.py run
```

### Common Commands
```bash
# Update only the current season and regenerate the CSV
python main.py run --seasons 2026-27

# Force a full refresh of all seasons
python main.py run --force

# Re-run CSV and report generation from cached JSON files in build/ (no network requests)
python main.py analyze

# Regenerate only the Markdown + interactive HTML reports from the CSV
python main.py report

# Run unit tests
python -m unittest discover -s tests -v
```

## Web Dashboard (`web/` — GrizzThree)

An interactive React + TypeScript + Vite editorial sports-analytics web app styled for Oakland University (Black & Gold) with 4 views (`Game Log`, `Timing & Histogram`, `Players`, `Seasons & Trends`), slide-over Game and Player Dossier drawers, CSV/JSON export, and a live `Sync 2026-27` button:

```bash
cd web
npm install
npm run dev      # Express API (:3002) + Vite React UI (:5173)
npm run build    # Type-check and build production bundle into web/dist/
npm run start    # Serve built app + API on http://localhost:3002
```

## Outputs
- `oakland_complete_3pt_stats.csv` — Full per-game dataset
- `reports/oakland_3pt_report.md` — Summary records, 1-three games, minute distribution, and player leaderboard
- `reports/oakland_3pt_report.html` — Standalone offline interactive HTML report
- `web/public/data/ou_3pt_data.json` — Rich JSON dataset (including per-game 3-point shot logs) powering the web app

## Project Layout
- `main.py` — Unified CLI entry point (`scrape`, `analyze`, `report`, `run`)
- `ou_bball/config.py` — Season list, URLs, and Oakland team aliases
- `ou_bball/normalize.py` — Player/opponent name normalization, team resolution, and elapsed-time helpers
- `ou_bball/parsers/schedule.py` — Sidearm schedule parser, exhibition detector, and recap box score finder
- `ou_bball/parsers/sidearm.py` — Modern Sidearm Sports box score + play-by-play parser
- `ou_bball/parsers/legacy.py` — Legacy StatCrew HTML (`<pre>` and table) box score + play-by-play parser
- `ou_bball/scraper.py` — HTTP session with retries, legacy FTP fallbacks, and per-season JSON cache (`build/<season>/`)
- `ou_bball/analyzer.py` — Cross-validated 3-point analytics and CSV export
- `ou_bball/report.py` — Automated Markdown and interactive HTML report generator
- `tests/test_pipeline.py` — Automated unit tests
