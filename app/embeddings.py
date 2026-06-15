"""Embeddings abstraction for SourceFetch.

We compute embeddings ourselves and hand the vectors to Chroma, so the vector
store is used purely as an ANN index and never reaches out to download a model.
Two backends, chosen by the EMBEDDINGS_BACKEND env var:

  hashing  (default)  Offline, zero-download, deterministic. A HashingVectorizer
                      over word 1-2 grams. This is essentially lexical, so it is
                      "good enough to show the pipeline and rank correctly," not
                      semantically strong. It exists so the app runs anywhere
                      with no model fetch — handy for CI and quick demos.

  sentence-transformers  Recommended for real use. all-MiniLM-L6-v2 from the
                      Hugging Face ecosystem gives proper semantic retrieval.
                      Downloads the model on first use.

Switching backends changes the vector space and dimensionality, so re-run
ingestion after changing it (scripts/ingest.py recreates the collection).
"""

from __future__ import annotations
import os
from typing import List

import numpy as np


class Embedder:
    """Base interface: turn text into L2-normalized float32 vectors."""

    dim: int
    name: str

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


class HashingEmbedder(Embedder):
    """Offline, deterministic, no network. Lexical similarity via feature hashing."""

    def __init__(self, n_features: int = 4096):
        from sklearn.feature_extraction.text import HashingVectorizer

        self.dim = n_features
        self.name = f"hashing-{n_features}"
        self._vec = HashingVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            n_features=n_features,
            alternate_sign=False,
            norm="l2",
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        mat = self._vec.transform(texts).toarray().astype(np.float32)
        return mat.tolist()


class SentenceTransformerEmbedder(Embedder):
    """Semantic embeddings from the Hugging Face sentence-transformers library."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # lazy: heavy import

        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()
        self.name = f"st-{model_name}"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        vecs = self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        ).astype(np.float32)
        return vecs.tolist()


def get_embedder() -> Embedder:
    """Factory driven by EMBEDDINGS_BACKEND (default: hashing)."""
    backend = os.getenv("EMBEDDINGS_BACKEND", "hashing").strip().lower()
    if backend in ("st", "sentence-transformers", "sentence_transformers"):
        model = os.getenv("ST_MODEL", "all-MiniLM-L6-v2")
        return SentenceTransformerEmbedder(model)
    return HashingEmbedder(int(os.getenv("HASH_FEATURES", "4096")))
