from __future__ import annotations

import math
import re
from collections import Counter

from ..config import settings
from .llm import get_client

_EMBED_MODEL = "gemini-embedding-001"

# BM25 term-frequency saturation parameter.
_BM25_K1 = 1.5


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def compute_bm25_score(query: str, corpus_text: str) -> float:
    """Keyword-overlap score in [0, 1]: the fraction of the query's (JD's) unique
    terms that the resume covers, each weighted by a BM25 TF-saturation curve so a
    term repeated many times can't dominate.

    We deliberately do NOT use ``BM25Okapi([corpus_tokens])``: with a single-document
    corpus every IDF collapses to a negative value (log of a fraction < 1), which the
    library floors to a negative epsilon — producing meaningless negative scores
    (the old code returned e.g. -0.022). Here we compute the TF component directly
    against the one resume document, which is well-defined and always non-negative."""
    query_terms = set(_tokenize(query))
    doc_tokens = _tokenize(corpus_text)
    if not doc_tokens or not query_terms:
        return 0.0
    tf = Counter(doc_tokens)
    # avgdl == doc_len for a single doc, so BM25's length-normalisation term is 1.
    score = 0.0
    for term in query_terms:
        f = tf.get(term, 0)
        if f:
            score += (f * (_BM25_K1 + 1)) / (f + _BM25_K1)  # saturating tf, max ~1
    return min(score / len(query_terms), 1.0)


def _embed(text: str) -> list[float]:
    result = get_client().models.embed_content(model=_EMBED_MODEL, contents=text[:2048])
    return result.embeddings[0].values


def compute_semantic_score(text_a: str, text_b: str) -> float:
    """Cosine similarity between two texts using Gemini embeddings.
    Returns a neutral 0.5 on any failure (no key, rate limit, API error) so a
    single embeddings hiccup never aborts the match pipeline."""
    if not settings.gemini_api_key:
        return 0.5  # neutral fallback when no key configured
    try:
        emb_a = _embed(text_a)
        emb_b = _embed(text_b)
    except Exception as e:
        print(f"[scoring] embedding error: {e} — neutral 0.5")
        return 0.5
    dot = sum(a * b for a, b in zip(emb_a, emb_b))
    norm_a = math.sqrt(sum(a * a for a in emb_a))
    norm_b = math.sqrt(sum(b * b for b in emb_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, dot / (norm_a * norm_b))
