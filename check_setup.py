import os

import feedparser
import requests
from dotenv import load_dotenv

load_dotenv()

print("=" * 50)
print("1. Gemini API key check")
print("=" * 50)
api_key = os.getenv("GEMINI_API_KEY", "").strip()
if not api_key or "paste" in api_key:
    print("FAIL: GEMINI_API_KEY is missing in the .env file")
else:
    try:
        response = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": api_key, "pageSize": 100},
            timeout=30,
        )
        if response.status_code == 200:
            models = [
                m["name"].replace("models/", "")
                for m in response.json().get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])
                and "flash" in m["name"]
            ]
            print("OK: key works. Available flash models:")
            for name in models[:12]:
                print("  -", name)
        else:
            print("FAIL: status", response.status_code, response.text[:200])
    except Exception as error:
        print("FAIL:", type(error).__name__, error)

print()
print("=" * 50)
print("2. RSS feeds check")
print("=" * 50)
feeds = {
    "Dawn": "https://www.dawn.com/feeds/home",
    "BBC": "https://feeds.bbci.co.uk/news/rss.xml",
    "Express Tribune": "https://tribune.com.pk/feed/home",
}
for name, url in feeds.items():
    try:
        feed = feedparser.parse(url)
        count = len(feed.entries)
        if count:
            print(f"OK: {name} -> {count} articles. First: {feed.entries[0].title[:70]}")
        else:
            print(f"FAIL: {name} -> no articles")
    except Exception as error:
        print(f"FAIL: {name} ->", type(error).__name__)