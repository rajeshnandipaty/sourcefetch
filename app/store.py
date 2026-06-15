"""Vector store: a thin wrapper around ChromaDB.

Chroma is used purely as a persistent ANN index. We pass embeddings in
explicitly (computed by app.embeddings), so Chroma never instantiates its own
embedding function and never downloads anything. Distances are cosine; we expose
similarity as 1 - distance for readability.
"""

from __future__ import annotations
import os
from typing import List, Dict, Any

import chromadb

from .chunking import Chunk

DATA_DIR = os.getenv("CHROMA_DIR", os.path.join(os.path.dirname(__file__), "..", "data", "chroma"))
COLLECTION = os.getenv("CHROMA_COLLECTION", "policy")


class VectorStore:
    def __init__(self, path: str = DATA_DIR, collection: str = COLLECTION):
        os.makedirs(path, exist_ok=True)
        self._client = chromadb.PersistentClient(path=path)
        self._collection_name = collection

    def _collection(self):
        return self._client.get_or_create_collection(
            name=self._collection_name, metadata={"hnsw:space": "cosine"}
        )

    def reset(self):
        """Drop and recreate the collection (used by ingest to rebuild cleanly)."""
        try:
            self._client.delete_collection(self._collection_name)
        except Exception:
            pass
        return self._collection()

    def add(self, chunks: List[Chunk], embeddings: List[List[float]]):
        if not chunks:
            return
        col = self._collection()
        col.add(
            ids=[c.id for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[{"source": c.source, "index": c.index} for c in chunks],
        )

    def query(self, embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
        col = self._collection()
        n = min(k, max(col.count(), 1))
        res = col.query(query_embeddings=[embedding], n_results=n)
        hits: List[Dict[str, Any]] = []
        for doc, dist, meta, _id in zip(
            res["documents"][0], res["distances"][0], res["metadatas"][0], res["ids"][0]
        ):
            hits.append(
                {
                    "id": _id,
                    "text": doc,
                    "source": meta.get("source", "?"),
                    "index": meta.get("index", -1),
                    "score": round(1.0 - float(dist), 4),
                }
            )
        return hits

    def count(self) -> int:
        return self._collection().count()

    def sources(self) -> List[str]:
        col = self._collection()
        got = col.get(include=["metadatas"])
        return sorted({m.get("source", "?") for m in got.get("metadatas", [])})
