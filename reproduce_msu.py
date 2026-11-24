
from parse_legacy_stats import parse_legacy_play_by_play
import json

filename = "msu1227.html"
print(f"Parsing {filename}...")

with open(filename, "r", encoding="utf-8") as f:
    html = f.read()

plays = parse_legacy_play_by_play(html)
print(f"Total plays found: {len(plays)}")

if len(plays) > 0:
    print("First 5 plays:")
    print(json.dumps(plays[:5], indent=2))
else:
    print("No plays found. Dumping first 50 lines of Play-by-Play section:")
    if "Play-by-Play" in html:
        lines = html.split("Play-by-Play")[1].splitlines()[:50]
        for line in lines:
            print(f"'{line}'")
