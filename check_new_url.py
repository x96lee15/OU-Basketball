import requests

url = "https://goldengrizzlies.com/sports/mens-basketball/stats/2025-26/youngstown-state/boxscore/13058"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers, timeout=15)
    print(f"Status Code: {response.status_code}")
    print(f"Content Length: {len(response.text)}")
    
    with open("goldengrizzlies_test.html", "w", encoding="utf-8") as f:
            f.write(response.text)
            
    if "Play By Play" in response.text or "play-by-play" in response.text.lower():
         print("Found 'Play By Play' text.")
    else:
         print("Did not find explicit 'Play By Play' text, manual inspection needed.")
        
except Exception as e:
    print(f"Error: {e}")
