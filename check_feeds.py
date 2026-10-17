import feedparser
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

FEEDS = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "BBC Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "Dawn": "https://www.dawn.com/feeds/home",
    "Express Tribune": "https://tribune.com.pk/feed/home",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "NPR": "https://feeds.npr.org/1001/rss.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "Hacker News": "https://hnrss.org/frontpage",
    "ESPNcricinfo": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
}

for name, url in FEEDS.items():
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        feed = feedparser.parse(response.content)
        count = len(feed.entries)
        status = "OK  " if count else "FAIL"
        print(f"{status} {name:16} {count:3} articles (HTTP {response.status_code})")
    except Exception as error:
        print(f"FAIL {name:16} {type(error).__name__}")