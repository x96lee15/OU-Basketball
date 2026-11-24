
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Full URL for recap
URL = "https://goldengrizzlies.com/news/2009/1/31/SDSU_Rallies_Past_Oakland_in_Overtime_74_68.aspx"
headers = {
    "User-Agent": "Mozilla/5.0"
}

try:
    print(f"Fetching {URL}...")
    response = requests.get(URL, headers=headers, verify=False, timeout=30)
    response.raise_for_status()
    
    with open("recap_sdsu.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Saved recap_sdsu.html")
except Exception as e:
    print(f"Error fetching: {e}")
