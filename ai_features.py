"""Gemini features: 3 takeaways and an editor's note. Never crashes the app."""
import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _call_gemini(prompt: str):
    key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if not key:
        return None
    try:
        response = requests.post(
            API_URL.format(model=model),
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"},
            },
            timeout=40,
        )
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except Exception:
        return None


def make_insights(user_name: str, articles: list):
    """Return {'takeaways': [3 strings], 'note': str} or None if Gemini is unavailable."""
    lines = []
    for a in articles[:12]:
        summary = (a.get("summary") or "")
        if summary.startswith("http"):
            summary = ""
        lines.append(f"- [{a['topic']}] {a['title']}. {summary[:200]}")
    prompt = (
        f"You edit a personal morning newspaper for a reader named {user_name}.\n"
        "From the stories below, write exactly 3 takeaways: the three most important things "
        "the reader should remember today. Each takeaway is one clear sentence under 25 words. "
        "Then write a one-sentence friendly editor's note (under 25 words) for the reader.\n"
        'Reply ONLY with JSON: {"takeaways": ["...", "...", "..."], "note": "..."}\n\n'
        "Stories:\n" + "\n".join(lines)
    )
    data = _call_gemini(prompt)
    if not isinstance(data, dict):
        return None
    takeaways = [str(t) for t in data.get("takeaways", [])][:3]
    if len(takeaways) < 3:
        return None
    return {"takeaways": takeaways, "note": str(data.get("note", ""))}