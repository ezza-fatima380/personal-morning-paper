import json
from datetime import date, datetime, timedelta, timezone

from database import get_connection
from reader_profile import (
    DEFAULT_TOPIC_WEIGHT,
    get_feedback_ids,
    get_keyword_weights,
    get_topic_weights,
    tokenize,
)


def hours_old(published: str) -> float:
    try:
        moment = datetime.fromisoformat(published)
    except Exception:
        return 72.0
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - moment).total_seconds() / 3600)


def candidate_articles(days: int = 3) -> list:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM articles WHERE published >= ? ORDER BY published DESC", (cutoff,)
        ).fetchall()
        if len(rows) < 40:
            rows = connection.execute(
                "SELECT * FROM articles ORDER BY published DESC LIMIT 400"
            ).fetchall()
    return [dict(row) for row in rows]


def score_article(article: dict, topic_weights: dict, keyword_weights: dict):
    topic_weight = topic_weights.get(article["topic"], DEFAULT_TOPIC_WEIGHT)
    words = set(tokenize(article["title"] + " " + (article.get("summary") or "")))
    matches = sorted(
        ((word, keyword_weights[word]) for word in words if word in keyword_weights),
        key=lambda pair: pair[1],
        reverse=True,
    )
    keyword_score = max(-1.5, min(sum(weight for _, weight in matches), 3.0))
    age = hours_old(article["published"])
    recency = max(0.0, 1.0 - age / 72)
    image_bonus = 0.15 if article.get("image_url") else 0.0

    total = 2.0 * topic_weight + keyword_score + 1.2 * recency + image_bonus

    parts = []
    if topic_weight >= 1.0:
        parts.append(f"you follow {article['topic']}")
    good = [word for word, weight in matches if weight >= 0.5][:2]
    if good:
        parts.append("it matches " + ", ".join(f"'{word}'" for word in good))
    if age < 6:
        parts.append("it broke in the last few hours")
    if not parts:
        parts.append("it is a fresh story")
    return total, "Shown because " + " and ".join(parts) + "."


def seen_article_ids(user_id: int) -> set:
    today = date.today().isoformat()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT payload FROM editions WHERE user_id = ? AND edition_date != ?",
            (user_id, today),
        ).fetchall()
    seen = set()
    for row in rows:
        seen.update(article["id"] for article in json.loads(row["payload"]))
    return seen


def build_edition(user_id: int, size: int = 16, per_source: int = 4,
                  per_topic: int = 5, wildcards: int = 2) -> list:
    topic_weights = get_topic_weights(user_id)
    keyword_weights = get_keyword_weights(user_id)
    skipped = get_feedback_ids(user_id, "skip")
    seen = seen_article_ids(user_id)

    scored = []
    for article in candidate_articles():
        if article["id"] in skipped or article["id"] in seen:
            continue
        total, reason = score_article(article, topic_weights, keyword_weights)
        scored.append({**article, "score": round(total, 3), "reason": reason, "wildcard": False})
    scored.sort(key=lambda item: item["score"], reverse=True)

    picked, per_source_count, per_topic_count = [], {}, {}
    for article in scored:
        if len(picked) >= size - wildcards:
            break
        if per_source_count.get(article["source"], 0) >= per_source:
            continue
        if per_topic_count.get(article["topic"], 0) >= per_topic:
            continue
        picked.append(article)
        per_source_count[article["source"]] = per_source_count.get(article["source"], 0) + 1
        per_topic_count[article["topic"]] = per_topic_count.get(article["topic"], 0) + 1

    picked_ids = {article["id"] for article in picked}
    pool = [
        article for article in scored
        if article["id"] not in picked_ids
        and topic_weights.get(article["topic"], DEFAULT_TOPIC_WEIGHT) <= 0.5
    ]
    for article in pool[:wildcards]:
        wild = dict(article)
        wild["wildcard"] = True
        wild["reason"] = "Wildcard: outside your usual topics, to help the paper discover new interests."
        picked.append(wild)
    return picked


def save_edition(user_id: int, articles: list, edition_date: str = None) -> None:
    edition_date = edition_date or date.today().isoformat()
    with get_connection() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO editions (user_id, edition_date, payload, created_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, edition_date, json.dumps(articles), datetime.now(timezone.utc).isoformat()),
        )


def get_edition(user_id: int, edition_date: str):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT payload FROM editions WHERE user_id = ? AND edition_date = ?",
            (user_id, edition_date),
        ).fetchone()
    return json.loads(row["payload"]) if row else None


def list_editions(user_id: int) -> list:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT edition_date FROM editions WHERE user_id = ? ORDER BY edition_date DESC",
            (user_id,),
        ).fetchall()
    return [row["edition_date"] for row in rows]