#!/usr/bin/env python3
"""Ingest the corpus into the vector store.

Reads every .md, .txt, and .pdf under corpus/ (override with --dir), chunks each
document, embeds the chunks with the configured backend, and rebuilds the Chroma
collection from scratch so re-running is idempotent.

    python scripts/ingest.py
    python scripts/ingest.py --dir /path/to/cms_manual_pdfs

PDF support uses pypdf, so you can drop the real CMS policy manual PDFs straight
into corpus/ and re-ingest. Switching EMBEDDINGS_BACKEND requires re-ingesting,
which this script does by recreating the collection.
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.chunking import chunk_document  # noqa: E402
from app.embeddings import get_embedder  # noqa: E402
from app.store import VectorStore  # noqa: E402


def read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(ROOT / "corpus"), help="folder of documents to ingest")
    args = ap.parse_args()

    corpus_dir = Path(args.dir)
    files = sorted(
        p for p in corpus_dir.rglob("*") if p.suffix.lower() in {".md", ".txt", ".pdf"}
    )
    if not files:
        print(f"No .md/.txt/.pdf files found in {corpus_dir}")
        sys.exit(1)

    embedder = get_embedder()
    store = VectorStore()
    store.reset()
    print(f"Embedder: {embedder.name} (dim {embedder.dim})")

    total_chunks = 0
    for f in files:
        text = read_file(f)
        chunks = chunk_document(text, source=f.name)
        if not chunks:
            print(f"  {f.name}: no text extracted, skipped")
            continue
        embeddings = embedder.embed_documents([c.text for c in chunks])
        store.add(chunks, embeddings)
        total_chunks += len(chunks)
        print(f"  {f.name}: {len(chunks)} chunks")

    print(f"\nIngested {total_chunks} chunks from {len(files)} files into collection '{store._collection_name}'.")
    print("Start the API with:  uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
