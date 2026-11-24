
from parse_legacy_stats import parse_legacy_play_by_play
import json
import os

filename = "ore1117.html"
if not os.path.exists(filename):
    print(f"Error: {filename} not found.")
    exit(1)

print(f"Parsing {filename}...")
with open(filename, "r", encoding="utf-8") as f:
    html = f.read()

plays = parse_legacy_play_by_play(html)
print(f"Total plays found: {len(plays)}")

if len(plays) > 0:
    print("First 3 plays:")
    print(json.dumps(plays[:3], indent=2))
else:
    print("No plays found!")
