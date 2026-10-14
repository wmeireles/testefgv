# store , in-memory document store seeded from data/documents.json (embeddings computed once at load)
import json
import os

from app.embeddings import embed

_DOCS = None


def documents():
    global _DOCS
    if _DOCS is None:
        path = os.path.join(os.path.dirname(__file__), "..", "data", "documents.json")
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        for d in raw:
            d["embedding"] = embed(d["text"])
        _DOCS = raw
    return _DOCS
