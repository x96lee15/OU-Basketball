
import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats/2008-2009/msu1227.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    print(f"Fetching {URL}...")
    response = requests.get(URL, headers=headers, verify=False, timeout=30)
    response.raise_for_status()
    
    with open("msu1227.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Saved msu1227.html")
except Exception as e:
    print(f"Error fetching: {e}")
