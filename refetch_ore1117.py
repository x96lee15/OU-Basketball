
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Based on msu1227 URL structure: 
# https://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats/2008-2009/msu1227.html
# ore1117 should be similar
URL = "https://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats/2008-2009/ore1117.html"
headers = {
    "User-Agent": "Mozilla/5.0"
}

try:
    print(f"Fetching {URL}...")
    response = requests.get(URL, headers=headers, verify=False, timeout=30)
    response.raise_for_status()
    
    with open("ore1117.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Saved ore1117.html")
except Exception as e:
    print(f"Error fetching: {e}")
