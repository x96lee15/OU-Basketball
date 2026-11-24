import requests
import re
import csv
import time
from bs4 import BeautifulSoup

BASE_URL = "https://www.espn.com"
SCHEDULE_URL = "https://www.espn.com/mens-college-basketball/team/schedule/_/id/2473/season/{}"
OUTPUT_FILE = "oakland_first_threes_2002_2018.csv"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_schedule_urls(season):
    """Return list of (game date, opponent, play-by-play URL) for the given season."""
    url = SCHEDULE_URL.format(season)
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    games = []

    # Find links that contain ESPN game IDs
    for row in soup.select("table tr"):
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        # Look for links like .../game/_/gameId/401234567...
        link = row.find("a", href=re.compile(r"/game/_/gameId/\d+"))
        if not link:
            continue

        href = link["href"]
        m = re.search(r"gameId/(\d+)", href)
        if not m:
            continue

        game_id = m.group(1)

        date = cols[0].get_text(strip=True)
        opponent = cols[1].get_text(strip=True)

        # Build the Play-by-Play page URL directly
        pbp_url = f"https://www.espn.com/mens-college-basketball/playbyplay/_/gameId/{game_id}"

        games.append((date, opponent, pbp_url))

    print("DEBUG: games extracted:", games)
    return games


def parse_first_oakland_three(url):
    """Return (player, time, period, description) of first made 3PT FG by Oakland."""
    r = requests.get(url, headers=HEADERS)
    html = r.text

    print(url)

    # Try to find Oakland’s first made three-point
    pattern = re.compile(
        r'"clock":\{"displayValue":"(.*?)".*?"period":\{"number":(\d+).*?\}.*?"text":"(.*?made Three Point.*?)","team":\{"id":\d+.*?"displayName":"(Oakland.*?)"',
        re.DOTALL
    )
    matches = pattern.findall(html)
    if not matches:
        return None

    def parse_time(clock):
        m, s = map(int, clock.split(":"))
        return m * 60 + s

    matches.sort(key=lambda x: (-int(x[1]), -parse_time(x[0])))
    time_display, period_num, play_text, _ = matches[0]

    player_match = re.search(r'^(.*?) made Three Point', play_text)
    player = player_match.group(1).strip() if player_match else "Unknown"
    period = "1st Half" if period_num == "1" else "2nd Half"

    return player, time_display, period, play_text

def main():
    #seasons = list(range(2003, 2019))  # ESPN uses the ending year for season URLs
    seasons = [2025]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Season", "Date", "Opponent", "Player", "Time", "Period", "Description"])

        for season in seasons:
            print(f"Processing {season-1}-{str(season)[-2:]} season...")

            try:
                games = get_schedule_urls(season)
            except Exception as e:
                print(f"  Failed to load schedule for {season}: {e}")
                continue

            for date, opponent, p_url in games:
                try:
                    data = parse_first_oakland_three(p_url)
                    if data:
                        player, time_display, period, desc = data
                        writer.writerow([f"{season-1}-{str(season)[-2:]}", date, opponent, player, time_display, period, desc])
                        print(f"   {date}: {player} {time_display} ({period})")
                    else:
                        print(f"   {date}: No 3PT found")
                except Exception as e:
                    print(f"   Error parsing {p_url}: {e}")
                time.sleep(1.0)  # Be polite to ESPN servers

    print(f"\n✅ Done! Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
