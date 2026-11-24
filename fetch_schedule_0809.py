
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://goldengrizzlies.com/sports/mens-basketball/schedule/2008-09"
headers = {
    "User-Agent": "Mozilla/5.0"
}

try:
    print(f"Fetching {URL}...")
    response = requests.get(URL, headers=headers, verify=False, timeout=30)
    response.raise_for_status()
    
    with open("schedule_2008_09.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Saved schedule_2008_09.html")
except Exception as e:
    print(f"Error fetching: {e}")
