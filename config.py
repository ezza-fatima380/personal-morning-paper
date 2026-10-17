from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "paper.db"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

TOPICS = [
    "World", "Pakistan", "Business", "Technology",
    "Science", "Health", "Sports", "Entertainment",
]

FEEDS = [
    {"source": "BBC News", "topic": "World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"source": "NPR", "topic": "World", "url": "https://feeds.npr.org/1001/rss.xml"},
    {"source": "Dawn", "topic": "Pakistan", "url": "https://www.dawn.com/feeds/home"},
    {"source": "The Express Tribune", "topic": "Pakistan", "url": "https://tribune.com.pk/feed/home"},
    {"source": "BBC Business", "topic": "Business", "url": "https://feeds.bbci.co.uk/news/business/rss.xml"},
    {"source": "Dawn Business", "topic": "Business", "url": "https://www.dawn.com/feeds/business"},
    {"source": "BBC Technology", "topic": "Technology", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
    {"source": "TechCrunch", "topic": "Technology", "url": "https://techcrunch.com/feed/"},
    {"source": "The Verge", "topic": "Technology", "url": "https://www.theverge.com/rss/index.xml"},
    {"source": "Ars Technica", "topic": "Technology", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"source": "BBC Science", "topic": "Science", "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"},
    {"source": "BBC Health", "topic": "Health", "url": "https://feeds.bbci.co.uk/news/health/rss.xml"},
    {"source": "ESPNcricinfo", "topic": "Sports", "url": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"},
    {"source": "BBC Sport", "topic": "Sports", "url": "https://feeds.bbci.co.uk/sport/rss.xml"},
    {"source": "BBC Entertainment", "topic": "Entertainment", "url": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"},
]