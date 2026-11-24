import requests

url = "https://stats.ncaa.org/contests/6457517/play_by_play.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Content Length: {len(response.text)}")
    if "Play-by-Play" in response.text or "table" in response.text:
         print("Found 'Play-by-Play' or 'table' in content.")
    else:
         print("Did not find expected content markers.")
    
    # Check for keywords that imply frames
    if "<iframe" in response.text:
        print("Found iframe tag.")
        
except Exception as e:
    print(f"Error: {e}")
