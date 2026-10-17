from datetime import datetime, timezone

from pdf_builder import build_pdf
from ranker import is_duplicate, score_article
from reader_profile import tokenize


def make_article(topic="Sports", title="Cricket final tonight", hours_ago=1):
    published = datetime.now(timezone.utc).isoformat()
    return {
        "id": "a1",
        "title": title,
        "summary": "A short summary.",
        "topic": topic,
        "published": published,
        "image_url": "",
        "link": "https://example.com/story",
        "source": "Test",
    }


def test_tokenize_lowercases():
    assert "cricket" in tokenize("CRICKET Final")


def test_tokenize_removes_stopwords():
    assert "the" not in tokenize("the cricket final")


def test_is_duplicate_detects_same_story():
    kept = [set(tokenize("Army chief warns adversaries against any miscalculation"))]
    words = set(tokenize("Any miscalculation will draw warning from army chief adversaries"))
    assert is_duplicate(words, kept) is True


def test_is_duplicate_allows_different_story():
    kept = [set(tokenize("Army chief warns adversaries against any miscalculation"))]
    words = set(tokenize("Mumbai Indians and head coach part ways"))
    assert is_duplicate(words, kept) is False


def test_score_follows_topic_weight():
    article = make_article(topic="Sports")
    high, _ = score_article(article, {"Sports": 2.0}, {})
    low, _ = score_article(article, {"Sports": 0.2}, {})
    assert high > low


def test_score_rewards_matching_keyword():
    article = make_article(title="Cricket final tonight")
    with_keyword, _ = score_article(article, {"Sports": 1.0}, {"cricket": 1.0})
    without, _ = score_article(article, {"Sports": 1.0}, {})
    assert with_keyword > without


def test_build_pdf_returns_pdf_bytes():
    articles = [make_article(title="Lead story"), {**make_article(title="Second story"), "id": "a2"}]
    data = build_pdf("Test Reader", "Saturday, 17 October 2026", articles,
                     takeaways=["One", "Two", "Three"], editor_note="Hello",
                     topic_weights={"Sports": 1.5})
    assert data.startswith(b"%PDF")