import os

import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
print("Key found:", bool(key))
print("Model:", model)

url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
try:
    response = requests.post(
        url,
        headers={"x-goog-api-key": key or "", "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": 'Reply ONLY with JSON: {"ok": true}'}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        },
        timeout=40,
    )
    print("Status:", response.status_code)
    print(response.text[:600])
except Exception as error:
    print("Request failed:", error)