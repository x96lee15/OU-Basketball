"""Parse Oakland basketball season box scores to extract first 3-pointer data."""

import csv
import re
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

oakland_mbball_urls = [
    #"https://goldengrizzlies.com/sports/mens-basketball/schedule/2025-26",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2024-25",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2023-24",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2022-23",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2021-22",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2020-21",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2019-20",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2018-19",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2017-18",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2016-17",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2015-16",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2014-15",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2013-14",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2012-13",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2011-12",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2010-11",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2009-10",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2008-09",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2007-08",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2006-07",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2005-06",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2004-05",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2003-04",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2002-03",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2001-02",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2000-01",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1999-00",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1998-99",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1997-98",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1996-97",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1995-96",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1994-95",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1993-94",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1992-93",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1991-92",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1990-91",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1989-90",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1988-89",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1987-88",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1986-87",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1985-86",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1984-85"
]

# Constants
DEBUG = False
BASE_URL = "https://goldengrizzlies.com"
SCHEDULE_URL = f"{BASE_URL}/sports/mens-basketball/schedule/2024-25"
REQUEST_TIMEOUT = 10  # seconds
OUTPUT_FILE = "oakland_first_3pts.csv"
CSV_FIELDNAMES = [
    "Oakland_First_3pt_Time",
    "Oakland_First_3pt_Player",
    "Oakland_First_3pt_Half",
    "Game",
    "Boxscore_URL",
    "Opponent_First_3pt_Time",
    "Opponent_First_3pt_Player",
    "Opponent_First_3pt_Half",
]

# Compile regex patterns once for efficiency
THREE_PT_PATTERN = re.compile(r"GOOD\s+3PT", re.IGNORECASE)
FIRST_HALF_PATTERN = re.compile(r"(1[0-9]:|[5-9]:)")


def get_boxscore_links(url) -> List[str]:
    """
    Collect all unique box score URLs from the season schedule page.
    
    Returns:
        List of unique box score URLs.
        
    Raises:
        requests.RequestException: If the request fails.
    """
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Error fetching schedule: {e}")
        raise

    soup = BeautifulSoup(response.text, "html.parser")

    # Use set for O(1) duplicate checking, then convert to list
    links: Set[str] = set()
    
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "boxscore" in href:
            # Use urljoin to handle both relative and absolute URLs properly
            url = urljoin(BASE_URL, href)
            #if "defiance" in url:
            links.add(url)
    
    return links


def detect_oakland_side(soup: BeautifulSoup) -> str:
    """
    Determine which column (left or right) contains Oakland's play-by-play data.
    
    Args:
        soup: BeautifulSoup object of the box score page.
        
    Returns:
        'left' or 'right' indicating Oakland's column position.
    """
    header_cells = soup.select("table thead tr th")
    
    for i, th in enumerate(header_cells):
        text = th.get_text(strip=True)
        #print("text:", text)
        if "Oak" in text:
            # Determine side based on position relative to midpoint
            return "left" if i < len(header_cells) // 2 else "right"
    
    # Default fallback
    return "left"


def is_three_pointer(play_text: str) -> bool:
    """
    Check if a play description indicates a made 3-pointer.
    
    Args:
        play_text: The play description text.
        
    Returns:
        True if the play is a made 3-pointer, False otherwise.
    """
    return bool(THREE_PT_PATTERN.search(play_text))


def determine_half(time_text: str) -> str:
    """
    Determine which half of the game based on the game clock.
    
    Args:
        time_text: The game clock time (e.g., "15:30", "3:45").
        
    Returns:
        '1st Half' or '2nd Half'.
    """
    return "1st Half" if FIRST_HALF_PATTERN.match(time_text) else "2nd Half"


def parse_boxscore(box_url: str) -> Optional[Dict[str, str]]:
    """
    Extract first made 3-pointer for each team from a box score page.
    
    Args:
        box_url: URL of the box score page.
        
    Returns:
        Dictionary containing first 3-pointer data for both teams, or None if parsing fails.
    """
    try:
        response = requests.get(box_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Error fetching box score {box_url}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    oakland_side = detect_oakland_side(soup)
    rows = soup.find_all("tr")

    first_oakland_3: Optional[Tuple[str, str, str]] = None
    first_opponent_3: Optional[Tuple[str, str, str]] = None

    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 6:
            continue

        time_text = tds[0].get_text(strip=True)
        left_play = tds[1].get_text(strip=True)
        right_play = tds[5].get_text(strip=True)

        half = determine_half(time_text)

        # Assign plays based on Oakland's side
        oak_play, opp_play = (left_play, right_play) if oakland_side == "left" else (right_play, left_play)

        if DEBUG: print("time: ", time_text)
        if DEBUG: print("lp:", left_play)
        if DEBUG: print("rp:", right_play)
        team = tds[3].find("img")
        if team:
            #print("team:",team['alt'])
            team = team['alt']
        else:
            team = ""
        
        if DEBUG: print("team:", team)

        if "oakland" in team.lower():
            if DEBUG: print("oak detected")
            if left_play:
                if DEBUG: print("oak left")
                oak_play = left_play
                opp_play = right_play
            else:
                if DEBUG: print("oak right")
                oak_play = right_play
                opp_play = left_play

        if DEBUG: print("oak_play:", oak_play)
        if DEBUG: print("opp_play:", opp_play)

        # Check for first 3-pointers
        if not first_oakland_3 and is_three_pointer(oak_play) and "oakland" in team.lower():
            first_oakland_3 = (time_text, oak_play, half)
        if not first_opponent_3 and is_three_pointer(opp_play) and "oakland" not in team.lower():
            first_opponent_3 = (time_text, opp_play, half)

        if DEBUG: print("first_oak_3", first_oakland_3)
        if DEBUG: print("----")

        #print("oakland:", first_oakland_3)
        #print("opp:", first_opponent_3)

        # Exit early if both found
        #if first_oakland_3 and first_opponent_3:
        if first_oakland_3:
            break

    # Extract game title for identification
    game_title = soup.title.get_text(strip=True) if soup.title else box_url

    # Build result dictionary
    return {
        "Oakland_First_3pt_Time": first_oakland_3[0] if first_oakland_3 else "",
        "Oakland_First_3pt_Player": first_oakland_3[1] if first_oakland_3 else "",
        "Oakland_First_3pt_Half": first_oakland_3[2] if first_oakland_3 else "",
        "Game": game_title,
        "Boxscore_URL": box_url,
        "Opponent_First_3pt_Time": first_opponent_3[0] if first_opponent_3 else "",
        "Opponent_First_3pt_Player": first_opponent_3[1] if first_opponent_3 else "",
        "Opponent_First_3pt_Half": first_opponent_3[2] if first_opponent_3 else "",
    }


def unit_test() -> None:
    data = parse_boxscore("https://goldengrizzlies.com/sports/mens-basketball/stats/2019-20/cleveland-state/boxscore/6949")

def main() -> None:
    """Main execution function."""
    print("Fetching schedule...")
    
    for season in oakland_mbball_urls:
        print(season)

        try:
            box_links = get_boxscore_links(season)
        except requests.RequestException:
            print("❌ Failed to fetch schedule. Exiting.")
            return
    
        print(f"Found {len(box_links)} box scores.")

        results: List[Dict[str, str]] = []
        failed_count = 0
    
        for i, link in enumerate(box_links, 1):
            print(f"[{i}/{len(box_links)}] Parsing {link}...")
            #data = parse_boxscore("https://goldengrizzlies.com/sports/mens-basketball/stats/2019-20/cleveland-state/boxscore/6949")
            #return
            data = parse_boxscore(link)
        
            if data:
                results.append(data)
            else:
                failed_count += 1
                print(f"⚠️  Skipping {link} due to parsing error.")

        # Write results to CSV
        try:
            with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
                writer.writeheader()
                writer.writerows(results)
        
            print(f"\n✅ Done! Successfully parsed {len(results)} box scores.")
            if failed_count > 0:
                print(f"⚠️  {failed_count} box score(s) failed to parse.")
            print(f"📄 Data saved to {OUTPUT_FILE}")
        
        except IOError as e:
            print(f"❌ Error writing to CSV file: {e}")


if __name__ == "__main__":
    main()
