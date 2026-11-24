import re
from bs4 import BeautifulSoup

def parse_legacy_play_by_play(html):
    """
    Parses legacy text-based play-by-play (e.g., 2017-18).
    Returns list of play dictionaries matching the structure of parse_ougrizzlies.py.
    """
    soup = BeautifulSoup(html, "lxml")
    
    # Legacy logs often put the PBP in a <pre> tag or just raw text in the body 
    # if it's a specific .html#GAME.PLY page.
    
    # Try to extract team names from title or header
    # Convention usually: Visitor vs Home
    home_team_name = "Home"
    vis_team_name = "Visitor"

    title_tag = soup.find("title")
    if title_tag:
        t_text = title_tag.get_text().strip()
        # Split by " vs " or " vs. "
        # e.g. "Oakland University vs South Dakota State (01/31/09...)"
        parts = re.split(r'\s+vs\.?\s+', t_text, flags=re.I)
        if len(parts) >= 2:
             vis_candidate = parts[0].strip()
             # Home part might have date/location attached in parens
             # "South Dakota State (01/31/09...)"
             # Safer: just take everything before the first '('
             home_part = parts[1]
             home_team_name = home_part.split('(')[0].strip()
             vis_team_name = vis_candidate
             
             # print(f"  Extracted teams: Vis='{vis_team_name}', Home='{home_team_name}'")


    # If it's the table format (e.g. msu1227.html), it might not use <pre> tags for PBP.
    # Check for period headers with "Play-by-Play"
    period_headers = soup.find_all(re.compile(r"h[1-6]"), string=re.compile(r"Period Play-by-Play", re.I))
    if period_headers:
         return parse_legacy_table_pbp(soup, home_team_name, vis_team_name)

    # Check for table-based PBP that doesn't use H tags (e.g. SDSU 2009)
    # Look for table with "HOME TEAM" and "VISITORS" in header
    tables = soup.find_all("table")
    for t in tables:
        txt = t.get_text().lower()
        # Keywords that strongly suggest PBP table vs generic box score
        if "home team" in txt and "visitors" in txt and "time" in txt and "score" in txt:
             return parse_legacy_table_pbp(soup, home_team_name, vis_team_name)
         
    pre_tags = soup.find_all("pre")
    text_content = ""
    
    # Find the pre tag that looks like PBP
    for pre in pre_tags:
        text = pre.get_text()
        if "Play-by-Play" in text or "HOME TEAM:" in text:
            text_content += "\n" + text
            
    # If no pre tags, try getting all text if it looks like a raw text page
    if not text_content:
        text_content = soup.get_text()
        
    lines = text_content.splitlines()
    plays = []
    
    # Regex to find the time column in the middle
    # Structure: [Home Event] [Time] [Score] [Margin] [Visitor Event]
    # Time is roughly MM:SS
    # Score is N-N
    # Margin is H N or V N
    
    # Regex breakdown:
    # ^                     Start of line
    # (?P<home_text>.*?)    Capture Home Event (non-greedy)
    # \s+                   Whitespace separator
    # (?P<clock>\d{1,2}:\d{2}) Capture Clock (e.g. 19:45)
    # \s*                   Whitespace
    # (?P<score>\d+-\d+)?   Optional Score (e.g. 2-0)
    # \s*                   Whitespace
    # (?P<margin>[HV]\s+\d+)? Optional Margin (e.g. H 2)
    # \s*                   Whitespace
    # (?P<vis_text>.*)$     Capture Visitor Event (rest of line)
    
    # Regex for header line: "HOME TEAM: Oakland ... VISITORS: IUPUI"
    # Note: text might be spread or have extra spaces.
    # Defaults already set above, but specific lines might override
    
    for line in lines:
        if "HOME TEAM:" in line and "VISITORS:" in line:
            # HOME TEAM: Oakland             TIME   SCORE  MAR  VISITORS: IUPUI
            # Parse simplistic
            try:
                # Split by logic
                # Find "HOME TEAM:" index
                h_idx = line.find("HOME TEAM:")
                v_idx = line.find("VISITORS:")
                
                # Assume HOME TEAM comes first usually?
                if h_idx < v_idx:
                    # HOME TEAM: [Name] ... VISITORS: [Name]
                    # This line format in the chunk is:
                    # HOME TEAM: Oakland TIME SCORE MAR VISITORS: IUPUI
                    # We can try to grab text between "HOME TEAM:" and "TIME"
                    # But "TIME" might not be strictly there or stick to columns.
                    
                    # Simpler regex for the header line
                    # HOME TEAM:\s+(?P<home>.*?)\s+(?:TIME|SCORE|MAR)\s+.*VISITORS:\s+(?P<vis>.*)
                    header_match = re.search(r'HOME TEAM:\s+(?P<home>.*?)\s+(?:TIME|SCORE|MAR).*VISITORS:\s+(?P<vis>.*)', line)
                    if header_match:
                        home_team_name = header_match.group("home").strip()
                        vis_team_name = header_match.group("vis").strip()
                    else:
                        # Falback, just take substring
                        pass
            except:
                pass
            break

    # Updated Regex to handle lines that start with the clock (Visitor only events where leading space was stripped)
    # ^(?:(?P<home_text>.*?)\s+)?(?P<clock>\d{1,2}:\d{2}) ...
    line_regex = re.compile(r'^(?:(?P<home_text>.*?)\s+)?(?P<clock>\d{1,2}:\d{2})\s*(?P<score>\d+-\d+)?\s*(?P<margin>[HV]\s+\d+)?\s*(?P<vis_text>.*)$')
    
    current_period = 0
    
    # Heuristic for period detection
    # "1st PERIOD" or "2nd PERIOD" in text
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
            
        # Check for period headers
        if "1st PERIOD" in line_clean:
            current_period = 1
            continue
        elif "2nd PERIOD" in line_clean:
            current_period = 2
            continue
        elif "OT PERIOD" in line_clean:
            current_period = 3 # or increment
            continue
            
        match = line_regex.match(line_clean)
        if match:
            home_text = match.group("home_text")
            if home_text:
                home_text = home_text.strip()
            else:
                home_text = ""
                
            clock = match.group("clock")
            score_str = match.group("score")
            # margin = match.group("margin")
            vis_text = match.group("vis_text").strip()
            
            # Skip header lines like "HOME TEAM: Oakland TIME SCORE..." which might match the regex
            if "HOME TEAM" in home_text or "VISITORS" in vis_text:
                continue
                
            # If line is just dashes
            if "---" in home_text or "---" in vis_text:
                continue

            # Determine who did what
            # If home_text is present, it's a home event.
            # If vis_text is present, it's a visitor event.
            # Sometimes BOTH are present? e.g. "SUB IN" on one side, "SUB OUT" on other? 
            # Or "REBOUND" on left, "MISSED" on right?
            # Yes, standard stat crew format can have events on same line if they happen at same time.
            
            events = []
            
            if home_text:
                events.append({"team": home_team_name, "text": home_text})
            if vis_text:
                events.append({"team": vis_team_name, "text": vis_text})
                
            for event in events:
                text = event["text"]
                team = event["team"]
                
                # Classify event
                event_type, shot_result, shot_type = classify_event_legacy(text)
                player = get_player_name_legacy(text)
                
                play = {
                    "period": current_period,
                    "clock": clock,
                    "team": team, # 'Home' or 'Visitor' - ideally we'd map to real names but 'Home'/'Visitor' is consistent
                    "player": player,
                    "event_type": event_type,
                    "shot_type": shot_type,
                    "shot_result": shot_result,
                    "event_detail": text,
                    "score": score_str, # Keep raw for now
                    "raw_text": line_clean
                }
                plays.append(play)

    return plays


def parse_legacy_table_pbp(soup, home_team_name="Home", vis_team_name="Visitor"):
    """
    Parses legacy HTML where PBP is in a <table> (e.g. msu1227.html, sdsu0131.html).
    Supports 4-column (Time, Team, Event, Score) and 5-column (Home, Time, Score, Margin, Visitor).
    """
    plays = []
    periods = []

    # 1. Locate PBP tables via H headers (Standard Legacy)
    headers = soup.find_all(re.compile(r"h[1-6]"))
    for h in headers:
        text = h.get_text().strip().lower()
        if "play-by-play" in text and ("period" in text or "half" in text):
            p_num = 0
            if "1st" in text: p_num = 1
            elif "2nd" in text: p_num = 2
            elif "ot" in text: p_num = 3
            elif "overtime" in text: p_num = 3
            
            next_table = h.find_next("table")
            if next_table:
                periods.append((p_num, next_table))

    # 2. Fallback: Locate PBP tables via Column Headers (SDSU Legacy)
    if not periods:
        tables = soup.find_all("table")
        for table in tables:
            header_text = table.get_text().lower()
            # Check keywords for 5-col header
            if "home team" in header_text and "visitors" in header_text:
                # Attempt to identify period from preceding text
                prev = table.find_previous(string=re.compile(r"PERIOD|HALF", re.I))
                p_num = 0
                if prev:
                    ptxt = prev.lower()
                    if "1st" in ptxt: p_num = 1
                    elif "2nd" in ptxt: p_num = 2
                    elif "ot" in ptxt: p_num = 3
                
                if p_num > 0:
                     periods.append((p_num, table))
    
    for period_num, table in periods:
        rows = table.find_all("tr")
        last_time = "20:00"
        
        # Detect format based on header row or first data row
        is_5_col = False
        
        # Check header row first
        for row in rows[:5]:
            txt = row.get_text().lower()
            if "home team" in txt and "visitors" in txt and "margin" in txt:
                is_5_col = True
                break
        
        for row in rows:
            cells = row.find_all("td")
            if not cells:
                continue
            
            cell_texts = [c.get_text().strip() for c in cells]
            if not cell_texts:
                continue
            
            # Skip rows that are clearly headers
            row_txt = "".join(cell_texts).lower()
            if "home team" in row_txt and "visitors" in row_txt:
                continue
            if "score" in row_txt and "margin" in row_txt:
                continue

            clock = None
            home_evt = ""
            vis_evt = ""
            score = None
            team = "Unknown"
            
            if is_5_col:
                # Expected: [0] Home, [1] Time, [2] Score, [3] Margin, [4] Visitor
                if len(cell_texts) >= 5:
                    time_candidate = cell_texts[1]
                    if re.match(r"\d{1,2}:\d{2}", time_candidate):
                        clock = time_candidate
                        last_time = clock
                    elif not time_candidate:
                        clock = last_time
                    else:
                         pass
                    
                    if not clock: clock = last_time

                    home_evt = cell_texts[0]
                    score = cell_texts[2]
                    vis_evt = cell_texts[4]
                    
                    events_to_add = []
                    if home_evt: events_to_add.append((home_team_name, home_evt))
                    if vis_evt: events_to_add.append((vis_team_name, vis_evt))
                    
                    for t, txt in events_to_add:
                        plays.append(create_play_legacy(period_num, clock, t, txt, score, " | ".join(cell_texts)))
                    
                    continue

            # Standard 4-col: [0] Time, [1] Team, [2] Play, [3] Score (maybe)
            # Check col 0 for time
            time_match = re.match(r"\d{1,2}:\d{2}", cell_texts[0])
            if time_match:
                clock = time_match.group(0)
                last_time = clock
            else:
                if not cell_texts[0]:
                    clock = last_time
                else:
                    continue
            
            team_abbr = "Unknown"
            play_text = ""
            
            if len(cell_texts) >= 3:
                    if cell_texts[1]: team_abbr = cell_texts[1]
                    play_text = cell_texts[2]
                    if len(cell_texts) >= 4 and "-" in cell_texts[3]:
                        score = cell_texts[3]
            
            if play_text and play_text.lower() != "score":
                plays.append(create_play_legacy(period_num, clock, team_abbr, play_text, score, " | ".join(cell_texts)))

    return plays

def create_play_legacy(period, clock, team, text, score, raw):
    event_type, shot_result, shot_type = classify_event_legacy(text)
    player = get_player_name_legacy(text)
    return {
        "period": period,
        "clock": clock,
        "team": team,
        "player": player,
        "event_type": event_type,
        "shot_type": shot_type,
        "shot_result": shot_result,
        "event_detail": text,
        "score": score,
        "raw_text": raw
    }

def classify_event_legacy(text):
    t = text.lower()
    shot_result = None
    shot_type = None
    event_type = "other"
    
    if "good" in t:
        event_type = "shot"
        shot_result = "made"
        if "3 ptr" in t or "3ptr" in t:
            shot_type = "3pt"
        else:
            shot_type = "2pt" # simplified
    elif "miss" in t:
        event_type = "shot"
        shot_result = "missed"
        if "3 ptr" in t or "3ptr" in t:
            shot_type = "3pt"
        else:
            shot_type = "2pt"
    elif "rebound" in t:
        event_type = "rebound"
    elif "assist" in t:
        event_type = "assist"
    elif "turnover" in t:
        event_type = "turnover"
    elif "foul" in t:
        event_type = "foul"
    elif "sub" in t:
        event_type = "substitution"
    elif "steal" in t:
        event_type = "steal"
    elif "block" in t:
        event_type = "block"
    elif "timeout" in t:
        event_type = "timeout"
        
    return event_type, shot_result, shot_type

def get_player_name_legacy(text):
    # Format: "GOOD! LAYUP by SCOTT,Stan [PNT]"
    # "MISSED 3 PTR by ROGERS, Nick"
    # "REBOUND (DEF) by BROCK,Isaiah"
    
    if " by " in text:
        parts = text.split(" by ")
        if len(parts) > 1:
            # Take part after 'by'
            # Stop at [ or ( if present?
            # e.g. "SCOTT,Stan [PNT]" -> "SCOTT,Stan"
            suffix = parts[1]
            # Remove [PNT], (P1T1), etc
            suffix = re.sub(r'\[.*?\]', '', suffix)
            # Sometimes "(P1T1)" fouls
            suffix = re.sub(r'\(.*?\)', '', suffix)
            return suffix.strip()
    return None
