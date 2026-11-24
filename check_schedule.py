import requests

url = "https://goldengrizzlies.com/sports/mens-basketball/schedule/2025-26"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers, timeout=15)
    print(f"Status Code: {response.status_code}")
    print(f"Content Length: {len(response.text)}")
    
    with open("schedule_test.html", "w", encoding="utf-8") as f:
            f.write(response.text)
    
    if "boxscore" in response.text:
        print("Found 'boxscore' in text.")
    
except Exception as e:
    print(f"Error: {e}")
