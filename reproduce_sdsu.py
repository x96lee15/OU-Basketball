
from parse_legacy_stats import parse_legacy_play_by_play
import json

filename = "sdsu0131.html"
print(f"Parsing {filename}...")

with open(filename, "r", encoding="utf-8") as f:
    html = f.read()

plays = parse_legacy_play_by_play(html)
print(f"Total plays found: {len(plays)}")

if len(plays) > 0:
    print("First 5 plays:")
    print(json.dumps(plays[:5], indent=2))
else:
    print("No plays found. Dumping detected <pre> tags or Play-by-Play section:")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    pre_tags = soup.find_all("pre")
    if pre_tags:
        print(f"Found {len(pre_tags)} pre tags.")
        for i, pre in enumerate(pre_tags):
            print(f"--- PRE TAG {i} ---")
            print(pre.get_text()[:500])
    else:
        print("No pre tags found.")
        
    headers = soup.find_all("h2")
    for h in headers:
        print(f"Header: {h.get_text()}")
