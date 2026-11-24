import requests
from bs4 import BeautifulSoup
import json
import re

# URL for the Golden Grizzlies game
PLAY_BY_PLAY_URL = "https://goldengrizzlies.com/sports/mens-basketball/stats/2025-26/youngstown-state/boxscore/13058"

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_html(url):
    print(f"Fetching {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=30, verify=False)
    response.raise_for_status()
    return response.text

def parse_score_cell(cell_text):
    """
    Parses score from cell like "36 (+3)" or just "36".
    Returns int score.
    """
    # Remove (+3) or similar
    text = re.sub(r'\s*\(.*?\)', '', cell_text).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None

def detect_shot_type(text):
    t = text.lower()
    if "free throw" in t:
        return "ft"
    if "3ptr" in t or "3-pt" in t:
        return "3pt"
    # "jumper", "layup", "dunker", "tipin" imply 2pt if not 3ptr
    if any(x in t for x in ["jumper", "layup", "dunk", "tipin", "paint"]):
        return "2pt"
    return None

def classify_event(text):
    t = text.lower()
    if "good" in t:
        return "shot", "made"
    if "miss" in t:
        return "shot", "missed"
    if "rebound" in t:
        return "rebound", None
    if "assist" in t:
        return "assist", None
    if "turnover" in t:
        return "turnover", None
    if "foul" in t:
        return "foul", None
    if "sub" in t and ("in" in t or "out" in t):
        return "substitution", None
    if "timeout" in t:
        return "timeout", None
    
    return "other", None

def get_player_name(text):
    # Format typically: "GOOD 3PTR by CARROLL,CRIS" or "FOUL by HOUGE,MICHAEL"
    # Sometimes "by TEAM"
    if " by " in text:
        parts = text.split(" by ")
        if len(parts) > 1:
            # Take the part after "by", but stop at "(" if exists (e.g. "(in the paint)")
            name_part = parts[1].split("(")[0].strip()
            return name_part
    return None

def parse_play_by_play(html):
    soup = BeautifulSoup(html, "lxml")
    plays = []
    
    # Locate period containers
    # usually #period-1, #period-2, etc.
    periods = soup.find_all("div", id=re.compile(r"period-\d+"))
    
    current_away_score = 0
    current_home_score = 0

    # Try to find team names from the first period table headers
    away_team_name = "Away"
    home_team_name = "Home"
    
    if periods:
        first_table = periods[0].find("table", class_="play-by-play")
        if first_table:
            ths = first_table.find("thead").find_all("th")
            if len(ths) >= 6:
                # Based on inspection: index 1 is Away Name, index 5 is Home Name
                cand_away = ths[1].get_text(strip=True)
                cand_home = ths[5].get_text(strip=True)
                if cand_away: away_team_name = cand_away
                if cand_home: home_team_name = cand_home

    print(f"Detected Team Names: Away='{away_team_name}', Home='{home_team_name}'")

    for period_div in periods:
        period_id = period_div.get("id")
        # Extract period number from "period-1" -> 1
        period_num = int(period_id.split("-")[-1])
        
        table = period_div.find("table", class_="play-by-play")
        if not table:
            continue
            
        rows = table.find("tbody").find_all("tr")
        
        last_clock = None
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            # Column mapping based on inspection:
            # 0: Time
            # 1: Away Text (Oakland?)
            # 2: Away Score
            # 5: Home Text (YSU?)
            # 4: Home Score (Actually index 4 is home score in previous logic?)
            # Let's re-verify indices from previous code:
            # away_score_raw = cells[2]
            # home_score_raw = cells[4]
            # home_text = cells[5]
            
            clock = cells[0].get_text(strip=True)
            if not clock:
                if last_clock:
                    clock = last_clock
            else:
                last_clock = clock
                
            away_text = cells[1].get_text(" ", strip=True)
            away_score_raw = cells[2].get_text(strip=True)
            
            home_score_raw = cells[4].get_text(strip=True)
            home_text = cells[5].get_text(" ", strip=True)
            
            # Update running scores if available
            a_score = parse_score_cell(away_score_raw)
            h_score = parse_score_cell(home_score_raw)
            
            if a_score is not None:
                current_away_score = a_score
            if h_score is not None:
                current_home_score = h_score
                
            # Determine which team triggered the event
            if away_text:
                team = away_team_name
                text = away_text
            elif home_text:
                team = home_team_name
                text = home_text
            else:
                continue # Empty row?
            
            event_type, shot_result = classify_event(text)
            shot_type = detect_shot_type(text) if event_type == "shot" else None
            player = get_player_name(text)

            play = {
                "period": period_num,
                "clock": clock,
                "team": team,
                "player": player,
                "event_type": event_type,
                "shot_type": shot_type,
                "shot_result": shot_result,
                "event_detail": text,
                "score": {
                    away_team_name: current_away_score,
                    home_team_name: current_home_score
                },
                "raw_text": text
            }
            
            plays.append(play)
            
    return plays

if __name__ == "__main__":
    try:
        html = fetch_html(PLAY_BY_PLAY_URL)
        plays = parse_play_by_play(html)
        
        outfile = "play_by_play.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(plays, f, indent=2)
            
        print(f"Successfully parsed {len(plays)} plays. Saved to {outfile}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
