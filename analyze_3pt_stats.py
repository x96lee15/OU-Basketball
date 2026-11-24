
import os
import json
import csv
import re
import glob

def parse_time_str(time_str):
    return time_str

OAKLAND_ALIASES = ["OAK", "OAKLAND", "Oak", "Golden Grizzlies", "Oakland University", "OU", "M-514"]

KNOWN_OAKLAND_PLAYERS = [
    "BADER", "KANGAS", "BENSON", "JONES, JOHNATHON", "JONES, JOHN",
    "MONDY", "PETROS", "VALENTINE, DREW", "DREW VALENTINE", "VALENTINE", 
    "WILLIAMS, DANTE", "DANTE WILLIAMS", "BASS, RYAN", "RYAN BASS",
    "CARTER, RAPHAEL", "RAPHAEL CARTER", "BAENZIGER", "HAMILTON, REGGIE", "NELSON, DERICK",
    "HUDSON, WILL", "WATERSTRADT", "CUSHINGBERRY", "SAMUELS", "MAYNARD",
    "FELDER", "KAHLIL", "DANIELS, NICK", "HOOPER, MAX", "HOOPER", "HAYES, JALEN", "MCCUNE",
    "HILL-MAIS", "NORRIS, BRADEN", "CUMBERLAND", "NEWMAN, KARMARI", "BRECHTING"
]

def is_oakland(team_name):
    if not team_name: return False
    # Check if any alias Matches as a word (case-insensitive)
    t = team_name.upper()
    for alias in OAKLAND_ALIASES:
        # Escape alias just in case, add word boundaries
        if re.search(rf"\b{re.escape(alias.upper())}\b", t):
            return True
    return False

def is_oakland_play(play):
    # Check team name first
    if is_oakland(play.get("team")):
        return True
        
    # Fallback: Check player name
    player = play.get("player")
    if player:
        p_upper = player.upper()
        for kp in KNOWN_OAKLAND_PLAYERS:
            # Simple substring match for player names as they are specific enough
            if kp in p_upper:
                return True
    return False

def get_first_3pt(plays):
    first_3pt = None
    count_3pt = 0
    
    for play in plays:
        if play.get("shot_type") == "3pt" and play.get("shot_result") == "made":
            if is_oakland_play(play):
                count_3pt += 1
                if first_3pt is None:
                    first_3pt = play
                
    return first_3pt, count_3pt

def analyze_all_files():
    # Find all play_by_play_*.json files
    files = glob.glob(os.path.join("build", "play_by_play_*.json"))
    print(f"Found {len(files)} game files.")
    
    results = []
    
    for filename in files:
        with open(filename, "r", encoding="utf-8") as f:
            try:
                plays = json.load(f)
            except json.JSONDecodeError:
                print(f"Error reading {filename}")
                continue
                
        # filename format: play_by_play_{YYYY-MM-DD}_{game_id}_{opponent}.json
        # Old format: play_by_play_{season}_{game_id}_{opponent}.json
        base_name = os.path.basename(filename)
        parts = base_name.replace(".json", "").split("_")
        
        season = "Unknown"
        game_date = "Unknown"
        game_id = "Unknown"
        opponent = "Unknown"
        
        # Heuristic for filename parsing
        if len(parts) >= 6:
            # Check if parts[3] looks like a date (2025-01-01) or season (2025-26)
            token = parts[3]
            if re.match(r'\d{4}-\d{2}-\d{2}', token):
                # It's a date
                game_date = token
                game_id = parts[4]
                opponent = "_".join(parts[5:])
                # Infer season from date? 
                # e.g. 2024-11-10 -> 2024-25
                # e.g. 2025-03-01 -> 2024-25
                try:
                    y, m, d = map(int, game_date.split("-"))
                    if m >= 8: # start of season
                        season = f"{y}-{str(y+1)[-2:]}"
                    else: # end of season
                        season = f"{y-1}-{str(y)[-2:]}"
                except:
                    pass
            elif re.match(r'\d{4}-\d{2}', token):
                # It's a season string likely
                season = token
                game_id = parts[4]
                opponent = "_".join(parts[5:])
        elif len(parts) >= 5:
             # Fallback
             game_id = parts[3]
             opponent = "_".join(parts[4:])
        
        first_3pt, count_3pt = get_first_3pt(plays)
        
        row = {
            "Season": season,
            "GameDate": game_date,
            "GameID": game_id,
            "Opponent": opponent,
            "Total_3PM": count_3pt,
            "First_3Pt_Player": first_3pt.get("player") if first_3pt else None,
            "First_3Pt_Time": first_3pt.get("clock") if first_3pt else None,
            "First_3Pt_Period": first_3pt.get("period") if first_3pt else None,
            "First_3Pt_Team": first_3pt.get("team") if first_3pt else None
        }
            
        results.append(row)
        
    output_file = "oakland_complete_3pt_stats.csv"
    
    if not results:
        print("No results to save.")
        return

    keys = results[0].keys()
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(results)
        
    print(f"Saved stats to {output_file}")
    
if __name__ == "__main__":
    analyze_all_files()
