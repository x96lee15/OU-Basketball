import re
import requests

import parse_season

oakland_mbball_urls = [
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2025-26",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2024-25",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2023-24",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2022-23",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2021-22",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2020-21",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2019-20",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2018-19",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2017-18",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2016-17",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2015-16",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2014-15",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2013-14",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2012-13",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2011-12",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2010-11",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2009-10",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2008-09",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2007-08",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2006-07",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2005-06",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2004-05",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2003-04",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2002-03",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2001-02",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2000-01",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1999-00",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1998-99",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1997-98",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1996-97",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1995-96",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1994-95",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1993-94",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1992-93",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1991-92",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1990-91",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1989-90",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1988-89",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1987-88",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1986-87",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1985-86",
    "https://goldengrizzlies.com/sports/mens-basketball/schedule/1984-85"
]

#oakland_mbball_urls = [    "https://goldengrizzlies.com/sports/mens-basketball/schedule/2008-09" ]

def fetch_url_content(url: str) -> str:
    """Fetch and return the HTML content of the given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise error for bad status codes
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return ""

def run_regex_patterns(content: str, patterns: list[str]):
    """Run each regex pattern on the content and print matches."""
    for pattern in patterns:
        print(f"\n🔍 Pattern: {pattern}")
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            print(f"Found {len(matches)} matches:")
            for m in matches[:20]:  # show only first 20 results
                print(f"  {m}")
            if len(matches) > 20:
                print(f"  ...and {len(matches) - 20} more")
        else:
            print("No matches found.")

def main():
    for url in oakland_mbball_urls:
        #url = input("Enter the URL to fetch: ").strip()
        html_content = fetch_url_content(url)
        if not html_content:
            return

    print("\nEnter one or more regular expressions to run (empty line to stop):")
    patterns = []
    while True:
        pattern = input("> ").strip()
        if not pattern:
            break
        patterns.append(pattern)

    run_regex_patterns(html_content, patterns)

if __name__ == "__main__":
    main()
