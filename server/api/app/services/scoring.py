from __future__ import annotations

import math
import re

from google import genai
from rank_bm25 import BM25Okapi

from ..config import settings

_EMBED_MODEL = "gemini-embedding-001"


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def compute_bm25_score(query: str, corpus_text: str) -> float:
    """BM25 relevance score, normalised to [0, 1]."""
    query_tokens = _tokenize(query)
    corpus_tokens = _tokenize(corpus_text)
    if not corpus_tokens or not query_tokens:
        return 0.0
    bm25 = BM25Okapi([corpus_tokens])
    raw = float(bm25.get_scores(query_tokens)[0])
    return min(raw / 50.0, 1.0)


def _embed(text: str) -> list[float]:
    client = genai.Client(api_key=settings.gemini_api_key)
    result = client.models.embed_content(model=_EMBED_MODEL, contents=text[:2048])
    return result.embeddings[0].values


def compute_semantic_score(text_a: str, text_b: str) -> float:
    """Cosine similarity between two texts using Gemini embeddings."""
    if not settings.gemini_api_key:
        return 0.5  # neutral fallback when no key configured
    emb_a = _embed(text_a)
    emb_b = _embed(text_b)
    dot = sum(a * b for a, b in zip(emb_a, emb_b))
    norm_a = math.sqrt(sum(a * a for a in emb_a))
    norm_b = math.sqrt(sum(b * b for b in emb_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, dot / (norm_a * norm_b))
