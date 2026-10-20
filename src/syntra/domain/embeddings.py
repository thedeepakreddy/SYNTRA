"""Pluggable embedding provider protocol and deterministic token/hash vectorizer.

IMPORTANT: The DeterministicTokenEmbeddingProvider implements token and n-gram feature
hashing for offline, hermetic retrieval and testing. It reflects lexical and subword
overlap. It is NOT a genuine semantic language model and does NOT understand synonyms.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, runtime_checkable

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for memory vectorization providers."""

    @property
    def dimension(self) -> int:
        """The dimensionality of generated embedding vectors."""
        ...

    async def embed_text(self, text: str) -> list[float]:
        """Compute an embedding vector for a single text string."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Compute embedding vectors for a batch of text strings."""
        ...


def compute_cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two float vectors.

    Safely handles zero vectors and floating-point edge cases.
    Returns 0.0 if either vector is empty or has zero norm.
    """
    if not vec_a or not vec_b:
        return 0.0

    if len(vec_a) != len(vec_b):
        raise ValueError(f"Vector dimension mismatch: {len(vec_a)} vs {len(vec_b)}")

    dot_product = 0.0
    norm_a_sq = 0.0
    norm_b_sq = 0.0

    for a, b in zip(vec_a, vec_b, strict=True):
        if not math.isfinite(a) or not math.isfinite(b):
            raise ValueError("Vector contains non-finite floating point values (NaN or Inf).")
        dot_product += a * b
        norm_a_sq += a * a
        norm_b_sq += b * b

    norm_a = math.sqrt(norm_a_sq)
    norm_b = math.sqrt(norm_b_sq)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    similarity = dot_product / (norm_a * norm_b)
    return max(-1.0, min(1.0, similarity))


class DeterministicTokenEmbeddingProvider:
    """Deterministic token and n-gram hash projection for offline, hermetic retrieval.

    NOTE: This engine projects lexical tokens and subword n-grams into a fixed-dimension
    unit hypersphere using SHA-256 feature hashing. It measures lexical/subword overlap,
    NOT semantic synonymy or conceptual equivalence.
    """

    def __init__(self, dimension: int = 64) -> None:
        if dimension <= 0:
            raise ValueError(f"Embedding dimension must be positive, got {dimension}")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _extract_features(self, text: str) -> list[str]:
        """Extract word tokens and character 3-grams for subword overlap."""
        cleaned = text.lower().strip()
        if not cleaned:
            return []

        words = TOKEN_PATTERN.findall(cleaned)
        features: list[str] = list(words)

        # Generate character 3-grams for words with >= 3 chars
        for word in words:
            if len(word) >= 3:
                for i in range(len(word) - 2):
                    features.append(f"ng:{word[i : i + 3]}")

        return features

    def _vectorize(self, text: str) -> list[float]:
        """Project features to a unit L2-normalized vector."""
        features = self._extract_features(text)
        if not features:
            return [0.0] * self._dimension

        vec = [0.0] * self._dimension
        for feat in features:
            digest = hashlib.sha256(feat.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self._dimension
            sign = 1.0 if (digest[4] % 2 == 0) else -1.0
            vec[idx] += sign

        # Compute L2 norm
        norm_sq = sum(x * x for x in vec)
        norm = math.sqrt(norm_sq)

        if norm == 0.0:
            return [0.0] * self._dimension

        normalized = [x / norm for x in vec]
        # Validate finite values
        assert all(math.isfinite(x) for x in normalized)
        return normalized

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string asynchronously."""
        return self._vectorize(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple text strings asynchronously."""
        return [self._vectorize(t) for t in texts]
