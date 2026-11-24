import requests
from bs4 import BeautifulSoup
import time
import os
import json
import re
from urllib.parse import urljoin
from parse_ougrizzlies import fetch_html, parse_play_by_play

import requests
from bs4 import BeautifulSoup
import time
import os
import json
import re
from urllib.parse import urljoin
from parse_ougrizzlies import fetch_html, parse_play_by_play
from parse_legacy_stats import parse_legacy_play_by_play
from generate_report import oakland_mbball_urls

print("Script starting...")

BASE_URL = "https://goldengrizzlies.com"

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip().replace(" ", "_")

def extract_season_year(url):
    # Extracts year from URL like .../schedule/2025-26 -> 2025-26
    match = re.search(r'schedule/(\d{4}-\d{2})', url)
    if match:
        return match.group(1)
    # Fallback for older formats if needed, or return 'unknown'
    return "unknown"

def process_season(season_url):
    season_year = extract_season_year(season_url)
    print(f"\n=== Processing Season: {season_year} ({season_url}) ===")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(season_url, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch schedule for {season_year}: {e}")
        return

    soup = BeautifulSoup(response.text, "lxml")
    
    # Adapt to potential different page structures if needed.
    # Standard sidearm schedule structure usually involves 'sidearm-schedule-game'
    games = soup.find_all("li", class_="sidearm-schedule-game")
    
    # If no games found via LI, try checking for a TABLE based schedule (older style)
    if not games: 
        print(f"  No 'li.sidearm-schedule-game' found. Checking for table-based schedule...")
        # Placeholder for table logic if we encounter it.
        # many sidearm sites use same structure back to ~2010.
        
    print(f"  Found {len(games)} scheduled games.")
    
    processed_count = 0
    
    # Pre-calculate season start/end years for date logic
    # Season is "2025-26" -> Start=2025, End=2026
    start_year = int(season_year.split("-")[0])
    end_year = start_year + 1
    
    for game in games:
        # Extract Date
        date_div = game.find("div", class_="sidearm-schedule-game-opponent-date")
        game_date_str = ""
        game_date_iso = "0000-00-00"
        
        if date_div:
            # Format usually: "Nov 10 (Fri)" or similar
            game_date_str = date_div.get_text(strip=True)
            # Clean it up: remove day name in parens
            # "Nov 10 (Fri)" -> "Nov 10"
            date_clean = re.sub(r'\(.*?\)', '', game_date_str).strip()
            
            # Parse to ISO
            try:
                # Need to add year. Logic: Oct-Dec = start_year, Jan-Jul = end_year
                # Helper dictionary for months
                months = {
                    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
                }
                parts = date_clean.split()
                if len(parts) >= 2:
                    month_str = parts[0][:3] # Ensure 3 chars
                    day = int(re.sub(r'\D', '', parts[1])) # Remove 'th', 'st' if any
                    
                    month_num = months.get(month_str, 0)
                    
                    year = start_year
                    if month_num < 8: # Arbitrary cutoff: Jan-July belong to end_year
                        year = end_year
                        
                    game_date_iso = f"{year}-{month_num:02d}-{day:02d}"
            except Exception as e:
                # print(f"Date parse error: {e}")
                pass

        # Check for boxscore link
        # Check for boxscore link
        # Legacy links might look like .../stats/2017-2018/file.html
        boxscore_element = game.find("a", href=re.compile(r"(boxscore|stats/.*\.html|stats/.*\.htm)", re.I))
        
        # Sometimes it's in a specific li class, sometimes just an 'a' tag in the game block
        if not boxscore_element:
             # Try specifically looking in the links section if it exists
             links_div = game.find("div", class_="sidearm-schedule-game-links")
             if links_div:
                 boxscore_element = links_div.find("a", string=re.compile("Box Score", re.I))
        
        href = None
        if boxscore_element:
            href = boxscore_element.get("href")

        # Fallback: Check for Recap link if no boxscore link found
        if not href:
            # Look for Recap link
            recap_element = game.find("a", string=re.compile("Recap", re.I))
            if not recap_element:
                 recap_li = game.find("li", class_="sidearm-schedule-game-links-recap")
                 if recap_li:
                     recap_element = recap_li.find("a")
            
            if recap_element:
                recap_href = recap_element.get("href")
                recap_url = urljoin(BASE_URL, recap_href)
                # print(f"  Checking Recap for boxscore: {recap_url}")
                try:
                    recap_html = fetch_html(recap_url)
                    recap_soup = BeautifulSoup(recap_html, "lxml")
                    
                    # Look for Stats/Box Score link in recap
                    bs_link = recap_soup.find("a", href=re.compile(r"(boxscore|stats/.*\.html|stats/.*\.htm)", re.I))
                    if not bs_link:
                         bs_link = recap_soup.find("a", string=re.compile("Box Score", re.I))
                    
                    if bs_link:
                        href = bs_link.get("href")
                        # print(f"  Found boxscore in recap: {href}")
                except Exception as e:
                    print(f"  Failed to fetch/parse recap: {e}")

        if not href:
            continue
            
        href = href # ensure href is set
        full_url = urljoin(BASE_URL, href)
        
        # Extract metadata
        opponent_div = game.find("div", class_="sidearm-schedule-game-opponent-name")
        opponent_name = "Unknown"
        if opponent_div:
            opponent_name = opponent_div.get_text(strip=True)
            # Clean up opponent name (remove ranking #, etc if desired)
        else:
             # Fallback for older layouts
             opponent_div = game.find("span", class_="sidearm-schedule-game-opponent-name")
             if opponent_div:
                 opponent_name = opponent_div.get_text(strip=True)

        game_id = "00000"
        match = re.search(r'boxscore/(\d+)', href)
        if match:
            game_id = match.group(1)
        else:
            # Try extracting from legacy html filename e.g. 0304iupu.html
            # Just use the filename base as ID
            base = os.path.basename(href)
            base_cleaned = re.sub(r'\.html?', '', base, flags=re.I)
            if base_cleaned:
                game_id = base_cleaned
            
        safe_opponent = sanitize_filename(opponent_name)
        
        # New Filename Format: play_by_play_YYYY-MM-DD_ID_Opponent.json
        # Prefix with date so it sorts naturally.
        # Fallback to season year if date parse failed (0000-00-00) -- hopefully rare
        
        if not os.path.exists("build"):
            os.makedirs("build")
        filename = os.path.join("build", f"play_by_play_{game_date_iso}_{game_id}_{safe_opponent}.json")
        
        if os.path.exists(filename):
            # print(f"  Skipping {filename}, already exists.")
            continue
            
        print(f"  Processing Game {game_id} vs {opponent_name} ({game_date_iso})...")
        
        try:
            html = fetch_html(full_url)
            
            # Soft 404 detection: Sidearm sometimes serves a generic wrapper with no stats
            # If "Play-by-Play" is missing, assume it's a soft 404 and try fallbacks (FTP)
            if html and not re.search(r'play-by-play', html, re.IGNORECASE):
                # print("    Soft 404 detected (no 'Play-by-Play' marker), ignoring content.")
                html = None

            
            # Detect format
            # New format (sidearm XML-ish rendered) usually handled by parse_play_by_play
            # Legacy format (text based) usually has "Welcome to the exciting world of..." or specific pre tags?
            # Or check if parse_play_by_play returns empty?
            
            # Heuristic: Check if basic parse returns plays. If not, try legacy.
            plays = parse_play_by_play(html)
            
            if not plays:
                # Try legacy
                # print("    Standard parse failed/empty, trying legacy parse...")
                plays = parse_legacy_play_by_play(html)
                
                # Fallback: If legacy parse empty and URL is .html, try .htm specific for legacy FTP issues
                if not plays and re.search(r'\.html?$', full_url, re.I):
                    try:
                        fallback_url = re.sub(r'\.html?$', '.htm', full_url, flags=re.I)
                        # print(f"    Legacy parse failed, trying .htm fallback: {fallback_url}")
                        html_sec = fetch_html(fallback_url)
                        plays_sec = parse_legacy_play_by_play(html_sec)
                        if plays_sec:
                            plays = plays_sec
                            print(f"    Fallback to .htm succeeded: {len(plays)} plays.")
                    except Exception as e:
                        # print(f"    Fallback failed: {e}")
                        pass
                
                # Fallback: Try FTP legacy site if still empty
                if not plays:
                     try:
                         # Construct FTP URL: http://oaklandu_ftp.sidearmsports.com/old_site/sports/m-baskbl/stats/{YYYY-YYYY}/{filename}.htm
                         # Need full 4-digit years for season
                         ftp_season = f"{start_year}-{end_year}"
                         
                         # extract filename base (e.g. sdsu0131.htm or .html)
                         base_name = os.path.basename(full_url)
                         # Force .htm extension as common on FTP
                         base_name_no_ext = os.path.splitext(base_name)[0]
                         ftp_filename = base_name_no_ext + ".htm"
                         
                         ftp_url = f"http://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats/{ftp_season}/{ftp_filename}"
                         
                         # print(f"    Trying FTP fallback: {ftp_url}")
                         html_ftp = fetch_html(ftp_url)
                         plays_ftp = parse_legacy_play_by_play(html_ftp)
                         if plays_ftp:
                             plays = plays_ftp
                             print(f"    Fallback to FTP ({ftp_url}) succeeded: {len(plays)} plays.")
                     except Exception as e:
                         # print(f"    FTP Fallback failed: {e}")
                         pass

                if plays:
                    pass

            
            if not plays:
                print(f"    Warning: No plays parsed for {filename} (tried both formats). Skipping save.")
                # Optional: Delete if exists to clean up
                if os.path.exists(filename):
                    os.remove(filename)
            else:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(plays, f, indent=2)
                    
                processed_count += 1
                # Be polite
                time.sleep(1)
            
        except Exception as e:
            print(f"    Error processing {full_url}: {e}")

    print(f"  Season {season_year} complete. Processed {processed_count} new games.")

def batch_process():
    # Only process a subset for testing or all?
    # User said "parse all available". 
    # Let's verify if we should run ALL. It might take a while.
    # I'll check if the user wants to run all or just a test. 
    # The request was "run the plan" -> "scrape all available".
    # I will reverse the list to start from newest (2025-26) backwards.
    
    urls = oakland_mbball_urls
    
    for url in urls:
        process_season(url)

if __name__ == "__main__":
    batch_process()
