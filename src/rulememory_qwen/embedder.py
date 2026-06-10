"""Embedding backends for semantic recall.

``SentenceTransformerEmbedder`` uses a small local sentence-transformers model
when available (real dense embeddings). When it is not installed, the agent
falls back to ``HashingTfidfEmbedder`` — a fully deterministic hashing-TF-IDF
vectorizer so that semantic recall is still *real* (cosine over bag-of-hashed-
ngrams), with zero heavyweight dependencies. CI uses the fallback.
"""

from __future__ import annotations

import math
import re
from typing import List, Sequence

import numpy as np


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    words = _TOKEN_RE.findall(text.lower())
    # word unigrams + char trigrams for a little fuzziness
    grams = list(words)
    joined = " ".join(words)
    for i in range(len(joined) - 2):
        grams.append(joined[i : i + 3])
    return grams


class Embedder:
    name = "base"
    dim = 0

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        raise NotImplementedError


class HashingTfidfEmbedder(Embedder):
    """Deterministic hashing vectorizer with sublinear TF and L2 norm."""

    name = "hashing-tfidf"

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        toks = _tokens(text)
        if not toks:
            return v
        counts: dict[int, float] = {}
        for t in toks:
            h = hash_token(t) % self.dim
            counts[h] = counts.get(h, 0.0) + 1.0
        for h, c in counts.items():
            v[h] = 1.0 + math.log(c)  # sublinear TF
        n = np.linalg.norm(v)
        return v / n if n > 0 else v

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        return np.vstack([self._vec(t) for t in texts]) if texts else np.zeros((0, self.dim), np.float32)


def hash_token(token: str) -> int:
    """Stable, process-independent hash (Python's hash() is salted)."""
    h = 2166136261
    for ch in token.encode("utf-8"):
        h = (h ^ ch) * 16777619 & 0xFFFFFFFF
    return h


class SentenceTransformerEmbedder(Embedder):
    name = "sentence-transformers"

    def __init__(self, model_id: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_id)
        self.dim = self.model.get_sentence_embedding_dimension()
        self.model_id = model_id

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), np.float32)
        return np.asarray(
            self.model.encode(list(texts), normalize_embeddings=True, convert_to_numpy=True),
            dtype=np.float32,
        )


def make_embedder(prefer: str | None = None) -> Embedder:
    """Sentence-transformers if installed and not disabled, else hashing-TFIDF."""
    import os

    if prefer == "hashing" or os.environ.get("RULEMEMORY_FORCE_HASH_EMBED") == "1":
        return HashingTfidfEmbedder()
    if prefer == "sentence-transformers" or prefer is None:
        try:
            return SentenceTransformerEmbedder()
        except Exception:
            pass
    return HashingTfidfEmbedder()


def cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity of query vector(s) ``a`` against matrix ``b`` (both L2-normed)."""
    if b.shape[0] == 0:
        return np.zeros((0,), np.float32)
    return b @ a
