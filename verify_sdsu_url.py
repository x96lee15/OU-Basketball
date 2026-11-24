
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

urls_to_try = [
    "http://www.ougrizzlies.com/sports/m-baskbl/stats/2008-2009/sdsu0131.html",
    "https://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats/2008-2009/sdsu0131.html",
    "https://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats/2008-2009/SDSU0131.html",
    "https://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats/2008-2009/sdsu0131.htm",
    "https://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats/2008-2009/SDSU0131.htm",
    "https://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats/2008-2009/013109aaa.html",
    "https://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats/2008-2009/013109aaa.htm",
    "https://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats/2008-2009/013109.html",
     "https://oaklandu_ftp.sidearmsports.com/custompages/sports/m-baskbl/stats/2008-2009/013109.htm",
]

headers = {
    "User-Agent": "Mozilla/5.0"
}

for url in urls_to_try:
    try:
        print(f"Checking {url}...")
        resp = requests.get(url, headers=headers, verify=False, timeout=10)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            if "not found" in resp.text.lower() or "404 detected" in resp.text.lower():
                print("  -> Soft 404 content")
            else:
                print(f"  -> SUCCESS! Length: {len(resp.text)}")
                # Check for content keywords
                if "play-by-play" in resp.text.lower() or "pre>" in resp.text.lower():
                     print("  -> CONTENT FOUND (PBP/PRE)!")
                     with open("sdsu0131_candidate.html", "w", encoding="utf-8") as f:
                        f.write(resp.text)
                     print("  -> Saved to sdsu0131_candidate.html")
    except Exception as e:
        print(f"  Error: {e}")
