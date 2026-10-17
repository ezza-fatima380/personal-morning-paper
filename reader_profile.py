import re
from datetime import datetime, timezone

from config import TOPICS
from database import get_connection

DEFAULT_TOPIC_WEIGHT = 0.2
SHORT_WORDS_OK = {"ai", "ml", "uk", "un", "ev"}
STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "had", "her",
    "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "new", "now",
    "see", "two", "way", "who", "did", "its", "let", "say", "she", "too", "use", "that",
    "with", "have", "this", "will", "your", "from", "they", "know", "want", "been",
    "much", "some", "time", "very", "when", "come", "here", "just", "like", "long",
    "make", "many", "over", "such", "take", "than", "them", "well", "were", "what",
    "said", "each", "which", "their", "about", "would", "these", "other", "into",
    "more", "also", "after", "could", "first", "being", "those", "still", "while",
    "where", "there", "should", "because", "before", "between", "through", "during",
    "says", "amid", "over", "under", "against", "why", "may", "his", "off", "set",
}


def tokenize(text: str) -> list:
    words = re.findall(r"[a-zA-Z]{2,}", (text or "").lower())
    return [w for w in words if (len(w) >= 3 or w in SHORT_WORDS_OK) and w not in STOPWORDS]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_profile_tables() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS topic_weights (
                user_id INTEGER, topic TEXT, weight REAL,
                PRIMARY KEY (user_id, topic)
            );
            CREATE TABLE IF NOT EXISTS keyword_weights (
                user_id INTEGER, keyword TEXT, weight REAL,
                PRIMARY KEY (user_id, keyword)
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, article_id TEXT, action TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS editions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, edition_date TEXT, payload TEXT, created_at TEXT,
                UNIQUE (user_id, edition_date)
            );
            """
        )


def get_users() -> list:
    with get_connection() as connection:
        rows = connection.execute("SELECT id, name FROM users ORDER BY name").fetchall()
    return [(row["id"], row["name"]) for row in rows]


def get_or_create_user(name: str) -> int:
    with get_connection() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO users (name, created_at) VALUES (?, ?)", (name, _now())
        )
        row = connection.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone()
    return row["id"]


def save_interests(user_id: int, topics: list, keywords_text: str) -> None:
    with get_connection() as connection:
        for topic in TOPICS:
            weight = 1.5 if topic in topics else DEFAULT_TOPIC_WEIGHT
            connection.execute(
                "INSERT OR REPLACE INTO topic_weights (user_id, topic, weight) VALUES (?, ?, ?)",
                (user_id, topic, weight),
            )
        for word in set(tokenize(keywords_text)):
            connection.execute(
                "INSERT OR REPLACE INTO keyword_weights (user_id, keyword, weight) VALUES (?, ?, ?)",
                (user_id, word, 2.0),
            )


def get_topic_weights(user_id: int) -> dict:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT topic, weight FROM topic_weights WHERE user_id = ?", (user_id,)
        ).fetchall()
    return {row["topic"]: row["weight"] for row in rows}


def get_keyword_weights(user_id: int) -> dict:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT keyword, weight FROM keyword_weights WHERE user_id = ?", (user_id,)
        ).fetchall()
    return {row["keyword"]: row["weight"] for row in rows}


def get_feedback_ids(user_id: int, action: str) -> set:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT article_id FROM feedback WHERE user_id = ? AND action = ?",
            (user_id, action),
        ).fetchall()
    return {row["article_id"] for row in rows}


def record_feedback(user_id: int, article: dict, action: str) -> None:
    """Learning step: a like or skip moves the topic and keyword weights."""
    topic_delta, keyword_delta = {"like": (0.3, 0.15), "skip": (-0.2, -0.08)}[action]
    words = list(dict.fromkeys(tokenize(article["title"])))[:8]

    with get_connection() as connection:
        connection.execute(
            "INSERT INTO feedback (user_id, article_id, action, created_at) VALUES (?, ?, ?, ?)",
            (user_id, article["id"], action, _now()),
        )
        row = connection.execute(
            "SELECT weight FROM topic_weights WHERE user_id = ? AND topic = ?",
            (user_id, article["topic"]),
        ).fetchone()
        current = row["weight"] if row else DEFAULT_TOPIC_WEIGHT
        connection.execute(
            "INSERT OR REPLACE INTO topic_weights (user_id, topic, weight) VALUES (?, ?, ?)",
            (user_id, article["topic"], min(3.0, max(0.0, current + topic_delta))),
        )
        for word in words:
            row = connection.execute(
                "SELECT weight FROM keyword_weights WHERE user_id = ? AND keyword = ?",
                (user_id, word),
            ).fetchone()
            current = row["weight"] if row else 0.0
            connection.execute(
                "INSERT OR REPLACE INTO keyword_weights (user_id, keyword, weight) VALUES (?, ?, ?)",
                (user_id, word, min(3.0, max(-1.0, current + keyword_delta))),
            )