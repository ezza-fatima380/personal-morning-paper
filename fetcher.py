import calendar
import hashlib
import html
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import feedparser
import requests

from config import FEEDS, HEADERS
from database import count_by_topic, init_db, save_articles

MAX_PER_FEED = 25


def clean_text(text: str, limit: int = 400) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def extract_image(entry) -> str:
    for key in ("media_thumbnail", "media_content"):
        items = entry.get(key) or []
        if items and items[0].get("url"):
            return items[0]["url"]
    for link in entry.get("links", []):
        if link.get("type", "").startswith("image"):
            return link.get("href", "")
    return ""


def to_iso(entry) -> str:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        moment = datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
    else:
        moment = datetime.now(timezone.utc)
    return moment.isoformat()


def fetch_feed(feed: dict):
    try:
        response = requests.get(feed["url"], headers=HEADERS, timeout=20)
        parsed = feedparser.parse(response.content)
    except Exception as error:
        return feed, [], type(error).__name__

    now = datetime.now(timezone.utc).isoformat()
    articles = []
    for entry in parsed.entries[:MAX_PER_FEED]:
        link = entry.get("link", "").strip()
        title = clean_text(entry.get("title", ""), 200)
        if not link or not title:
            continue
        articles.append({
            "id": hashlib.sha1(link.encode("utf-8")).hexdigest(),
            "title": title,
            "summary": clean_text(entry.get("summary", "")),
            "link": link,
            "source": feed["source"],
            "topic": feed["topic"],
            "image_url": extract_image(entry),
            "published": to_iso(entry),
            "fetched_at": now,
        })
    return feed, articles, ""


def fetch_all() -> int:
    init_db()
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(fetch_feed, FEEDS))

    total_new = 0
    for feed, articles, error in results:
        new_count = save_articles(articles) if articles else 0
        total_new += new_count
        status = "OK  " if articles else "FAIL"
        note = f"({error})" if error else ""
        print(f"{status} {feed['source']:20} {feed['topic']:14} "
              f"{len(articles):3} fetched, {new_count:3} new {note}")
    return total_new


if __name__ == "__main__":
    added = fetch_all()
    print()
    print("New articles saved:", added)
    print("Articles per topic:")
    for topic, total in count_by_topic():
        print(f"  {topic:14} {total}")