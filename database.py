import sqlite3

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                summary TEXT,
                link TEXT NOT NULL,
                source TEXT,
                topic TEXT,
                image_url TEXT,
                published TEXT,
                fetched_at TEXT
            )
            """
        )


def save_articles(articles: list) -> int:
    """Save articles and return how many were new (duplicates are skipped)."""
    with get_connection() as connection:
        before = connection.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        connection.executemany(
            """
            INSERT OR IGNORE INTO articles
            (id, title, summary, link, source, topic, image_url, published, fetched_at)
            VALUES (:id, :title, :summary, :link, :source, :topic, :image_url, :published, :fetched_at)
            """,
            articles,
        )
        after = connection.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    return after - before


def count_by_topic() -> list:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT topic, COUNT(*) AS total FROM articles GROUP BY topic ORDER BY total DESC"
        ).fetchall()
    return [(row["topic"], row["total"]) for row in rows]