"""Generate Markdown and interactive HTML reports from oakland_complete_3pt_stats.csv."""

from __future__ import annotations

import collections
import csv
import html as html_lib
import json
import math
import os
from dataclasses import dataclass
from typing import Any

from ou_bball.config import DEFAULT_OUTPUT_CSV, DEFAULT_REPORT_DIR


@dataclass
class GeneratedReports:
    markdown_path: str
    html_path: str
    total_games: int
    pbp_games: int


def _fmt_elapsed(seconds: int) -> str:
    mins, secs = divmod(seconds, 60)
    return f"{mins}:{secs:02d}"


def _fmt_period_label(period: str) -> str:
    if period == "1":
        return "1st Half"
    if period == "2":
        return "2nd Half"
    return period or ""


def compute_report_data(csv_path: str = DEFAULT_OUTPUT_CSV) -> dict[str, Any]:
    """Read the exported CSV and compute all summary records, player counts, and histogram bins."""
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    pbp_rows = [
        r for r in rows
        if r.get("PBP_Available") == "True" and str(r.get("First_3Pt_Elapsed_Sec", "")).isdigit()
    ]

    seasons = sorted({r["Season"] for r in rows if r.get("Season")})
    season_span = f"{seasons[0]}–{seasons[-1]}" if seasons else "N/A"

    # Fastest first 3PT
    fastest_sorted = sorted(pbp_rows, key=lambda r: (int(r["First_3Pt_Elapsed_Sec"]), r["Game_Date"]))
    min_sec = int(fastest_sorted[0]["First_3Pt_Elapsed_Sec"]) if fastest_sorted else None
    fastest_tied = [r for r in fastest_sorted if int(r["First_3Pt_Elapsed_Sec"]) == min_sec] if min_sec is not None else []

    # Longest wait before first 3PT
    longest_sorted = sorted(pbp_rows, key=lambda r: (-int(r["First_3Pt_Elapsed_Sec"]), r["Game_Date"]))
    max_sec = int(longest_sorted[0]["First_3Pt_Elapsed_Sec"]) if longest_sorted else None
    longest_tied = [r for r in longest_sorted if int(r["First_3Pt_Elapsed_Sec"]) == max_sec] if max_sec is not None else []

    # Games with exactly 1 made 3PT
    one_three_games = sorted(
        [r for r in rows if str(r.get("Oakland_3PM", "")).isdigit() and int(r["Oakland_3PM"]) == 1],
        key=lambda r: r["Game_Date"],
    )

    # Most 3s in a game
    scored_rows = [r for r in rows if str(r.get("Oakland_3PM", "")).isdigit()]
    most_sorted = sorted(
        scored_rows,
        key=lambda r: (-int(r["Oakland_3PM"]), -float(r["Oakland_3P_Pct"] or 0), r["Game_Date"]),
    )
    max_3pm = int(most_sorted[0]["Oakland_3PM"]) if most_sorted else None
    most_tied = [r for r in most_sorted if int(r["Oakland_3PM"]) == max_3pm] if max_3pm is not None else []

    # Player first-3PT leaderboard
    player_counts = collections.Counter(r["First_3Pt_Player"] for r in pbp_rows if r.get("First_3Pt_Player"))
    player_leaderboard = sorted(player_counts.items(), key=lambda kv: (-kv[1], kv[0]))

    # Elapsed timing summary stats
    elapsed_vals = sorted(int(r["First_3Pt_Elapsed_Sec"]) for r in pbp_rows)
    n_pbp = len(elapsed_vals)
    avg_sec = round(sum(elapsed_vals) / n_pbp, 1) if n_pbp else 0.0
    med_sec = elapsed_vals[n_pbp // 2] if n_pbp else 0
    p90_sec = elapsed_vals[min(n_pbp - 1, int(n_pbp * 0.9))] if n_pbp else 0

    # Minute-by-minute histogram bins
    buckets: dict[int, list[dict[str, str]]] = collections.defaultdict(list)
    for r in pbp_rows:
        sec = int(r["First_3Pt_Elapsed_Sec"])
        minute = sec // 60
        if sec == 1200 and r.get("First_3Pt_Period") == "1":
            minute = 19
        buckets[minute].append(r)

    max_minute = max(buckets.keys(), default=20)
    histogram_bins: list[dict[str, Any]] = []
    running = 0
    for m in range(0, max_minute + 1):
        items = buckets.get(m, [])
        cnt = len(items)
        wins = sum(1 for r in items if r.get("Result") == "W")
        losses = sum(1 for r in items if r.get("Result") == "L")
        running += cnt
        pct = round((cnt / n_pbp) * 100, 1) if n_pbp else 0.0
        cum_pct = round((running / n_pbp) * 100, 1) if n_pbp else 0.0
        samples = [
            f"{r['Game_Date']} vs {r['Opponent']} ({r['First_3Pt_Player']}, {r['First_3Pt_Clock']})"
            for r in sorted(items, key=lambda x: (int(x["First_3Pt_Elapsed_Sec"]), x["Game_Date"]))[:3]
        ]
        histogram_bins.append(
            {
                "min": m,
                "count": cnt,
                "w": wins,
                "l": losses,
                "pct": pct,
                "cum_pct": cum_pct,
                "samples": samples,
            }
        )

    peak_bin = max(histogram_bins, key=lambda b: b["count"]) if histogram_bins else {"min": 0, "count": 0}
    first_half_count = sum(b["count"] for b in histogram_bins if b["min"] < 20)
    second_half_bins = [b for b in histogram_bins if b["min"] >= 20]
    second_half_count = sum(b["count"] for b in second_half_bins)
    second_half_w = sum(b["w"] for b in second_half_bins)
    second_half_l = sum(b["l"] for b in second_half_bins)
    first_five_count = sum(b["count"] for b in histogram_bins if b["min"] < 5)

    return {
        "total_games": len(rows),
        "pbp_games": n_pbp,
        "season_span": season_span,
        "fastest_sec": min_sec,
        "fastest_tied": fastest_tied,
        "fastest_top5": fastest_sorted[:5],
        "longest_sec": max_sec,
        "longest_tied": longest_tied,
        "longest_top5": longest_sorted[:5],
        "one_three_games": one_three_games,
        "max_3pm": max_3pm,
        "most_tied": most_tied,
        "most_top5": most_sorted[:5],
        "player_leaderboard": player_leaderboard,
        "avg_sec": avg_sec,
        "med_sec": med_sec,
        "p90_sec": p90_sec,
        "peak_bin": peak_bin,
        "first_half_count": first_half_count,
        "first_half_pct": round((first_half_count / n_pbp) * 100, 1) if n_pbp else 0.0,
        "second_half_count": second_half_count,
        "second_half_w": second_half_w,
        "second_half_l": second_half_l,
        "first_five_count": first_five_count,
        "first_five_pct": round((first_five_count / n_pbp) * 100, 1) if n_pbp else 0.0,
        "histogram_bins": histogram_bins,
    }


def render_markdown_report(data: dict[str, Any]) -> str:
    """Render a clean Markdown report from computed statistics."""
    lines: list[str] = [
        "# Oakland University Men's Basketball — 3-Point Statistics Report",
        "",
        f"Generated from `oakland_complete_3pt_stats.csv` covering **{data['total_games']}** regular-season/postseason games "
        f"(`{data['season_span']}`, **{data['pbp_games']}** with play-by-play timing).",
        "",
        "## Key Timing Summary",
        f"- **Fastest 1st 3-Pointer:** `{data['fastest_sec']}s` elapsed ({_fmt_elapsed(data['fastest_sec']) if data['fastest_sec'] is not None else 'N/A'})",
        f"- **Longest Wait for 1st 3-Pointer:** `{data['longest_sec']}s` elapsed ({_fmt_elapsed(data['longest_sec']) if data['longest_sec'] is not None else 'N/A'})",
        f"- **Median / Mean Time to 1st 3-Pointer:** `{_fmt_elapsed(data['med_sec'])}` median / `{_fmt_elapsed(int(round(data['avg_sec'])))}` mean",
        f"- **Peak Minute:** Minute `{data['peak_bin']['min']}–{data['peak_bin']['min'] + 1}` (**{data['peak_bin']['count']}** games)",
        f"- **First 5 Minutes:** **{data['first_five_count']}** games (**{data['first_five_pct']:.1f}%**)",
        f"- **1st Half vs 2nd Half:** **{data['first_half_count']}** ({data['first_half_pct']:.1f}%) in 1st Half; "
        f"**{data['second_half_count']}** in 2nd Half (record: `{data['second_half_w']}-{data['second_half_l']}`)",
        "",
        "## Fastest 1st 3-Pointer Made (Top 5)",
        "| Elapsed | Half & Clock | Date | Season | Opponent | Player | Score (3PT) |",
        "| ---: | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for r in data["fastest_top5"]:
        lines.append(
            f"| {r['First_3Pt_Elapsed_Sec']}s | {_fmt_period_label(r['First_3Pt_Period'])} `{r['First_3Pt_Clock']}` | "
            f"`{r['Game_Date']}` | `{r['Season']}` | {r['Opponent']} | {r['First_3Pt_Player']} | "
            f"{r['Result']} {r['Oakland_Score']}–{r['Opponent_Score']} ({r['Oakland_3PM']}–{r['Oakland_3PA']}) |"
        )

    lines.extend([
        "",
        "## Longest Wait Before 1st 3-Pointer (Top 5)",
        "| Elapsed | Half & Clock | Date | Season | Opponent | Player | Score (3PT) |",
        "| ---: | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])
    for r in data["longest_top5"]:
        sec = int(r["First_3Pt_Elapsed_Sec"])
        lines.append(
            f"| {_fmt_elapsed(sec)} ({sec}s) | {_fmt_period_label(r['First_3Pt_Period'])} `{r['First_3Pt_Clock']}` | "
            f"`{r['Game_Date']}` | `{r['Season']}` | {r['Opponent']} | {r['First_3Pt_Player']} | "
            f"{r['Result']} {r['Oakland_Score']}–{r['Opponent_Score']} ({r['Oakland_3PM']}–{r['Oakland_3PA']}) |"
        )

    lines.extend([
        "",
        f"## Games With Only 1 Made 3-Pointer ({len(data['one_three_games'])} games)",
        "| Date | Season | Location | Opponent | Result | 3PT | Made By | Half & Clock |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])
    for r in data["one_three_games"]:
        lines.append(
            f"| `{r['Game_Date']}` | `{r['Season']}` | {r['Location']} | {r['Opponent']} | "
            f"{r['Result']} {r['Oakland_Score']}–{r['Opponent_Score']} | {r['Oakland_3PM']}–{r['Oakland_3PA']} | "
            f"{r['First_3Pt_Player']} | {_fmt_period_label(r['First_3Pt_Period'])} `{r['First_3Pt_Clock']}` |"
        )

    lines.extend([
        "",
        "## Most 3-Pointers Made in a Game (Top 5)",
        "| 3PM–3PA | 3P% | Date | Season | Location | Opponent | Score |",
        "| :--- | ---: | :--- | :--- | :--- | :--- | :--- |",
    ])
    for r in data["most_top5"]:
        pct_str = f"{float(r['Oakland_3P_Pct']) * 100:.1f}%" if r.get("Oakland_3P_Pct") else ""
        lines.append(
            f"| **{r['Oakland_3PM']}–{r['Oakland_3PA']}** | {pct_str} | `{r['Game_Date']}` | `{r['Season']}` | "
            f"{r['Location']} | {r['Opponent']} | {r['Result']} {r['Oakland_Score']}–{r['Opponent_Score']} |"
        )

    lines.extend([
        "",
        "## Minute-by-Minute Distribution of First 3-Pointer",
        "| Elapsed Min | Half | Games | W–L | Share | Cumulative |",
        "| :--- | :--- | ---: | :--- | ---: | ---: |",
    ])
    for b in data["histogram_bins"]:
        half = "1st Half" if b["min"] < 20 else "2nd Half"
        lines.append(
            f"| {b['min']}–{b['min'] + 1} | {half} | {b['count']} | {b['w']}–{b['l']} | {b['pct']:.1f}% | {b['cum_pct']:.1f}% |"
        )

    players = data["player_leaderboard"]
    lines.extend([
        "",
        f"## Players by Total First 3-Pointers Made ({len(players)} players)",
        "| Rank | Player | First 3s |",
        "| ---: | :--- | ---: |",
    ])
    for idx, (player, cnt) in enumerate(players, 1):
        lines.append(f"| {idx} | {player} | {cnt} |")

    lines.append("")
    return "\n".join(lines)


def render_html_report(data: dict[str, Any]) -> str:
    """Render a fully self-contained interactive HTML report (works offline in any browser)."""
    bins_json = json.dumps(data["histogram_bins"])
    total_pbp = data["pbp_games"]
    peak = data["peak_bin"]
    med_str = _fmt_elapsed(data["med_sec"])
    avg_str = _fmt_elapsed(int(round(data["avg_sec"])))
    med_min_float = round(data["med_sec"] / 60.0, 2)
    max_bar = max(10, int(math.ceil(peak["count"] / 10.0) * 10))

    fastest_desc = ", ".join(
        f"{html_lib.escape(r['First_3Pt_Player'])} ({r['Game_Date']} vs {html_lib.escape(r['Opponent'])})"
        for r in data["fastest_tied"]
    )
    longest_desc = ", ".join(
        f"{html_lib.escape(r['First_3Pt_Player'])} ({r['Game_Date']} vs {html_lib.escape(r['Opponent'])})"
        for r in data["longest_tied"]
    )
    most_desc = ", ".join(
        f"{r['Oakland_3PM']}-{r['Oakland_3PA']} vs {html_lib.escape(r['Opponent'])} ({r['Game_Date']})"
        for r in data["most_tied"]
    )

    one_rows_html = "\n".join(
        f"<tr><td>{html_lib.escape(r['Game_Date'])}</td><td>{html_lib.escape(r['Season'])}</td>"
        f"<td>{html_lib.escape(r['Location'])}</td><td>{html_lib.escape(r['Opponent'])}</td>"
        f"<td>{html_lib.escape(r['Result'])} {r['Oakland_Score']}-{r['Opponent_Score']}</td>"
        f"<td>{r['Oakland_3PM']}-{r['Oakland_3PA']}</td>"
        f"<td>{html_lib.escape(r['First_3Pt_Player'])} ({_fmt_period_label(r['First_3Pt_Period'])} {r['First_3Pt_Clock']})</td></tr>"
        for r in data["one_three_games"]
    )

    player_rows_html = "\n".join(
        f"<tr><td class='num'>{idx}</td><td>{html_lib.escape(name)}</td><td class='num'><strong>{cnt}</strong></td></tr>"
        for idx, (name, cnt) in enumerate(data["player_leaderboard"], 1)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Oakland Men's Basketball — 3-Point Statistics Report</title>
  <style>
    :root {{
      --bg: #0f1117;
      --surface: #171a23;
      --border: #2a2f3d;
      --fg: #e8ecf4;
      --muted: #9aa3b8;
      --gold: #c8a951;
      --blue: #5ca4f6;
      --green: #3fb97a;
      --red: #e05d5d;
      --amber: #e6a23c;
    }}
    @media (prefers-color-scheme: light) {{
      :root {{
        --bg: #f6f7fa;
        --surface: #ffffff;
        --border: #dfe3ec;
        --fg: #181c24;
        --muted: #5c667a;
        --gold: #8c6d1f;
        --blue: #2563eb;
        --green: #16a34a;
        --red: #dc2626;
        --amber: #d97706;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 24px;
      background: var(--bg);
      color: var(--fg);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      font-size: 14px;
      line-height: 1.5;
    }}
    .container {{ max-width: 1040px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }}
    h1 {{ margin: 0 0 4px; font-size: 22px; }}
    h2 {{ margin: 0 0 12px; font-size: 16px; }}
    .sub {{ color: var(--muted); font-size: 13px; margin: 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }}
    .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }}
    .k-label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}
    .k-val {{ font-size: 22px; font-weight: 700; margin: 4px 0; font-variant-numeric: tabular-nums; color: var(--gold); }}
    .k-note {{ color: var(--muted); font-size: 12px; }}
    .toolbar {{ display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 10px; }}
    .btn-group {{ display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }}
    button {{
      border: none; background: transparent; color: var(--muted); padding: 5px 10px;
      font-size: 12px; cursor: pointer; font-weight: 500;
    }}
    button.active {{ background: var(--gold); color: #111; }}
    label.chk {{ display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--muted); cursor: pointer; }}
    #chart {{ width: 100%; height: auto; display: block; }}
    .detail {{
      margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border);
      font-size: 12px; display: flex; flex-direction: column; gap: 4px;
    }}
    .detail-top {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-variant-numeric: tabular-nums; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--border); }}
    th {{ color: var(--muted); font-weight: 600; font-size: 12px; }}
    td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .search {{
      padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border);
      background: var(--bg); color: var(--fg); font-size: 13px; width: 220px;
    }}
    .table-scroll {{ max-height: 380px; overflow-y: auto; }}
  </style>
</head>
<body>
  <div class="container">
    <div>
      <h1>Oakland University Men's Basketball — 3-Point Statistics</h1>
      <p class="sub">{data['total_games']} regular-season/postseason games ({html_lib.escape(data['season_span'])}) • {total_pbp} with play-by-play timing</p>
    </div>

    <div class="grid">
      <div class="card">
        <div class="k-label">Fastest 1st 3-Pointer</div>
        <div class="k-val">{data['fastest_sec']}s</div>
        <div class="k-note">{fastest_desc}</div>
      </div>
      <div class="card">
        <div class="k-label">Longest Wait for 1st 3PT</div>
        <div class="k-val">{_fmt_elapsed(data['longest_sec']) if data['longest_sec'] is not None else 'N/A'}</div>
        <div class="k-note">{longest_desc}</div>
      </div>
      <div class="card">
        <div class="k-label">Most 3s in a Game</div>
        <div class="k-val">{data['max_3pm']}</div>
        <div class="k-note">{most_desc}</div>
      </div>
      <div class="card">
        <div class="k-label">Typical 1st 3PT Timing</div>
        <div class="k-val">{med_str} med</div>
        <div class="k-note">Mean {avg_str} • {data['first_five_pct']:.1f}% in first 5 min • {data['first_half_pct']:.1f}% in 1H</div>
      </div>
    </div>

    <div class="card">
      <div class="toolbar">
        <h2 style="margin:0">Minute of Oakland's First Made 3-Pointer</h2>
        <div style="display:flex;align-items:center;gap:12px;">
          <div class="btn-group">
            <button id="btn-all" class="active">Total</button>
            <button id="btn-wl">W / L</button>
          </div>
          <label class="chk"><input id="chk-cum" type="checkbox" checked /> Cumulative %</label>
        </div>
      </div>
      <svg id="chart" viewBox="0 0 800 270"></svg>
      <div class="detail">
        <div class="detail-top">
          <strong id="detail-title">Hover or click any bar</strong>
          <span id="detail-stats" class="mono" style="color:var(--muted)"></span>
        </div>
        <div id="detail-samples" style="color:var(--muted)"></div>
      </div>
    </div>

    <div class="card">
      <h2>Games With Only 1 Made 3-Pointer ({len(data['one_three_games'])})</h2>
      <table>
        <thead><tr><th>Date</th><th>Season</th><th>Loc</th><th>Opponent</th><th>Score</th><th>3PT</th><th>Made By</th></tr></thead>
        <tbody>{one_rows_html}</tbody>
      </table>
    </div>

    <div class="card">
      <div class="toolbar">
        <h2 style="margin:0">First 3-Pointer Leaderboard ({len(data['player_leaderboard'])} players)</h2>
        <input id="player-filter" class="search" type="search" placeholder="Filter player..." />
      </div>
      <div class="table-scroll">
        <table id="player-table">
          <thead><tr><th class="num">#</th><th>Player</th><th class="num">First 3s</th></tr></thead>
          <tbody>{player_rows_html}</tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    const DATA = {bins_json};
    const MAX_VAL = {max_bar};
    const MED_MIN = {med_min_float};
    const MED_LABEL = "{med_str}";
    let mode = "all";
    let showCum = true;
    let activeIdx = {peak['min']};

    const svg = document.getElementById("chart");
    const NS = "http://www.w3.org/2000/svg";

    function el(tag, attrs = {{}}, text = null) {{
      const node = document.createElementNS(NS, tag);
      for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
      if (text !== null) node.textContent = text;
      return node;
    }}

    function clockRange(min) {{
      return min < 20 ? `1H ${{20 - min}}:00–${{19 - min}}:01` : `2H ${{40 - min}}:00–${{39 - min}}:01`;
    }}

    function updateDetail(idx) {{
      const d = DATA[idx];
      if (!d) return;
      document.getElementById("detail-title").textContent = `Minute ${{d.min}}–${{d.min + 1}} (${{clockRange(d.min)}})`;
      const wl = d.count > 0 ? ` • Record: ${{d.w}}-${{d.l}} (${{Math.round((d.w / d.count) * 100)}}% W)` : "";
      document.getElementById("detail-stats").textContent =
        `${{d.count}} game${{d.count === 1 ? "" : "s"}} (${{d.pct.toFixed(1)}}% • cum ${{d.cum_pct.toFixed(1)}}%)${{wl}}`;
      document.getElementById("detail-samples").textContent =
        d.samples.length ? `Examples: ${{d.samples.join("  •  ")}}` : "No games in this minute.";
    }}

    function render() {{
      svg.innerHTML = "";
      const W = 800, H = 270, padL = 40, padR = 44, padT = 20, padB = 36;
      const plotW = W - padL - padR, plotH = H - padT - padB;
      const barStep = plotW / DATA.length;
      const barW = Math.max(8, barStep - 4);

      const step = Math.max(10, Math.round(MAX_VAL / 4 / 5) * 5);
      for (let tick = 0; tick <= MAX_VAL; tick += step) {{
        const y = padT + plotH - (tick / MAX_VAL) * plotH;
        svg.appendChild(el("line", {{
          x1: padL, x2: W - padR, y1: y, y2: y,
          stroke: "var(--border)", "stroke-width": 1, "stroke-dasharray": tick === 0 ? "" : "2,3"
        }}));
        svg.appendChild(el("text", {{
          x: padL - 7, y: y + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 11
        }}, String(tick)));
      }}

      if (showCum) {{
        [0, 50, 100].forEach(pct => {{
          const y = padT + plotH - (pct / 100) * plotH;
          svg.appendChild(el("text", {{
            x: W - padR + 7, y: y + 4, "text-anchor": "start", fill: "var(--blue)", "font-size": 11
          }}, `${{pct}}%`));
        }});
      }}

      if (DATA.length > 20) {{
        const halfX = padL + 20 * barStep;
        svg.appendChild(el("line", {{
          x1: halfX, x2: halfX, y1: padT, y2: padT + plotH,
          stroke: "var(--amber)", "stroke-width": 1.25, "stroke-dasharray": "4,3"
        }}));
        svg.appendChild(el("text", {{
          x: halfX + 5, y: padT + 12, fill: "var(--amber)", "font-size": 11, "font-weight": 600
        }}, "2nd Half →"));
      }}

      const medX = padL + MED_MIN * barStep;
      svg.appendChild(el("line", {{
        x1: medX, x2: medX, y1: padT, y2: padT + plotH,
        stroke: "var(--muted)", "stroke-width": 1, "stroke-dasharray": "2,2"
      }}));
      svg.appendChild(el("text", {{
        x: medX + 5, y: padT + 12, fill: "var(--muted)", "font-size": 11
      }}, `Median (${{MED_LABEL}})`));

      DATA.forEach((d, i) => {{
        const x = padL + i * barStep + (barStep - barW) / 2;
        const totalH = (d.count / MAX_VAL) * plotH;
        const y = padT + plotH - totalH;
        const isActive = i === activeIdx;

        if (isActive) {{
          svg.appendChild(el("rect", {{
            x: padL + i * barStep, y: padT, width: barStep, height: plotH,
            fill: "var(--border)", opacity: 0.35, rx: 2
          }}));
        }}

        if (mode === "all") {{
          svg.appendChild(el("rect", {{
            x, y, width: barW, height: Math.max(0, totalH), rx: 2,
            fill: d.min >= 20 ? "var(--amber)" : "var(--gold)", opacity: isActive ? 1 : 0.85
          }}));
        }} else {{
          const wH = (d.w / MAX_VAL) * plotH;
          const lH = (d.l / MAX_VAL) * plotH;
          svg.appendChild(el("rect", {{
            x, y: padT + plotH - wH, width: barW, height: Math.max(0, wH), rx: 1,
            fill: "var(--green)", opacity: isActive ? 1 : 0.85
          }}));
          svg.appendChild(el("rect", {{
            x, y: padT + plotH - wH - lH, width: barW, height: Math.max(0, lH), rx: 1,
            fill: "var(--red)", opacity: isActive ? 1 : 0.82
          }}));
        }}

        if (d.count >= 16 || (isActive && d.count > 0)) {{
          svg.appendChild(el("text", {{
            x: x + barW / 2, y: y - 4, "text-anchor": "middle",
            fill: isActive ? "var(--fg)" : "var(--muted)", "font-size": 10.5, "font-weight": isActive ? 700 : 400
          }}, String(d.count)));
        }}

        if (i % 2 === 0 || i === DATA.length - 1) {{
          svg.appendChild(el("text", {{
            x: x + barW / 2, y: padT + plotH + 15, "text-anchor": "middle", fill: "var(--muted)", "font-size": 11
          }}, String(d.min)));
        }}

        const hit = el("rect", {{
          x: padL + i * barStep, y: padT, width: barStep, height: plotH + 18,
          fill: "transparent", style: "cursor:pointer"
        }});
        hit.addEventListener("mouseenter", () => {{ activeIdx = i; render(); updateDetail(i); }});
        hit.addEventListener("click", () => {{ activeIdx = i; render(); updateDetail(i); }});
        svg.appendChild(hit);
      }});

      if (showCum) {{
        const pts = DATA.map((d, i) => {{
          const cx = padL + i * barStep + barStep / 2;
          const cy = padT + plotH - (d.cum_pct / 100) * plotH;
          return `${{cx.toFixed(1)}},${{cy.toFixed(1)}}`;
        }}).join(" ");
        svg.appendChild(el("polyline", {{
          points: pts, fill: "none", stroke: "var(--blue)",
          "stroke-width": 2, "stroke-linejoin": "round", "pointer-events": "none"
        }}));
        const ad = DATA[activeIdx];
        if (ad) {{
          svg.appendChild(el("circle", {{
            cx: padL + activeIdx * barStep + barStep / 2,
            cy: padT + plotH - (ad.cum_pct / 100) * plotH,
            r: 3.5, fill: "var(--blue)", stroke: "var(--surface)", "stroke-width": 1.5, "pointer-events": "none"
          }}));
        }}
      }}

      svg.appendChild(el("text", {{
        x: padL + plotW / 2, y: H - 4, "text-anchor": "middle", fill: "var(--muted)", "font-size": 11
      }}, "Elapsed Game Minute (0 = tip-off, 20 = start of 2nd half)"));
    }}

    document.getElementById("btn-all").addEventListener("click", () => {{
      mode = "all";
      document.getElementById("btn-all").classList.add("active");
      document.getElementById("btn-wl").classList.remove("active");
      render();
    }});
    document.getElementById("btn-wl").addEventListener("click", () => {{
      mode = "wl";
      document.getElementById("btn-wl").classList.add("active");
      document.getElementById("btn-all").classList.remove("active");
      render();
    }});
    document.getElementById("chk-cum").addEventListener("change", (e) => {{
      showCum = e.target.checked;
      render();
    }});

    document.getElementById("player-filter").addEventListener("input", (e) => {{
      const q = e.target.value.trim().toLowerCase();
      document.querySelectorAll("#player-table tbody tr").forEach(tr => {{
        const name = tr.children[1].textContent.toLowerCase();
        tr.style.display = name.includes(q) ? "" : "none";
      }});
    }});

    render();
    updateDetail(activeIdx);
  </script>
</body>
</html>
"""


def generate_reports(
    csv_path: str = DEFAULT_OUTPUT_CSV,
    report_dir: str = DEFAULT_REPORT_DIR,
) -> GeneratedReports:
    """Generate Markdown and standalone interactive HTML reports from the CSV."""
    data = compute_report_data(csv_path)
    os.makedirs(report_dir, exist_ok=True)

    md_path = os.path.join(report_dir, "oakland_3pt_report.md")
    html_path = os.path.join(report_dir, "oakland_3pt_report.html")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown_report(data))

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(render_html_report(data))

    return GeneratedReports(
        markdown_path=md_path,
        html_path=html_path,
        total_games=data["total_games"],
        pbp_games=data["pbp_games"],
    )
