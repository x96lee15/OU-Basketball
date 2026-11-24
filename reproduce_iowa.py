
from parse_legacy_stats import parse_legacy_play_by_play
import json

with open("iowa1123.html", "r", encoding="utf-8") as f:
    html = f.read()

print("Parsing iowa1123.html...")
plays = parse_legacy_play_by_play(html)

print(f"Total plays parsed: {len(plays)}")
print("Plays found in 1st Period:")
for p in plays:
    if p['clock'] in ["19:24", "19:16"]: 
        print(json.dumps(p, indent=2))
        
# Inspect raw lines from file around 19:24
print("\n--- Inspecting raw lines around 19:24 ---")
lines = html.splitlines()
for line in lines:
    if "19:24" in line or "19:16" in line:
        print(f"RAW: '{line}'")
