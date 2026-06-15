"""Chunking: split a document into retrieval-sized, overlapping pieces.

RAG retrieves chunks, not whole documents, so chunk boundaries matter. We split
on paragraph boundaries first and pack paragraphs up to a target character
budget, carrying a small overlap so a fact that straddles a boundary still lands
whole in at least one chunk. Each chunk keeps its source and position so answers
can cite where they came from.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    index: int  # position of this chunk within its source document


def _split_paragraphs(text: str) -> List[str]:
    parts = re.split(r"\n\s*\n", text.strip())
    return [re.sub(r"[ \t]+", " ", p.strip()) for p in parts if p.strip()]


def chunk_document(
    text: str,
    source: str,
    target_chars: int = 900,
    overlap_chars: int = 150,
) -> List[Chunk]:
    """Pack paragraphs into ~target_chars windows with overlap_chars carryover."""
    paragraphs = _split_paragraphs(text)
    chunks: List[Chunk] = []
    buf = ""

    def flush(buffer: str):
        if not buffer.strip():
            return
        idx = len(chunks)
        chunks.append(
            Chunk(id=f"{source}::{idx}", text=buffer.strip(), source=source, index=idx)
        )

    for para in paragraphs:
        # A single oversized paragraph gets hard-split.
        if len(para) > target_chars * 1.5:
            if buf:
                flush(buf)
                buf = ""
            for i in range(0, len(para), target_chars):
                flush(para[i : i + target_chars])
            continue

        if buf and len(buf) + len(para) + 1 > target_chars:
            flush(buf)
            tail = buf[-overlap_chars:] if overlap_chars else ""
            buf = (tail + "\n" + para).strip()
        else:
            buf = (buf + "\n" + para).strip() if buf else para

    flush(buf)
    return chunks
