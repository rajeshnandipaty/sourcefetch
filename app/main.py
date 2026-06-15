"""FastAPI service for SourceFetch.

Three JSON endpoints plus a static UI:
  GET  /api/status   what's loaded and which backends are active
  POST /api/search   retrieval only — passages + similarity scores (transparent)
  POST /api/ask      retrieve + grounded, cited answer
Ingestion is a CLI step (scripts/ingest.py), so the running service is read-only.
"""

from __future__ import annotations
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from .rag import Rag, GEN_MODEL  # noqa: E402  (after load_dotenv so env is set)

app = FastAPI(title="SourceFetch", description="Grounded Q&A over billing & coding policy")

# Build the RAG engine once. Embedder + store are cheap to hold open.
_rag = Rag()

STATIC_DIR = Path(__file__).parent / "static"


class Query(BaseModel):
    question: str
    k: int = 5


@app.get("/api/status")
def status():
    return {
        "chunks": _rag.store.count(),
        "sources": _rag.store.sources(),
        "embedder": _rag.embedder.name,
        "embedding_dim": _rag.embedder.dim,
        "generation": "anthropic" if os.getenv("ANTHROPIC_API_KEY") else "extractive",
        "model": GEN_MODEL if os.getenv("ANTHROPIC_API_KEY") else None,
    }


@app.post("/api/search")
def search(q: Query):
    return {"hits": _rag.retrieve(q.question, k=q.k)}


@app.post("/api/ask")
def ask(q: Query):
    return _rag.answer(q.question, k=q.k)


# ---- static UI ----
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
