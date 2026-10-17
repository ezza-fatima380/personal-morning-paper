import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reader_profile import tokenize


def test_tokenize_removes_stopwords():
    words = tokenize("The cricket match and the final")
    assert "the" not in words
    assert "and" not in words
    assert "cricket" in words


def test_tokenize_lowercases():
    words = tokenize("Cricket AI")
    assert "cricket" in words